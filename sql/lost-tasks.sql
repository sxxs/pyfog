-- Clean up what FOG lost track of. Run as the database root, never as
-- pyfog's account. The default is a dry run that only lists what would
-- change:
--
--   mysql fog < lost-tasks.sql                                        (report only)
--   mysql --init-command="SET @dry_run = 0" fog < lost-tasks.sql       (clean up)
--
-- (--init-command sets session variables before the file runs; it works
-- with the mysql and the mariadb client alike, unlike SOURCE after a
-- semicolon in -e.) Knobs, set the same way, comma separated:
--   @hours         how long a task or imaging run may stay silent before
--                  it counts as lost (default 12)
--   @open_imaging  what to do with imagingLog rows that never got a finish
--                  time: 'delete' (default; nothing proves the host
--                  finished) or 'close' (the host did finish, FOG's
--                  multicast manager closed its task before it could
--                  report: the finish time becomes the host's last
--                  progress report, the host's deploy time is set, and the
--                  task log gets the Complete row the host could not write)
--
-- What counts as lost, in the order it is cleaned:
--   1. tasks still Queued, Checked In or In-Progress that were created
--      more than @hours ago and have not checked in for @hours (a Queued
--      task the host never picked up counts too, so read the report
--      before applying). They become Cancelled, with a taskLog row that
--      names this script, the way FOG's own cancel leaves a trace.
--   2. multicast sessions still active whose tasks are all finished or
--      lost; they become Cancelled with a completion time, and FOG's
--      multicast service then stops the udp-sender.
--   3. imagingLog rows without a finish time for hosts that no longer have
--      a task; see @open_imaging. A row whose task was cancelled is taken
--      whatever its age: cancelling is someone deciding the run ends here,
--      so there is nothing left to wait for, and such a row is always
--      deleted rather than closed -- the host stopped, it did not finish.
--   4. snapin jobs still pending for hosts without a task, with their
--      snapin tasks.
-- Nothing else is touched: hosts, images, groups and history stay.

SET @hours := COALESCE(@hours, 12);
SET @dry_run := COALESCE(@dry_run, 1);
SET @open_imaging := COALESCE(@open_imaging, 'delete');
SET @cutoff := NOW() - INTERVAL @hours HOUR;

DROP TEMPORARY TABLE IF EXISTS lost_tasks, lost_sessions, lost_imaging, lost_snapin_jobs;

CREATE TEMPORARY TABLE lost_tasks AS
SELECT t.taskID, t.taskHostID, h.hostName, ts.tsName AS state, tt.ttName AS type,
       t.taskCreateTime, t.taskCheckIn
FROM tasks t
LEFT JOIN hosts h ON h.hostID = t.taskHostID
LEFT JOIN taskStates ts ON ts.tsID = t.taskStateID
LEFT JOIN taskTypes tt ON tt.ttID = t.taskTypeID
WHERE t.taskStateID IN (0, 1, 2, 3)
  AND t.taskCreateTime < @cutoff
  AND t.taskCheckIn < @cutoff;          -- a never-checked-in task has the zero date

-- Tasks that stay active after step 1, per host: what "still has a task" means below.
CREATE TEMPORARY TABLE live_hosts AS
SELECT DISTINCT t.taskHostID
FROM tasks t
WHERE t.taskStateID IN (0, 1, 2, 3)
  AND t.taskID NOT IN (SELECT taskID FROM lost_tasks);

CREATE TEMPORARY TABLE lost_sessions AS
SELECT ms.msID, ms.msName, ms.msStartDateTime, ms.msPercent
FROM multicastSessions ms
WHERE ms.msState IN (0, 1, 2, 3)
  AND ms.msStartDateTime < @cutoff
  AND NOT EXISTS (SELECT 1 FROM multicastSessionsAssoc a
                  JOIN tasks t ON t.taskID = a.tID
                  WHERE a.msID = ms.msID AND t.taskStateID IN (0, 1, 2, 3)
                    AND t.taskHostID IN (SELECT taskHostID FROM live_hosts));

CREATE TEMPORARY TABLE lost_imaging AS
SELECT il.ilID, il.ilHostID, h.hostName, il.ilImageName, il.ilType, il.ilStartTime,
       lt.taskID AS lastTaskID, ts.tsName AS lastState,
       (lt.taskStateID = 4 AND NOT EXISTS (SELECT 1 FROM taskLog l
            WHERE l.taskID = lt.taskID AND l.taskStateID = 4)) AS closedByServer,
       (lt.taskStateID = 5) AS cancelled,
       GREATEST(il.ilStartTime, COALESCE(lt.taskCheckIn, il.ilStartTime)) AS finish
FROM imagingLog il
LEFT JOIN hosts h ON h.hostID = il.ilHostID
LEFT JOIN tasks lt ON lt.taskID = (
    SELECT t2.taskID FROM tasks t2
    WHERE t2.taskHostID = il.ilHostID AND t2.taskCreateTime <= il.ilStartTime
    ORDER BY t2.taskCreateTime DESC, t2.taskID DESC LIMIT 1)
LEFT JOIN taskStates ts ON ts.tsID = lt.taskStateID
WHERE il.ilFinishTime = '0000-00-00 00:00:00'
  AND (il.ilStartTime < @cutoff OR lt.taskStateID = 5)
  AND il.ilHostID NOT IN (SELECT taskHostID FROM live_hosts);

CREATE TEMPORARY TABLE lost_snapin_jobs AS
SELECT sj.sjID, sj.sjHostID, h.hostName, sj.sjCreateTime
FROM snapinJobs sj
LEFT JOIN hosts h ON h.hostID = sj.sjHostID
WHERE sj.sjStateID IN (0, 1, 2, 3)
  AND sj.sjCreateTime < @cutoff
  AND sj.sjHostID NOT IN (SELECT taskHostID FROM live_hosts);

-- The report, in every mode.
SELECT IF(@dry_run, 'DRY RUN, nothing changed', 'CLEANING UP') AS mode,
       @hours AS silent_for_hours, @open_imaging AS open_imaging;
SELECT 'task' AS what, taskID AS id, hostName AS host, CONCAT(type, ' ', state) AS detail,
       taskCreateTime AS since, taskCheckIn AS last_checkin FROM lost_tasks
UNION ALL
SELECT 'multicast session', msID, msName, CONCAT(msPercent, '%'), msStartDateTime, NULL
FROM lost_sessions
UNION ALL
SELECT 'imaging run', ilID, hostName,
       CONCAT(ilType, ' ', ilImageName,
              IF(lastTaskID IS NULL, ', no task',
                 CONCAT(', task ', lastTaskID, ' ', lastState,
                        IF(closedByServer, ' (closed by server before the host reported)', ''),
                        IF(cancelled, ' (run left open by the cancel, deleted)', '')))),
       ilStartTime, IF(@open_imaging = 'close' AND NOT cancelled, finish, NULL)
FROM lost_imaging
UNION ALL
SELECT 'snapin job', sjID, hostName, NULL, sjCreateTime, NULL FROM lost_snapin_jobs
ORDER BY what, since;

-- The cleanup; every statement is a no-op in a dry run.
INSERT INTO taskLog (taskID, taskStateID, ip, createTime, createdBy)
SELECT taskID, 5, '', NOW(), 'lost-tasks.sql' FROM lost_tasks WHERE @dry_run = 0;

UPDATE tasks SET taskStateID = 5
WHERE taskID IN (SELECT taskID FROM lost_tasks) AND @dry_run = 0;

UPDATE multicastSessions SET msState = 5, msCompleteDateTime = NOW()
WHERE msID IN (SELECT msID FROM lost_sessions) AND @dry_run = 0;

-- A cancelled run is deleted whatever @open_imaging says: closing it would
-- record a deployment that was called off, and set the host's deploy time
-- to an image it never received.
DELETE FROM imagingLog
WHERE ilID IN (SELECT ilID FROM lost_imaging WHERE @open_imaging = 'delete' OR cancelled)
  AND @dry_run = 0;

UPDATE imagingLog il JOIN lost_imaging li ON li.ilID = il.ilID
SET il.ilFinishTime = li.finish
WHERE @dry_run = 0 AND @open_imaging = 'close' AND NOT li.cancelled;

UPDATE hosts h JOIN lost_imaging li ON li.ilHostID = h.hostID
SET h.hostLastDeploy = li.finish
WHERE @dry_run = 0 AND @open_imaging = 'close' AND NOT li.cancelled
  AND li.ilType = 'down' AND h.hostLastDeploy < li.finish;

INSERT INTO taskLog (taskID, taskStateID, ip, createTime, createdBy)
SELECT lastTaskID, 4, '', finish, 'lost-tasks.sql' FROM lost_imaging
WHERE @dry_run = 0 AND @open_imaging = 'close' AND closedByServer;

UPDATE snapinTasks SET stState = 5
WHERE stJobID IN (SELECT sjID FROM lost_snapin_jobs) AND stState IN (0, 1, 2, 3) AND @dry_run = 0;

UPDATE snapinJobs SET sjStateID = 5
WHERE sjID IN (SELECT sjID FROM lost_snapin_jobs) AND @dry_run = 0;

SELECT IF(@dry_run, 'dry run: run again with SET @dry_run = 0 to apply', 'done') AS result;

DROP TEMPORARY TABLE IF EXISTS lost_tasks, live_hosts, lost_sessions, lost_imaging, lost_snapin_jobs;

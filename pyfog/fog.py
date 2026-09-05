"""The data layer: what is going on inside a FOG server, as plain dicts.

Every public method of Fog returns JSON-serialisable data (str, int,
bool, None, lists, dicts). Timestamps are "YYYY-MM-DD HH:MM:SS" strings in
the database server's local time, ages are seconds relative to the
database server's NOW(). Nothing in here prints or colours anything.

Column names follow FOG's schema (packages/web/commons/schema.php); the
class files in packages/web/lib/fog/ document which column means what.
"""

from datetime import datetime, timedelta

from . import local
from .util import dt_text, normalize_mac, parse_dt, pretty_mac, seconds_since, to_int

# taskStates.tsID; multicastSessions.msState and snapinTasks.stState use the
# same table. See lib/fog/taskstate.class.php.
QUEUED, CHECKED_IN, IN_PROGRESS, COMPLETE, CANCELLED = 1, 2, 3, 4, 5
ACTIVE_STATES = (0, QUEUED, CHECKED_IN, IN_PROGRESS)
FINISHED_STATES = (COMPLETE, CANCELLED)
ACTIVE = "(0, 1, 2, 3)"  # for use inside SQL text

# images.imageFormat, see lib/pages/imagemanagementpage.class.php
IMAGE_FORMATS = {"0": "Partclone Gzip", "1": "Partimage", "2": "Partclone Gzip split",
                 "3": "Partclone uncompressed", "4": "Partclone uncompressed split",
                 "5": "Partclone Zstd", "6": "Partclone Zstd split"}

# imagingLog.ilType, see lib/reports/imaging_log.report.php
IMAGING_KINDS = {"up": "capture", "down": "deploy"}

# taskTypes.ttID. Only these write an imagingLog row of their own
# (isDeploy() and isCapture() in lib/fog/tasktype.class.php).
IMAGING_TYPES = "(1, 2, 8, 15, 16, 17, 24)"  # for use inside SQL text
# Snapin jobs are the one kind of task whose taskCheckIn keeps moving:
# the FOG client writes it again on every contact
# (lib/client/snapinclient.class.php), so it is a last report, not a start.
SNAPIN_TYPES = (12, 13)

# A FOG client that authorizes gets hosts.hostSecTime = now + 30 minutes
# (lib/fog/fogpage.class.php), so hostSecTime - 30 min is the last
# authorization the database can prove.
TOKEN_LIFETIME = timedelta(minutes=30)

PRIMARY_MAC = ("(SELECT hmMAC FROM hostMAC WHERE hmHostID = h.hostID "
               "ORDER BY hmPrimary DESC, hmID LIMIT 1)")

TASK_SQL = """
SELECT t.taskID, t.taskName, t.taskStateID, ts.tsName AS stateName,
       t.taskTypeID, tt.ttName AS typeName,
       t.taskHostID, h.hostName, h.hostIP, """ + PRIMARY_MAC + """ AS mac,
       i.imageID, i.imageName,
       t.taskPCT, t.taskBPM, t.taskTimeElapsed, t.taskTimeRemaining,
       t.taskDataCopied, t.taskDataTotal,
       t.taskCreateTime, t.taskCreateBy, t.taskCheckIn, t.taskScheduledStartTime,
       t.taskForce, t.taskIsDebug, t.taskShutdown, t.taskWOL,
       sn.ngmMemberName AS nodeName,
       (SELECT msID FROM multicastSessionsAssoc WHERE tID = t.taskID LIMIT 1) AS msID
FROM tasks t
LEFT JOIN hosts h ON h.hostID = t.taskHostID
LEFT JOIN images i ON i.imageID = COALESCE(NULLIF(t.taskImageID, 0), h.hostImage)
LEFT JOIN taskStates ts ON ts.tsID = t.taskStateID
LEFT JOIN taskTypes tt ON tt.ttID = t.taskTypeID
LEFT JOIN nfsGroupMembers sn ON sn.ngmID = t.taskNFSMemberID
"""

SESSION_SQL = """
SELECT ms.msID, ms.msName, ms.msBasePort, ms.msSessClients, ms.msPercent, ms.msState,
       ts.tsName AS stateName, ms.msStartDateTime, ms.msCompleteDateTime,
       ms.msSenderPID, ms.msSenderNode, ms.msSenderStart, ms.msInterface,
       i.imageName, ng.ngName AS groupName,
       sn.ngmMemberName AS nodeName, sn.ngmHostname AS nodeAddress,
       (SELECT COUNT(*) FROM multicastSessionsAssoc a WHERE a.msID = ms.msID) AS inSession
FROM multicastSessions ms
LEFT JOIN images i ON i.imageID = ms.msImage
LEFT JOIN taskStates ts ON ts.tsID = ms.msState
LEFT JOIN nfsGroups ng ON ng.ngID = ms.msNFSGroupID
LEFT JOIN nfsGroupMembers sn ON sn.ngmID = ms.msSenderNode
"""


def like(term):
    return "%" + term + "%"


def host_filter(term, where, params):
    """Append a host name / IP match to a WHERE list."""
    if term:
        where.append("(h.hostName LIKE %s OR h.hostIP LIKE %s)")
        params += [like(term), like(term)]


def where_sql(where):
    return (" WHERE " + " AND ".join(where)) if where else ""


def text(value):
    """Stripped string or None, for FOG's many empty-string-means-nothing columns."""
    return (value or "").strip() or None


class Fog(object):
    """One snapshot of a FOG server. now() is fixed at first use so every
    age in one report refers to the same instant."""

    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        self._now = None
        self._utc_now = None
        self._now_source = None
        self._settings = None
        self._network = None

    # -- reference facts ----------------------------------------------------

    def now(self):
        """Reference time in the same wall clock as the stored timestamps.

        FOG writes every datetime in the time zone named by FOG_TZ_INFO
        (default UTC), through its PHP layer, regardless of the database
        server's own time zone. If the server's clock differs -- a UTC FOG
        on a database whose system zone is local time is the usual case --
        then SELECT NOW() is not the clock the rows are in, and every age
        computed against it is wrong by the offset (tasks look stale, hosts
        look silent). So the reference is UTC_TIMESTAMP() converted into
        FOG's zone, never the raw NOW()."""
        self._resolve_now()
        return self._now

    def fog_timezone(self):
        return (self.setting("FOG_TZ_INFO") or "UTC").strip() or "UTC"

    def _resolve_now(self):
        if self._now is not None:
            return
        tz = self.fog_timezone()
        row = self.db.one("SELECT UTC_TIMESTAMP() AS utc, NOW() AS db, "
                          "CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', %s) AS fog", [tz])
        self._utc_now = row["utc"]
        if tz.upper() in ("UTC", "GMT", "+00:00", "ETC/UTC", "ETC/GMT"):
            self._now, self._now_source = row["utc"], "FOG stores UTC"
        elif row["fog"] is not None:
            self._now, self._now_source = row["fog"], "FOG stores " + tz
        else:
            # CONVERT_TZ returns NULL when the named zone is not in the
            # server's mysql.time_zone_name table; the database clock is
            # then the best guess (correct when its zone matches FOG's).
            self._now = row["db"]
            self._now_source = ("database clock; FOG_TZ_INFO is %r but the MySQL "
                                "time zone tables are not loaded" % tz)

    def setting(self, key, default=None):
        """A row from globalSettings."""
        if self._settings is None:
            rows = self.db.query("SELECT settingKey, settingValue FROM globalSettings")
            self._settings = {r["settingKey"]: r["settingValue"] for r in rows}
        return self._settings.get(key, default)

    def _fog_utc_offset(self):
        """Seconds FOG's clock is ahead of UTC. Access log lines carry their
        own offset and are reduced to naive UTC; adding this puts them in
        the same wall clock as now(), whatever the database server's own
        zone is."""
        self._resolve_now()
        return int((self._now - self._utc_now).total_seconds())

    def checkin_timeout(self):
        """Seconds without check-in after which FOG re-queues a task
        (lib/fog/task.class.php enforces the 180 s floor)."""
        return max(to_int(self.setting("FOG_CHECKIN_TIMEOUT")), 180)

    # -- tasks --------------------------------------------------------------

    def _task(self, row):
        state = row["taskStateID"]
        checkin_age = seconds_since(row["taskCheckIn"], self.now())
        flags = ["multicast"] if row["msID"] else []
        flags += [flag for column, flag in (("taskForce", "forced"), ("taskIsDebug", "debug"),
                                            ("taskShutdown", "shutdown"), ("taskWOL", "wol"))
                  if row[column] == "1"]
        return {
            "id": row["taskID"],
            "name": row["taskName"],
            "type": row["typeName"],
            "type_id": row["taskTypeID"],
            "state": row["stateName"] or str(state),
            "state_id": state,
            "active": state in ACTIVE_STATES,
            "host": row["hostName"],
            "host_id": row["taskHostID"],
            "ip": row["hostIP"],
            "mac": pretty_mac(row["mac"]),
            "image": row["imageName"],
            "image_id": row["imageID"],
            "percent": row["taskPCT"],
            "copied": text(row["taskDataCopied"]),
            "total": text(row["taskDataTotal"]),
            "rate": text(row["taskBPM"]),
            "elapsed": text(row["taskTimeElapsed"]),
            "remaining": text(row["taskTimeRemaining"]),
            "node": row["nodeName"],
            "created": dt_text(row["taskCreateTime"]),
            "created_by": text(row["taskCreateBy"]),
            "scheduled": dt_text(row["taskScheduledStartTime"]),
            "last_checkin": dt_text(row["taskCheckIn"]),
            "checkin_age": checkin_age,
            # A task the host stopped reporting on; FOG will re-queue it.
            "stale": state in (CHECKED_IN, IN_PROGRESS) and checkin_age is not None
            and checkin_age > self.checkin_timeout(),
            "multicast_session": row["msID"],
            "flags": flags,
        }

    def tasks(self, states=ACTIVE_STATES, host=None, image=None, kind=None, limit=500):
        """Tasks as FOG stores them, one row per host."""
        where, params = [], []
        if states:
            where.append("t.taskStateID IN (%s)" % ",".join(["%s"] * len(states)))
            params += list(states)
        host_filter(host, where, params)
        if image:
            where.append("i.imageName LIKE %s")
            params.append(like(image))
        if kind:
            where.append("tt.ttName LIKE %s")
            params.append(like(kind))
        sql = TASK_SQL + where_sql(where) + \
            " ORDER BY t.taskStateID DESC, t.taskCreateTime DESC, t.taskID DESC LIMIT %s"
        return [self._task(r) for r in self.db.query(sql, params + [limit])]

    def task(self, task_id):
        """One task with everybody imaging alongside it."""
        row = self.db.one(TASK_SQL + " WHERE t.taskID = %s", [task_id])
        if row is None:
            return None
        task = self._task(row)
        session = None
        if task["multicast_session"]:
            session = self._session(self.db.one(
                SESSION_SQL + " WHERE ms.msID = %s", [task["multicast_session"]]))
            peers = self._participants(task["multicast_session"])
            source = "multicast session"
        else:
            # A group task is one loop over the group's hosts with the same
            # name and timestamp (lib/fog/group.class.php), so this is the batch.
            peers = [self._task(r) for r in self.db.query(
                TASK_SQL + " WHERE t.taskName = %s AND t.taskTypeID = %s "
                "AND ABS(TIMESTAMPDIFF(SECOND, t.taskCreateTime, %s)) <= 2 ORDER BY h.hostName",
                [task["name"], task["type_id"], task["created"]])]
            source = "same name and creation time"
        group = None
        if " - " in (task["name"] or ""):
            # Group tasks are named "<type> - <group name>".
            group = self.db.one(
                "SELECT groupID, groupName, (SELECT COUNT(*) FROM groupMembers "
                "WHERE gmGroupID = groupID) AS members FROM groups WHERE groupName = %s",
                [task["name"].rsplit(" - ", 1)[1].strip()])
        return {
            "task": task,
            "session": session,
            "group": {"id": group["groupID"], "name": group["groupName"],
                      "members": group["members"]} if group else None,
            "participants_source": source,
            "participants": peers,
        }

    def _participants(self, session_id):
        return [self._task(r) for r in self.db.query(
            TASK_SQL + " JOIN multicastSessionsAssoc a ON a.tID = t.taskID "
            "WHERE a.msID = %s ORDER BY h.hostName", [session_id])]

    def history(self, host=None, image=None, days=None, limit=100):
        """Finished tasks with the times FOG really recorded for them.

        Not from taskLog: FOG writes its two rows, In-Progress and
        Complete, with the *task's* creation time in both
        (taskLog() in lib/reg-task/taskingelement.class.php), so taskLog
        says that a host reported, never when, and every task read out of
        it lasts zero seconds. The times that are real are
        tasks.taskCheckIn, written once when the host takes the task, and
        the imagingLog row a deploy or capture writes itself. FOG's own
        host history page pairs the two the same way, by host and start
        time (lib/pages/hostmanagementpage.class.php).
        """
        where = ["t.taskStateID IN (%s, %s)"]
        params = list(FINISHED_STATES)
        host_filter(host, where, params)
        if image:
            where.append("i.imageName LIKE %s")
            params.append(like(image))
        if days:
            where.append("t.taskCreateTime >= DATE_SUB(NOW(), INTERVAL %s DAY)")
            params.append(days)
        sql = TASK_SQL.replace("FROM tasks t", """
            , (SELECT COUNT(*) FROM taskLog l WHERE l.taskID = t.taskID
                 AND l.taskStateID = %s) AS completeRows
            , il.ilStartTime AS imagingStart
            , NULLIF(il.ilFinishTime, '0000-00-00 00:00:00') AS finished
            FROM tasks t
            LEFT JOIN imagingLog il ON il.ilID = (
                SELECT il2.ilID FROM imagingLog il2
                WHERE il2.ilHostID = t.taskHostID
                  AND t.taskTypeID IN """ + IMAGING_TYPES + """
                  AND ABS(TIMESTAMPDIFF(SECOND, il2.ilStartTime, t.taskCheckIn)) <= 2
                ORDER BY il2.ilID DESC LIMIT 1)""")
        sql += where_sql(where) + \
            " ORDER BY COALESCE(finished, t.taskCheckIn, t.taskCreateTime) DESC LIMIT %s"
        entries = []
        for row in self.db.query(sql, [COMPLETE] + params + [limit]):
            task = self._task(row)
            started = parse_dt(row["imagingStart"])
            if started is None and row["taskTypeID"] not in SNAPIN_TYPES:
                started = parse_dt(row["taskCheckIn"])
            finished = parse_dt(row["finished"])
            task.update(
                started=dt_text(started),
                finished=dt_text(finished),
                duration=int((finished - started).total_seconds())
                if started and finished else None,
                result="ok" if task["state_id"] == COMPLETE else "cancelled",
                # Complete without the host's own completion row: the server
                # closed it (see imaging_open).
                reported=row["completeRows"] > 0,
            )
            entries.append(task)
        return entries

    def scheduled(self):
        """Delayed and cron style tasks FOG will create later."""
        rows = self.db.query("""
            SELECT st.stID, st.stName, st.stType, st.stActive,
                   IF(st.stDateTime > 0, FROM_UNIXTIME(st.stDateTime), NULL) AS stWhen,
                   st.stMinute, st.stHour, st.stDOM, st.stMonth, st.stDOW,
                   st.stIsGroup, tt.ttName, i.imageName, h.hostName, g.groupName
            FROM scheduledTasks st
            LEFT JOIN taskTypes tt ON tt.ttID = st.stTaskTypeID
            LEFT JOIN images i ON i.imageID = st.stImageID
            LEFT JOIN hosts h ON st.stIsGroup = '0' AND h.hostID = st.stGroupHostID
            LEFT JOIN groups g ON st.stIsGroup = '1' AND g.groupID = st.stGroupHostID
            ORDER BY st.stDateTime, st.stID""")
        out = []
        for row in rows:
            once, is_group = row["stType"] == "S", row["stIsGroup"] == "1"
            out.append({
                "id": row["stID"],
                "name": row["stName"],
                "type": row["ttName"],
                "kind": "once" if once else "cron",
                "active": row["stActive"] == "1",
                "when": dt_text(row["stWhen"]) if once else None,
                "cron": None if once else " ".join(
                    row[c] or "*" for c in ("stMinute", "stHour", "stDOM", "stMonth", "stDOW")),
                "target": row["groupName"] if is_group else row["hostName"],
                "target_kind": "group" if is_group else "host",
                "image": row["imageName"],
            })
        return out

    def imaging_open(self):
        """Hosts that reported the start of an imaging run but not its end.

        imagingLog is written by the host itself (lib/reg-task/taskingelement.php):
        one row when the run starts, the finish time when it ends. A row
        with no finish time and no active task is therefore not one fact
        but three different ones, and they are told apart here because
        only one of them is a problem:

          cancelled  the task was cancelled while the host was imaging.
                     A cancelled host never reports a finish, so the row
                     stays open by design -- expected debris, not a loss.
          lost       no task at all, or one the server completed before
                     the host could report: FOG lost track of a run that
                     may well still be writing to the disk.
          running    the host still has an active task; nothing to see.
        """
        rows = self.db.query("""
            SELECT il.ilID, il.ilHostID, h.hostName, h.hostIP, il.ilImageName, il.ilType,
                   il.ilStartTime, il.ilCreatedBy,
                   (SELECT COUNT(*) FROM tasks t WHERE t.taskHostID = il.ilHostID
                      AND t.taskStateID IN """ + ACTIVE + """) AS activeTasks,
                   lt.taskID AS lastTaskID, lt.taskStateID AS lastState, ts.tsName AS lastStateName,
                   tt.ttName AS lastType, lt.taskCheckIn AS lastCheckIn, lt.taskPCT AS lastPercent,
                   (SELECT COUNT(*) FROM taskLog l WHERE l.taskID = lt.taskID
                      AND l.taskStateID = %s) AS reported
            FROM imagingLog il
            LEFT JOIN hosts h ON h.hostID = il.ilHostID
            LEFT JOIN tasks lt ON lt.taskID = (
                SELECT t2.taskID FROM tasks t2
                WHERE t2.taskHostID = il.ilHostID AND t2.taskCreateTime <= il.ilStartTime
                ORDER BY t2.taskCreateTime DESC, t2.taskID DESC LIMIT 1)
            LEFT JOIN taskStates ts ON ts.tsID = lt.taskStateID
            LEFT JOIN taskTypes tt ON tt.ttID = lt.taskTypeID
            WHERE il.ilFinishTime IN ('0000-00-00 00:00:00', '')
            ORDER BY il.ilStartTime DESC""", [COMPLETE])
        return [{
            "id": r["ilID"],
            "host": r["hostName"],
            "host_id": r["ilHostID"],
            "ip": r["hostIP"],
            "image": r["ilImageName"],
            "kind": IMAGING_KINDS.get(r["ilType"], "unknown"),
            "started": dt_text(r["ilStartTime"]),
            "age": seconds_since(r["ilStartTime"], self.now()),
            "created_by": text(r["ilCreatedBy"]),
            "has_task": r["activeTasks"] > 0,
            # Cancelling a task is someone deciding this run ends here, so
            # the open row is the expected trace of that decision. Only
            # what nobody decided is reported as lost.
            "cancelled": r["activeTasks"] == 0 and r["lastState"] == CANCELLED,
            "lost": r["activeTasks"] == 0 and r["lastState"] != CANCELLED,
            # The task that was current when the run started. A Complete
            # task without the taskLog row the host writes on completion
            # was closed by the server (FOG's multicast manager does that
            # as soon as udp-sender exits) before the host could report.
            "task": None if r["lastTaskID"] is None else {
                "id": r["lastTaskID"],
                "type": r["lastType"],
                "state": r["lastStateName"] or str(r["lastState"]),
                "state_id": r["lastState"],
                "active": r["lastState"] in ACTIVE_STATES,
                "percent": r["lastPercent"],
                "last_checkin": dt_text(r["lastCheckIn"]),
                "reported": r["reported"] > 0,
                "closed_by_server": r["lastState"] == COMPLETE and r["reported"] == 0,
                "cancelled": r["lastState"] == CANCELLED,
            },
        } for r in rows]

    # -- network ------------------------------------------------------------

    def network(self, busy):
        """Interface throughput, measured once per snapshot.

        Only while hosts are imaging. The first reading in a process has
        nothing to compare against and costs a second of wall clock
        (local.throughput), which is not worth spending on a server where
        nothing is being deployed or captured; a quiet call therefore
        neither measures nor remembers, so the busy call that follows it in
        the same snapshot still takes its reading.
        """
        if not busy or self._network is not None:
            return self._network or []
        self._network = local.throughput()
        return self._network

    # -- multicast ----------------------------------------------------------

    def _session(self, row):
        """One session row.

        Neither count here is "how many hosts are receiving": the database
        does not know that, only the udpcast log does. `clients_in_session`
        is the rows in multicastSessionsAssoc, that is the tasks linked to
        the session -- queued upfront for a group deploy, added as they
        arrive for a named session hosts join from the PXE menu.
        `clients_expected` is the --min-receivers the multicast manager
        computes from them, max(linked tasks, msSessClients)
        (lib/service/multicasttask.class.php), so the sender holds for
        stragglers a named session was sized for. msClients is deliberately
        not read: it is a marker, not a count -- -2 for a named session, 0
        once one is finished (lib/service/multicastmanager.class.php), and
        left at 0 for the ordinary group deploy that owns most sessions.
        """
        return {
            "id": row["msID"],
            "name": row["msName"],
            "image": row["imageName"],
            "state": row["stateName"] or str(row["msState"]),
            "state_id": row["msState"],
            "active": row["msState"] in ACTIVE_STATES,
            "port": row["msBasePort"],
            "clients_in_session": row["inSession"],
            "clients_expected": max(row["inSession"], int(row["msSessClients"] or 0)),
            "percent": row["msPercent"],
            "started": dt_text(row["msStartDateTime"]),
            "completed": dt_text(row["msCompleteDateTime"]),
            "storage_group": row["groupName"],
            "interface": text(row["msInterface"]),
            "sender_pid": row["msSenderPID"] or None,
            "sender_node": row["nodeName"],
            "sender_address": row["nodeAddress"],
            "sender_started": dt_text(row["msSenderStart"]),
        }

    def multicast(self, include_finished=False, limit=20, participants=True):
        """Sessions with their participants and the udp-sender processes.

        FOG records the pid of the /bin/sh it starts the sender through
        (lib/service/multicasttask.class.php), so the udp-sender itself is a
        child of that pid. Both are checked, and senders nobody claims are
        reported as orphans. Every active session takes part in that
        matching, whatever the listing is limited to.
        """
        order = " ORDER BY ms.msStartDateTime DESC, ms.msID DESC"
        active = [self._session(r) for r in
                  self.db.query(SESSION_SQL + " WHERE ms.msState IN " + ACTIVE + order)]
        if include_finished:
            by_id = {s["id"]: s for s in active}
            rows = self.db.query(SESSION_SQL + order + " LIMIT %s", [limit])
            shown = [by_id.get(r["msID"]) or self._session(r) for r in rows]
        else:
            shown = active[:limit]

        procs = local.processes()
        senders = {pid: dict(local.sender_options(p["argv"]), pid=pid,
                             started=dt_text(p["started"]), ppid=p["ppid"])
                   for pid, p in procs.items() if local.is_udp_sender(p)}
        claimed = match_senders(active + [s for s in shown if not s["active"]],
                                procs, senders, local.local_names())

        log_dir = (self.setting("SERVICE_LOG_PATH") or "/opt/fog/log").rstrip("/")
        log_name = self.setting("MULTICASTLOGFILENAME") or "multicast.log"
        # A running sender is the one case where the traffic is certainly
        # the imaging: it has a file open and is pushing it at the wire.
        rates = self.network(any(s["active"] and s["senders"] for s in shown))
        for session in shown:
            session["participants"] = self._participants(session["id"]) if participants else None
            session["log"] = local.udpcast_log("%s/%s.udpcast.%s" % (log_dir, log_name, session["id"])) \
                if session["sender_local"] else None
            # FOG stores the interface it told udp-sender to send on, so
            # the rate shown under a session is that interface's, not
            # whatever else the machine happens to be doing.
            session["rate"] = next((r for r in rates if r["interface"] == session["interface"]), None) \
                if session["senders"] else None
        return {
            "sessions": shown,
            "network": rates,
            "orphan_senders": [s for pid, s in senders.items() if pid not in claimed],
            "udp_sender_path": self.settings.values.get("UDPSENDERPATH"),
        }

    # -- clients ------------------------------------------------------------

    def clients(self, log_paths=None, log_bytes=32 * 1024 * 1024):
        """When each host last talked to FOG, from the best source available."""
        hosts = self.db.query("""
            SELECT h.hostID, h.hostName, h.hostIP, h.hostSecTime, h.hostPending,
                   i.imageName, """ + PRIMARY_MAC + """ AS mac
            FROM hosts h LEFT JOIN images i ON i.imageID = h.hostImage
            ORDER BY h.hostName""")
        mac_to_host = {normalize_mac(r["hmMAC"]): r["hmHostID"]
                       for r in self.db.query("SELECT hmHostID, hmMAC FROM hostMAC")}

        paths = local.find_access_logs() if log_paths is None else log_paths
        seen, unreadable = local.client_calls(paths, log_bytes)
        offset = timedelta(seconds=self._fog_utc_offset())
        calls = {}
        for mac, entry in seen.items():
            entry["last_seen"] += offset  # naive UTC -> the database's clock
            host_id = mac_to_host.get(mac)
            if host_id and (host_id not in calls or entry["last_seen"] > calls[host_id]["last_seen"]):
                calls[host_id] = entry

        now = self.now()
        out = []
        for row in hosts:
            token = parse_dt(row["hostSecTime"])
            last_auth = token - TOKEN_LIFETIME if token else None
            call = calls.get(row["hostID"])
            best, source = last_auth, "token" if last_auth else None
            if call and (best is None or call["last_seen"] > best):
                best, source = call["last_seen"], "log"
            out.append({
                "host": row["hostName"],
                "host_id": row["hostID"],
                "ip": row["hostIP"],
                "mac": pretty_mac(row["mac"]),
                "image": row["imageName"],
                "pending": row["hostPending"] == "1",
                "last_seen": dt_text(best),
                "age": seconds_since(best, now),
                "source": source,
                "last_auth": dt_text(last_auth),
                "last_call": dt_text(call["last_seen"]) if call else None,
                "last_call_from": call["ip"] if call else None,
                "last_call_path": call["path"] if call else None,
            })
        out.sort(key=lambda e: (e["age"] is None, e["age"] or 0))
        return {"hosts": out, "logs": [p for p in paths if p not in unreadable],
                "logs_unreadable": unreadable, "now": dt_text(now), "probed": False}

    def probe(self, data, timeout=1.0):
        """Ask the hosts in a clients() result whether they are powered on.

        The one thing FOG cannot tell: its own idea of "seen" is the
        client calling in, so a machine that is up with a stopped, broken
        or never-installed FOG client is indistinguishable from one that
        is off. ARP is answered by the network stack, so it does not care
        what runs on the host.

        Asked at the address the kernel last saw the MAC at, and only at
        hosts.hostIP when the ARP cache has nothing on it -- FOG's record
        can be years out of date. The answering MAC is compared with the
        host's, so a reply from whoever holds that address today is not
        read as this host being up. Unlike everything else pyfog does this
        puts packets on the network: one ARP request per host, and only
        when asked for.
        """
        cache = local.neighbours()
        fallback = local.default_interface()
        targets, asked = [], {}
        for host in data["hosts"]:
            mac = normalize_mac(host["mac"])
            known = cache.get(mac) or {}
            ip = known.get("ip") or host["ip"] or None
            host["live"] = {"up": None, "ip": ip, "how": None,
                            "mac_seen": None, "error": None}
            if ip:
                targets.append((ip, known.get("device") or fallback))
                asked.setdefault(ip, []).append((host, mac))
        answers = local.arping(targets, timeout)
        errors = []
        for ip, (seen, error) in answers.items():
            for host, mac in asked[ip]:
                host["live"].update(how="arping", error=error,
                                    mac_seen=pretty_mac(seen) if seen else None,
                                    up=None if error else (seen == mac))
            if error and error not in errors:
                errors.append(error)
        data["probed"] = True
        data["probe_error"] = errors[0] if errors else None
        return data

    # -- deployments and images ---------------------------------------------

    def deployments(self, host=None, image=None, days=None, kind=None, limit=200):
        """imagingLog: which host captured or received which image, when."""
        where, params = [], []
        host_filter(host, where, params)
        if image:
            where.append("il.ilImageName LIKE %s")
            params.append(like(image))
        if days:
            where.append("il.ilStartTime >= DATE_SUB(NOW(), INTERVAL %s DAY)")
            params.append(days)
        if kind:
            codes = [c for c, name in IMAGING_KINDS.items() if name == kind]
            if not codes:
                raise ValueError("kind must be deploy or capture")
            where.append("il.ilType = %s")
            params.append(codes[0])
        sql = """
            SELECT il.ilID, il.ilHostID, h.hostName, h.hostIP, il.ilImageName, il.ilType,
                   il.ilStartTime, il.ilFinishTime, il.ilCreatedBy
            FROM imagingLog il LEFT JOIN hosts h ON h.hostID = il.ilHostID"""
        sql += where_sql(where) + " ORDER BY il.ilStartTime DESC, il.ilID DESC LIMIT %s"
        out = []
        for row in self.db.query(sql, params + [limit]):
            started, finished = parse_dt(row["ilStartTime"]), parse_dt(row["ilFinishTime"])
            out.append({
                "id": row["ilID"],
                "host": row["hostName"],
                "host_id": row["ilHostID"],
                "ip": row["hostIP"],
                "image": row["ilImageName"],
                "kind": IMAGING_KINDS.get(row["ilType"], "unknown"),
                "started": dt_text(started),
                "finished": dt_text(finished),
                "duration": int((finished - started).total_seconds())
                if started and finished else None,
                "created_by": text(row["ilCreatedBy"]),
            })
        return out

    def current_images(self):
        """Per host: the image assigned now versus the image last deployed."""
        rows = self.db.query("""
            SELECT h.hostID, h.hostName, h.hostIP, h.hostLastDeploy,
                   i.imageName AS assigned,
                   il.ilImageName AS deployed, il.ilStartTime, il.ilFinishTime
            FROM hosts h
            LEFT JOIN images i ON i.imageID = h.hostImage
            LEFT JOIN imagingLog il ON il.ilID = (
                SELECT ilID FROM imagingLog
                WHERE ilHostID = h.hostID AND ilType <> 'up'
                  AND ilFinishTime NOT IN ('0000-00-00 00:00:00', '')
                ORDER BY ilFinishTime DESC, ilID DESC LIMIT 1)
            ORDER BY h.hostName""")
        return [{
            "host": r["hostName"],
            "host_id": r["hostID"],
            "ip": r["hostIP"],
            "assigned": r["assigned"],
            "deployed": r["deployed"],
            "deployed_at": dt_text(r["ilFinishTime"]) or dt_text(r["hostLastDeploy"]),
            "matches": bool(r["deployed"]) and r["deployed"] == r["assigned"],
        } for r in rows]

    def images(self):
        rows = self.db.query("""
            SELECT i.imageID, i.imageName, i.imageDesc, i.imagePath, i.imageFormat,
                   i.imageEnabled, i.imageProtect, i.imageSize, i.imageServerSize,
                   i.imageLastDeploy, i.imageDateTime, i.imageCreateBy,
                   o.osName, it.imageTypeName, ipt.imagePartitionTypeName,
                   (SELECT COUNT(*) FROM hosts WHERE hostImage = i.imageID) AS hostCount,
                   (SELECT GROUP_CONCAT(ng.ngName ORDER BY iga.igaPrimary DESC, ng.ngName)
                      FROM imageGroupAssoc iga JOIN nfsGroups ng ON ng.ngID = iga.igaStorageGroupID
                     WHERE iga.igaImageID = i.imageID) AS storageGroups
            FROM images i
            LEFT JOIN os o ON o.osID = i.imageOSID
            LEFT JOIN imageTypes it ON it.imageTypeID = i.imageTypeID
            LEFT JOIN imagePartitionTypes ipt ON ipt.imagePartitionTypeID = i.imagePartitionTypeID
            ORDER BY i.imageName""")
        return [{
            "id": r["imageID"],
            "name": r["imageName"],
            "description": text(r["imageDesc"]),
            "path": r["imagePath"],
            "os": r["osName"],
            "type": r["imageTypeName"],
            "partitions": r["imagePartitionTypeName"],
            "format": IMAGE_FORMATS.get(r["imageFormat"], r["imageFormat"]),
            "enabled": r["imageEnabled"] != "0",
            "protected": bool(r["imageProtect"]),
            "size_on_server": r["imageServerSize"] or None,
            "size_on_client": (r["imageSize"] or "").strip(":") or None,
            "hosts_assigned": r["hostCount"],
            "storage_groups": r["storageGroups"].split(",") if r["storageGroups"] else [],
            "last_deploy": dt_text(r["imageLastDeploy"]),
            "created": dt_text(r["imageDateTime"]),
            "created_by": text(r["imageCreateBy"]),
        } for r in rows]

    # -- hosts, groups, snapins ---------------------------------------------

    def hosts(self, search=None):
        where, params = [], []
        if search:
            where.append("(h.hostName LIKE %s OR h.hostIP LIKE %s OR h.hostDesc LIKE %s)")
            params += [like(search)] * 3
        rows = self.db.query("""
            SELECT h.hostID, h.hostName, h.hostDesc, h.hostIP, h.hostLastDeploy,
                   h.hostPending, h.hostCreateDate, i.imageName, """ + PRIMARY_MAC + """ AS mac,
                   (SELECT GROUP_CONCAT(g.groupName ORDER BY g.groupName)
                      FROM groupMembers gm JOIN groups g ON g.groupID = gm.gmGroupID
                     WHERE gm.gmHostID = h.hostID) AS groupNames,
                   (SELECT CONCAT(tt.ttName, ' / ', ts.tsName) FROM tasks t
                      LEFT JOIN taskTypes tt ON tt.ttID = t.taskTypeID
                      LEFT JOIN taskStates ts ON ts.tsID = t.taskStateID
                     WHERE t.taskHostID = h.hostID AND t.taskStateID IN """ + ACTIVE + """
                     ORDER BY t.taskID DESC LIMIT 1) AS activeTask
            FROM hosts h LEFT JOIN images i ON i.imageID = h.hostImage
            """ + where_sql(where) + " ORDER BY h.hostName", params)
        return [{
            "id": r["hostID"],
            "name": r["hostName"],
            "description": text(r["hostDesc"]),
            "ip": r["hostIP"],
            "mac": pretty_mac(r["mac"]),
            "image": r["imageName"],
            "groups": r["groupNames"].split(",") if r["groupNames"] else [],
            "active_task": r["activeTask"],
            "last_deploy": dt_text(r["hostLastDeploy"]),
            "pending": r["hostPending"] == "1",
            "created": dt_text(r["hostCreateDate"]),
        } for r in rows]

    def groups(self):
        rows = self.db.query("""
            SELECT g.groupID, g.groupName, g.groupDesc, g.groupCreateBy,
                   (SELECT GROUP_CONCAT(h.hostName ORDER BY h.hostName)
                      FROM groupMembers gm JOIN hosts h ON h.hostID = gm.gmHostID
                     WHERE gm.gmGroupID = g.groupID) AS members
            FROM groups g ORDER BY g.groupName""")
        return [{
            "id": r["groupID"],
            "name": r["groupName"],
            "description": text(r["groupDesc"]),
            "created_by": text(r["groupCreateBy"]),
            "members": r["members"].split(",") if r["members"] else [],
        } for r in rows]

    def snapins(self, host=None, snapin=None, failed_only=False, days=None, limit=200):
        """Snapin runs per host with their exit codes (snapinTasks)."""
        where, params = [], []
        host_filter(host, where, params)
        if snapin:
            where.append("s.sName LIKE %s")
            params.append(like(snapin))
        if failed_only:
            where.append("(st.stReturnCode <> 0 OR st.stState = %s)")
            params.append(CANCELLED)
        if days:
            where.append("sj.sjCreateTime >= DATE_SUB(NOW(), INTERVAL %s DAY)")
            params.append(days)
        sql = """
            SELECT st.stID, st.stJobID, st.stState, ts.tsName AS stateName,
                   st.stCheckinDate, st.stCompleteDate, st.stReturnCode, st.stReturnDetails,
                   s.sName, sj.sjHostID, h.hostName, h.hostIP, sj.sjCreateTime
            FROM snapinTasks st
            JOIN snapinJobs sj ON sj.sjID = st.stJobID
            LEFT JOIN snapins s ON s.sID = st.stSnapinID
            LEFT JOIN hosts h ON h.hostID = sj.sjHostID
            LEFT JOIN taskStates ts ON ts.tsID = st.stState"""
        sql += where_sql(where) + """
            ORDER BY COALESCE(NULLIF(st.stCompleteDate, '0000-00-00 00:00:00'),
                              st.stCheckinDate, sj.sjCreateTime) DESC, st.stID DESC LIMIT %s"""
        out = []
        for r in self.db.query(sql, params + [limit]):
            state, code = r["stState"], r["stReturnCode"]
            result = {COMPLETE: "ok" if code == 0 else "failed",
                      CANCELLED: "cancelled"}.get(state, "pending")
            out.append({
                "id": r["stID"],
                "job_id": r["stJobID"],
                "host": r["hostName"],
                "host_id": r["sjHostID"],
                "ip": r["hostIP"],
                "snapin": r["sName"],
                "state": r["stateName"] or str(state),
                "result": result,
                "return_code": code if state == COMPLETE else None,
                "details": text(r["stReturnDetails"]),
                "queued": dt_text(r["sjCreateTime"]),
                "checked_in": dt_text(r["stCheckinDate"]),
                "completed": dt_text(r["stCompleteDate"]),
            })
        return out

    # -- overview -----------------------------------------------------------

    def info(self):
        count = lambda sql: self.db.scalar(sql)
        nodes = self.db.query("""
            SELECT ngm.ngmMemberName, ngm.ngmHostname, ngm.ngmIsMasterNode, ngm.ngmIsEnabled,
                   ngm.ngmInterface, ngm.ngmMaxClients, ng.ngName
            FROM nfsGroupMembers ngm LEFT JOIN nfsGroups ng ON ng.ngID = ngm.ngmGroupID
            ORDER BY ng.ngName, ngm.ngmIsMasterNode DESC, ngm.ngmMemberName""")
        values = self.settings.values
        return {
            "fog_version": self.settings.fog_version(),
            "schema_version": self.db.scalar("SELECT MAX(vValue) FROM schemaVersion"),
            "config_source": self.settings.source,
            "database": "%s@%s/%s" % (values["DATABASE_USERNAME"], values["DATABASE_HOST"],
                                      values["DATABASE_NAME"]),
            "server_time": dt_text(self.now()),
            "clock": self.clock_diagnosis(),
            "checkin_timeout": self.checkin_timeout(),
            "client": self.client_settings(),
            "udp_sender": values.get("UDPSENDERPATH"),
            "multicast_port_base": to_int(self.setting("FOG_UDPCAST_STARTINGPORT")),
            "counts": {
                "hosts": count("SELECT COUNT(*) FROM hosts"),
                "hosts_pending": count("SELECT COUNT(*) FROM hosts WHERE hostPending = '1'"),
                "images": count("SELECT COUNT(*) FROM images"),
                "groups": count("SELECT COUNT(*) FROM groups"),
                "snapins": count("SELECT COUNT(*) FROM snapins"),
                "tasks_active": count("SELECT COUNT(*) FROM tasks WHERE taskStateID IN " + ACTIVE),
                "tasks_total": count("SELECT COUNT(*) FROM tasks"),
                "multicast_active": count(
                    "SELECT COUNT(*) FROM multicastSessions WHERE msState IN " + ACTIVE),
            },
            "storage_nodes": [{
                "name": n["ngmMemberName"],
                "address": n["ngmHostname"],
                "group": n["ngName"],
                "master": n["ngmIsMasterNode"] == "1",
                "enabled": n["ngmIsEnabled"] == "1",
                "interface": n["ngmInterface"],
                "max_clients": n["ngmMaxClients"],
            } for n in nodes],
        }

    def clock_diagnosis(self):
        """How the reference clock relates to the database server's own, so
        pyfog can say when a time zone mismatch would skew every age."""
        self._resolve_now()
        db_now = self.db.scalar("SELECT NOW()")
        skew = int((db_now - self._now).total_seconds())
        return {
            "reference": dt_text(self._now),
            "source": self._now_source,
            "db_now": dt_text(db_now),
            "db_skew": skew,
            "fog_timezone": self.fog_timezone(),
        }

    def client_settings(self):
        """What the FOG client (the Windows/Linux service) is told, and what
        it does with it. Both values are global: FOG keeps no per-host or
        per-group check-in or grace time.

        lib/fog/fogpage.class.php requestClientInfo() answers the client's
        configure call with sleep = FOG_CLIENT_CHECKIN_TIME + a random
        offset (mt_rand(1, 91) as FOG ships it) and promptTime =
        FOG_GRACE_TIMEOUT. fog-client 0.13 (Service/FOGSystemService.cs,
        Zazzles/AbstractService.cs) accepts a sleep of 30..7200 s and a
        prompt of 60..600 s; anything else is logged as invalid and replaced
        by 60 s.

        The offset is a literal in FOG's source, so it is read from the web
        root (Settings.client_jitter); patches/fog-client-checkin-jitter.patch
        narrows it, and the answer says which of the two it is.
        """
        checkin = to_int(self.setting("FOG_CLIENT_CHECKIN_TIME"))
        grace = to_int(self.setting("FOG_GRACE_TIMEOUT"))
        sleep_accepted, grace_accepted = (30, 7200), (60, 600)
        jitter = self.settings.client_jitter()
        low, high = jitter if jitter else (1, 91)
        sent = (checkin + low, checkin + high)
        return {
            "checkin_time": checkin,
            "jitter": (low, high),
            "jitter_source": "web root" if jitter else "FOG 1.5.10 default, web root not read",
            "sleep_sent": sent,
            "sleep_accepted": sleep_accepted,
            "sleep_effective": tuple(s if sleep_accepted[0] <= s <= sleep_accepted[1] else 60
                                     for s in sent),
            "grace_timeout": grace,
            "grace_accepted": grace_accepted,
            "grace_effective": grace if grace_accepted[0] <= grace <= grace_accepted[1] else 60,
            "force_reboot": self.setting("FOG_TASK_FORCE_REBOOT") == "1",
            "per_host_or_group": False,
        }

    # -- dashboard ----------------------------------------------------------

    def dashboard(self, recent=8):
        """Everything one screen of live state needs, in one dict.

        Active tasks (folded per multicast session), imaging runs without
        a task, the active multicast sessions with their sender processes,
        the last few finished tasks and the pending scheduled tasks. The
        access log is deliberately not read here: parsing it every few
        seconds would cost more than it tells.
        """
        tasks = self.tasks()
        states, stale = {}, 0
        for task in tasks:
            states[task["state"]] = states.get(task["state"], 0) + 1
            stale += task["stale"]
        multicast = self.multicast(participants=False)
        return {
            "now": dt_text(self.now()),
            "timeout": self.checkin_timeout(),
            "count": len(tasks),
            "states": states,
            "stale": stale,
            "entries": group_multicast(tasks),
            "imaging_open": self.imaging_open(),
            "sessions": multicast["sessions"],
            "orphan_senders": multicast["orphan_senders"],
            "network": self.network(imaging_now(tasks)),
            "recent": group_multicast(self.history(limit=recent)),
            "scheduled": [s for s in self.scheduled() if s["active"]],
        }


def imaging_now(tasks):
    """Is a host actually moving an image right now?

    Checked-in counts: a multicast task never advances past it (the
    session, not the task, carries the progress), so waiting for
    In-Progress would miss every multicast deploy there is.
    """
    return any(t["state_id"] in (CHECKED_IN, IN_PROGRESS) for t in tasks)


def match_senders(sessions, procs, senders, here):
    """Attach process facts to each session; returns the sender pids some
    active session claims.

    Only a session whose sender runs on this machine (or has no node yet)
    can be checked: a session on another storage node gets no process
    facts, so a local sender on the same port stays unclaimed. Finished
    sessions do not claim either, or an old row with a reused port would
    hide a sender that really is orphaned.
    """
    claimed = set()
    for session in sessions:
        pid = session["sender_pid"]
        session["sender_local"] = (session["sender_address"] or "").lower() in here \
            or session["sender_node"] is None
        session["wrapper_alive"] = pid in procs if session["sender_local"] and pid else None
        session["senders"] = []
        if session["sender_local"] and session["active"]:
            session["senders"] = [s for s in senders.values()
                                  if s.get("portbase") == session["port"]
                                  or (pid and s["pid"] in local.descendants(procs, pid))]
            claimed.update(s["pid"] for s in session["senders"])
    return claimed


def group_multicast(tasks):
    """Fold the per-host rows of a multicast session into one entry.

    FOG queues one task per participating host; for a person one multicast
    deploy is one event. Returns entries in the input order, each either a
    task dict or {"session": id, ..., "tasks": [task, ...]}.
    """
    entries, sessions = [], {}
    for task in tasks:
        session_id = task["multicast_session"]
        if not session_id:
            entries.append(task)
            continue
        if session_id not in sessions:
            sessions[session_id] = {
                "session": session_id,
                "name": task["name"].rsplit(" - ", 1)[-1] if task["name"] else None,
                "type": task["type"],
                "image": task["image"],
                "created": task["created"],
                "tasks": [],
                "states": {},
            }
            entries.append(sessions[session_id])
        entry = sessions[session_id]
        entry["tasks"].append(task)
        entry["states"][task["state"]] = entry["states"].get(task["state"], 0) + 1
        entry["created"] = min(entry["created"], task["created"] or entry["created"])
    for entry in sessions.values():
        started = [t["percent"] for t in entry["tasks"] if t["percent"]]
        entry["percent_min"] = min(started) if started else None
        entry["percent_max"] = max(started) if started else None
        entry["stale"] = any(t["stale"] for t in entry["tasks"])
    return entries

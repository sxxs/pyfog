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

# images.imageFormat, see lib/pages/imagemanagementpage.class.php
IMAGE_FORMATS = {"0": "Partclone Gzip", "1": "Partimage", "2": "Partclone Gzip split",
                 "3": "Partclone uncompressed", "4": "Partclone uncompressed split",
                 "5": "Partclone Zstd", "6": "Partclone Zstd split"}

# imagingLog.ilType, see lib/reports/imaging_log.report.php
IMAGING_KINDS = {"up": "capture", "down": "deploy"}

# A FOG client that authorizes gets hosts.hostSecTime = now + 30 minutes
# (lib/fog/fogpage.class.php), so hostSecTime - 30 min is the last
# authorization the database can prove.
TOKEN_LIFETIME = timedelta(minutes=30)

PRIMARY_MAC = ("(SELECT hmMAC FROM hostMAC WHERE hmHostID = h.hostID "
               "ORDER BY hmPrimary DESC, hmID LIMIT 1)")

TASK_SQL = """
SELECT t.taskID, t.taskName, t.taskStateID, ts.tsName AS stateName,
       t.taskTypeID, tt.ttName AS typeName,
       t.taskHostID, h.hostName, h.hostIP, %s AS mac,
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
""" % PRIMARY_MAC

SESSION_SQL = """
SELECT ms.msID, ms.msName, ms.msBasePort, ms.msClients, ms.msPercent, ms.msState,
       ts.tsName AS stateName, ms.msStartDateTime, ms.msCompleteDateTime,
       ms.msSenderPID, ms.msSenderNode, ms.msSenderStart, ms.msInterface,
       i.imageName, ng.ngName AS groupName,
       sn.ngmMemberName AS nodeName, sn.ngmHostname AS nodeAddress,
       (SELECT COUNT(*) FROM multicastSessionsAssoc a WHERE a.msID = ms.msID) AS joined
FROM multicastSessions ms
LEFT JOIN images i ON i.imageID = ms.msImage
LEFT JOIN taskStates ts ON ts.tsID = ms.msState
LEFT JOIN nfsGroups ng ON ng.ngID = ms.msNFSGroupID
LEFT JOIN nfsGroupMembers sn ON sn.ngmID = ms.msSenderNode
"""


def _like(term):
    return "%" + term + "%"


class Fog(object):
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings

    # -- reference facts ----------------------------------------------------

    def now(self):
        return self.db.now()

    def checkin_timeout(self):
        """Seconds without check-in after which FOG re-queues a task
        (lib/fog/task.class.php enforces the 180 s floor)."""
        return max(to_int(self.db.setting("FOG_CHECKIN_TIMEOUT")), 180)

    # -- tasks --------------------------------------------------------------

    def _task(self, row):
        now = self.now()
        state = to_int(row["taskStateID"])
        checkin_age = seconds_since(row["taskCheckIn"], now)
        flags = []
        if to_int(row["msID"]):
            flags.append("multicast")
        for column, flag in (("taskForce", "forced"), ("taskIsDebug", "debug"),
                             ("taskShutdown", "shutdown"), ("taskWOL", "wol")):
            if row[column] == "1":
                flags.append(flag)
        return {
            "id": to_int(row["taskID"]),
            "name": row["taskName"],
            "type": row["typeName"],
            "type_id": to_int(row["taskTypeID"]),
            "state": row["stateName"] or str(state),
            "state_id": state,
            "active": state in ACTIVE_STATES,
            "host": row["hostName"],
            "host_id": to_int(row["taskHostID"]),
            "ip": row["hostIP"],
            "mac": pretty_mac(row["mac"]),
            "image": row["imageName"],
            "image_id": to_int(row["imageID"]) or None,
            "percent": to_int(row["taskPCT"]),
            "copied": (row["taskDataCopied"] or "").strip() or None,
            "total": (row["taskDataTotal"] or "").strip() or None,
            "rate": (row["taskBPM"] or "").strip() or None,
            "elapsed": (row["taskTimeElapsed"] or "").strip() or None,
            "remaining": (row["taskTimeRemaining"] or "").strip() or None,
            "node": row["nodeName"],
            "created": dt_text(row["taskCreateTime"]),
            "created_by": row["taskCreateBy"] or None,
            "scheduled": dt_text(row["taskScheduledStartTime"]),
            "last_checkin": dt_text(row["taskCheckIn"]),
            "checkin_age": checkin_age,
            # A task the host stopped reporting on; FOG will re-queue it.
            "stale": state in (CHECKED_IN, IN_PROGRESS) and checkin_age is not None
            and checkin_age > self.checkin_timeout(),
            "multicast_session": to_int(row["msID"]) or None,
            "flags": flags,
        }

    def tasks(self, states=ACTIVE_STATES, host=None, image=None, kind=None, limit=500):
        """Tasks as FOG stores them, one row per host."""
        where, params = [], []
        if states:
            where.append("t.taskStateID IN (%s)" % ",".join("?" * len(states)))
            params.extend(states)
        if host:
            where.append("(h.hostName LIKE ? OR h.hostIP LIKE ?)")
            params += [_like(host), _like(host)]
        if image:
            where.append("i.imageName LIKE ?")
            params.append(_like(image))
        if kind:
            where.append("tt.ttName LIKE ?")
            params.append(_like(kind))
        sql = TASK_SQL + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY t.taskStateID DESC, t.taskCreateTime DESC, t.taskID DESC LIMIT %d" % limit
        return [self._task(r) for r in self.db.query(sql, params)]

    def task(self, task_id):
        """One task with everybody imaging alongside it."""
        row = self.db.one(TASK_SQL + " WHERE t.taskID = ?", [task_id])
        if row is None:
            return None
        task = self._task(row)
        session = None
        if task["multicast_session"]:
            session = self._session(self.db.one(
                SESSION_SQL + " WHERE ms.msID = ?", [task["multicast_session"]]))
            peers = self.db.query(
                TASK_SQL + " JOIN multicastSessionsAssoc a ON a.tID = t.taskID "
                "WHERE a.msID = ? ORDER BY h.hostName", [task["multicast_session"]])
            source = "multicast session"
        else:
            # A group task is one loop over the group's hosts with the same
            # name and timestamp (lib/fog/group.class.php), so this is the batch.
            peers = self.db.query(
                TASK_SQL + " WHERE t.taskName = ? AND t.taskTypeID = ? "
                "AND ABS(TIMESTAMPDIFF(SECOND, t.taskCreateTime, ?)) <= 2 ORDER BY h.hostName",
                [task["name"], task["type_id"], task["created"]])
            source = "same name and creation time"
        group = None
        if " - " in (task["name"] or ""):
            # Group tasks are named "<type> - <group name>".
            group = self.db.one(
                "SELECT groupID, groupName, (SELECT COUNT(*) FROM groupMembers "
                "WHERE gmGroupID = groupID) AS members FROM groups WHERE groupName = ?",
                [task["name"].rsplit(" - ", 1)[1].strip()])
        return {
            "task": task,
            "session": session,
            "group": {"id": to_int(group["groupID"]), "name": group["groupName"],
                      "members": to_int(group["members"])} if group else None,
            "participants_source": source,
            "participants": [self._task(p) for p in peers],
        }

    def history(self, host=None, image=None, days=None, limit=100):
        """Finished tasks with the times taskLog recorded for them."""
        where = ["t.taskStateID IN (%s)" % ",".join("?" * len(FINISHED_STATES))]
        params = list(FINISHED_STATES)
        if host:
            where.append("(h.hostName LIKE ? OR h.hostIP LIKE ?)")
            params += [_like(host), _like(host)]
        if image:
            where.append("i.imageName LIKE ?")
            params.append(_like(image))
        if days:
            where.append("t.taskCreateTime >= DATE_SUB(NOW(), INTERVAL ? DAY)")
            params.append(days)
        sql = TASK_SQL.replace(
            "FROM tasks t",
            ", (SELECT MIN(createTime) FROM taskLog WHERE taskID = t.taskID "
            "   AND taskStateID = %d) AS started,"
            " (SELECT MAX(createTime) FROM taskLog WHERE taskID = t.taskID "
            "   AND taskStateID = %d) AS finished FROM tasks t" % (IN_PROGRESS, COMPLETE))
        sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(finished, t.taskCheckIn, t.taskCreateTime) DESC LIMIT %d" % limit
        entries = []
        for row in self.db.query(sql, params):
            task = self._task(row)
            started, finished = parse_dt(row["started"]), parse_dt(row["finished"])
            task.update(
                started=dt_text(started),
                finished=dt_text(finished),
                duration=int((finished - started).total_seconds())
                if started and finished else None,
                result="ok" if task["state_id"] == COMPLETE else "cancelled",
            )
            entries.append(task)
        return entries

    def scheduled(self):
        """Delayed and cron style tasks FOG will create later."""
        rows = self.db.query("""
            SELECT st.stID, st.stName, st.stType, st.stActive, st.stDateTime,
                   st.stMinute, st.stHour, st.stDOM, st.stMonth, st.stDOW,
                   st.stIsGroup, st.stGroupHostID, tt.ttName, i.imageName,
                   h.hostName, g.groupName
            FROM scheduledTasks st
            LEFT JOIN taskTypes tt ON tt.ttID = st.stTaskTypeID
            LEFT JOIN images i ON i.imageID = st.stImageID
            LEFT JOIN hosts h ON st.stIsGroup = '0' AND h.hostID = st.stGroupHostID
            LEFT JOIN groups g ON st.stIsGroup = '1' AND g.groupID = st.stGroupHostID
            ORDER BY st.stDateTime, st.stID""")
        out = []
        for row in rows:
            once = row["stType"] == "S"
            out.append({
                "id": to_int(row["stID"]),
                "name": row["stName"],
                "type": row["ttName"],
                "kind": "once" if once else "cron",
                "active": row["stActive"] == "1",
                "when": dt_text(datetime.fromtimestamp(to_int(row["stDateTime"])))
                if once and to_int(row["stDateTime"]) else None,
                "cron": None if once else " ".join(
                    row[c] or "*" for c in ("stMinute", "stHour", "stDOM", "stMonth", "stDOW")),
                "target": row["groupName"] if row["stIsGroup"] == "1" else row["hostName"],
                "target_kind": "group" if row["stIsGroup"] == "1" else "host",
                "image": row["imageName"],
            })
        return out

    def imaging_open(self):
        """Hosts that reported the start of an imaging run but not its end.

        imagingLog is written by the host itself (lib/reg-task/taskingelement.php),
        so a row here with no active task is a host still imaging after FOG
        lost track of it.
        """
        rows = self.db.query("""
            SELECT il.ilID, il.ilHostID, h.hostName, h.hostIP, il.ilImageName, il.ilType,
                   il.ilStartTime, il.ilCreatedBy,
                   (SELECT COUNT(*) FROM tasks t WHERE t.taskHostID = il.ilHostID
                      AND t.taskStateID IN (%s)) AS activeTasks
            FROM imagingLog il
            LEFT JOIN hosts h ON h.hostID = il.ilHostID
            WHERE il.ilFinishTime IN ('0000-00-00 00:00:00', '')
            ORDER BY il.ilStartTime DESC""" % ",".join(str(s) for s in ACTIVE_STATES))
        return [{
            "id": to_int(r["ilID"]),
            "host": r["hostName"],
            "host_id": to_int(r["ilHostID"]),
            "ip": r["hostIP"],
            "image": r["ilImageName"],
            "kind": IMAGING_KINDS.get(r["ilType"], "unknown"),
            "started": dt_text(r["ilStartTime"]),
            "age": seconds_since(r["ilStartTime"], self.now()),
            "created_by": r["ilCreatedBy"] or None,
            "has_task": to_int(r["activeTasks"]) > 0,
        } for r in rows]

    # -- multicast ----------------------------------------------------------

    def _session(self, row):
        return {
            "id": to_int(row["msID"]),
            "name": row["msName"],
            "image": row["imageName"],
            "state": row["stateName"] or row["msState"],
            "state_id": to_int(row["msState"]),
            "active": to_int(row["msState"]) in ACTIVE_STATES,
            "port": to_int(row["msBasePort"]),
            "clients_expected": to_int(row["msClients"]),
            "clients_joined": to_int(row["joined"]),
            "percent": to_int(row["msPercent"]),
            "started": dt_text(row["msStartDateTime"]),
            "completed": dt_text(row["msCompleteDateTime"]),
            "storage_group": row["groupName"],
            "interface": row["msInterface"] or None,
            "sender_pid": to_int(row["msSenderPID"]) or None,
            "sender_node": row["nodeName"],
            "sender_address": row["nodeAddress"],
            "sender_started": dt_text(row["msSenderStart"]),
        }

    def multicast(self, include_finished=False, limit=20):
        """Sessions with their participants and the udp-sender processes.

        FOG records the pid of the /bin/sh it starts the sender through
        (lib/service/multicasttask.class.php), so the udp-sender itself is a
        child of that pid. Both are checked, and senders nobody claims are
        reported as orphans.
        """
        sql = SESSION_SQL
        if not include_finished:
            sql += " WHERE ms.msState IN (%s)" % ",".join(str(s) for s in ACTIVE_STATES)
        sql += " ORDER BY ms.msStartDateTime DESC, ms.msID DESC LIMIT %d" % limit
        sessions = [self._session(r) for r in self.db.query(sql)]

        procs = local.processes()
        senders = {pid: dict(local.sender_options(p["argv"]), pid=pid,
                             started=dt_text(p["started"]), ppid=p["ppid"])
                   for pid, p in procs.items() if local.is_udp_sender(p)}
        here = local.local_names()
        log_dir = (self.db.setting("SERVICE_LOG_PATH") or "/opt/fog/log").rstrip("/")
        log_name = self.db.setting("MULTICASTLOGFILENAME") or "multicast.log"

        claimed = set()
        for session in sessions:
            session["participants"] = [self._task(r) for r in self.db.query(
                TASK_SQL + " JOIN multicastSessionsAssoc a ON a.tID = t.taskID "
                "WHERE a.msID = ? ORDER BY h.hostName", [session["id"]])]
            session["sender_local"] = (session["sender_address"] or "").lower() in here \
                or session["sender_node"] is None
            pid = session["sender_pid"]
            session["wrapper_alive"] = pid in procs if session["sender_local"] and pid else None
            mine = [s for s in senders.values()
                    if s.get("portbase") == session["port"]
                    or (pid and s["pid"] in local.descendants(procs, pid))]
            claimed.update(s["pid"] for s in mine)
            session["senders"] = mine
            session["log"] = local.udpcast_log("%s/%s.udpcast.%s"
                                               % (log_dir, log_name, session["id"]))
        return {
            "sessions": sessions,
            "orphan_senders": [s for pid, s in senders.items() if pid not in claimed],
            "udp_sender_path": self.settings.values.get("UDPSENDERPATH"),
        }

    # -- clients ------------------------------------------------------------

    def clients(self, log_paths=None, log_bytes=32 * 1024 * 1024):
        """When each host last talked to FOG, from the best source available."""
        hosts = self.db.query("""
            SELECT h.hostID, h.hostName, h.hostIP, h.hostSecTime, h.hostPending,
                   i.imageName, %s AS mac
            FROM hosts h LEFT JOIN images i ON i.imageID = h.hostImage
            ORDER BY h.hostName""" % PRIMARY_MAC)
        mac_to_host = {}
        for row in self.db.query("SELECT hmHostID, hmMAC FROM hostMAC"):
            mac_to_host[normalize_mac(row["hmMAC"])] = to_int(row["hmHostID"])

        paths = local.find_access_logs() if log_paths is None else log_paths
        calls = {}
        for mac, entry in local.client_calls(paths, log_bytes).items():
            host_id = mac_to_host.get(mac)
            if host_id and (host_id not in calls or entry["last_seen"] > calls[host_id]["last_seen"]):
                calls[host_id] = entry

        now = self.now()
        out = []
        for row in hosts:
            host_id = to_int(row["hostID"])
            token = parse_dt(row["hostSecTime"])
            last_auth = token - TOKEN_LIFETIME if token else None
            call = calls.get(host_id)
            best, source = last_auth, "token" if last_auth else None
            if call and (best is None or call["last_seen"] > best):
                best, source = call["last_seen"], "log"
            out.append({
                "host": row["hostName"],
                "host_id": host_id,
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
        return {"hosts": out, "logs": paths, "now": dt_text(now)}

    # -- deployments and images ---------------------------------------------

    def deployments(self, host=None, image=None, days=None, kind=None, limit=200):
        """imagingLog: which host captured or received which image, when."""
        where, params = [], []
        if host:
            where.append("(h.hostName LIKE ? OR h.hostIP LIKE ?)")
            params += [_like(host), _like(host)]
        if image:
            where.append("il.ilImageName LIKE ?")
            params.append(_like(image))
        if days:
            where.append("il.ilStartTime >= DATE_SUB(NOW(), INTERVAL ? DAY)")
            params.append(days)
        if kind:
            codes = [c for c, name in IMAGING_KINDS.items() if name == kind]
            if not codes:
                raise ValueError("kind must be deploy or capture")
            where.append("il.ilType = ?")
            params.append(codes[0])
        sql = """
            SELECT il.ilID, il.ilHostID, h.hostName, h.hostIP, il.ilImageName, il.ilType,
                   il.ilStartTime, il.ilFinishTime, il.ilCreatedBy
            FROM imagingLog il LEFT JOIN hosts h ON h.hostID = il.ilHostID"""
        sql += (" WHERE " + " AND ".join(where)) if where else ""
        sql += " ORDER BY il.ilStartTime DESC, il.ilID DESC LIMIT %d" % limit
        out = []
        for row in self.db.query(sql, params):
            started, finished = parse_dt(row["ilStartTime"]), parse_dt(row["ilFinishTime"])
            out.append({
                "id": to_int(row["ilID"]),
                "host": row["hostName"],
                "host_id": to_int(row["ilHostID"]),
                "ip": row["hostIP"],
                "image": row["ilImageName"],
                "kind": IMAGING_KINDS.get(row["ilType"], "unknown"),
                "started": dt_text(started),
                "finished": dt_text(finished),
                "duration": int((finished - started).total_seconds())
                if started and finished else None,
                "created_by": row["ilCreatedBy"] or None,
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
            "host_id": to_int(r["hostID"]),
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
            "id": to_int(r["imageID"]),
            "name": r["imageName"],
            "description": r["imageDesc"] or None,
            "path": r["imagePath"],
            "os": r["osName"],
            "type": r["imageTypeName"],
            "partitions": r["imagePartitionTypeName"],
            "format": IMAGE_FORMATS.get(r["imageFormat"], r["imageFormat"]),
            "enabled": r["imageEnabled"] != "0",
            "protected": to_int(r["imageProtect"]) > 0,
            "size_on_server": to_int(r["imageServerSize"]) or None,
            "size_on_client": (r["imageSize"] or "").strip(":") or None,
            "hosts_assigned": to_int(r["hostCount"]),
            "storage_groups": (r["storageGroups"] or "").split(",") if r["storageGroups"] else [],
            "last_deploy": dt_text(r["imageLastDeploy"]),
            "created": dt_text(r["imageDateTime"]),
            "created_by": r["imageCreateBy"] or None,
        } for r in rows]

    # -- hosts, groups, snapins ---------------------------------------------

    def hosts(self, search=None):
        where, params = "", []
        if search:
            where = " WHERE h.hostName LIKE ? OR h.hostIP LIKE ? OR h.hostDesc LIKE ?"
            params = [_like(search)] * 3
        rows = self.db.query("""
            SELECT h.hostID, h.hostName, h.hostDesc, h.hostIP, h.hostLastDeploy,
                   h.hostPending, h.hostCreateDate, i.imageName, %s AS mac,
                   (SELECT GROUP_CONCAT(g.groupName ORDER BY g.groupName)
                      FROM groupMembers gm JOIN groups g ON g.groupID = gm.gmGroupID
                     WHERE gm.gmHostID = h.hostID) AS groupNames,
                   (SELECT CONCAT(tt.ttName, ' / ', ts.tsName) FROM tasks t
                      LEFT JOIN taskTypes tt ON tt.ttID = t.taskTypeID
                      LEFT JOIN taskStates ts ON ts.tsID = t.taskStateID
                     WHERE t.taskHostID = h.hostID AND t.taskStateID IN (%s)
                     ORDER BY t.taskID DESC LIMIT 1) AS activeTask
            FROM hosts h LEFT JOIN images i ON i.imageID = h.hostImage
            %s ORDER BY h.hostName""" % (PRIMARY_MAC, ",".join(str(s) for s in ACTIVE_STATES), where),
            params)
        return [{
            "id": to_int(r["hostID"]),
            "name": r["hostName"],
            "description": r["hostDesc"] or None,
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
            "id": to_int(r["groupID"]),
            "name": r["groupName"],
            "description": r["groupDesc"] or None,
            "created_by": r["groupCreateBy"] or None,
            "members": r["members"].split(",") if r["members"] else [],
        } for r in rows]

    def snapins(self, host=None, snapin=None, failed_only=False, days=None, limit=200):
        """Snapin runs per host with their exit codes (snapinTasks)."""
        where, params = [], []
        if host:
            where.append("(h.hostName LIKE ? OR h.hostIP LIKE ?)")
            params += [_like(host), _like(host)]
        if snapin:
            where.append("s.sName LIKE ?")
            params.append(_like(snapin))
        if failed_only:
            where.append("(st.stReturnCode <> 0 OR st.stState = %d)" % CANCELLED)
        if days:
            where.append("sj.sjCreateTime >= DATE_SUB(NOW(), INTERVAL ? DAY)")
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
        sql += (" WHERE " + " AND ".join(where)) if where else ""
        sql += (" ORDER BY COALESCE(NULLIF(st.stCompleteDate, '0000-00-00 00:00:00'),"
                " st.stCheckinDate, sj.sjCreateTime) DESC, st.stID DESC LIMIT %d" % limit)
        out = []
        for r in self.db.query(sql, params):
            state, code = to_int(r["stState"]), to_int(r["stReturnCode"])
            if state == COMPLETE:
                result = "ok" if code == 0 else "failed"
            elif state == CANCELLED:
                result = "cancelled"
            else:
                result = "pending"
            out.append({
                "id": to_int(r["stID"]),
                "job_id": to_int(r["stJobID"]),
                "host": r["hostName"],
                "host_id": to_int(r["sjHostID"]),
                "ip": r["hostIP"],
                "snapin": r["sName"],
                "state": r["stateName"] or str(state),
                "result": result,
                "return_code": code if state == COMPLETE else None,
                "details": (r["stReturnDetails"] or "").strip() or None,
                "queued": dt_text(r["sjCreateTime"]),
                "checked_in": dt_text(r["stCheckinDate"]),
                "completed": dt_text(r["stCompleteDate"]),
            })
        return out

    # -- overview -----------------------------------------------------------

    def info(self):
        count = lambda sql: to_int(self.db.scalar(sql))
        active = ",".join(str(s) for s in ACTIVE_STATES)
        nodes = self.db.query("""
            SELECT ngm.ngmMemberName, ngm.ngmHostname, ngm.ngmIsMasterNode, ngm.ngmIsEnabled,
                   ngm.ngmInterface, ngm.ngmMaxClients, ng.ngName
            FROM nfsGroupMembers ngm LEFT JOIN nfsGroups ng ON ng.ngID = ngm.ngmGroupID
            ORDER BY ng.ngName, ngm.ngmIsMasterNode DESC, ngm.ngmMemberName""")
        return {
            "fog_version": self.settings.fog_version(),
            "schema_version": to_int(self.db.scalar("SELECT MAX(vValue) FROM schemaVersion")),
            "config_source": self.settings.source,
            "database": "%s@%s/%s" % (self.settings.values["DATABASE_USERNAME"],
                                      self.settings.values["DATABASE_HOST"],
                                      self.settings.values["DATABASE_NAME"]),
            "client": self.db.client,
            "server_time": dt_text(self.now()),
            "checkin_timeout": self.checkin_timeout(),
            "client_checkin_interval": to_int(self.db.setting("FOG_CLIENT_CHECKIN_TIME")),
            "udp_sender": self.settings.values.get("UDPSENDERPATH"),
            "multicast_port_base": to_int(self.db.setting("FOG_UDPCAST_STARTINGPORT")),
            "counts": {
                "hosts": count("SELECT COUNT(*) FROM hosts"),
                "hosts_pending": count("SELECT COUNT(*) FROM hosts WHERE hostPending = '1'"),
                "images": count("SELECT COUNT(*) FROM images"),
                "groups": count("SELECT COUNT(*) FROM groups"),
                "snapins": count("SELECT COUNT(*) FROM snapins"),
                "tasks_active": count("SELECT COUNT(*) FROM tasks WHERE taskStateID IN (%s)" % active),
                "tasks_total": count("SELECT COUNT(*) FROM tasks"),
                "multicast_active": count(
                    "SELECT COUNT(*) FROM multicastSessions WHERE msState IN (%s)" % active),
            },
            "storage_nodes": [{
                "name": n["ngmMemberName"],
                "address": n["ngmHostname"],
                "group": n["ngName"],
                "master": n["ngmIsMasterNode"] == "1",
                "enabled": n["ngmIsEnabled"] == "1",
                "interface": n["ngmInterface"],
                "max_clients": to_int(n["ngmMaxClients"]),
            } for n in nodes],
        }


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

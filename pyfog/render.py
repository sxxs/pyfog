"""Terminal presentation of the dicts the data layer produces.

Nothing in here touches the database or the file system. Every function
takes data from fog.Fog and writes text to a stream.
"""

import re
import shutil
import sys


ANSI = re.compile(r"\033\[[0-9;]*m")


def age_text(seconds):
    if seconds is None:
        return "-"
    sign, seconds = ("-" if seconds < 0 else ""), abs(int(seconds))
    if seconds < 60:
        text = "%ds" % seconds
    elif seconds < 3600:
        text = "%dm %02ds" % divmod(seconds, 60)
    elif seconds < 86400:
        text = "%dh %02dm" % (seconds // 3600, seconds % 3600 // 60)
    else:
        text = "%dd %02dh" % (seconds // 86400, seconds % 86400 // 3600)
    return sign + text


def short_dt(text):
    """Drop the seconds; tables are wide enough as they are."""
    return text[:16] if text else "-"


def size_text(size):
    if size is None:
        return "-"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return ("%d %s" if unit == "B" else "%.1f %s") % (size, unit)
        size /= 1024.0


class Palette(object):
    """ANSI colours, or plain text when disabled."""

    def __init__(self, enabled):
        self.enabled = enabled

    def _wrap(self, code, text):
        text = "-" if text in ("", None) else str(text)
        return "\033[%sm%s\033[0m" % (code, text) if self.enabled else text

    def red(self, text):
        return self._wrap("31", text)

    def green(self, text):
        return self._wrap("32", text)

    def yellow(self, text):
        return self._wrap("33", text)

    def dim(self, text):
        return self._wrap("2", text)

    def bold(self, text):
        return self._wrap("1", text)

    def state(self, name, active=True, stale=False):
        """Task or session state, coloured by what it means."""
        if stale:
            return self.red(name + " (stale)")
        if name in ("In-Progress", "Checked In"):
            return self.green(name)
        if name == "Queued":
            return self.yellow(name)
        if name == "Cancelled":
            return self.red(name)
        return self.dim(name) if not active else name

    def result(self, value):
        return {"ok": self.green, "failed": self.red, "cancelled": self.red,
                "pending": self.yellow}.get(value, str)(value)


def _visible(text):
    return len(ANSI.sub("", text))


def _clip(text, width):
    plain = ANSI.sub("", text)
    if len(plain) <= width:
        return text
    return plain[:max(0, width - 1)] + "…"


class Table(object):
    """Aligned columns that shrink the widest ones to fit the terminal."""

    def __init__(self, *columns):
        # A column is "NAME" (left aligned) or ">NAME" (right aligned).
        self.aligns = ["r" if c.startswith(">") else "l" for c in columns]
        self.headers = [c.lstrip(">") for c in columns]
        self.rows = []

    def add(self, *cells):
        self.rows.append(["-" if c in (None, "") else str(c) for c in cells])

    def write(self, out, palette, indent=""):
        if not self.rows:
            out.write(indent + palette.dim("(nothing)") + "\n")
            return
        widths = [max([_visible(h)] + [_visible(r[i]) for r in self.rows])
                  for i, h in enumerate(self.headers)]
        room = shutil.get_terminal_size((160, 25)).columns - len(indent)
        while sum(widths) + 2 * (len(widths) - 1) > room and max(widths) > 10:
            widths[widths.index(max(widths))] -= 1
        for cells in [self.headers] + self.rows:
            parts = []
            for cell, width, align in zip(cells, widths, self.aligns):
                cell = _clip(cell, width)
                pad = " " * (width - _visible(cell))
                parts.append(pad + cell if align == "r" else cell + pad)
            line = "  ".join(parts).rstrip()
            out.write(indent + (palette.bold(line) if cells is self.headers else line) + "\n")


def _progress(task):
    parts = ["%d%%" % task["percent"]] if task["percent"] else []
    if task["copied"] and task["total"]:
        parts.append("%s/%s" % (task["copied"], task["total"]))
    return " ".join(parts)


# -- one function per command --------------------------------------------


def tasks(data, palette, out=sys.stdout, expand=False):
    """data: {"entries": group_multicast(...), "now", "timeout", "imaging_open"}"""
    heading = "Tasks: %d  (server time %s, check-in timeout %ds)" % (
        data["count"], data["now"], data["timeout"])
    out.write(palette.bold(heading) + "\n")
    task_table(data["entries"], palette, expand).write(out, palette)
    imaging_section(data["imaging_open"], palette, out)


def task_table(entries, palette, expand=False):
    """One row per task; a multicast session is one row, or a row plus its hosts."""
    table = Table(">ID", "HOST", "IP", "TYPE", "STATE", "IMAGE", "PROGRESS",
                  ">ELAPSED", ">LEFT", "NODE", "CREATED", ">CHECK-IN", "FLAGS")
    for entry in entries:
        if "session" in entry:
            table.add("MC%d" % entry["session"], "%d hosts: %s" % (len(entry["tasks"]), entry["name"]),
                      "", entry["type"], _session_states(entry, palette), entry["image"],
                      _session_percent(entry), "", "", "", short_dt(entry["created"]), "",
                      "multicast")
            rows = entry["tasks"] if expand else []
        else:
            rows = [entry]
        for task in rows:
            _task_row(table, task, palette, indent="  " if "session" in entry else "")
    return table


def imaging_section(runs, palette, out):
    """Open imagingLog rows, under their heading; nothing when there are none."""
    if not runs:
        return
    out.write("\n" + palette.bold("Imaging runs reported as started but not finished") + "\n")
    table = Table("HOST", "IP", "IMAGE", "KIND", "STARTED", ">AGE", "TASK")
    for run in runs:
        table.add(run["host"], run["ip"], run["image"], run["kind"], run["started"],
                  age_text(run["age"]), _imaging_task(run, palette))
    table.write(out, palette)


def _imaging_task(run, palette):
    """What became of the task behind an imaging run that never finished."""
    if run["has_task"]:
        return "yes"
    task = run.get("task")
    if task is None:
        return palette.red("none (FOG lost track)")
    if task["closed_by_server"]:
        last = short_dt(task["last_checkin"]) if task["last_checkin"] else "never"
        return palette.red("%d closed by server before the host reported; last report %s"
                           % (task["id"], last))
    return palette.red("%d %s" % (task["id"], task["state"]))


def orphan_section(procs, palette, out):
    """udp-sender processes no active local session claims; nothing when none."""
    if not procs:
        return
    out.write("\n" + palette.red("udp-sender processes no active session claims:") + "\n")
    for proc in procs:
        out.write("  pid %d: portbase %s, min-receivers %s, file %s, since %s\n" % (
            proc["pid"], proc.get("portbase"), proc.get("min_receivers"), proc.get("file"),
            proc["started"]))


def _session_states(entry, palette):
    text = ", ".join("%d %s" % (n, s) for s, n in sorted(entry["states"].items()))
    return palette.red(text + " (stale)") if entry["stale"] else text


def _session_percent(entry):
    low, high = entry["percent_min"], entry["percent_max"]
    if low is None:
        return ""
    return "%d%%" % low if low == high else "%d-%d%%" % (low, high)


def _task_row(table, task, palette, indent=""):
    checkin = age_text(task["checkin_age"]) if task["last_checkin"] else "never"
    if task["stale"]:
        checkin = palette.red(checkin)
    table.add(indent + str(task["id"]), task["host"], task["ip"], task["type"],
              palette.state(task["state"], task["active"], task["stale"]), task["image"],
              _progress(task), task["elapsed"], task["remaining"], task["node"],
              short_dt(task["created"]), checkin, ",".join(task["flags"]))


def task(data, palette, out=sys.stdout):
    t = data["task"]
    out.write(palette.bold("Task %d: %s" % (t["id"], t["name"])) + "\n")
    lines = [
        ("Type", t["type"]),
        ("State", palette.state(t["state"], t["active"], t["stale"])),
        ("Host", "%s  %s  %s" % (t["host"], t["ip"] or "-", t["mac"] or "-")),
        ("Image", t["image"]),
        ("Progress", _progress(t) or "-"),
        ("Elapsed / left", "%s / %s" % (t["elapsed"] or "-", t["remaining"] or "-")),
        ("Rate", t["rate"]),
        ("Created", "%s by %s" % (t["created"], t["created_by"] or "?")),
        ("Scheduled", t["scheduled"]),
        ("Last check-in", "%s (%s ago)" % (t["last_checkin"], age_text(t["checkin_age"]))
         if t["last_checkin"] else "never"),
        ("Storage node", t["node"]),
        ("Flags", ", ".join(t["flags"])),
    ]
    if data["group"]:
        g = data["group"]
        lines.append(("Group", "%s (#%d, %d members)" % (g["name"], g["id"], g["members"])))
    _pairs(lines, palette, out)
    if data["session"]:
        out.write("\n")
        session_summary(data["session"], palette, out)
    out.write("\n" + palette.bold("Participants (%d, by %s)" % (
        len(data["participants"]), data["participants_source"])) + "\n")
    table = Table(">TASK", "HOST", "IP", "MAC", "STATE", "PROGRESS", ">ELAPSED", ">LEFT",
                  ">CHECK-IN", "NODE")
    for p in data["participants"]:
        checkin = age_text(p["checkin_age"]) if p["last_checkin"] else "never"
        table.add(("*" if p["id"] == t["id"] else "") + str(p["id"]), p["host"], p["ip"],
                  p["mac"], palette.state(p["state"], p["active"], p["stale"]), _progress(p),
                  p["elapsed"], p["remaining"], palette.red(checkin) if p["stale"] else checkin,
                  p["node"])
    table.write(out, palette, indent="  ")


def _pairs(lines, palette, out, indent="  "):
    width = max(len(label) for label, _ in lines)
    for label, value in lines:
        out.write("%s%-*s  %s\n" % (indent, width, label, "-" if value in (None, "") else value))


def session_summary(s, palette, out):
    """The session as the database describes it; process facts when present."""
    out.write(palette.bold("Multicast session %d: %s" % (s["id"], s["name"])) + "\n")
    if not s["sender_pid"]:
        sender = "not started yet"
    elif "wrapper_alive" not in s:
        sender = "wrapper shell pid %d on node %s (see: pyfog multicast)" % (s["sender_pid"], s["sender_node"])
    elif not s["sender_local"]:
        sender = "on node %s (%s), not checkable from here" % (s["sender_node"], s["sender_address"])
    elif s["wrapper_alive"]:
        sender = "wrapper shell pid %d alive since %s" % (s["sender_pid"], s["sender_started"])
    else:
        sender = palette.red("wrapper shell pid %d recorded but gone" % s["sender_pid"])
    _pairs([
        ("State", palette.state(s["state"], s["active"])),
        ("Image", s["image"]),
        ("Port", s["port"]),
        ("Clients", "%d joined of %d expected" % (s["clients_joined"], s["clients_expected"])),
        ("Percent", "%d%%" % s["percent"]),
        ("Started", "%s%s" % (s["started"], "  completed " + s["completed"] if s["completed"] else "")),
        ("Storage group", s["storage_group"]),
        ("Sender", sender),
    ], palette, out)
    for proc in s.get("senders", []):
        out.write("  udp-sender pid %d: portbase %s, min-receivers %s, file %s, since %s\n" % (
            proc["pid"], proc.get("portbase"), proc.get("min_receivers"),
            proc.get("file"), proc["started"]))
    if s.get("log"):
        log = s["log"]
        out.write("  udpcast log: %s, %d receivers connected%s\n" % (
            log["phase"], len(log["receivers"]),
            " (" + ", ".join(log["receivers"]) + ")" if log["receivers"] else ""))


def multicast(data, palette, out=sys.stdout):
    if not data["sessions"]:
        out.write(palette.dim("no multicast sessions") + "\n")
    for s in data["sessions"]:
        session_summary(s, palette, out)
        table = Table(">TASK", "HOST", "IP", "STATE", "PROGRESS", ">ELAPSED", ">LEFT", ">CHECK-IN")
        for p in s["participants"]:
            checkin = age_text(p["checkin_age"]) if p["last_checkin"] else "never"
            table.add(p["id"], p["host"], p["ip"], palette.state(p["state"], p["active"], p["stale"]),
                      _progress(p), p["elapsed"], p["remaining"],
                      palette.red(checkin) if p["stale"] else checkin)
        table.write(out, palette, indent="  ")
    orphan_section(data["orphan_senders"], palette, out)


def clients(data, palette, out=sys.stdout, stale_after=None):
    logs = ", ".join(data["logs"]) or "none readable, token times only"
    if data["logs_unreadable"]:
        logs += "; not readable: " + ", ".join(data["logs_unreadable"])
    out.write(palette.bold("Last contact per host (server time %s; logs: %s)"
                           % (data["now"], logs)) + "\n")
    table = Table("HOST", "IP", "MAC", "IMAGE", "LAST SEEN", ">AGE", "SOURCE", "LAST CALL FROM")
    for h in data["hosts"]:
        age = age_text(h["age"])
        if h["age"] is None:
            age = palette.dim("never")
        elif stale_after and h["age"] > stale_after:
            age = palette.red(age)
        table.add(h["host"] + (" (pending)" if h["pending"] else ""), h["ip"], h["mac"],
                  h["image"], h["last_seen"], age, h["source"], h["last_call_from"])
    table.write(out, palette)


def deployments(data, palette, out=sys.stdout):
    table = Table(">ID", "HOST", "IP", "IMAGE", "KIND", "STARTED", "FINISHED", ">DURATION", "BY")
    for d in data:
        table.add(d["id"], d["host"], d["ip"], d["image"], d["kind"], d["started"],
                  d["finished"] or palette.yellow("running"), age_text(d["duration"]),
                  d["created_by"])
    table.write(out, palette)


def current_images(data, palette, out=sys.stdout):
    table = Table("HOST", "IP", "ASSIGNED", "LAST DEPLOYED", "WHEN", "MATCH")
    for h in data:
        if h["deployed"]:
            match = palette.green("yes") if h["matches"] else palette.red("no")
        elif h["deployed_at"]:
            match = palette.dim("unknown (no imaging log)")
        else:
            match = palette.dim("never deployed")
        table.add(h["host"], h["ip"], h["assigned"], h["deployed"], h["deployed_at"], match)
    table.write(out, palette)


def images(data, palette, out=sys.stdout):
    table = Table(">ID", "NAME", "OS", "TYPE", "FORMAT", ">SIZE", ">HOSTS", "STORAGE",
                  "LAST DEPLOY", "FLAGS", "PATH")
    for i in data:
        flags = [f for f, on in (("disabled", not i["enabled"]), ("protected", i["protected"])) if on]
        table.add(i["id"], i["name"], i["os"], i["type"], i["format"],
                  size_text(i["size_on_server"]), i["hosts_assigned"],
                  ",".join(i["storage_groups"]), short_dt(i["last_deploy"]),
                  ",".join(flags), i["path"])
    table.write(out, palette)


def hosts(data, palette, out=sys.stdout):
    table = Table(">ID", "NAME", "IP", "MAC", "IMAGE", "GROUPS", "ACTIVE TASK", "LAST DEPLOY")
    for h in data:
        table.add(h["id"], h["name"] + (" (pending)" if h["pending"] else ""), h["ip"], h["mac"],
                  h["image"], ",".join(h["groups"]), h["active_task"], short_dt(h["last_deploy"]))
    table.write(out, palette)


def groups(data, palette, out=sys.stdout):
    table = Table(">ID", "NAME", ">MEMBERS", "HOSTS", "DESCRIPTION")
    for g in data:
        table.add(g["id"], g["name"], len(g["members"]), ", ".join(g["members"]), g["description"])
    table.write(out, palette)


def snapins(data, palette, out=sys.stdout):
    table = Table("HOST", "SNAPIN", "RESULT", ">CODE", "QUEUED", "COMPLETED", "DETAILS")
    for s in data:
        table.add(s["host"], s["snapin"], palette.result(s["result"]), s["return_code"],
                  short_dt(s["queued"]), short_dt(s["completed"]), s["details"])
    table.write(out, palette)


def history(data, palette, out=sys.stdout, expand=False):
    table = Table(">ID", "HOST", "TYPE", "IMAGE", "RESULT", "CREATED", "STARTED", "FINISHED",
                  ">DURATION", "BY")
    for entry in data:
        if "session" in entry:
            done = sum(1 for t in entry["tasks"] if t["result"] == "ok")
            table.add("MC%d" % entry["session"], "%d hosts: %s" % (len(entry["tasks"]), entry["name"]),
                      entry["type"], entry["image"],
                      palette.result("ok" if done == len(entry["tasks"]) else "failed")
                      + " (%d/%d ok)" % (done, len(entry["tasks"])),
                      short_dt(entry["created"]), "", "", "", "")
            rows = entry["tasks"] if expand else []
        else:
            rows = [entry]
        for t in rows:
            table.add(("  " if "session" in entry else "") + str(t["id"]), t["host"], t["type"],
                      t["image"], palette.result(t["result"]), short_dt(t["created"]),
                      short_dt(t["started"]), _finished(t, palette), age_text(t["duration"]),
                      t["created_by"])
    table.write(out, palette)


def _finished(task, palette):
    """FOG logs no time for a cancellation, and none for a task the server
    closed itself, so the last sign of life stands in."""
    if task["finished"]:
        return short_dt(task["finished"])
    last = short_dt(task["last_checkin"]) if task["last_checkin"] else None
    if task["result"] == "ok":
        return palette.dim("closed by server" + (", last report " + last if last else ""))
    return palette.dim("silent since " + last if last else "never checked in")


def scheduled(data, palette, out=sys.stdout):
    table = Table(">ID", "NAME", "TYPE", "WHEN", "TARGET", "IMAGE", "ACTIVE")
    for s in data:
        table.add(s["id"], s["name"], s["type"],
                  s["when"] or ("cron " + s["cron"] if s["cron"] else palette.dim("never")),
                  "%s %s" % (s["target_kind"], s["target"]), s["image"],
                  "yes" if s["active"] else palette.dim("no"))
    table.write(out, palette)


def info(data, palette, out=sys.stdout):
    c = data["counts"]
    _pairs([
        ("FOG version", data["fog_version"] or "unknown (web root not found)"),
        ("Schema version", data["schema_version"]),
        ("Database", data["database"]),
        ("Settings from", data["config_source"]),
        ("Server time", data["server_time"]),
        ("Check-in timeout", "%d s" % data["checkin_timeout"]),
        ("Client interval", "%d s" % data["client_checkin_interval"]),
        ("udp-sender", data["udp_sender"]),
        ("Multicast ports", "from %d" % data["multicast_port_base"]),
        ("Hosts", "%d (%d pending approval)" % (c["hosts"], c["hosts_pending"])),
        ("Images / groups / snapins", "%d / %d / %d" % (c["images"], c["groups"], c["snapins"])),
        ("Tasks", "%d active, %d in table" % (c["tasks_active"], c["tasks_total"])),
        ("Multicast sessions", "%d active" % c["multicast_active"]),
    ], palette, out, indent="")
    out.write("\n" + palette.bold("Storage nodes") + "\n")
    table = Table("NAME", "ADDRESS", "GROUP", "ROLE", "INTERFACE", ">MAX CLIENTS", "ENABLED")
    for n in data["storage_nodes"]:
        table.add(n["name"], n["address"], n["group"], "master" if n["master"] else "node",
                  n["interface"], n["max_clients"], "yes" if n["enabled"] else palette.red("no"))
    table.write(out, palette)


# -- dashboard ------------------------------------------------------------


def dashboard(data, palette, out=sys.stdout):
    """One screen of live state; data from Fog.dashboard()."""
    heading = "FOG dashboard  server time %s, check-in timeout %ds" % (data["now"], data["timeout"])
    out.write(palette.bold(heading) + "\n")
    states = ["%d %s" % (n, state) for state, n in sorted(data["states"].items())]
    if data["stale"]:
        states.append(palette.red("%d stale" % data["stale"]))
    parts = ["Active tasks: %d" % data["count"] + (" (%s)" % ", ".join(states) if states else "")]
    if data["sessions"]:
        parts.append("%d multicast session%s" % (len(data["sessions"]),
                                                  "" if len(data["sessions"]) == 1 else "s"))
    lost = sum(1 for run in data["imaging_open"] if not run["has_task"])
    if lost:
        parts.append(palette.red("%d imaging run%s without a task" % (lost, "" if lost == 1 else "s")))
    if data["orphan_senders"]:
        parts.append(palette.red("%d udp-sender without a session" % len(data["orphan_senders"])))
    out.write("  ".join(parts) + "\n\n")

    task_table(data["entries"], palette, expand=True).write(out, palette)
    imaging_section(data["imaging_open"], palette, out)
    for s in data["sessions"]:
        out.write("\n")
        session_summary(s, palette, out)
    orphan_section(data["orphan_senders"], palette, out)
    if data["recent"]:
        out.write("\n" + palette.bold("Recently finished tasks") + "\n")
        history(data["recent"], palette, out)
    if data["scheduled"]:
        out.write("\n" + palette.bold("Scheduled tasks") + "\n")
        scheduled(data["scheduled"], palette, out)


def frame(text, size=None):
    """Turn rendered text into one screen update for a terminal.

    Built for slow links and ssh sessions: no alternate screen, no full
    clear, no cursor games. The cursor goes home, every line overwrites
    its predecessor to the end of the line, and whatever the previous
    frame left below is cleared once. Lines that do not fit the terminal
    are dropped and counted in the last row, so the screen never scrolls.
    """
    columns, rows = size or shutil.get_terminal_size((160, 25))
    # A pty without a window size reports 0x0 on older Pythons.
    columns, rows = (columns if columns > 1 else 160), (rows if rows > 1 else 25)
    # One column short: a line that fills the row leaves the cursor in the
    # terminal's pending-wrap state, where erase-to-end eats the last cell.
    lines = [_clip(line, columns - 1) for line in text.rstrip("\n").split("\n")]
    if len(lines) > rows:
        lines = lines[:rows - 1] + ["… %d more lines" % (len(lines) - rows + 1)]
    return "\033[H" + "\033[K\n".join(lines) + "\033[K\033[J"

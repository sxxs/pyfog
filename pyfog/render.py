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


def rate_text(rate):
    """One interface's throughput, in the direction that matters: a deploy
    is the server sending, a capture is the server receiving."""
    return "%s  out %s/s  in %s/s" % (rate["interface"], size_text(rate["tx"]), size_text(rate["rx"]))


def network_text(rates, floor=100 * 1024):
    """The busy interfaces, or the busiest one when the machine is quiet,
    so the line never disappears while a task is running."""
    if not rates:
        return None
    busy = [r for r in rates if r["rx"] + r["tx"] >= floor][:2] or rates[:1]
    return "  ".join(rate_text(r) for r in busy) + "  (%.1fs sample)" % busy[0]["seconds"]


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


class Sort(object):
    """Which column a table is sorted by, chosen with keys in the live
    views. column may be None (the order the data came in); Table.write
    clamps it to the table it is applied to, which is how a negative
    column comes to mean "the last one"."""

    def __init__(self, column=None, reverse=False):
        self.column = column
        self.reverse = reverse

    def move(self, step):
        self.column = (0 if step > 0 else -1) if self.column is None else self.column + step


AGE = re.compile(r"^(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?$")
NUMBER = re.compile(r"^-?\d+(?:\.\d+)?")


def sort_key(cell):
    """Order for one cell as rendered: ages by duration, cells that start
    with a number by it (sizes, percentages, dates), then text; "-" last."""
    plain = ANSI.sub("", cell).strip()
    if plain in ("", "-"):
        return (2, 0, "")
    match = AGE.match(plain)
    if match and any(match.groups()):
        d, h, m, s = (int(g or 0) for g in match.groups())
        return (0, ((d * 24 + h) * 60 + m) * 60 + s, plain)
    match = NUMBER.match(plain)
    if match:
        return (0, float(match.group()), plain)
    return (1, 0, plain.lower())


class Table(object):
    """Aligned columns that shrink the widest ones to fit the terminal."""

    def __init__(self, *columns):
        # A column is "NAME" (left aligned) or ">NAME" (right aligned).
        self.aligns = ["r" if c.startswith(">") else "l" for c in columns]
        self.headers = [c.lstrip(">") for c in columns]
        self.rows = []
        self.children = []  # per row: belongs under the previous top-level row

    def add(self, *cells, **options):
        self.rows.append(["-" if c in (None, "") else str(c) for c in cells])
        self.children.append(bool(options.get("child")))

    def _ordered(self, sort):
        """Rows in sort order; child rows travel with their parent."""
        if sort is None or sort.column is None or not self.rows:
            return list(self.rows)
        sort.column = max(0, min(sort.column if sort.column >= 0 else len(self.headers) - 1,
                                 len(self.headers) - 1))
        blocks = []
        for row, child in zip(self.rows, self.children):
            if child and blocks:
                blocks[-1].append(row)
            else:
                blocks.append([row])
        keys = {id(block): sort_key(block[0][sort.column]) for block in blocks}
        # Reverse the values only; empty cells stay last either way.
        blocks.sort(key=lambda block: keys[id(block)][1:], reverse=sort.reverse)
        blocks.sort(key=lambda block: keys[id(block)][0])
        return [row for block in blocks for row in block]

    def write(self, out, palette, indent="", sort=None):
        if not self.rows:
            out.write(indent + palette.dim("(nothing)") + "\n")
            return
        rows = self._ordered(sort)
        headers = list(self.headers)
        if sort is not None and sort.column is not None:
            headers[sort.column] += "▴" if sort.reverse else "▾"
        widths = [max([_visible(h)] + [_visible(r[i]) for r in rows])
                  for i, h in enumerate(headers)]
        room = shutil.get_terminal_size((160, 25)).columns - len(indent)
        while sum(widths) + 2 * (len(widths) - 1) > room and max(widths) > 10:
            widths[widths.index(max(widths))] -= 1
        for cells in [headers] + rows:
            parts = []
            for cell, width, align in zip(cells, widths, self.aligns):
                cell = _clip(cell, width)
                pad = " " * (width - _visible(cell))
                parts.append(pad + cell if align == "r" else cell + pad)
            line = "  ".join(parts).rstrip()
            out.write(indent + (palette.bold(line) if cells is headers else line) + "\n")


def _progress(task):
    parts = ["%d%%" % task["percent"]] if task["percent"] else []
    if task["copied"] and task["total"]:
        parts.append("%s/%s" % (task["copied"], task["total"]))
    return " ".join(parts)


# -- one function per command --------------------------------------------


def tasks(data, palette, out=sys.stdout, expand=False, sort=None):
    """data: {"entries": group_multicast(...), "now", "timeout", "imaging_open"}"""
    heading = "Tasks: %d  (server time %s, check-in timeout %ds)" % (
        data["count"], data["now"], data["timeout"])
    out.write(palette.bold(heading) + "\n")
    network = network_text(data.get("network"))
    if network:
        out.write("Network  " + network + "\n")
    task_table(data["entries"], palette, expand).write(out, palette, sort=sort)
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
    if any(run.get("cancelled") for run in runs):
        # Said once, under the table: without it a row that only says
        # "Cancelled" reads as something still going wrong.
        out.write(palette.dim(
            "  A cancelled task leaves its run open: the host stops without reporting a"
            " finish. Nothing is still running; sql/lost-tasks.sql clears the rows.") + "\n")


def _imaging_task(run, palette):
    """What became of the task behind an imaging run that never finished."""
    if run["has_task"]:
        return "yes"
    task = run.get("task")
    if task is None:
        return palette.red("none (FOG lost track)")
    if task["cancelled"]:
        return palette.dim("%d cancelled, run left open" % task["id"])
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
              short_dt(task["created"]), checkin, ",".join(task["flags"]), child=bool(indent))


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


def _clients(s):
    """The two counts the database has. Neither is "receiving right now":
    only the udpcast log line below knows who actually connected."""
    text = "%d in session" % s["clients_in_session"]
    if s["clients_expected"] > s["clients_in_session"]:
        text += " of %d the sender waits for" % s["clients_expected"]
    return text


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
        ("Clients", _clients(s)),
        ("Percent", "%d%%" % s["percent"]),
        ("Started", "%s%s" % (s["started"], "  completed " + s["completed"] if s["completed"] else "")),
        ("Storage group", s["storage_group"]),
        ("Sender", sender),
    ] + ([("Throughput", rate_text(s["rate"]) + "  (%.1fs sample)" % s["rate"]["seconds"])]
         if s.get("rate") else []), palette, out)
    for proc in s.get("senders", []):
        out.write("  udp-sender pid %d: portbase %s, min-receivers %s, file %s, since %s\n" % (
            proc["pid"], proc.get("portbase"), proc.get("min_receivers"),
            proc.get("file"), proc["started"]))
    if s.get("log"):
        log = s["log"]
        out.write("  udpcast log: %s, %d receivers connected%s\n" % (
            log["phase"], len(log["receivers"]),
            " (" + ", ".join(log["receivers"]) + ")" if log["receivers"] else ""))


def multicast(data, palette, out=sys.stdout, sort=None):
    if not data["sessions"]:
        out.write(palette.dim("no multicast sessions") + "\n")
    network = network_text(data.get("network"))
    if network:
        out.write("Network  " + network + "\n\n")
    for s in data["sessions"]:
        session_summary(s, palette, out)
        table = Table(">TASK", "HOST", "IP", "STATE", "PROGRESS", ">ELAPSED", ">LEFT", ">CHECK-IN")
        for p in s["participants"]:
            checkin = age_text(p["checkin_age"]) if p["last_checkin"] else "never"
            table.add(p["id"], p["host"], p["ip"], palette.state(p["state"], p["active"], p["stale"]),
                      _progress(p), p["elapsed"], p["remaining"],
                      palette.red(checkin) if p["stale"] else checkin)
        table.write(out, palette, indent="  ", sort=sort)
    orphan_section(data["orphan_senders"], palette, out)


def arp_text(live, palette):
    """What one ARP probe means. "silent" and not "off": a host on another
    segment, or one behind a firewall that drops nothing but is simply not
    on this wire, is quiet for reasons that have nothing to do with power."""
    if not live or live["how"] is None:
        return palette.dim("-")           # no address to ask at
    if live["error"]:
        return palette.dim("?")           # could not ask; see the heading
    if live["up"]:
        return palette.green("up")
    if live["mac_seen"]:
        return palette.red("other host")  # that address answers, this host does not own it
    return palette.dim("silent")


def clients(data, palette, out=sys.stdout, stale_after=None, sort=None):
    logs = ", ".join(data["logs"]) or "none readable, token times only"
    if data["logs_unreadable"]:
        logs += "; not readable: " + ", ".join(data["logs_unreadable"])
    out.write(palette.bold("Last contact per host (server time %s; logs: %s)"
                           % (data["now"], logs)) + "\n")
    if data.get("probe_error"):
        out.write(palette.red("arp: " + data["probe_error"]) + "\n")
    probed = data.get("probed")
    columns = ["HOST", "IP", "MAC", "IMAGE", "LAST SEEN", ">AGE", "SOURCE", "LAST CALL FROM"]
    if probed:
        columns.insert(1, "ARP")
    table = Table(*columns)
    for h in data["hosts"]:
        age = age_text(h["age"])
        if h["age"] is None:
            age = palette.dim("never")
        elif stale_after and h["age"] > stale_after:
            age = palette.red(age)
        row = [h["host"] + (" (pending)" if h["pending"] else ""), h["ip"], h["mac"],
               h["image"], h["last_seen"], age, h["source"], h["last_call_from"]]
        if probed:
            row.insert(1, arp_text(h.get("live"), palette))
        table.add(*row)
    table.write(out, palette, sort=sort)


def deployments(data, palette, out=sys.stdout, sort=None):
    table = Table(">ID", "HOST", "IP", "IMAGE", "KIND", "STARTED", "FINISHED", ">DURATION", "BY")
    for d in data:
        table.add(d["id"], d["host"], d["ip"], d["image"], d["kind"], d["started"],
                  d["finished"] or palette.yellow("running"), age_text(d["duration"]),
                  d["created_by"])
    table.write(out, palette, sort=sort)


def current_images(data, palette, out=sys.stdout, sort=None):
    table = Table("HOST", "IP", "ASSIGNED", "LAST DEPLOYED", "WHEN", "MATCH")
    for h in data:
        if h["deployed"]:
            match = palette.green("yes") if h["matches"] else palette.red("no")
        elif h["deployed_at"]:
            match = palette.dim("unknown (no imaging log)")
        else:
            match = palette.dim("never deployed")
        table.add(h["host"], h["ip"], h["assigned"], h["deployed"], h["deployed_at"], match)
    table.write(out, palette, sort=sort)


def images(data, palette, out=sys.stdout, sort=None):
    table = Table(">ID", "NAME", "OS", "TYPE", "FORMAT", ">SIZE", ">HOSTS", "STORAGE",
                  "LAST DEPLOY", "FLAGS", "PATH")
    for i in data:
        flags = [f for f, on in (("disabled", not i["enabled"]), ("protected", i["protected"])) if on]
        table.add(i["id"], i["name"], i["os"], i["type"], i["format"],
                  size_text(i["size_on_server"]), i["hosts_assigned"],
                  ",".join(i["storage_groups"]), short_dt(i["last_deploy"]),
                  ",".join(flags), i["path"])
    table.write(out, palette, sort=sort)


def hosts(data, palette, out=sys.stdout, sort=None):
    table = Table(">ID", "NAME", "IP", "MAC", "IMAGE", "GROUPS", "ACTIVE TASK", "LAST DEPLOY")
    for h in data:
        table.add(h["id"], h["name"] + (" (pending)" if h["pending"] else ""), h["ip"], h["mac"],
                  h["image"], ",".join(h["groups"]), h["active_task"], short_dt(h["last_deploy"]))
    table.write(out, palette, sort=sort)


def groups(data, palette, out=sys.stdout, sort=None):
    table = Table(">ID", "NAME", ">MEMBERS", "HOSTS", "DESCRIPTION")
    for g in data:
        table.add(g["id"], g["name"], len(g["members"]), ", ".join(g["members"]), g["description"])
    table.write(out, palette, sort=sort)


def snapins(data, palette, out=sys.stdout, sort=None):
    table = Table("HOST", "SNAPIN", "RESULT", ">CODE", "QUEUED", "COMPLETED", "DETAILS")
    for s in data:
        table.add(s["host"], s["snapin"], palette.result(s["result"]), s["return_code"],
                  short_dt(s["queued"]), short_dt(s["completed"]), s["details"])
    table.write(out, palette, sort=sort)


def history(data, palette, out=sys.stdout, expand=False, sort=None):
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
                      t["created_by"], child="session" in entry)
    table.write(out, palette, sort=sort)


def _finished(task, palette):
    """A finish time exists only where the host wrote one: the imagingLog
    row of a deploy or capture. For everything else -- a cancellation, a
    task the server closed itself, an inventory or a snapin job, which
    report that they are done but not when -- the last sign of life
    stands in."""
    if task["finished"]:
        return short_dt(task["finished"])
    last = short_dt(task["last_checkin"]) if task["last_checkin"] else None
    if task["result"] != "ok":
        return palette.dim("silent since " + last if last else "never checked in")
    if task.get("reported"):
        return palette.dim("reported, no end time logged")
    return palette.dim("closed by server" + (", last report " + last if last else ""))


def scheduled(data, palette, out=sys.stdout, sort=None):
    table = Table(">ID", "NAME", "TYPE", "WHEN", "TARGET", "IMAGE", "ACTIVE")
    for s in data:
        table.add(s["id"], s["name"], s["type"],
                  s["when"] or ("cron " + s["cron"] if s["cron"] else palette.dim("never")),
                  "%s %s" % (s["target_kind"], s["target"]), s["image"],
                  "yes" if s["active"] else palette.dim("no"))
    table.write(out, palette, sort=sort)


def _clock(clock, palette):
    """The reference clock, and a warning when the database server's own
    clock differs, because then every age depends on getting this right."""
    text = "%s  (%s)" % (clock["reference"], clock["source"])
    if clock["db_skew"]:
        text += palette.red("; the database server clock is %s, %+d s away, so its "
                            "own NOW() would skew every age" % (clock["db_now"], clock["db_skew"]))
    return text


def info(data, palette, out=sys.stdout, sort=None):
    c = data["counts"]
    _pairs([
        ("FOG version", data["fog_version"] or "unknown (web root not found)"),
        ("Schema version", data["schema_version"]),
        ("Database", data["database"]),
        ("Settings from", data["config_source"]),
        ("Reference time", _clock(data["clock"], palette)),
        ("Check-in timeout", "%d s" % data["checkin_timeout"]),
        ("udp-sender", data["udp_sender"]),
        ("Multicast ports", "from %d" % data["multicast_port_base"]),
        ("Hosts", "%d (%d pending approval)" % (c["hosts"], c["hosts_pending"])),
        ("Images / groups / snapins", "%d / %d / %d" % (c["images"], c["groups"], c["snapins"])),
        ("Tasks", "%d active, %d in table" % (c["tasks_active"], c["tasks_total"])),
        ("Multicast sessions", "%d active" % c["multicast_active"]),
    ], palette, out, indent="")
    c = data["client"]
    out.write("\n" + palette.bold("FOG client (global; FOG has no per-host or per-group values)") + "\n")
    sleep = "%d s set; the server sends %d-%d s (it adds a random %d-%d s%s)" % (
        c["checkin_time"], c["sleep_sent"][0], c["sleep_sent"][1],
        c["jitter"][0], c["jitter"][1],
        "" if c["jitter_source"] == "web root" else "; " + c["jitter_source"])
    if c["sleep_effective"] != c["sleep_sent"]:
        sleep += palette.red("; the client accepts %d-%d s and uses 60 s for anything outside"
                             % c["sleep_accepted"])
    grace = "%d s set" % c["grace_timeout"]
    if c["grace_effective"] != c["grace_timeout"]:
        grace += palette.red("; the client accepts %d-%d s and uses %d s instead"
                             % (c["grace_accepted"] + (c["grace_effective"],)))
    _pairs([
        ("Check-in time", sleep),
        ("Reboot countdown", grace),
        ("Force reboot", "yes" if c["force_reboot"] else "no"),
    ], palette, out)
    out.write("\n" + palette.bold("Storage nodes") + "\n")
    table = Table("NAME", "ADDRESS", "GROUP", "ROLE", "INTERFACE", ">MAX CLIENTS", "ENABLED")
    for n in data["storage_nodes"]:
        table.add(n["name"], n["address"], n["group"], "master" if n["master"] else "node",
                  n["interface"], n["max_clients"], "yes" if n["enabled"] else palette.red("no"))
    table.write(out, palette, sort=sort)


# -- dashboard ------------------------------------------------------------


def dashboard(data, palette, out=sys.stdout, sort=None):
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
    lost = sum(1 for run in data["imaging_open"] if run.get("lost", not run["has_task"]))
    if lost:
        parts.append(palette.red("%d imaging run%s without a task" % (lost, "" if lost == 1 else "s")))
    stopped = sum(1 for run in data["imaging_open"] if run.get("cancelled"))
    if stopped:
        parts.append(palette.dim("%d run%s left open by a cancelled task"
                                 % (stopped, "" if stopped == 1 else "s")))
    if data["orphan_senders"]:
        parts.append(palette.red("%d udp-sender without a session" % len(data["orphan_senders"])))
    out.write("  ".join(parts) + "\n")
    network = network_text(data.get("network"))
    if network:
        out.write("Network  " + network + "\n")
    out.write("\n")

    task_table(data["entries"], palette, expand=True).write(out, palette, sort=sort)
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


def frame(text, size=None, fixed=0, skip=0):
    """Turn rendered text into one screen update for a terminal.

    Built for slow links and ssh sessions: no alternate screen, no full
    clear, no cursor games. The cursor goes home, every line overwrites
    its predecessor to the end of the line, and whatever the previous
    frame left below is cleared once. The first `fixed` lines always
    show; of the rest, `skip` lines are scrolled off the top and what
    does not fit is counted in the last row, so the screen never scrolls
    by itself. Returns (screen, first, last, total): which body lines
    (1-based) are on screen, of how many.
    """
    columns, rows = size or shutil.get_terminal_size((160, 25))
    # A pty without a window size reports 0x0 on older Pythons.
    columns, rows = (columns if columns > 1 else 160), (rows if rows > 1 else 25)
    # One column short: a line that fills the row leaves the cursor in the
    # terminal's pending-wrap state, where erase-to-end eats the last cell.
    lines = [_clip(line, columns - 1) for line in text.rstrip("\n").split("\n")]
    head, body = lines[:fixed], lines[fixed:]
    room = max(1, rows - len(head))
    skip = max(0, min(skip, len(body) - room))
    shown = body[skip:]
    if len(shown) > room:
        shown = shown[:room - 1] + ["… %d more lines" % (len(shown) - room + 1)]
    screen = "\033[H" + "\033[K\n".join(head + shown) + "\033[K\033[J"
    return screen, skip + 1, skip + len(shown), len(body)

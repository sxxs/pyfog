"""Facts read from the machine pyfog runs on, outside the database.

    processes      /proc, to find udp-sender processes and FOG's sh wrappers
    access logs    the web server log, to see when a FOG client last called in
    udpcast logs   udp-sender's own output, to see which receivers joined
"""

import gzip
import os
import re
import socket
import subprocess
from datetime import datetime

from .util import normalize_mac, to_int

ACCESS_LOG_CANDIDATES = (
    "/var/log/apache2/access.log",
    "/var/log/apache2/other_vhosts_access.log",
    "/var/log/httpd/access_log",
    "/var/log/nginx/access.log",
    "/var/log/lighttpd/access.log",
)

# Combined log format, with or without a leading "vhost:port" field.
ACCESS_LINE = re.compile(r'(\S+) \S+ \S+ \[([^\]]+)\] "[A-Z]+ ([^" ]+)')
MAC_PARAM = re.compile(r"[?&]mac=([^&\s]+)")


# -- processes ------------------------------------------------------------


def _boot_time():
    try:
        with open("/proc/stat") as handle:
            for line in handle:
                if line.startswith("btime "):
                    return float(line.split()[1])
    except IOError:
        pass
    return None


def processes():
    """pid -> {pid, ppid, argv, started, exe} for every readable process."""
    procs = {}
    btime = _boot_time()
    ticks = os.sysconf("SC_CLK_TCK")
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        base = "/proc/%d" % pid
        try:
            with open(base + "/cmdline", "rb") as handle:
                argv = [a.decode("utf-8", "replace")
                        for a in handle.read().split(b"\0") if a]
            with open(base + "/stat") as handle:
                fields = handle.read().rsplit(")", 1)[1].split()
        except (IOError, OSError, IndexError):
            continue
        if not argv:
            continue
        started = None
        if btime is not None:
            started = datetime.fromtimestamp(btime + float(fields[19]) / ticks)
        try:
            exe = os.readlink(base + "/exe")
        except OSError:
            exe = None
        procs[pid] = {"pid": pid, "ppid": int(fields[1]), "argv": argv,
                      "started": started, "exe": exe}
    return procs


def is_udp_sender(proc):
    """A real udp-sender, as opposed to the /bin/sh FOG wraps it in."""
    names = [os.path.basename(proc["argv"][0])]
    if proc["exe"]:
        names.append(os.path.basename(proc["exe"]))
    return any(n.startswith("udp-sender") for n in names)


def sender_options(argv):
    """The udp-sender flags worth showing."""
    wanted = {"--portbase": "portbase", "--min-receivers": "min_receivers",
              "--interface": "interface", "--file": "file",
              "--mcast-data-address": "address", "--max-bitrate": "max_bitrate"}
    found = {}
    for flag, value in zip(argv, argv[1:] + [None]):
        if flag in wanted:
            found[wanted[flag]] = value
    for key in ("portbase", "min_receivers"):
        if key in found:
            found[key] = to_int(found[key], None)
    return found


def descendants(procs, root):
    children = {}
    for proc in procs.values():
        children.setdefault(proc["ppid"], []).append(proc["pid"])
    found, stack = [], list(children.get(root, []))
    while stack:
        pid = stack.pop()
        if pid not in found:
            found.append(pid)
            stack.extend(children.get(pid, []))
    return found


def local_names():
    """Hostnames and addresses that mean "this machine"."""
    names = {"localhost", "127.0.0.1", "::1"}
    hostname = socket.gethostname()
    names.update({hostname.lower(), hostname.split(".")[0].lower()})
    try:
        names.update(info[4][0] for info in socket.getaddrinfo(hostname, None))
    except socket.gaierror:
        pass
    try:
        out = subprocess.check_output(["ip", "-o", "addr"], stderr=subprocess.DEVNULL)
        names.update(re.findall(r"inet6?\s+([0-9a-fA-F:.]+)/", out.decode("ascii", "replace")))
    except (OSError, subprocess.CalledProcessError):
        pass
    return names


# -- web server access log --------------------------------------------------


def find_access_logs():
    return [p for p in ACCESS_LOG_CANDIDATES if os.path.isfile(p)]


def _tail_lines(path, max_bytes):
    """The last max_bytes of a (possibly gzipped) file, as complete lines."""
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            data = handle.read()[-max_bytes:]
    else:
        with open(path, "rb") as handle:
            handle.seek(max(0, os.path.getsize(path) - max_bytes))
            data = handle.read()
    lines = data.decode("utf-8", "replace").splitlines()
    return lines[1:] if os.path.getsize(path) > max_bytes else lines


def client_calls(paths, max_bytes):
    """mac -> {"last_seen", "ip", "path", "count"} from FOG client requests.

    The FOG client identifies itself with a mac= parameter on every call
    (lib/fog/fogbase.class.php reads it from GET or POST), so any logged
    request carrying that parameter is a client check-in.
    """
    seen = {}
    for path in paths:
        for line in _tail_lines(path, max_bytes):
            match = ACCESS_LINE.search(line)
            if not match:
                continue
            ip, stamp, url = match.groups()
            macs = MAC_PARAM.search(url)
            if not macs:
                continue
            try:
                when = datetime.strptime(stamp, "%d/%b/%Y:%H:%M:%S %z")
            except ValueError:
                continue
            when = when.astimezone().replace(tzinfo=None)
            for raw in re.split(r"[|,]|%7C|%2C", macs.group(1), flags=re.I):
                mac = normalize_mac(raw.replace("%3A", ":").replace("%3a", ":"))
                if len(mac) != 12:
                    continue
                entry = seen.setdefault(mac, {"last_seen": None, "ip": ip,
                                              "path": url, "count": 0})
                entry["count"] += 1
                if entry["last_seen"] is None or when > entry["last_seen"]:
                    entry.update(last_seen=when, ip=ip, path=url.split("?")[0])
    return seen


# -- udpcast session log ----------------------------------------------------


def udpcast_log(path, max_bytes=256 * 1024):
    """Receivers and phase from a udp-sender log FOG keeps per session."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        handle.seek(max(0, os.path.getsize(path) - max_bytes))
        text = handle.read().decode("utf-8", "replace").replace("\r", "\n")
    receivers = []
    for match in re.finditer(r"New connection from (\S+)", text):
        if match.group(1) not in receivers:
            receivers.append(match.group(1))
    phase = "waiting"
    if "Transfer complete" in text:
        phase = "complete"
    elif "Starting transfer" in text:
        phase = "transferring"
    return {"path": path, "receivers": receivers, "phase": phase,
            "last_line": text.strip().splitlines()[-1] if text.strip() else None}

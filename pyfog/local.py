"""Facts read from the machine pyfog runs on, outside the database.

    processes      /proc, to find udp-sender processes and FOG's sh wrappers
    interfaces     /proc/net/dev, for the throughput while hosts are imaging
    neighbours     /proc/net/arp and arping, to see which hosts answer on the wire
    access logs    the web server log, to see when a FOG client last called in
    image store    the storage node's own directories, for what an image weighs
    udpcast logs   udp-sender's own output, to see which receivers joined
"""

import gzip
import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone

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
    try:
        entries = os.listdir("/proc")
        ticks = os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError):
        return {}  # not Linux, or /proc not mounted: no process facts
    for entry in entries:
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


_local_names = None


def local_names():
    """Hostnames and addresses that mean "this machine". Cached: a watch
    loop must not resolve the hostname on every refresh."""
    global _local_names
    if _local_names is None:
        _local_names = _find_local_names()
    return _local_names


def _find_local_names():
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


# -- interface throughput ---------------------------------------------------


NET_DEV = "/proc/net/dev"

# The reading the last call left behind: (monotonic time, counters).
_last_bytes = None


def interface_bytes():
    """interface -> (received, sent) byte counters since boot."""
    counters = {}
    try:
        with open(NET_DEV) as handle:
            lines = handle.readlines()[2:]  # two header lines
    except IOError:
        return counters  # not Linux, or /proc not mounted
    for line in lines:
        name, sep, rest = line.partition(":")
        fields = rest.split()
        if not sep or len(fields) < 9:
            continue
        try:
            counters[name.strip()] = (int(fields[0]), int(fields[8]))
        except ValueError:
            continue
    return counters


def throughput(sample=1.0, min_gap=0.4, max_gap=60.0):
    """Bytes per second per interface, busiest first.

    The same numbers `vnstat -l` shows, taken from the same place vnstat
    takes them: the kernel's counters in /proc/net/dev. Two readings and
    the time between them are the whole measurement, so nothing has to be
    installed or kept running for it.

    The previous reading is remembered. `pyfog dashboard` redraws every
    few seconds, and the gap between two redraws is a longer and steadier
    sample than anything a single call could take, so a watch loop pays
    nothing for this. A one-shot command has no reading to compare
    against, and sleeps `sample` seconds for a second one; a reading older
    than `max_gap` (a paused watch, a resumed terminal) is treated the
    same way, because a rate averaged over minutes says nothing about now.
    """
    global _last_bytes
    now = time.monotonic()
    counters = interface_bytes()
    if not counters:
        return []
    before = _last_bytes
    _last_bytes = (now, counters)
    if before is None or not (min_gap <= now - before[0] <= max_gap):
        before = _last_bytes
        time.sleep(sample)
        now, counters = time.monotonic(), interface_bytes()
        _last_bytes = (now, counters)
    gap = now - before[0]
    if gap <= 0:
        return []
    rates = []
    for name, (rx, tx) in sorted(counters.items()):
        was = before[1].get(name)
        # Unknown a moment ago (an interface that just came up), or the
        # counter went backwards: a 32 bit counter wrapped, or the
        # interface was reset. Either way there is no rate to report.
        if name == "lo" or was is None or rx < was[0] or tx < was[1]:
            continue
        rates.append({"interface": name, "seconds": gap,
                      "rx": (rx - was[0]) / gap, "tx": (tx - was[1]) / gap})
    rates.sort(key=lambda r: r["rx"] + r["tx"], reverse=True)
    return rates


# -- who answers on the wire ------------------------------------------------


PROC_ARP = "/proc/net/arp"

# Both arpings (iputils and Habets) name the answering MAC in their reply
# line and nowhere before it: "Unicast reply from 10.0.0.11 [00:11:...]"
# and "60 bytes from 00:11:... (10.0.0.11)".
MAC_IN_TEXT = re.compile(r"[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}")


def neighbours():
    """mac -> {"ip", "device"} from the kernel's ARP cache.

    Free, and no packet leaves the machine: this is what the server
    already knows. Incomplete entries (flags 0x0) are left out -- they are
    addresses the kernel asked about and got no answer for, which is the
    opposite of the fact wanted here.
    """
    found = {}
    try:
        with open(PROC_ARP) as handle:
            lines = handle.readlines()[1:]  # one header line
    except IOError:
        return found
    for line in lines:
        fields = line.split()
        if len(fields) < 6 or fields[2] == "0x0":
            continue
        mac = normalize_mac(fields[3])
        if len(mac) == 12:
            found[mac] = {"ip": fields[0], "device": fields[5]}
    return found


def default_interface():
    """The device the default route uses; arping wants one on a server with
    more than one network."""
    try:
        out = subprocess.check_output(["ip", "-o", "route", "show", "default"],
                                      stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"\bdev\s+(\S+)", out.decode("ascii", "replace"))
    return match.group(1) if match else None


def arping_one(ip, interface=None, timeout=1.0):
    """One ARP request to one address: (answering mac or None, error or None).

    ARP is answered by the network stack itself, so a machine that is on
    but whose FOG client is not running still replies. It also never
    leaves the local segment: a host behind a router is silent here no
    matter how healthy it is.
    """
    cmd = ["arping", "-c", "1", "-w", "%d" % max(1, int(round(timeout)))]
    if interface:
        cmd += ["-I", interface]
    cmd.append(ip)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as error:
        return None, "arping: %s" % error.strerror  # not installed
    try:
        out = proc.communicate(timeout=timeout + 5)[0]
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None, "arping did not return"
    text = out.decode("utf-8", "replace")
    match = MAC_IN_TEXT.search(text)
    if proc.returncode == 0 and match:
        return normalize_mac(match.group(0)), None
    if proc.returncode not in (0, 1):
        # Not "no answer" but a refusal: no permission for a raw socket,
        # an interface that does not exist, an address it cannot route.
        return None, text.strip().splitlines()[-1] if text.strip() else "arping failed"
    return None, None


def arping(targets, timeout=1.0, workers=32):
    """Probe several addresses at once; ip -> (mac or None, error or None).

    targets: [(ip, interface)]. One packet each, `workers` in flight, so a
    lab of a few hundred hosts is one short burst of ARP rather than one
    timeout after another.
    """
    targets = list(dict.fromkeys(targets))
    if not targets:
        return {}
    try:
        from concurrent.futures import ThreadPoolExecutor
    except ImportError:  # pragma: no cover - stdlib since 3.2
        return {ip: arping_one(ip, iface, timeout) for ip, iface in targets}
    with ThreadPoolExecutor(max_workers=min(workers, len(targets))) as pool:
        results = list(pool.map(lambda t: arping_one(t[0], t[1], timeout), targets))
    return {ip: result for (ip, _), result in zip(targets, results)}


# -- image store ------------------------------------------------------------


def stored_size(path):
    """What an image weighs here: the sum of the files under path, or the
    file's own size when the image is a single file.

    None when nothing can be measured -- the path is missing, or a
    directory in it cannot be listed. That is not always an error: with
    more than one storage node the image may live on another machine than
    the one pyfog runs on, and the caller then falls back to what the
    database was last told. A partial sum is never returned, because a
    size that is quietly too small is worse than no size at all.
    """
    if not path:
        return None
    if not os.path.isdir(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return None
    failed, total = [], 0
    for parent, _dirs, files in os.walk(path, onerror=failed.append):
        for name in files:
            try:
                total += os.lstat(os.path.join(parent, name)).st_size
            except OSError:
                # A file that went away mid-walk: a capture in progress
                # writes into its directory while this runs.
                failed.append(name)
    return None if failed else total


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
    """(mac -> {"last_seen", "ip", "path", "count"}, unreadable paths) from
    FOG client requests. last_seen is naive UTC; the caller shifts it to
    the clock it compares against.

    The FOG client identifies itself with a mac= parameter on every call
    (lib/fog/fogbase.class.php reads it from GET or POST), so any logged
    request carrying that parameter is a client check-in.
    """
    seen, unreadable = {}, []
    for path in paths:
        try:
            lines = _tail_lines(path, max_bytes)
        except OSError:
            unreadable.append(path)
            continue
        for line in lines:
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
            when = when.astimezone(timezone.utc).replace(tzinfo=None)
            for raw in re.split(r"[|,]|%7C|%2C", macs.group(1), flags=re.I):
                mac = normalize_mac(raw.replace("%3A", ":").replace("%3a", ":"))
                if len(mac) != 12:
                    continue
                entry = seen.setdefault(mac, {"last_seen": None, "ip": ip,
                                              "path": url, "count": 0})
                entry["count"] += 1
                if entry["last_seen"] is None or when > entry["last_seen"]:
                    entry.update(last_seen=when, ip=ip, path=url.split("?")[0])
    return seen, unreadable


# -- udpcast session log ----------------------------------------------------


def udpcast_log(path, max_bytes=256 * 1024):
    """Receivers and phase from a udp-sender log FOG keeps per session."""
    try:
        with open(path, "rb") as handle:
            handle.seek(max(0, os.path.getsize(path) - max_bytes))
            text = handle.read().decode("utf-8", "replace").replace("\r", "\n")
    except OSError:
        return None  # no log for this session, or not ours to read
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

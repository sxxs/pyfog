"""Command line wiring: parse arguments, call the data layer, print."""

import argparse
import io
import json
import os
import select
import sys
import termios
import time
import tty

from . import __version__, fog, render
from .config import ConfigError, Settings
from .db import Database, DatabaseError

# Keys that switch the live screen to another command's output.
VIEWS = [("t", "tasks"), ("m", "multicast"), ("h", "history"), ("s", "scheduled"),
         ("c", "clients"), ("d", "deployments"), ("i", "images"), ("o", "hosts"),
         ("g", "groups"), ("n", "snapins"), ("f", "info")]

STATE_WORDS = {"queued": [fog.QUEUED, fog.CHECKED_IN], "running": [fog.IN_PROGRESS],
               "complete": [fog.COMPLETE], "cancelled": [fog.CANCELLED],
               "active": list(fog.ACTIVE_STATES)}


def build_parser():
    def options(target, default):
        # Shared by the main parser and every subcommand, so they work in
        # both positions. SUPPRESS keeps a subcommand from resetting a value
        # given before it.
        target.add_argument("--json", action="store_true", default=default,
                            help="print JSON instead of tables")
        target.add_argument("--no-color", action="store_true", default=default)
        target.add_argument("--debug", action="store_true", default=default,
                            help="log every SQL statement to stderr")
        target.add_argument("--config", default=default, help="path to FOG's config.class.php")
        for name in ("--db-host", "--db-name", "--db-user", "--db-password"):
            target.add_argument(name, default=default)

    parser = argparse.ArgumentParser(
        prog="pyfog", description="Read-only view on a FOG server, straight from its database.")
    parser.add_argument("--version", action="version", version="pyfog " + __version__)
    options(parser, None)
    common = argparse.ArgumentParser(add_help=False)
    options(common, argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", metavar="command", parser_class=lambda **kw:
                                argparse.ArgumentParser(parents=[common], **kw))
    sub.required = True

    p = sub.add_parser("tasks", help="tasks that are queued or running (one line per multicast session)")
    p.add_argument("--state", help="active (default), queued, running, complete, cancelled, all, or ids")
    p.add_argument("--host", help="host name or IP contains")
    p.add_argument("--image", help="image name contains")
    p.add_argument("--type", help="task type contains, e.g. deploy, capture, multi")
    p.add_argument("--expand", action="store_true", help="one line per host inside multicast sessions")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--watch", type=int, metavar="SECONDS", help="refresh every N seconds")

    p = sub.add_parser("task", help="one task with everybody imaging alongside it")
    p.add_argument("id", type=int)

    p = sub.add_parser("history", help="finished tasks, newest first")
    p.add_argument("--host")
    p.add_argument("--image")
    p.add_argument("--days", type=int)
    p.add_argument("--expand", action="store_true")
    p.add_argument("--limit", type=int, default=100)

    sub.add_parser("scheduled", help="delayed and cron tasks FOG will create later")

    p = sub.add_parser("multicast", help="multicast sessions, participants, udp-sender processes")
    p.add_argument("--all", action="store_true", help="include finished sessions")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--watch", type=int, metavar="SECONDS")

    p = sub.add_parser("clients", help="when each host's FOG client last called in")
    p.add_argument("--log", action="append", help="web server access log (repeatable)")
    p.add_argument("--log-bytes", type=int, default=32 * 1024 * 1024,
                   help="how much of each log's tail to read")
    p.add_argument("--stale", type=int, metavar="MINUTES", help="mark hosts silent for longer than MINUTES")
    p.add_argument("--only-stale", action="store_true", help="with --stale: list only the hosts marked silent")

    p = sub.add_parser("deployments", help="imaging log: who got which image when")
    p.add_argument("--host")
    p.add_argument("--image")
    p.add_argument("--days", type=int)
    p.add_argument("--kind", choices=("deploy", "capture"))
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--current", action="store_true",
                   help="per host: assigned image versus last deployed image")

    sub.add_parser("images", help="image inventory")
    p = sub.add_parser("hosts", help="host inventory")
    p.add_argument("search", nargs="?", help="name, IP or description contains")
    sub.add_parser("groups", help="groups and their members")

    p = sub.add_parser("snapins", help="snapin runs per host with exit codes")
    p.add_argument("--host")
    p.add_argument("--snapin")
    p.add_argument("--failed", action="store_true")
    p.add_argument("--days", type=int)
    p.add_argument("--limit", type=int, default=200)

    sub.add_parser("info", help="versions, connection, counts, storage nodes")

    p = sub.add_parser("dashboard", help="one screen of live state, redrawn every few seconds; "
                       "single keys switch to the other commands' output")
    p.add_argument("--interval", type=int, default=3, metavar="SECONDS",
                   help="seconds between refreshes (default 3)")
    p.add_argument("--once", action="store_true",
                   help="print one screen and exit (implied when the output is not a terminal)")
    p.add_argument("--recent", type=int, default=8, metavar="N",
                   help="how many finished tasks to list (default 8)")
    return parser


def parse_states(text):
    if not text or text == "active":
        return fog.ACTIVE_STATES
    if text == "all":
        return ()
    states = []
    for word in text.split(","):
        word = word.strip().lower()
        if word.isdigit():
            states.append(int(word))
        elif word in STATE_WORDS:
            states.extend(STATE_WORDS[word])
        else:
            raise ValueError("unknown state %r; use %s, all or numbers"
                             % (word, ", ".join(STATE_WORDS)))
    return states


def collect(api, args):
    """Run the command's query; returns (data, render function, render kwargs)."""
    if args.command == "tasks":
        tasks = api.tasks(parse_states(args.state), args.host, args.image, args.type, args.limit)
        data = {"count": len(tasks), "entries": fog.group_multicast(tasks),
                "now": fog.dt_text(api.now()), "timeout": api.checkin_timeout(),
                "imaging_open": api.imaging_open()}
        return data, render.tasks, {"expand": args.expand}
    if args.command == "task":
        data = api.task(args.id)
        if data is None:
            raise LookupError("task %d does not exist" % args.id)
        return data, render.task, {}
    if args.command == "history":
        entries = fog.group_multicast(api.history(args.host, args.image, args.days, args.limit))
        return entries, render.history, {"expand": args.expand}
    if args.command == "scheduled":
        return api.scheduled(), render.scheduled, {}
    if args.command == "multicast":
        return api.multicast(args.all, args.limit), render.multicast, {}
    if args.command == "clients":
        data = api.clients(args.log, args.log_bytes)
        stale = args.stale * 60 if args.stale else None
        if stale and args.only_stale:
            data["hosts"] = [h for h in data["hosts"] if h["age"] is None or h["age"] > stale]
        return data, render.clients, {"stale_after": stale}
    if args.command == "deployments":
        if args.current:
            return api.current_images(), render.current_images, {}
        data = api.deployments(args.host, args.image, args.days, args.kind, args.limit)
        return data, render.deployments, {}
    if args.command == "images":
        return api.images(), render.images, {}
    if args.command == "hosts":
        return api.hosts(args.search), render.hosts, {}
    if args.command == "groups":
        return api.groups(), render.groups, {}
    if args.command == "snapins":
        data = api.snapins(args.host, args.snapin, args.failed, args.days, args.limit)
        return data, render.snapins, {}
    if args.command == "info":
        return api.info(), render.info, {}
    if args.command == "dashboard":
        return api.dashboard(args.recent), render.dashboard, {}
    raise ValueError(args.command)


def refresh_interval(args):
    """Seconds between rounds, or None for a single run."""
    interval = args.interval if args.command == "dashboard" else getattr(args, "watch", None)
    if interval is not None and interval < 1:
        raise ValueError("the refresh interval must be at least 1 second")
    if args.command == "dashboard" and (args.once or args.json or not sys.stdout.isatty()):
        return None
    return interval


def main(argv=None):
    args = build_parser().parse_args(argv)
    colour = not args.no_color and sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    palette = render.Palette(colour)
    try:
        settings = Settings(args.config, args.db_host, args.db_name, args.db_user, args.db_password)
        db = Database(settings, debug=args.debug)
    except (ConfigError, DatabaseError) as exc:
        sys.stderr.write("pyfog: %s\n" % exc)
        return 2
    try:
        interval = refresh_interval(args)
        if interval:
            db, watched = None, db
            return watch(args, settings, watched, palette, interval)
        data, show, kwargs = collect(fog.Fog(db, settings), args)
        if args.json:
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            show(data, palette, **kwargs)
        return 0
    except BrokenPipeError:
        # Output piped into head or less that stopped reading.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    except (DatabaseError, LookupError, ValueError, OSError) as exc:
        sys.stderr.write("pyfog: %s\n" % exc)
        return 1
    except KeyboardInterrupt:
        return 130
    finally:
        if db is not None:
            db.close()


def view_args(args, command):
    """Arguments for another command's view, with this run's global options."""
    view = build_parser().parse_args([command])
    for name in ("json", "no_color", "debug", "config", "db_host", "db_name", "db_user",
                 "db_password"):
        setattr(view, name, getattr(args, name))
    if command == "tasks":
        view.expand = True
    return view


class Keys(object):
    """Single key presses from a terminal on stdin, or nothing at all.

    Puts the terminal into cbreak mode (keys arrive without Enter, Ctrl-C
    still works) and restores it on exit. Without a terminal on stdin,
    for example `ssh host pyfog dashboard` without -t, read() only waits.
    """

    HOME = (b"\x1b[H", b"\x1b[1~", b"\x1bOH")

    def __init__(self, enabled=True):
        stdin = sys.stdin if enabled else None
        self.fd = stdin.fileno() if stdin is not None and stdin.isatty() else None
        self.saved = None

    def __enter__(self):
        if self.fd is not None:
            self.saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *exc):
        if self.saved is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)

    @property
    def enabled(self):
        return self.fd is not None

    def read(self, timeout, accept):
        """One of the accepted keys within timeout seconds, else None.
        Other keys are ignored and the wait goes on; "esc" and "home" name
        those keys, letters come back lower case."""
        deadline = time.monotonic() + max(0.0, timeout)
        if self.fd is None:
            time.sleep(max(0.0, timeout))
            return None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.fd], [], [], remaining)[0]:
                return None
            data = os.read(self.fd, 16)
            if data == b"\x1b" and select.select([self.fd], [], [], 0.05)[0]:
                data += os.read(self.fd, 16)  # the rest of a sequence over a slow link
            key = self.decode(data)
            if key in accept:
                return key

    @classmethod
    def decode(cls, data):
        if data == b"\x1b":
            return "esc"
        if data in cls.HOME:
            return "home"
        return data.decode("ascii", "replace").lower() if len(data) == 1 else None


def watch(args, settings, db, palette, interval):
    """Repeat the command every `interval` seconds until q or Ctrl-C.

    On a terminal the screen is redrawn in place: a status line owned by
    this loop, the key line, then the command's output. Keys switch to
    another command's output (see VIEWS); x, Escape or Home return to
    the command this started with. Into a pipe or with --json, every
    round appends one complete document instead, and errors go to stderr.

    A failed query does not end the loop: the last good screen stays up
    with the error in the status line, and the next round reconnects.
    """
    live = sys.stdout.isatty() and not args.json
    home = current = args
    body = ""
    views = dict(VIEWS)
    accept = set(views) | {"q", "x", "esc", "home"}
    key_line = "  ".join("%s %s" % (key, name) for key, name in VIEWS) + "  x back  q quit"
    try:
        with Keys(enabled=live) as keys:
            while True:
                started = time.monotonic()
                error = None
                try:
                    if db is None:
                        db = Database(settings, debug=args.debug)
                    data, show, kwargs = collect(fog.Fog(db, settings), current)
                    if args.json:
                        body = json.dumps(data, indent=2, ensure_ascii=False)
                    else:
                        out = io.StringIO()
                        show(data, palette, out=out, **kwargs)
                        body = out.getvalue()
                except (DatabaseError, OSError) as exc:
                    error = exc
                    if isinstance(exc, DatabaseError) and db is not None:
                        db.close()
                        db = None
                stamp = time.strftime("%H:%M:%S")
                if not live:
                    if error is None:
                        sys.stdout.write(body.rstrip("\n") + "\n")
                    else:
                        sys.stderr.write("pyfog: %s: %s, retrying in %ds\n" % (stamp, error, interval))
                else:
                    if error is None:
                        status = palette.dim("pyfog %s  refreshed %s in %d ms, every %ds" % (
                            current.command, stamp, (time.monotonic() - started) * 1000, interval))
                    else:
                        status = palette.red("pyfog %s  %s  %s, retrying every %ds" % (
                            current.command, stamp, error, interval))
                    if keys.enabled:
                        status += "\n" + palette.dim(key_line)
                    sys.stdout.write(render.frame(status + "\n" + body))
                sys.stdout.flush()
                key = keys.read(interval - (time.monotonic() - started), accept)
                if key == "q":
                    sys.stdout.write("\n")
                    return 0
                if key in ("x", "esc", "home"):
                    current = home
                elif key in views:
                    current = view_args(args, views[key])
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        return 130
    finally:
        if db is not None:
            db.close()

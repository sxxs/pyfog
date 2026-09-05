"""Command line wiring: parse arguments, call the data layer, print."""

import argparse
import json
import os
import sys
import time

from . import __version__, fog, render
from .config import ConfigError, Settings
from .db import Database, DatabaseError

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

    p = sub.add_parser("tasks", help="tasks that are queued or running (multicast folded per session)")
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
    p.add_argument("--stale", type=int, metavar="MINUTES", help="mark hosts silent for longer")
    p.add_argument("--only-stale", action="store_true", help="with --stale: list only those")

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
    raise ValueError(args.command)


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
    api = fog.Fog(db, settings)
    try:
        while True:
            data, show, kwargs = collect(api, args)
            if args.json:
                json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
                sys.stdout.write("\n")
            else:
                if getattr(args, "watch", None):
                    sys.stdout.write("\033[2J\033[H")
                show(data, palette, **kwargs)
            if not getattr(args, "watch", None):
                return 0
            sys.stdout.flush()
            time.sleep(args.watch)
            db._now = None
    except (DatabaseError, LookupError, ValueError) as exc:
        sys.stderr.write("pyfog: %s\n" % exc)
        return 1
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        # Output piped into head or less that stopped reading.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    finally:
        db.close()

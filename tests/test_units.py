"""Unit tests for the parts that need no database. Run: python3 -m unittest"""

import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyfog import cli, config, fog, local, render, util  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_php_defines_with_escaped_quotes(self):
        text = ("<?php define('DATABASE_HOST', 'db.example:3307');\n"
                "define('DATABASE_PASSWORD', 'it\\'s\\\\here');\n"
                "define('UDPSENDERPATH', '/usr/local/sbin/udp-sender');")
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as fh:
            fh.write(text)
        try:
            found = config.read_php_config(fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(found["DATABASE_PASSWORD"], "it's\\here")
        settings = config.Settings(environ={"PYFOG_CONF": "/nonexistent"},
                                   db_host="db.example:3307", db_user="fogread")
        self.assertEqual(settings.hostport, ("db.example", 3307))

    def test_fog_config_supplies_host_but_never_the_account(self):
        php = "<?php define('DATABASE_HOST', 'dbhost'); define('DATABASE_USERNAME', 'fogmaster');"
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as fh:
            fh.write(php)
        try:
            with self.assertRaises(config.ConfigError):
                config.Settings(config=fh.name, environ={"PYFOG_CONF": "/nonexistent"})
            settings = config.Settings(config=fh.name, environ={"PYFOG_CONF": "/nonexistent"},
                                       db_user="fogread", db_password="s")
        finally:
            os.unlink(fh.name)
        self.assertEqual(settings.values["DATABASE_HOST"], "dbhost")
        self.assertEqual(settings.values["DATABASE_USERNAME"], "fogread")
        self.assertEqual(settings.source, "user, password from command line; host from %s; "
                                          "database from default" % fh.name)

    def test_conf_below_environment_below_arguments(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("# pyfog\nPYFOG_DB_USER=fogread\nPYFOG_DB_PASSWORD='it''s'\nPYFOG_DB_HOST=confhost\n")
        try:
            environ = {"PYFOG_CONF": fh.name, "PYFOG_DB_HOST": "envhost", "PYFOG_CONFIG": "/nonexistent"}
            settings = config.Settings(environ=environ, db_name="other")
        finally:
            os.unlink(fh.name)
        self.assertEqual(settings.values["DATABASE_PASSWORD"], "it''s")
        self.assertEqual((settings.values["DATABASE_HOST"], settings.values["DATABASE_NAME"]),
                         ("envhost", "other"))
        self.assertEqual(settings.sources["DATABASE_USERNAME"], fh.name)

    def test_unreadable_fog_config_is_not_fatal(self):
        def denied(path):
            raise IOError(13, "Permission denied", path)
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False) as fh:
            fh.write("<?php\n")
        original = config.read_php_config
        config.read_php_config = denied
        try:
            settings = config.Settings(config=fh.name, environ={"PYFOG_CONF": "/nonexistent"},
                                       db_user="u")
        finally:
            config.read_php_config = original
            os.unlink(fh.name)
        self.assertEqual(settings.values["DATABASE_HOST"], "localhost")
        self.assertIn("not readable", settings.sources["DATABASE_HOST"])

    def test_fogsettings_fallback_strips_quotes(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("## FOG settings\nsnmysqlhost='db.example'\nsnmysqluser='fogmaster'\n"
                     "snmysqlpass=\"secret\"\nwebdirdest=\"/var/www/html/fog\"\n")
        try:
            found = config.read_fogsettings(fh.name)
        finally:
            os.unlink(fh.name)
        # FOG's own account is never picked up, only host and web root.
        self.assertEqual(found, {"DATABASE_HOST": "db.example", "WEBDIR": "/var/www/html/fog"})


class SqlTests(unittest.TestCase):
    def test_queries_use_pymysql_placeholders(self):
        # A literal % in SQL text would break PyMySQL's parameter substitution.
        import inspect
        source = inspect.getsource(fog)
        self.assertNotIn("?", re.sub(r'"""[\s\S]*?"""', "", source).split("class Fog")[0])
        for chunk in re.findall(r"%[^s(]", fog.TASK_SQL + fog.SESSION_SQL):
            self.fail("stray %% in SQL: %r" % chunk)


class UtilTests(unittest.TestCase):
    def test_zero_dates_are_never(self):
        self.assertIsNone(util.parse_dt("0000-00-00 00:00:00"))
        self.assertEqual(util.dt_text("2026-01-02 03:04:05"), "2026-01-02 03:04:05")

    def test_mac_normalisation(self):
        self.assertEqual(util.pretty_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(util.normalize_mac("00:11:22:33:44:55"), "001122334455")


class LocalTests(unittest.TestCase):
    def test_sender_options(self):
        argv = ["/usr/local/sbin/udp-sender", "--min-receivers", "3", "--portbase", "63100",
                "--nokbd", "--file", "/images/x/d1p1.img"]
        found = local.sender_options(argv)
        self.assertEqual(found["portbase"], 63100)
        self.assertEqual(found["min_receivers"], 3)
        self.assertEqual(found["file"], "/images/x/d1p1.img")

    def test_wrapper_is_not_a_sender(self):
        wrapper = {"argv": ["sh", "-c", "/usr/local/sbin/udp-sender --portbase 1"], "exe": "/bin/dash"}
        sender = {"argv": ["/usr/local/sbin/udp-sender", "--portbase", "1"], "exe": None}
        self.assertFalse(local.is_udp_sender(wrapper))
        self.assertTrue(local.is_udp_sender(sender))

    def test_client_calls_from_access_log(self):
        lines = [
            '10.0.0.11 - - [05/Sep/2026:08:00:00 +0000] "GET /fog/service/jobs.php?mac=00:11:22:33:44:01 HTTP/1.1" 200 1',
            'vhost:80 10.0.0.11 - - [05/Sep/2026:09:00:00 +0000] "GET /fog/management/index.php?sub=requestClientInfo&mac=00%3A11%3A22%3A33%3A44%3A01%7Caa:bb:cc:dd:ee:ff&json HTTP/1.1" 200 1',
            '10.0.0.99 - - [05/Sep/2026:09:30:00 +0000] "GET /fog/management/index.php?node=host HTTP/1.1" 200 1',
        ]
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("\n".join(lines) + "\n")
        try:
            calls, unreadable = local.client_calls([fh.name, "/nonexistent/access.log"], 1 << 20)
        finally:
            os.unlink(fh.name)
        self.assertEqual(unreadable, ["/nonexistent/access.log"])
        self.assertEqual(set(calls), {"001122334401", "aabbccddeeff"})
        self.assertEqual(calls["001122334401"]["count"], 2)
        self.assertEqual(calls["001122334401"]["path"], "/fog/management/index.php")
        # Naive UTC, whatever this process's time zone is.
        self.assertEqual(calls["001122334401"]["last_seen"], datetime(2026, 9, 5, 9, 0, 0))

    def test_udpcast_log(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("New connection from 10.0.0.11  (#0)\rNew connection from 10.0.0.12  (#1)\n"
                     "Starting transfer: 00000009\rbytes= 1 234\r")
        try:
            log = local.udpcast_log(fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(log["receivers"], ["10.0.0.11", "10.0.0.12"])
        self.assertEqual(log["phase"], "transferring")


def _task(**kw):
    base = {"id": 1, "name": "Multi-Cast - Lab", "type": "Multi-Cast", "image": "img",
            "created": "2026-01-01 10:00:00", "state": "Queued", "percent": 0, "stale": False,
            "multicast_session": 7}
    base.update(kw)
    return base


class SenderMatchingTests(unittest.TestCase):
    def session(self, **kw):
        base = {"id": 1, "active": True, "port": 63100, "sender_pid": 50,
                "sender_node": "fog", "sender_address": "fog.example"}
        base.update(kw)
        return base

    def test_remote_and_finished_sessions_claim_nothing(self):
        procs = {50: {"ppid": 1}, 99: {"ppid": 50}}
        senders = {99: {"pid": 99, "portbase": 63100}}
        local_session = self.session()
        remote = self.session(id=2, sender_address="other.example")
        finished = self.session(id=3, active=False)
        claimed = fog.match_senders([remote, finished], procs, senders, {"fog.example"})
        self.assertEqual(claimed, set())
        self.assertFalse(remote["sender_local"])
        self.assertEqual((remote["wrapper_alive"], remote["senders"]), (None, []))
        self.assertEqual((finished["wrapper_alive"], finished["senders"]), (True, []))
        claimed = fog.match_senders([local_session], procs, senders, {"fog.example"})
        self.assertEqual(claimed, {99})
        self.assertEqual([s["pid"] for s in local_session["senders"]], [99])

    def test_session_without_node_counts_as_local(self):
        session = self.session(sender_node=None, sender_address=None, sender_pid=None)
        fog.match_senders([session], {}, {}, set())
        self.assertTrue(session["sender_local"])
        self.assertIsNone(session["wrapper_alive"])


class GroupingTests(unittest.TestCase):
    def test_multicast_rows_fold_into_one_entry(self):
        tasks = [_task(id=1, state="In-Progress", percent=30),
                 _task(id=2, state="In-Progress", percent=45),
                 _task(id=3),
                 _task(id=4, multicast_session=None, name="Deploy - pc9")]
        entries = fog.group_multicast(tasks)
        self.assertEqual(len(entries), 2)
        session = entries[0]
        self.assertEqual(session["session"], 7)
        self.assertEqual(session["name"], "Lab")
        self.assertEqual(session["states"], {"In-Progress": 2, "Queued": 1})
        self.assertEqual((session["percent_min"], session["percent_max"]), (30, 45))
        self.assertEqual(entries[1]["id"], 4)


class CliTests(unittest.TestCase):
    def test_state_words(self):
        self.assertEqual(cli.parse_states("running,cancelled"), [3, 5])
        self.assertEqual(cli.parse_states("all"), ())
        self.assertEqual(cli.parse_states(None), fog.ACTIVE_STATES)
        with self.assertRaises(ValueError):
            cli.parse_states("bogus")

    def test_view_args_keep_global_options(self):
        args = cli.build_parser().parse_args(["--no-color", "--db-host", "x", "dashboard"])
        view = cli.view_args(args, "tasks")
        self.assertEqual((view.command, view.expand, view.no_color, view.db_host),
                         ("tasks", True, True, "x"))
        self.assertEqual(cli.view_args(args, "clients").command, "clients")
        self.assertEqual(sorted(name for _, name in cli.VIEWS),
                         sorted(("tasks", "multicast", "history", "scheduled", "clients",
                                 "deployments", "images", "hosts", "groups", "snapins", "info")))

    def test_keys_decode(self):
        self.assertEqual(cli.Keys.decode(b"\x1b"), "esc")
        self.assertEqual(cli.Keys.decode(b"\x1b[H"), "home")
        self.assertEqual(cli.Keys.decode(b"\x1bOH"), "home")
        self.assertIsNone(cli.Keys.decode(b"\x1b[A"))
        self.assertEqual(cli.Keys.decode(b"Q"), "q")

    def test_interval_must_be_positive(self):
        parser = cli.build_parser()
        for argv in (["dashboard", "--interval", "0"], ["tasks", "--watch", "-1"]):
            with self.assertRaises(ValueError):
                cli.refresh_interval(parser.parse_args(argv))

    def test_dashboard_refreshes_only_on_a_terminal(self):
        parser = cli.build_parser()
        self.assertIsNone(cli.refresh_interval(parser.parse_args(["dashboard", "--once"])))
        self.assertIsNone(cli.refresh_interval(parser.parse_args(["dashboard", "--json"])))
        self.assertEqual(cli.refresh_interval(parser.parse_args(["tasks", "--watch", "5"])), 5)
        self.assertIsNone(cli.refresh_interval(parser.parse_args(["tasks"])))

    def test_global_options_work_after_the_subcommand(self):
        parser = cli.build_parser()
        self.assertTrue(parser.parse_args(["tasks", "--json"]).json)
        self.assertTrue(parser.parse_args(["--json", "tasks"]).json)
        self.assertFalse(parser.parse_args(["tasks"]).json)


class RenderTests(unittest.TestCase):
    def test_age_text(self):
        self.assertEqual(render.age_text(59), "59s")
        self.assertEqual(render.age_text(3661), "1h 01m")
        self.assertEqual(render.age_text(None), "-")

    def test_table_fits_narrow_terminal(self):
        table = render.Table("A", ">B")
        table.add("x" * 300, 1)
        out = _Buffer()
        table.write(out, render.Palette(False))
        self.assertTrue(all(len(line) <= 200 for line in out.text.splitlines()))

    def test_dashboard_renders_the_fixture(self):
        with open(os.path.join(os.path.dirname(__file__), "dashboard.json")) as fh:
            data = json.load(fh)
        out = _Buffer()
        render.dashboard(data, render.Palette(False), out)
        for expected in ("Active tasks: 6", "1 stale", "1 imaging run without a task",
                         "MC1", "Multicast session 1", "Recently finished tasks", "Scheduled tasks"):
            self.assertIn(expected, out.text)

    def test_frame_never_scrolls_or_wraps(self):
        text = "\n".join("line %d, %s" % (i, "x" * 40) for i in range(40))
        frame = render.frame(text, size=(20, 10))
        self.assertTrue(frame.startswith("\033[H"))
        self.assertTrue(frame.endswith("\033[K\033[J"))
        self.assertEqual(frame.count("\n"), 9)
        self.assertIn("31 more lines", frame)
        lines = render.ANSI.sub("", frame.replace("\033[H", "").replace("\033[J", "")).split("\n")
        self.assertTrue(all(len(line.replace("\033[K", "")) <= 20 for line in lines))
        self.assertEqual(render.frame("a\nb", size=(20, 10)), "\033[Ha\033[K\nb\033[K\033[J")
        self.assertEqual(render.frame("x" * 20, size=(20, 10)).count("x"), 18)  # never the last column
        self.assertNotIn("more lines", render.frame("a\nb\nc", size=(0, 0)))

    def test_history_marks_cancelled_tasks_by_their_last_sign_of_life(self):
        task = {"id": 9, "host": "pc", "type": "Deploy", "image": "i", "result": "cancelled",
                "created": "2026-09-04 19:00:00", "started": "2026-09-04 19:38:00",
                "finished": None, "duration": None, "created_by": "fog",
                "last_checkin": "2026-09-04 19:47:32"}
        out = _Buffer()
        render.history([task], render.Palette(False), out)
        self.assertIn("silent since 2026-09-04 19:47", out.text)
        task.update(last_checkin=None)
        out = _Buffer()
        render.history([task], render.Palette(False), out)
        self.assertIn("never checked in", out.text)

    def test_scheduled_without_a_date(self):
        out = _Buffer()
        render.scheduled([{"id": 1, "name": "n", "type": "Deploy", "when": None, "cron": None,
                           "target_kind": "host", "target": "pc", "image": "i", "active": True}],
                         render.Palette(False), out)
        self.assertIn("never", out.text)


class _Buffer(object):
    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the parts that need no database. Run: python3 -m unittest"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime  # noqa: E402

from pyfog import cli, config, fog, local, render, util  # noqa: E402


def rows_dt(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")


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


    def test_client_jitter_is_read_from_the_web_root(self):
        root = tempfile.mkdtemp()
        fogdir = os.path.join(root, "lib", "fog")
        os.makedirs(fogdir)
        conf = os.path.join(fogdir, "config.class.php")
        page = os.path.join(fogdir, "fogpage.class.php")
        with open(conf, "w") as fh:
            fh.write("<?php define('DATABASE_HOST', 'dbhost');")
        settings = config.Settings(config=conf, environ={"PYFOG_CONF": "/nonexistent"},
                                   db_user="fogread", db_password="s")
        self.assertEqual(settings.webroot, root)
        # No fogpage.class.php: nothing is guessed.
        self.assertIsNone(settings.client_jitter())
        # Both call sites patched to the same window.
        with open(page, "w") as fh:
            fh.write("<?php\n$a = array_shift($Services) + mt_rand(1, 11);\n"
                     "$vals = array('sleep' => $checkin + mt_rand(1, 11));\n")
        self.assertEqual(settings.client_jitter(), (1, 11))
        # Only one of the two patched: pyfog says it does not know.
        with open(page, "w") as fh:
            fh.write("<?php\n$a = array_shift($Services) + mt_rand(1, 11);\n"
                     "$vals = array('sleep' => $checkin + mt_rand(1, 91));\n")
        self.assertIsNone(settings.client_jitter())
        shutil.rmtree(root)

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

    def test_stored_size_sums_an_image_directory(self):
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "WS20260905_01"))
            for name, size in (("d1p1.img", 15074415), ("d1p2.img", 5427), ("d1.mbr", 1048576)):
                with open(os.path.join(root, "WS20260905_01", name), "wb") as fh:
                    fh.write(b"\0" * 8)
                    fh.truncate(size)
            self.assertEqual(local.stored_size(os.path.join(root, "WS20260905_01")),
                             15074415 + 5427 + 1048576)
            # A single file image, and a path that is not there at all.
            self.assertEqual(local.stored_size(os.path.join(root, "WS20260905_01", "d1.mbr")),
                             1048576)
            self.assertIsNone(local.stored_size(os.path.join(root, "gone")))
            self.assertIsNone(local.stored_size(None))
        finally:
            shutil.rmtree(root)

    def test_stored_size_reports_nothing_rather_than_too_little(self):
        # An unreadable directory would otherwise be summed as 0 bytes, which
        # reads like an empty image instead of like a failed measurement.
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "img", "sub"))
            with open(os.path.join(root, "img", "d1p1.img"), "wb") as fh:
                fh.truncate(4096)
            os.chmod(os.path.join(root, "img", "sub"), 0)
            measured = local.stored_size(os.path.join(root, "img"))
            os.chmod(os.path.join(root, "img", "sub"), 0o755)
            if os.geteuid() != 0:  # root may list it anyway
                self.assertIsNone(measured)
        finally:
            shutil.rmtree(root)

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


class ClockTests(unittest.TestCase):
    class FakeDB(object):
        def __init__(self, rows, settings):
            self.rows = rows
            self._settings = settings

        def query(self, sql, params=()):
            if "globalSettings" in sql:
                return [{"settingKey": k, "settingValue": v} for k, v in self._settings.items()]
            return []

        def one(self, sql, params=()):
            return self.rows

        def scalar(self, sql, params=()):
            return self.rows["db"]

    def _fog(self, rows, tz):
        from datetime import datetime
        parsed = {k: datetime.strptime(v, "%Y-%m-%d %H:%M:%S") if v else None
                  for k, v in rows.items()}
        return fog.Fog(self.FakeDB(parsed, {"FOG_TZ_INFO": tz}), None)

    def test_reference_is_fog_utc_not_the_db_clock(self):
        # DB server runs local time (+2h); FOG stores UTC.
        rows = {"utc": "2026-09-05 12:00:00", "db": "2026-09-05 14:00:00", "fog": None}
        f = self._fog(rows, "UTC")
        self.assertEqual(f.now(), rows_dt(rows["utc"]))
        self.assertEqual(f._fog_utc_offset(), 0)
        self.assertEqual(f.clock_diagnosis()["db_skew"], 7200)

    def test_named_zone_uses_convert_tz(self):
        rows = {"utc": "2026-09-05 12:00:00", "db": "2026-09-05 12:00:00",
                "fog": "2026-09-05 14:00:00"}
        f = self._fog(rows, "Europe/Berlin")
        self.assertEqual(f.now(), rows_dt(rows["fog"]))
        self.assertEqual(f._fog_utc_offset(), 7200)

    def test_named_zone_without_tz_tables_falls_back(self):
        rows = {"utc": "2026-09-05 12:00:00", "db": "2026-09-05 13:00:00", "fog": None}
        f = self._fog(rows, "Europe/Berlin")
        self.assertEqual(f.now(), rows_dt(rows["db"]))
        self.assertIn("time zone tables", f._now_source)


class ClientSettingsTests(unittest.TestCase):
    """What pyfog info reports about the client's check-in interval, with and
    without patches/fog-client-checkin-jitter.patch on the server."""

    class FakeDB(object):
        def __init__(self, settings):
            self._settings = settings

        def query(self, sql, params=()):
            return [{"settingKey": k, "settingValue": v} for k, v in self._settings.items()]

    class FakeSettings(object):
        def __init__(self, jitter):
            self._jitter = jitter

        def client_jitter(self):
            return self._jitter

    def _client(self, jitter, checkin="29"):
        db = self.FakeDB({"FOG_CLIENT_CHECKIN_TIME": checkin, "FOG_GRACE_TIMEOUT": "300"})
        return fog.Fog(db, self.FakeSettings(jitter)).client_settings()

    def test_narrowed_jitter_from_the_web_root(self):
        c = self._client((1, 11))
        self.assertEqual(c["jitter"], (1, 11))
        self.assertEqual(c["sleep_sent"], (30, 40))
        self.assertEqual(c["sleep_effective"], (30, 40))
        self.assertEqual(c["jitter_source"], "web root")

    def test_unread_web_root_falls_back_to_the_shipped_window_and_says_so(self):
        c = self._client(None)
        self.assertEqual(c["sleep_sent"], (30, 120))
        self.assertIn("web root not read", c["jitter_source"])

    def test_check_in_time_below_the_client_floor_shows_the_replacement(self):
        # 20 + 1 = 21 s is under the client's minimum of 30 s, so it uses 60 s.
        c = self._client((1, 11), checkin="20")
        self.assertEqual(c["sleep_sent"], (21, 31))
        self.assertEqual(c["sleep_effective"], (60, 31))

class _Clock(object):
    """time.monotonic and time.sleep, on rails."""

    def __init__(self, *ticks):
        self.ticks, self.slept = list(ticks), []

    def monotonic(self):
        return self.ticks.pop(0)

    def sleep(self, seconds):
        self.slept.append(seconds)


class ThroughputTests(unittest.TestCase):
    def setUp(self):
        self.real_bytes, self.real_time = local.interface_bytes, local.time
        local._last_bytes = None

    def tearDown(self):
        local.interface_bytes, local.time = self.real_bytes, self.real_time
        local._last_bytes = None

    def readings(self, *counters):
        counters = list(counters)
        local.interface_bytes = lambda: counters.pop(0)

    def test_proc_net_dev_columns(self):
        path = os.path.join(tempfile.mkdtemp(), "dev")
        with open(path, "w") as fh:
            fh.write("Inter-|   Receive                    |  Transmit\n"
                     " face |bytes packets errs drop fifo frame compressed multicast|"
                     "bytes packets errs drop fifo colls carrier compressed\n"
                     "    lo:  100 1 0 0 0 0 0 0  100 1 0 0 0 0 0 0\n"
                     "  eth0:4294967296 9 0 0 0 0 0 0 8000 7 0 0 0 0 0 0\n")
        local.interface_bytes = self.real_bytes
        local.NET_DEV, old = path, local.NET_DEV
        try:
            self.assertEqual(local.interface_bytes(),
                             {"lo": (100, 100), "eth0": (4294967296, 8000)})
        finally:
            local.NET_DEV = old
        shutil.rmtree(os.path.dirname(path))

    def test_a_one_shot_call_takes_its_own_second_reading(self):
        self.readings({"eth0": (0, 0)}, {"eth0": (1024, 10 * 1024)})
        local.time = _Clock(100.0, 102.0)
        rates = local.throughput(sample=1.0)
        self.assertEqual(local.time.slept, [1.0])
        self.assertEqual(rates, [{"interface": "eth0", "seconds": 2.0,
                                  "rx": 512.0, "tx": 5120.0}])

    def test_a_watch_loop_measures_between_two_redraws(self):
        self.readings({"eth0": (0, 0)}, {"eth0": (0, 0)}, {"eth0": (0, 3000)})
        local.time = _Clock(100.0, 100.5)  # the first call has nothing to compare
        local.throughput(sample=0)
        local.time = _Clock(103.0)         # 2.5 s since the last redraw
        rates = local.throughput(sample=1.0)
        self.assertEqual(local.time.slept, [])
        self.assertEqual(rates[0]["tx"], 1200.0)

    def test_loopback_wrapped_counters_and_new_interfaces_are_left_out(self):
        self.readings({"lo": (0, 0), "eth0": (500, 0), "eth1": (900, 0)},
                      {"lo": (10 ** 9, 0), "eth0": (100, 0), "eth1": (1900, 0),
                       "eth2": (10 ** 6, 0)})
        local.time = _Clock(100.0, 101.0)
        rates = local.throughput(sample=0)
        self.assertEqual([r["interface"] for r in rates], ["eth1"])

    def test_quiet_machine_is_not_measured_at_all(self):
        self.readings()  # a reading would raise IndexError
        self.assertEqual(fog.Fog(None, None).network(busy=False), [])

    def test_imaging_now_counts_checked_in(self):
        self.assertTrue(fog.imaging_now([{"state_id": fog.CHECKED_IN}]))
        self.assertTrue(fog.imaging_now([{"state_id": fog.IN_PROGRESS}]))
        self.assertFalse(fog.imaging_now([{"state_id": fog.QUEUED},
                                          {"state_id": fog.COMPLETE}]))


class _Proc(object):
    """What subprocess.Popen gives back, without the process."""

    def __init__(self, text, returncode):
        self.text, self.returncode = text, returncode

    def communicate(self, timeout=None):
        return self.text.encode(), b""


class ArpTests(unittest.TestCase):
    def setUp(self):
        self.real_popen = local.subprocess.Popen

    def tearDown(self):
        local.subprocess.Popen = self.real_popen

    def answer(self, text, returncode=0):
        local.subprocess.Popen = lambda *a, **kw: _Proc(text, returncode)

    def test_arp_cache_skips_the_entries_nobody_answered(self):
        path = os.path.join(tempfile.mkdtemp(), "arp")
        with open(path, "w") as fh:
            fh.write("IP address       HW type     Flags       HW address"
                     "            Mask     Device\n"
                     "10.0.0.11        0x1         0x2         00:11:22:33:44:55"
                     "     *        eth0\n"
                     "10.0.0.99        0x1         0x0         00:00:00:00:00:00"
                     "     *        eth0\n")
        local.PROC_ARP, old = path, local.PROC_ARP
        try:
            self.assertEqual(local.neighbours(),
                             {"001122334455": {"ip": "10.0.0.11", "device": "eth0"}})
        finally:
            local.PROC_ARP = old
        shutil.rmtree(os.path.dirname(path))

    def test_both_arpings_are_read_the_same_way(self):
        self.answer("ARPING 10.0.0.11 from 10.0.0.1 eth0\n"
                    "Unicast reply from 10.0.0.11 [00:11:22:33:44:55]  0.700ms\n")
        self.assertEqual(local.arping_one("10.0.0.11"), ("001122334455", None))
        self.answer("ARPING 10.0.0.11\n"
                    "60 bytes from 00:11:22:33:44:55 (10.0.0.11): index=0 time=712.005 usec\n")
        self.assertEqual(local.arping_one("10.0.0.11"), ("001122334455", None))

    def test_silence_is_not_an_error_but_a_refusal_is(self):
        self.answer("ARPING 10.0.0.11\nTimeout\n", returncode=1)
        self.assertEqual(local.arping_one("10.0.0.11"), (None, None))
        self.answer("arping: socket: Operation not permitted\n", returncode=2)
        self.assertEqual(local.arping_one("10.0.0.11"),
                         (None, "arping: socket: Operation not permitted"))

    def test_a_missing_arping_is_reported_once_not_guessed_at(self):
        def missing(*a, **kw):
            raise OSError(2, "No such file or directory")
        local.subprocess.Popen = missing
        mac, error = local.arping_one("10.0.0.11")
        self.assertIsNone(mac)
        self.assertIn("No such file", error)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.real = (local.neighbours, local.default_interface, local.arping)

    def tearDown(self):
        local.neighbours, local.default_interface, local.arping = self.real

    def probe(self, hosts, cache, answers):
        local.neighbours = lambda: cache
        local.default_interface = lambda: "eth0"
        self.asked = []

        def arping(targets, timeout=1.0, workers=32):
            self.asked = list(targets)
            return {ip: answers[ip] for ip, _ in targets}
        local.arping = arping
        return fog.Fog(None, None).probe({"hosts": hosts})

    def test_the_kernel_knows_a_better_address_than_fogs_record(self):
        # FOG still has the address from the day the host was registered;
        # the ARP cache has where it answered from last.
        hosts = [{"mac": "00:11:22:33:44:55", "ip": "10.0.0.11"}]
        data = self.probe(hosts, {"001122334455": {"ip": "10.0.0.77", "device": "eth1"}},
                          {"10.0.0.77": ("001122334455", None)})
        self.assertEqual(self.asked, [("10.0.0.77", "eth1")])
        self.assertEqual(hosts[0]["live"]["up"], True)
        self.assertIsNone(data["probe_error"])

    def test_a_reply_from_a_different_machine_is_not_this_host(self):
        hosts = [{"mac": "00:11:22:33:44:55", "ip": "10.0.0.11"}]
        self.probe(hosts, {}, {"10.0.0.11": ("aabbccddeeff", None)})
        self.assertEqual(hosts[0]["live"]["up"], False)
        self.assertEqual(hosts[0]["live"]["mac_seen"], "aa:bb:cc:dd:ee:ff")

    def test_no_address_and_no_answer_are_told_apart(self):
        hosts = [{"mac": "00:11:22:33:44:55", "ip": None},
                 {"mac": "aa:bb:cc:dd:ee:ff", "ip": "10.0.0.12"},
                 {"mac": "00:00:00:00:00:01", "ip": "10.0.0.13"}]
        data = self.probe(hosts, {}, {"10.0.0.12": (None, None),
                                      "10.0.0.13": (None, "arping: not permitted")})
        self.assertEqual([h["live"]["how"] for h in hosts], [None, "arping", "arping"])
        self.assertEqual([h["live"]["up"] for h in hosts], [None, False, None])
        self.assertEqual(data["probe_error"], "arping: not permitted")


class SessionRowTests(unittest.TestCase):
    def row(self, **kw):
        base = {"msID": 5, "msName": "Multi-Cast Task - CPR_3", "imageName": "WS20260904_05",
                "stateName": "In-Progress", "msState": 3, "msBasePort": 63100,
                "inSession": 34, "msSessClients": 0, "msPercent": 0,
                "msStartDateTime": rows_dt("2026-09-05 16:09:10"),
                "msCompleteDateTime": None, "groupName": "default", "msInterface": "eth0",
                "msSenderPID": 293521, "nodeName": "fog", "nodeAddress": "fog.example",
                "msSenderStart": rows_dt("2026-09-05 16:09:13")}
        base.update(kw)
        return fog.Fog(None, None)._session(base)

    def test_the_assoc_rows_are_the_session_not_the_receivers(self):
        # 34 tasks linked to the session, nobody on the wire yet: the count
        # is what FOG queued, and msClients stays 0 for a group deploy.
        s = self.row()
        self.assertEqual(s["clients_in_session"], 34)
        self.assertEqual(s["clients_expected"], 34)

    def test_a_named_session_waits_for_the_size_it_was_given(self):
        # Hosts join a named session from the PXE menu, so the assoc rows
        # trail msSessClients until the last straggler has arrived.
        s = self.row(inSession=2, msSessClients=5)
        self.assertEqual((s["clients_in_session"], s["clients_expected"]), (2, 5))


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


class HistoryTests(unittest.TestCase):
    """Where the start and the end of a finished task come from.

    FOG stamps both of its taskLog rows with the task's creation time, so
    a task read out of taskLog always looks instantaneous. The real times
    are the host's check-in and, for a deploy or capture, the host's own
    imagingLog row.
    """

    class FakeDB(object):
        def __init__(self, rows):
            self.rows, self.sql = rows, None

        def query(self, sql, params=()):
            if "globalSettings" in sql:
                return []
            self.sql = sql
            return self.rows

        def one(self, sql, params=()):
            return {"utc": rows_dt("2026-09-05 21:40:00"), "db": None, "fog": None}

    def row(self, **kw):
        base = {"taskID": 321, "taskName": "Capture - LehrerPC100", "taskStateID": 4,
                "stateName": "Complete", "taskTypeID": 2, "typeName": "Capture",
                "taskHostID": 7, "hostName": "LehrerPC100", "hostIP": "10.0.0.100",
                "mac": "00:11:22:33:44:07", "imageID": 6, "imageName": "WS20260904_06",
                "taskPCT": 100, "taskBPM": "", "taskTimeElapsed": "", "taskTimeRemaining": "",
                "taskDataCopied": "", "taskDataTotal": "", "nodeName": "fog", "msID": None,
                "taskCreateTime": rows_dt("2026-09-05 21:16:00"),
                "taskCheckIn": rows_dt("2026-09-05 21:18:00"),
                "taskCreateBy": "fog", "taskScheduledStartTime": None,
                "taskForce": "0", "taskIsDebug": "0", "taskShutdown": "0", "taskWOL": "0",
                "completeRows": 1, "imagingStart": rows_dt("2026-09-05 21:18:00"),
                "finished": rows_dt("2026-09-05 21:28:00")}
        base.update(kw)
        db = self.FakeDB([base])
        self.db = db
        return fog.Fog(db, None).history()[0]

    def test_a_capture_lasts_as_long_as_its_imaging_run(self):
        entry = self.row()
        self.assertEqual((entry["started"], entry["finished"]),
                         ("2026-09-05 21:18:00", "2026-09-05 21:28:00"))
        self.assertEqual(entry["duration"], 600)
        self.assertTrue(entry["reported"])
        # The times taskLog holds are the task's creation time; asking it
        # for a duration is what made every task last zero seconds.
        self.assertNotIn("MIN(createTime)", self.db.sql)

    def test_a_task_that_writes_no_imaging_run_has_a_start_but_no_end(self):
        entry = self.row(taskID=317, taskTypeID=10, typeName="Hardware Inventory",
                         imagingStart=None, finished=None)
        self.assertEqual(entry["started"], "2026-09-05 21:18:00")
        self.assertIsNone(entry["finished"])
        self.assertIsNone(entry["duration"])
        self.assertTrue(entry["reported"])
        out = _Buffer()
        render.history([entry], render.Palette(False), out)
        self.assertIn("reported, no end time logged", out.text)

    def test_the_server_closing_a_task_still_reads_as_that(self):
        entry = self.row(taskTypeID=8, typeName="Multi-Cast", completeRows=0, finished=None)
        self.assertFalse(entry["reported"])
        out = _Buffer()
        render.history([entry], render.Palette(False), out)
        self.assertIn("closed by server, last report 2026-09-05 21:18", out.text)

    def test_a_snapin_job_has_no_start_because_its_check_in_keeps_moving(self):
        # The FOG client writes taskCheckIn again on every contact, so for
        # a snapin job it is the last report and not the start.
        entry = self.row(taskID=319, taskTypeID=13, typeName="Single Snapin",
                         imagingStart=None, finished=None)
        self.assertIsNone(entry["started"])
        self.assertEqual(entry["last_checkin"], "2026-09-05 21:18:00")


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

    def test_the_clients_view_inherits_the_probe_and_the_key_toggles_it(self):
        plain = cli.build_parser().parse_args(["dashboard"])
        probing = cli.build_parser().parse_args(["dashboard", "--arping",
                                                 "--arping-timeout", "2"])
        self.assertFalse(cli.view_args(plain, "clients").arping)
        view = cli.view_args(probing, "clients")
        self.assertEqual((view.arping, view.arping_timeout), (True, 2.0))
        # The key a is the live screen's own switch, so it wins over both.
        self.assertTrue(cli.view_args(plain, "clients", True).arping)
        self.assertFalse(cli.view_args(probing, "clients", False).arping)
        # A view that cannot probe is left alone rather than given the flag.
        self.assertFalse(hasattr(cli.view_args(probing, "tasks"), "arping"))
        self.assertEqual(sorted(name for _, name in cli.VIEWS),
                         sorted(("tasks", "multicast", "history", "scheduled", "clients",
                                 "deployments", "images", "hosts", "groups", "snapins", "info")))

    def test_keys_decode(self):
        self.assertEqual(cli.Keys.decode(b"\x1b"), "esc")
        self.assertEqual(cli.Keys.decode(b"\x1b[H"), "home")
        self.assertEqual(cli.Keys.decode(b"\x1bOH"), "home")
        self.assertEqual(cli.Keys.decode(b"\x1b[A"), "up")
        self.assertEqual(cli.Keys.decode(b"\x1b[6~"), "pgdn")
        self.assertIsNone(cli.Keys.decode(b"\x1b[Z"))
        self.assertEqual(cli.Keys.decode(b"Q"), "q")
        self.assertEqual(cli.Keys.decode(b"G"), "G")

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


class ImageSizeTests(unittest.TestCase):
    """Where the size of an image comes from, and what it means."""

    def test_image_dir_joins_the_node_root_and_the_image_folder(self):
        self.assertEqual(fog.image_dir("/images", "WS20260905_01"), "/images/WS20260905_01")
        self.assertEqual(fog.image_dir("/images/", "WS20260905_01"), "/images/WS20260905_01")
        self.assertEqual(fog.image_dir(None, "WS20260905_01"), "/images/WS20260905_01")
        # Old records keep a full path in imagePath; it is already the answer.
        self.assertEqual(fog.image_dir("/images", "/opt/img/x"), "/opt/img/x")
        self.assertIsNone(fog.image_dir("/images", ""))

    def test_client_size_sums_the_colon_list_fog_writes(self):
        self.assertEqual(fog.client_size("500107862016:"), 500107862016)
        self.assertEqual(fog.client_size("104857600:16777216:"), 121634816)
        self.assertIsNone(fog.client_size(""))
        self.assertIsNone(fog.client_size(None))
        self.assertIsNone(fog.client_size("0:"))

    def test_the_size_column_prefers_the_disk_and_marks_the_database(self):
        plain = render.Palette(False)
        base = {"id": 8, "name": "WS20260905_01", "os": "Windows 10", "type": "Single Disk",
                "format": "Partclone Zstd", "enabled": True, "protected": False,
                "hosts_assigned": 34, "storage_groups": ["default"], "path": "WS20260905_01",
                "last_deploy": "2026-09-05 22:11:00", "size_on_server": None}
        out = _Buffer()
        # Measured on this machine: shown, even though FOGImageSize has not
        # run yet and the database still says nothing.
        render.images([dict(base, size_on_disk=16817125329)], plain, out)
        self.assertIn("15.7 GiB", out.text)
        # Not measurable here: the database keeps the column populated.
        out = _Buffer()
        render.images([dict(base, size_on_disk=None, size_on_server=16323206183)], plain, out)
        self.assertIn("15.2 GiB", out.text)
        # Neither: no invented number.
        out = _Buffer()
        render.images([dict(base, size_on_disk=None)], plain, out)
        self.assertRegex(out.text.splitlines()[1], r"Zstd\s+-\s")


class RenderTests(unittest.TestCase):
    def test_age_text(self):
        self.assertEqual(render.age_text(59), "59s")
        self.assertEqual(render.age_text(3661), "1h 01m")
        self.assertEqual(render.age_text(None), "-")

    def test_clients_line_never_claims_receivers(self):
        self.assertEqual(render._clients({"clients_in_session": 34, "clients_expected": 34}),
                         "34 in session")
        self.assertEqual(render._clients({"clients_in_session": 2, "clients_expected": 5}),
                         "2 in session of 5 the sender waits for")

    def test_arp_column_says_which_kind_of_silence_it_is(self):
        plain = render.Palette(False)
        self.assertEqual(render.arp_text({"how": "arping", "up": True, "error": None,
                                          "mac_seen": "00:11:22:33:44:55"}, plain), "up")
        self.assertEqual(render.arp_text({"how": "arping", "up": False, "error": None,
                                          "mac_seen": "aa:bb:cc:dd:ee:ff"}, plain), "other host")
        self.assertEqual(render.arp_text({"how": "arping", "up": False, "error": None,
                                          "mac_seen": None}, plain), "silent")
        self.assertEqual(render.arp_text({"how": "arping", "up": None,
                                          "error": "no permission", "mac_seen": None}, plain), "?")
        self.assertEqual(render.arp_text({"how": None, "up": None, "error": None,
                                          "mac_seen": None}, plain), "-")
        self.assertEqual(render.arp_text(None, plain), "-")

    def test_arp_column_appears_only_when_the_hosts_were_asked(self):
        host = {"host": "pc01", "ip": "10.0.0.11", "mac": "00:11:22:33:44:55", "image": "Win11",
                "pending": False, "last_seen": "2026-09-05 12:00:00", "age": 30,
                "source": "log", "last_call_from": "10.0.0.11"}
        data = {"logs": ["/var/log/apache2/access.log"], "logs_unreadable": [],
                "now": "2026-09-05 12:00:30", "hosts": [dict(host)], "probed": False}
        out = _Buffer()
        render.clients(data, render.Palette(False), out)
        self.assertNotIn("ARP", out.text)
        data["probed"], data["probe_error"] = True, None
        data["hosts"] = [dict(host, live={"how": "arping", "up": True, "error": None,
                                          "mac_seen": "00:11:22:33:44:55"})]
        out = _Buffer()
        render.clients(data, render.Palette(False), out)
        self.assertIn("ARP", out.text.splitlines()[1])
        self.assertIn("up", out.text.splitlines()[2])

    def test_network_line_names_both_directions(self):
        rate = {"interface": "eth0", "rx": 2 * 1024, "tx": 120 * 1024 * 1024, "seconds": 3.0}
        self.assertEqual(render.network_text([rate]),
                         "eth0  out 120.0 MiB/s  in 2.0 KiB/s  (3.0s sample)")
        quiet = {"interface": "eth1", "rx": 10, "tx": 10, "seconds": 3.0}
        # Nothing is moving, but the line stays: one interface, the busiest.
        self.assertEqual(render.network_text([quiet]).split()[0], "eth1")
        self.assertIsNone(render.network_text([]))

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
                         "1 run left open by a cancelled task",
                         "10 cancelled, run left open",
                         "A cancelled task leaves its run open",
                         "Network  eth0  out 120.0 MiB/s  in 2.0 KiB/s  (3.0s sample)",
                         "Throughput     eth0  out 120.0 MiB/s",
                         "udp-sender pid 4712", "udpcast log: transferring, 2 receivers connected",
                         "MC1", "Multicast session 1", "Recently finished tasks", "Scheduled tasks"):
            self.assertIn(expected, out.text)

    def test_frame_never_scrolls_or_wraps(self):
        text = "\n".join("line %d, %s" % (i, "x" * 40) for i in range(40))
        frame, first, last, total = render.frame(text, size=(20, 10))
        self.assertTrue(frame.startswith("\033[H"))
        self.assertTrue(frame.endswith("\033[K\033[J"))
        self.assertEqual(frame.count("\n"), 9)
        self.assertIn("31 more lines", frame)
        self.assertEqual((first, last, total), (1, 10, 40))
        lines = render.ANSI.sub("", frame.replace("\033[H", "").replace("\033[J", "")).split("\n")
        self.assertTrue(all(len(line.replace("\033[K", "")) <= 20 for line in lines))
        self.assertEqual(render.frame("a\nb", size=(20, 10))[0], "\033[Ha\033[K\nb\033[K\033[J")
        self.assertEqual(render.frame("x" * 20, size=(20, 10))[0].count("x"), 18)  # never the last column
        self.assertNotIn("more lines", render.frame("a\nb\nc", size=(0, 0))[0])

    def test_frame_scrolls_the_body_under_a_fixed_head(self):
        text = "head\n" + "\n".join("line %d" % i for i in range(1, 41))
        frame, first, last, total = render.frame(text, size=(20, 10), fixed=1, skip=5)
        self.assertTrue(frame.startswith("\033[Hhead\033[K\nline 6\033[K"))
        self.assertEqual((first, last, total), (6, 14, 40))
        # Past the end: the last page stays full.
        frame, first, last, total = render.frame(text, size=(20, 10), fixed=1, skip=999)
        self.assertEqual((first, last, total), (32, 40, 40))
        self.assertNotIn("more lines", frame)

    def test_table_sorts_by_column_and_keeps_children(self):
        table = render.Table("HOST", ">AGE", "SIZE")
        table.add("MC1", "-", "3 hosts")
        table.add("  pc02", "5m 04s", "6.1GB/22.5GB", child=True)
        table.add("  pc01", "17h 00m", "6.0GB/22.5GB", child=True)
        table.add("pc09", "2d 01h", "-")
        table.add("pc03", "40s", "10.2GB/22.5GB")
        out = _Buffer()
        table.write(out, render.Palette(False), sort=render.Sort(1))
        hosts = [line.split()[0] for line in out.text.splitlines()[1:]]
        self.assertEqual(hosts, ["pc03", "pc09", "MC1", "pc02", "pc01"])  # "-" last, children attached
        self.assertIn("AGE▾", out.text)
        sort = render.Sort(-1, reverse=True)
        out = _Buffer()
        table.write(out, render.Palette(False), sort=sort)
        self.assertEqual(sort.column, 2)
        self.assertIn("SIZE▴", out.text)
        self.assertEqual(out.text.splitlines()[1].split()[0], "pc03")
        self.assertEqual(render.sort_key("45%"), (0, 45.0, "45%"))
        self.assertLess(render.sort_key("2026-09-04 19:47"), render.sort_key("2026-09-05 08:00"))

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

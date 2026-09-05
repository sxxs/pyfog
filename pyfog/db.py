"""SELECT-only access to the FOG database through the mysql client.

Every FOG server has the mysql/mariadb client installed (the installer
depends on it), so shelling out keeps pyfog free of Python packages. A
query returns a list of dicts whose values are str or None.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

from .util import parse_dt


class DatabaseError(Exception):
    pass


def sql_quote(value):
    """Quote a literal the way mysql_real_escape_string does."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value)
    for old, new in (("\\", "\\\\"), ("'", "\\'"), ('"', '\\"'), ("\n", "\\n"),
                     ("\r", "\\r"), ("\x1a", "\\Z"), ("\x00", "")):
        text = text.replace(old, new)
    return "'" + text + "'"


def inline(sql, params):
    """Replace ? placeholders with quoted literals."""
    for param in params:
        sql = sql.replace("?", sql_quote(param), 1)
    return sql


def _unescape_batch(cell):
    """Undo the escaping of `mysql --batch` output."""
    out, index = [], 0
    while index < len(cell):
        char = cell[index]
        if char == "\\" and index + 1 < len(cell):
            nxt = cell[index + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", "0": "\x00"}.get(nxt, nxt))
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


class Database(object):
    def __init__(self, settings, debug=False):
        self.settings = settings
        self.debug = debug
        self.client = shutil.which("mysql") or shutil.which("mariadb")
        if not self.client:
            raise DatabaseError("mysql client not found; install mariadb-client or mysql-client")
        self._defaults_file = None
        self._now = None
        self._settings_cache = None
        self.query("SELECT 1")

    def close(self):
        if self._defaults_file and os.path.exists(self._defaults_file):
            os.unlink(self._defaults_file)
            self._defaults_file = None

    def _defaults(self):
        """Password file for the client, so the password never hits argv."""
        if self._defaults_file is None:
            handle, path = tempfile.mkstemp(prefix="pyfog-", suffix=".cnf")
            # Option files process backslash escapes inside quotes.
            password = self.settings.values["DATABASE_PASSWORD"]
            with os.fdopen(handle, "w") as fh:
                fh.write('[client]\npassword="%s"\n'
                         % password.replace("\\", "\\\\").replace('"', '\\"'))
            os.chmod(path, 0o600)
            self._defaults_file = path
        return self._defaults_file

    def query(self, sql, params=()):
        """Run one SELECT with ? placeholders; returns a list of dicts."""
        sql = inline(" ".join(sql.split()), params)
        if not sql.lower().startswith(("select", "show")):
            raise DatabaseError("refusing to run a non-SELECT statement")
        if self.debug:
            sys.stderr.write("-- %s\n" % sql)
        host, port = self.settings.hostport
        cmd = [self.client, "--defaults-extra-file=%s" % self._defaults(), "--batch",
               "--host=%s" % host, "--user=%s" % self.settings.values["DATABASE_USERNAME"]]
        if port:
            cmd.append("--port=%d" % port)
        cmd.append(self.settings.values["DATABASE_NAME"])
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate(sql.encode("utf-8"))
        if proc.returncode != 0:
            raise DatabaseError(err.decode("utf-8", "replace").strip())
        lines = out.decode("utf-8", "replace").splitlines()
        if not lines:
            return []
        columns = lines[0].split("\t")
        # NULL and the string 'NULL' look alike in batch output; no column
        # this tool reads holds that string.
        return [dict(zip(columns, [None if c == "NULL" else _unescape_batch(c)
                                   for c in line.split("\t")]))
                for line in lines[1:]]

    def one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=()):
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

    def now(self):
        """Reference time from the database server, not from this machine."""
        if self._now is None:
            self._now = parse_dt(self.scalar("SELECT NOW()")) or datetime.now()
        return self._now

    def setting(self, key, default=None):
        """A row from globalSettings, cached for the process lifetime."""
        if self._settings_cache is None:
            rows = self.query("SELECT settingKey, settingValue FROM globalSettings")
            self._settings_cache = {r["settingKey"]: r["settingValue"] for r in rows}
        return self._settings_cache.get(key, default)

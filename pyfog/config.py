"""Where the database connection settings come from.

The account is pyfog's own read-only one, never FOG's. User and
password come from, highest first:

    --db-user / --db-password
    PYFOG_DB_USER / PYFOG_DB_PASSWORD
    /etc/pyfog.conf (or the file PYFOG_CONF names), written by install.sh

Host and database name take the same three, then fall back to FOG's own
config file (--config, PYFOG_CONFIG, or the usual locations) and to
/opt/fog/.fogsettings, the installer's answer file, which also tell
where the web root and udp-sender are.
"""

import errno
import os
import re


class ConfigError(Exception):
    pass


CONFIG_CANDIDATES = (
    "/var/www/html/fog/lib/fog/config.class.php",
    "/var/www/fog/lib/fog/config.class.php",
    "/var/www/html/lib/fog/config.class.php",
    "/var/www/lib/fog/config.class.php",
)

FOGSETTINGS_CANDIDATES = ("/opt/fog/.fogsettings",)

CONF_PATH = "/etc/pyfog.conf"

# The environment's names, also used inside /etc/pyfog.conf.
ENV_NAMES = {
    "DATABASE_HOST": "PYFOG_DB_HOST",
    "DATABASE_NAME": "PYFOG_DB_NAME",
    "DATABASE_USERNAME": "PYFOG_DB_USER",
    "DATABASE_PASSWORD": "PYFOG_DB_PASSWORD",
}


def _php_unquote(value):
    """Undo the escaping inside a PHP single quoted string literal."""
    return value.replace("\\\\", "\x00").replace("\\'", "'").replace("\x00", "\\")


def read_php_config(path):
    """The DATABASE_* and UDPSENDERPATH defines from config.class.php."""
    with open(path, "r", errors="replace") as handle:
        text = handle.read()
    found = {}
    for key in ("DATABASE_HOST", "DATABASE_NAME", "DATABASE_USERNAME",
                "DATABASE_PASSWORD", "UDPSENDERPATH", "MULTICASTINTERFACE"):
        match = re.search(
            r"define\(\s*['\"]" + key + r"['\"]\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)", text)
        if match:
            found[key] = _php_unquote(match.group(1))
    return found


def _assignments(path, mapping):
    """NAME=value lines of a shell style file, for the names in mapping,
    keyed by what mapping says; quotes around a value are dropped."""
    found = {}
    with open(path, "r", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() not in mapping:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            found[mapping[name.strip()]] = value
    return found


def read_fogsettings(path):
    """Fallback: the shell style answer file the installer leaves behind.
    Only host, database name and web root; FOG's account stays unused."""
    return _assignments(path, {"snmysqlhost": "DATABASE_HOST", "mysqldbname": "DATABASE_NAME",
                               "webdirdest": "WEBDIR"})


def read_conf(path):
    """/etc/pyfog.conf: PYFOG_DB_*=value lines."""
    return _assignments(path, {env: key for key, env in ENV_NAMES.items()})


class Settings(object):
    """Resolved connection settings plus where each of them was found."""

    def __init__(self, config=None, db_host=None, db_name=None, db_user=None,
                 db_password=None, environ=None):
        environ = os.environ if environ is None else environ
        self.webroot = None
        self.values = {
            "DATABASE_HOST": "localhost",
            "DATABASE_NAME": "fog",
            "UDPSENDERPATH": "/usr/local/sbin/udp-sender",
        }
        self.sources = {"DATABASE_HOST": "default", "DATABASE_NAME": "default"}

        # FOG's own files: host, database name, web root, udp-sender path.
        self.fog_config = None
        candidates = [config or environ.get("PYFOG_CONFIG")]
        if not candidates[0]:
            candidates = list(CONFIG_CANDIDATES)
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                found = read_php_config(path)
            except IOError as exc:
                if exc.errno != errno.EACCES:
                    raise
                self.sources["DATABASE_HOST"] = "default (%s not readable)" % path
                continue
            self.fog_config = path
            self.webroot = os.path.dirname(os.path.dirname(os.path.dirname(path)))
            break
        if self.fog_config is None:
            for path in FOGSETTINGS_CANDIDATES:
                try:
                    found = read_fogsettings(path)
                except IOError:
                    continue
                self.fog_config = path
                self.webroot = found.pop("WEBDIR", None)
                break
        if self.fog_config:
            for key in ("DATABASE_HOST", "DATABASE_NAME", "UDPSENDERPATH", "MULTICASTINTERFACE"):
                if key in found:
                    self.values[key] = found[key]
                    self.sources[key] = self.fog_config

        # pyfog's own account, and any overrides: conf < environment < args.
        conf_path = environ.get("PYFOG_CONF") or CONF_PATH
        try:
            layers = [(read_conf(conf_path), conf_path)]
        except IOError:
            layers = []
        layers.append(({key: environ[env] for key, env in ENV_NAMES.items() if environ.get(env)},
                       "environment"))
        layers.append(({key: value for key, value in (
            ("DATABASE_HOST", db_host), ("DATABASE_NAME", db_name),
            ("DATABASE_USERNAME", db_user), ("DATABASE_PASSWORD", db_password))
            if value is not None}, "command line"))
        for values, source in layers:
            for key, value in values.items():
                self.values[key] = value
                self.sources[key] = source
        if "DATABASE_USERNAME" not in self.values:
            raise ConfigError(
                "no database account: put PYFOG_DB_USER and PYFOG_DB_PASSWORD into %s "
                "(install.sh does that), or set them in the environment, or pass "
                "--db-user and --db-password" % conf_path)
        self.values.setdefault("DATABASE_PASSWORD", "")
        self.sources.setdefault("DATABASE_PASSWORD", self.sources["DATABASE_USERNAME"])

    @property
    def source(self):
        """Where the settings came from, for pyfog info."""
        labels = {"DATABASE_USERNAME": "user", "DATABASE_PASSWORD": "password",
                  "DATABASE_HOST": "host", "DATABASE_NAME": "database"}
        by_source = []
        for key, label in labels.items():
            source = self.sources[key]
            for entry in by_source:
                if entry[0] == source:
                    entry[1].append(label)
                    break
            else:
                by_source.append((source, [label]))
        return "; ".join("%s from %s" % (", ".join(names), source) for source, names in by_source)

    @property
    def hostport(self):
        """FOG stores 'host' or 'host:port' in one field."""
        host = self.values["DATABASE_HOST"]
        if host.count(":") == 1:
            name, _, port = host.partition(":")
            if port.isdigit():
                return name, int(port)
        return host, None

    def fog_version(self):
        """FOG_VERSION from the web root, the way FOG's own status page reads it."""
        if not self.webroot:
            return None
        path = os.path.join(self.webroot, "lib", "fog", "system.class.php")
        try:
            with open(path, "r", errors="replace") as handle:
                match = re.search(r"FOG_VERSION'\s*,\s*'([^']+)'", handle.read())
        except IOError:
            return None
        return match.group(1) if match else None

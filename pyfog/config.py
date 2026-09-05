"""Where the FOG database credentials come from.

Order of precedence, highest first:

    --db-host / --db-name / --db-user / --db-password
    PYFOG_DB_HOST / PYFOG_DB_NAME / PYFOG_DB_USER / PYFOG_DB_PASSWORD
    the FOG config file (--config, PYFOG_CONFIG, or the usual locations)
    /opt/fog/.fogsettings, the installer's answer file
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


def read_fogsettings(path):
    """Fallback: the shell style answer file the installer leaves behind."""
    mapping = {
        "snmysqlhost": "DATABASE_HOST",
        "snmysqluser": "DATABASE_USERNAME",
        "snmysqlpass": "DATABASE_PASSWORD",
        "mysqldbname": "DATABASE_NAME",
        "webdirdest": "WEBDIR",
    }
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


class Settings(object):
    """Resolved connection settings plus where they were found."""

    def __init__(self, config=None, db_host=None, db_name=None, db_user=None,
                 db_password=None, environ=None):
        environ = os.environ if environ is None else environ
        self.source = None
        self.webroot = None
        self.values = {
            "DATABASE_HOST": "localhost",
            "DATABASE_NAME": "fog",
            "DATABASE_USERNAME": "fogstorage",
            "DATABASE_PASSWORD": "",
            "UDPSENDERPATH": "/usr/local/sbin/udp-sender",
        }

        candidates = [config or environ.get("PYFOG_CONFIG")]
        if not candidates[0]:
            candidates = list(CONFIG_CANDIDATES)
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                self.values.update(read_php_config(path))
            except IOError as exc:
                if exc.errno == errno.EACCES:
                    raise ConfigError(
                        "%s is not readable; run as root or pass --db-* options" % path)
                raise
            self.source = path
            self.webroot = os.path.dirname(os.path.dirname(os.path.dirname(path)))
            break

        if self.source is None:
            for path in FOGSETTINGS_CANDIDATES:
                if not os.path.isfile(path):
                    continue
                try:
                    found = read_fogsettings(path)
                except IOError:
                    continue
                self.webroot = found.pop("WEBDIR", None)
                self.values.update(found)
                self.source = path
                break

        overrides = (
            ("DATABASE_HOST", db_host, environ.get("PYFOG_DB_HOST")),
            ("DATABASE_NAME", db_name, environ.get("PYFOG_DB_NAME")),
            ("DATABASE_USERNAME", db_user, environ.get("PYFOG_DB_USER")),
            ("DATABASE_PASSWORD", db_password, environ.get("PYFOG_DB_PASSWORD")),
        )
        for key, from_args, from_env in overrides:
            if from_args is not None:
                self.values[key] = from_args
                self.source = self.source or "command line"
            elif from_env:
                self.values[key] = from_env
                self.source = self.source or "environment"

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

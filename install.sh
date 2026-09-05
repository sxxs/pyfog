#!/bin/sh
# Install pyfog on a FOG server (or update an existing installation).
#
#   sudo ./install.sh                     install: PyMySQL from the distro,
#                                         the code under /opt/pyfog, a
#                                         `pyfog` command in /usr/local/bin
#   sudo ./install.sh --reader PASSWORD   the same, plus a SELECT-only
#                                         database account fogread@localhost
#   sudo ./install.sh --uninstall         remove /opt/pyfog and the command
#
# Run it from an unpacked release tarball or a git checkout; the files
# next to this script are what gets installed. PYFOG_PREFIX overrides
# /opt/pyfog.
set -e
PREFIX=${PYFOG_PREFIX:-/opt/pyfog}
BIN=/usr/local/bin/pyfog
SRC=$(cd "$(dirname "$0")" && pwd)

if [ "$(id -u)" != 0 ]; then
    echo "install.sh: run as root: sudo $0 $*" >&2
    exit 1
fi

if [ "$1" = "--uninstall" ]; then
    rm -rf "$PREFIX" "$BIN"
    echo "removed $PREFIX and $BIN"
    exit 0
fi

# -- PyMySQL from the distribution, never from pip --------------------------
if ! python3 -c 'import pymysql' 2>/dev/null; then
    if command -v apt-get >/dev/null; then
        apt-get update -qq && apt-get install -y -qq --no-install-recommends python3-pymysql
    elif command -v dnf >/dev/null; then
        dnf install -y python3-PyMySQL
    elif command -v yum >/dev/null; then
        yum install -y python3-PyMySQL
    elif command -v pacman >/dev/null; then
        pacman -S --noconfirm python-pymysql
    fi
    python3 -c 'import pymysql' 2>/dev/null || {
        echo "install.sh: python3 cannot import pymysql; install your distribution's" >&2
        echo "python3-pymysql package (or pip install pymysql) and run this again" >&2
        exit 1
    }
fi

# -- the code ---------------------------------------------------------------
mkdir -p "$PREFIX"
rm -rf "$PREFIX/pyfog" "$PREFIX/bin"
cp -R "$SRC/pyfog" "$SRC/bin" "$PREFIX/"
cp "$SRC/README.md" "$SRC/LICENSE" "$PREFIX/"
find "$PREFIX" -name __pycache__ -prune -exec rm -rf {} +
chmod 755 "$PREFIX/bin/pyfog"
ln -sfn "$PREFIX/bin/pyfog" "$BIN"
echo "installed pyfog $("$BIN" --version | cut -d' ' -f2) to $PREFIX, command: $BIN"

# -- optional read-only database account ------------------------------------
if [ "$1" = "--reader" ]; then
    [ -n "$2" ] || { echo "install.sh: --reader needs a password" >&2; exit 1; }
    SQL="CREATE USER IF NOT EXISTS 'fogread'@'localhost' IDENTIFIED BY '$2';
         GRANT SELECT ON fog.* TO 'fogread'@'localhost'; FLUSH PRIVILEGES;"
    if command -v mysql >/dev/null && echo "$SQL" | mysql -u root 2>/dev/null; then
        echo "created fogread@localhost with SELECT on fog.*; for users other than root:"
        echo "  export PYFOG_DB_HOST=localhost PYFOG_DB_NAME=fog PYFOG_DB_USER=fogread PYFOG_DB_PASSWORD='...'"
    else
        echo "install.sh: could not run the SQL as the database root; run it yourself:" >&2
        echo "$SQL" >&2
    fi
fi

# -- does it talk to the database? -------------------------------------------
echo
if "$BIN" info; then
    echo
    echo "try: pyfog tasks, pyfog multicast, pyfog dashboard (q quits)"
else
    echo
    echo "pyfog is installed but cannot reach the database from this account;" >&2
    echo "see README.md, Installation, for --db-* options and PYFOG_DB_* variables" >&2
    exit 1
fi

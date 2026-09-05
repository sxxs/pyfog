#!/bin/sh
# Install pyfog on a FOG server, or update an installation.
#
#   sudo ./install.sh [options]
#
#     --password PASSWORD   password for the read-only account fogread
#                           (default: a random one)
#     --root-password PW    the database root password, when root cannot
#                           log in through the socket without one
#     --group NAME          let members of this group read /etc/pyfog.conf
#                           and so run pyfog without sudo
#     --uninstall           remove /opt/pyfog, the command and the conf
#
# What it does: install the distribution's PyMySQL, copy the code to
# /opt/pyfog, link /usr/local/bin/pyfog, create the database account
# fogread with SELECT on fog.* (pyfog never uses FOG's own account),
# write its credentials to /etc/pyfog.conf (mode 0640, owner root), and
# run `pyfog info` as a check. Running it again keeps the password and
# updates the code.
#
# Run it from an unpacked release tarball or a git checkout; the files
# next to this script are what gets installed. PYFOG_PREFIX overrides
# /opt/pyfog, PYFOG_DB_HOST a database that is not on this machine.
set -e
PREFIX=${PYFOG_PREFIX:-/opt/pyfog}
BIN=/usr/local/bin/pyfog
CONF=/etc/pyfog.conf
DB_HOST=${PYFOG_DB_HOST:-localhost}
DB_NAME=${PYFOG_DB_NAME:-fog}
READER=fogread
SRC=$(cd "$(dirname "$0")" && pwd)
PASSWORD= ROOT_PASSWORD= GROUP=

while [ $# -gt 0 ]; do
    case "$1" in
        --password) PASSWORD=$2; shift 2 ;;
        --root-password) ROOT_PASSWORD=$2; shift 2 ;;
        --group) GROUP=$2; shift 2 ;;
        --uninstall)
            rm -rf "$PREFIX" "$BIN" "$CONF"
            echo "removed $PREFIX, $BIN and $CONF; the database account $READER stays"
            exit 0 ;;
        *) echo "install.sh: unknown option $1 (see the comment at the top)" >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" != 0 ]; then
    echo "install.sh: run as root: sudo $0" >&2
    exit 1
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

# -- the read-only database account -----------------------------------------
if [ -z "$PASSWORD" ] && [ -f "$CONF" ]; then
    PASSWORD=$(sed -n "s/^PYFOG_DB_PASSWORD='\(.*\)'$/\1/p" "$CONF")
fi
if [ -z "$PASSWORD" ]; then
    PASSWORD=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')
fi
case "$DB_HOST" in localhost|127.0.0.1|::1) FROM=localhost ;; *) FROM=% ;; esac
QUOTED=$(printf %s "$PASSWORD" | sed "s/'/''/g")
SQL="CREATE USER IF NOT EXISTS '$READER'@'$FROM' IDENTIFIED BY '$QUOTED';
ALTER USER '$READER'@'$FROM' IDENTIFIED BY '$QUOTED';
GRANT SELECT ON \`$DB_NAME\`.* TO '$READER'@'$FROM';
FLUSH PRIVILEGES;"
MYSQL="mysql -u root"
[ "$FROM" = localhost ] || MYSQL="$MYSQL -h $DB_HOST"
[ -z "$ROOT_PASSWORD" ] || MYSQL="$MYSQL -p$ROOT_PASSWORD"
if ! command -v mysql >/dev/null || ! echo "$SQL" | $MYSQL 2>/tmp/pyfog-install.err; then
    echo "install.sh: could not create the database account $READER as root" >&2
    echo "  ($(cat /tmp/pyfog-install.err 2>/dev/null || echo 'no mysql client found'))" >&2
    echo "run this as the database root and then install.sh again with the same --password:" >&2
    echo "$SQL" >&2
    exit 1
fi
umask 077
printf "# pyfog's own read-only database account, written by install.sh\nPYFOG_DB_USER=%s\nPYFOG_DB_PASSWORD='%s'\n" \
    "$READER" "$PASSWORD" > "$CONF"
chmod 0640 "$CONF"
[ -z "$GROUP" ] || chgrp "$GROUP" "$CONF"
GROUP=$(stat -c %G "$CONF")   # an earlier --group survives a rerun
if [ "$GROUP" != root ]; then
    echo "database account $READER@$FROM with SELECT on $DB_NAME.*; $CONF readable by root and group $GROUP"
else
    echo "database account $READER@$FROM with SELECT on $DB_NAME.*; $CONF readable by root (--group NAME to share it)"
fi

# -- does it talk to the database? -------------------------------------------
echo
if env -u PYFOG_DB_USER -u PYFOG_DB_PASSWORD "$BIN" info; then
    echo
    echo "try: pyfog tasks, pyfog multicast, pyfog dashboard (q quits)"
else
    echo
    echo "pyfog is installed and $CONF written, but pyfog info failed; see above" >&2
    exit 1
fi

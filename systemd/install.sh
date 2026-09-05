#!/bin/sh
# Install fog.target on a FOG server: one unit that starts, stops and
# restarts the seven FOG services together with the web server.
#
#   sudo ./install.sh [--uninstall]
#
# What it does: copy fog.target and fog.slice to /etc/systemd/system,
# add the web server (apache2 or httpd) and its PHP-FPM unit to the
# target, write the drop-in fog.conf (PartOf=fog.target, Slice=fog.slice)
# to /etc/systemd/system/<unit>.d/ for every unit in the target, and
# make fog.target the one thing enabled at boot: the individual FOG*
# units are disabled, since the target pulls them in. FOG's own installer
# copies its units to /lib/systemd/system and re-enables them on an
# upgrade; both are harmless, the drop-ins in /etc stay.
#
# Nothing is restarted. The slice takes effect for a service when it
# next starts; systemctl restart fog.target does that for all of them.
# --uninstall removes the target, the slice and the drop-ins and enables
# the FOG* units again.
set -e
SRC=$(cd "$(dirname "$0")" && pwd)
DEST=/etc/systemd/system
FOG_UNITS="FOGImageReplicator FOGImageSize FOGMulticastManager FOGPingHosts
           FOGScheduler FOGSnapinHash FOGSnapinReplicator"

if [ "$(id -u)" != 0 ]; then
    echo "install.sh: run as root: sudo $0" >&2
    exit 1
fi
command -v systemctl >/dev/null || { echo "install.sh: no systemctl here" >&2; exit 1; }

# a unit file exists (installed, not necessarily enabled or running)
have() { systemctl list-unit-files --no-legend "$1.service" 2>/dev/null | grep -q .; }

# the web server and PHP-FPM, whatever the distribution calls them
WEB_UNITS=
for u in apache2 httpd; do have $u && WEB_UNITS="$WEB_UNITS $u"; done
for u in $(systemctl list-unit-files --no-legend 'php*fpm.service' 2>/dev/null | sed 's/\.service .*//'); do
    WEB_UNITS="$WEB_UNITS $u"
done
PRESENT=
for u in $FOG_UNITS; do have $u && PRESENT="$PRESENT $u"; done
[ -n "$PRESENT" ] || { echo "install.sh: no FOG*.service units here; is this the FOG server?" >&2; exit 1; }

if [ "$1" = --uninstall ]; then
    systemctl disable --quiet fog.target 2>/dev/null || true
    for u in $FOG_UNITS $WEB_UNITS; do rm -rf "$DEST/$u.service.d/fog.conf"; rmdir "$DEST/$u.service.d" 2>/dev/null || true; done
    rm -f "$DEST/fog.target" "$DEST/fog.slice"
    systemctl daemon-reload
    for u in $PRESENT; do systemctl enable --quiet $u; done
    echo "removed fog.target, fog.slice and the drop-ins; enabled again:$PRESENT"
    echo "running services keep running; the slice goes away as each one restarts"
    exit 0
fi
[ $# -eq 0 ] || { echo "install.sh: unknown option $1 (see the comment at the top)" >&2; exit 2; }

# the target, with the web units this server has added to [Unit]
WANTS=$(for u in $WEB_UNITS; do echo "Wants=$u.service"; done)
awk -v wants="$WANTS" '/^\[Install\]/ && wants != "" { print wants; print "" } { print }' \
    "$SRC/fog.target" > "$DEST/fog.target"
cp "$SRC/fog.slice" "$DEST/fog.slice"

# the drop-ins
for u in $PRESENT $WEB_UNITS; do
    mkdir -p "$DEST/$u.service.d"
    cp "$SRC/fog.conf" "$DEST/$u.service.d/fog.conf"
done
systemctl daemon-reload

# one switch at boot
for u in $PRESENT; do systemctl disable --quiet $u 2>/dev/null || true; done
systemctl enable --quiet fog.target

echo "fog.target installed with:$PRESENT$WEB_UNITS"
echo "enabled at boot: fog.target (the FOG* units are pulled in by it, no longer on their own)"
if systemctl is-active --quiet fog.target; then
    echo "try: systemctl restart fog.target && systemctl status fog.slice"
else
    echo "try: systemctl start fog.target && systemctl status fog.slice"
fi

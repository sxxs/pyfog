"""pyfog - read-only command line view on a FOG imaging server.

Layers:

    config.py   where the database credentials come from
    db.py       SELECT-only MySQL access (PyMySQL or the mysql client)
    local.py    facts read from this machine: /proc, web server logs, udpcast logs
    fog.py      the data layer: plain dicts describing tasks, hosts, images ...
    render.py   terminal presentation of those dicts
    cli.py      argument parsing, wiring, JSON output

A later web front end should import fog.Fog and nothing else.
"""

__version__ = "1.0.0"

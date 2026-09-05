# pyfog

Read-only command line view on a [FOG](https://fogproject.org) imaging
server. It reads FOG's MySQL tables directly (plus the process list and
the web server log on the FOG host) and shows what the web GUI makes tedious to
find out. It never writes to the database and never calls the FOG API.

Python 3.6+ and [PyMySQL](https://pypi.org/project/PyMySQL/), nothing
else (`apt install python3-pymysql` on Debian/Ubuntu).

## Goal

FOG does the imaging well; its web GUI is a poor place to find out what
the server is doing. The questions that come up every day in a lab
with a few dozen machines take too many clicks, or cannot be answered
from the GUI at all:

* Which tasks are running right now, and which of them are actually
  still alive? The GUI drops a task from "Active Tasks" once its
  check-in is stale (older than the check-in timeout), while the host may be halfway through writing the
  image.
* Who takes part in a multicast deploy? FOG queues one task per host, so
  a session of twenty machines shows up as twenty unrelated rows instead
  of one event with twenty participants.
* Which hosts have talked to the server recently, and which have gone
  quiet? FOG keeps no "last seen" column.
* Which image did each machine last receive, and does that match the
  image assigned to it now?
* What happened yesterday? There is no task history beyond the per-host
  task log pages.
* Which snapins failed on which hosts?

pyfog answers these from the tables FOG itself writes, without going
through FOG's own PHP code or its API, so what pyfog shows is what the
database holds. Design rules, in order:

1. **Tell the truth.** Read the same rows FOG writes, name the source of
   every derived value (a stale task, a "last seen" time, a lost imaging
   run), and say when something cannot be known from the database.
2. **Stay small and readable.** No framework, one dependency, a few
   hundred lines per module, plain SQL that anyone can check against
   FOG's schema.
3. **Read only.** Only `SELECT`; a database account with `SELECT` on
   `fog.*` is all it needs.
4. **Separate data from display.** `pyfog/fog.py` returns plain dicts,
   the terminal tables are a thin layer on top, and `--json` prints the
   dicts as they are. A read-only web front end can be built on the
   data layer later without touching it.

Out of scope: creating, changing or cancelling tasks, hosts or images.
FOG's GUI and API remain the place for that.

## Commands

| command                    | answers                                                        |
|----------------------------|----------------------------------------------------------------|
| `pyfog tasks`             | what is queued or running right now; one line per multicast session; imaging runs FOG lost track of |
| `pyfog task <id>`         | one task in detail, with every host imaging alongside it (multicast session or group batch) |
| `pyfog history`           | finished tasks with start/end times from `taskLog`, newest first |
| `pyfog scheduled`         | delayed and cron tasks FOG will create later                    |
| `pyfog multicast`         | sessions, participants, the `udp-sender` processes and their udpcast log; orphaned senders |
| `pyfog clients`           | when each host's FOG client last called in                      |
| `pyfog deployments`       | imaging log: which host captured or received which image, when  |
| `pyfog deployments --current` | per host: assigned image versus last deployed image        |
| `pyfog images`            | image inventory                                                |
| `pyfog hosts [search]`    | host inventory with image, groups, active task                  |
| `pyfog groups`            | groups and their members                                        |
| `pyfog snapins`           | snapin runs per host with exit codes (`--failed` for the bad ones) |
| `pyfog info`              | versions, connection, counts, storage nodes                     |
| `pyfog dashboard`         | one screen of what is live: tasks, multicast, imaging runs, recent history, scheduled tasks; redrawn every 3 s, single keys switch to the other commands |

Every command takes `--json` for machine readable output; `tasks` and
`multicast` take `--watch SECONDS`, which redraws the screen the way the
dashboard does, or, into a pipe or with `--json`, appends one complete
document per round. `pyfog <command> --help` lists the filters.

### The dashboard

`pyfog dashboard` shows active tasks (multicast sessions with their
hosts), imaging runs FOG lost track of, each active multicast session
with its sender process, the last few finished tasks and the pending
scheduled tasks, and redraws every 3 seconds (`--interval`). It is meant
to be left open in an ssh session on the FOG server, so it keeps
terminal control to a minimum:

* It does not switch to a separate screen the way `less` or `top` do,
  and it never clears the whole screen. Each refresh is one write that
  puts the cursor back in the top left corner and overwrites line by
  line, so the screen updates in place without flashing, and what was on
  screen stays there after Ctrl-C.
* Lines that do not fit the terminal are dropped and counted in the
  last row (`… 13 more lines`); the screen never scrolls. Tables
  shrink their widest columns to the terminal width.
* A lost database connection does not end the dashboard. The last good
  screen stays up with the error in the status line, and every refresh
  tries to reconnect.
* Colour follows `--no-color` and `NO_COLOR`; there is nothing else in
  the way of terminal control.

The first line is the status line: the time of the last refresh by the
clock of the machine running pyfog (the heading below it shows the
database server's time), how long the queries took, and the interval.
The second line lists the keys. One letter switches the screen to
another command's output, refreshed at the same interval, so the other
commands can be found without remembering their names: `t` tasks (one
line per host), `m` multicast, `h` history, `s` scheduled, `c` clients,
`d` deployments, `i` images, `o` hosts, `g` groups, `n` snapins, `f`
info. `x` or Escape returns to the dashboard, `q` quits. The keys need
a terminal on standard input (`ssh -t` when running the command straight
from ssh); without one the dashboard only refreshes. With `--once`, or
when the output is not a terminal, it prints one screen and exits.
`--json` prints the same data as one dict. The web server access log is not
read, so "last seen" per client stays with `pyfog clients`.

```
$ pyfog tasks
Tasks: 6  (server time 2026-09-05 09:07:41, check-in timeout 600s)
 ID  HOST            IP         TYPE        STATE                    IMAGE      PROGRESS            ELAPSED      LEFT  NODE           CREATED           CHECK-IN  FLAGS
MC1  3 hosts: Lab-A  -          Multi-Cast  2 In-Progress, 1 Queued  Win11-Lab  30-31%                    -         -  -              2026-09-05 08:57         -  multicast
  1  pc01            10.0.0.11  Deploy      In-Progress              Win11-Lab  45% 10.2GB/22.5GB  00:05:12  00:06:00  DefaultMember  2026-09-05 08:55    2m 16s  wol
  2  pc02            10.0.0.12  Deploy      Checked In (stale)       Win11-Lab  -                         -         -  DefaultMember  2026-09-05 08:25   21m 46s  -
  3  pc03            10.0.0.13  Capture     Queued                   Win11-Lab  -                         -         -  DefaultMember  2026-09-05 09:03     never  forced

Imaging runs the hosts reported as started but not finished:
HOST  IP         IMAGE      KIND    STARTED                  AGE  TASK
pc01  10.0.0.11  Win11-Lab  deploy  2026-09-05 09:00:55   6m 46s  yes
pc04  10.0.0.14  Win11-Lab  deploy  2026-09-05 08:25:55  41m 46s  none (FOG lost track)
```

## Installation

On the FOG server, as root:

```
git clone https://github.com/sxxs/pyfog.git && sudo pyfog/install.sh
```

or, without git on the server, build a tarball on your machine with
`make dist`, copy `dist/pyfog-<version>.tar.gz` over and run

```
tar xzf pyfog-<version>.tar.gz && sudo pyfog-<version>/install.sh
```

`install.sh` installs the distribution's PyMySQL package (apt, dnf, yum
or pacman), copies the code to `/opt/pyfog`, links `/usr/local/bin/pyfog`
and ends with `pyfog info` as a check. Running it again updates the
installation; `--uninstall` removes it. Nothing else is written
anywhere: no service, no cron job, no config file.

Credentials are read from FOG's own `lib/fog/config.class.php` (falling
back to `/opt/fog/.fogsettings`), so as root nothing needs to be set up.
For other users, or from another machine, pass `--config PATH`,
`--db-host/--db-name/--db-user/--db-password`, or set the environment
variables `PYFOG_DB_HOST`, `PYFOG_DB_NAME`, `PYFOG_DB_USER`,
`PYFOG_DB_PASSWORD` (`PYFOG_CONFIG` for the config file). Without
`install.sh`, `bin/pyfog` runs from any checkout with `python3-pymysql`
installed, and `pip install .` installs a `pyfog` command into a venv.

A dedicated read-only database account is the sensible setup for
anyone who is not root; `install.sh --reader PASSWORD` creates it, or by
hand:

```sql
CREATE USER 'fogread'@'localhost' IDENTIFIED BY '...';
GRANT SELECT ON fog.* TO 'fogread'@'localhost';
```

`pyfog multicast` and `pyfog clients` read `/proc` and the web server
access log; both need to run on the FOG server itself (or the storage node
running the sender) to see those.

## Where the answers come from

FOG's web GUI goes through FOG's own PHP classes and the API; pyfog reads
the same tables the GUI writes, so a task that vanished from "Active Tasks"
but is still in `tasks` still shows up in pyfog. Column names and their meaning were
taken from FOG 1.5.10 (branch `stable`): `packages/web/commons/schema.php`
and the `$databaseFields` maps in `packages/web/lib/fog/*.class.php`.

* **Tasks** are `tasks` joined with `hosts`, `images`, `taskStates`,
  `taskTypes` and the storage node. A task is marked *stale* when its
  `taskCheckIn` is older than `FOG_CHECKIN_TIMEOUT` (minimum 180 s, as in
  `lib/fog/task.class.php`); FOG will re-queue it, while the host may
  well still be imaging.
* **Imaging runs** come from `imagingLog`, which the host itself opens at
  the start of imaging and closes at the end
  (`lib/reg-task/taskingelement.class.php`). An open row without an
  active task is a host still imaging after FOG lost track of it.
* **Multicast**: FOG queues one task per participating host and links
  them to the session through `multicastSessionsAssoc`. pyfog folds
  them back into one entry. The pid FOG stores in `msSenderPID` is the
  `/bin/sh` it starts the sender through (`lib/service/multicasttask.class.php`),
  so pyfog checks that pid and then looks for `udp-sender` children,
  matching by `--portbase`. Only sessions whose sender node is this
  machine take part in that matching, and only active ones; senders that
  no active session claims are listed as orphans. The udpcast log FOG keeps per session
  (`SERVICE_LOG_PATH/MULTICASTLOGFILENAME.udpcast.<id>`) supplies the
  receivers that actually connected.
* **Group tasks** share their name (`<type> - <group name>`) and creation
  timestamp (`lib/fog/group.class.php`), which is how `pyfog task` finds
  the batch a non-multicast task belongs to.
* **Client contact**: FOG keeps no "last seen" column. Two proxies are
  used. `hosts.hostSecTime` is the client's token expiry, set to
  now + 30 min whenever the client re-authorizes
  (`lib/fog/fogpage.class.php`), so `hostSecTime - 30 min` is the last
  authorization the database can prove (30 min resolution). The web
  server access log is exact: every FOG client request carries `mac=`,
  and pyfog maps that to hosts through `hostMAC`; log times go through
  UTC to the database session's clock before they are compared. The
  newer of the two is shown, with its source, and logs that exist but
  cannot be read are named in the heading.
* **History**: `taskLog` gets a row when a task goes In-Progress and one
  when it completes; `history` shows those as start and end.
* **Snapins**: `snapinTasks` holds state, exit code and the details
  string per snapin per job; exit code 0 on a completed task counts as ok.
* **Deployments** are `imagingLog` rows; `ilType` `down` is a deploy,
  `up` a capture. `--current` compares the last finished deploy per host
  with the image assigned in `hosts.hostImage`.

## Layout

```
bin/pyfog            launcher for running from a checkout
pyfog/config.py     credential discovery
pyfog/db.py         SELECT-only queries through PyMySQL
pyfog/local.py      /proc, access log, udpcast log
pyfog/fog.py        data layer: plain dicts, no printing
pyfog/render.py     tables for the terminal
pyfog/cli.py        argument parsing and wiring
tests/               python3 -m unittest
install.sh           installer for the FOG server
Makefile             make test, make smoke, make dist
```

A web front end can build on `pyfog.fog.Fog` alone; every method returns
what `--json` prints.

## Verification

pyfog is only useful if it tells the truth, so check it in three stages.

**1. Unit tests, no database.** `python3 -m unittest` covers credential
parsing, the access log and udp-sender parsing, the multicast folding
and the argument handling.

**2. A throwaway MariaDB with FOG's real layout.** `tests/fog-schema.sql`
is FOG 1.5.10's complete table layout, produced by running every
migration step of FOG's `schema.php` against an empty MariaDB and
dumping the result, together with the reference rows FOG inserts itself
(task states, task types, settings). `tests/seed.sql` adds six hosts,
two images, two groups, tasks in every state, one multicast session,
imaging and snapin logs, and `tests/access.log` a matching web server
log. With Docker Desktop on a development machine, `docker-compose.yml`
starts a MariaDB that loads both files on first start and runs pyfog in
a Debian container next to it, installed the way it would be on a FOG
server (`python3-pymysql` from apt):

```
docker compose run --rm pyfog tasks                    # any command
docker compose run --rm pyfog --json multicast
docker compose run --rm pyfog dashboard                # live, Ctrl-C to quit
docker compose run --rm --entrypoint tests/smoke.sh pyfog
docker compose down -v                                 # drop the database
```

The checkout is mounted into the container, so edits need no rebuild.
To use the database from the host instead, add a `ports: ["3307:3306"]`
entry to the `db` service and point `PYFOG_DB_HOST=127.0.0.1:3307`,
`PYFOG_DB_USER=root`, `PYFOG_DB_PASSWORD=fog`, `PYFOG_DB_NAME=fog` at it.

Any other MariaDB or MySQL works the same way; the seed uses
`NOW()`-relative timestamps, so ages and stale markers come out
plausible whenever it is loaded. What to expect from the seed: task 1
running, task 2 checked in but silent (stale), task 3 queued, tasks 4
to 6 folded into multicast session 1, pc04 imaging without a task, a
failed snapin on pc01, and pc02 silent for two days in `clients`.

The multicast process check needs real processes in the same container
as pyfog. To exercise it, start a stand-in sender the way FOG does and
store the shell's pid in the session:

```
docker compose run --rm --entrypoint sh pyfog
# inside the container:
sh -c 'sleep 3600; sleep 3600' &      # FOG wraps udp-sender in /bin/sh
python3 -c "import pymysql; c = pymysql.connect(host='db', user='root', password='fog', database='fog'); \
  c.cursor().execute('UPDATE multicastSessions SET msSenderPID=$! WHERE msID=1'); c.commit()"
python3 -m pyfog multicast
```

`pyfog multicast` then reports the wrapper as alive; with a real
`udp-sender --portbase 63100 ...` child it lists the sender too.

**3. Against the FOG server.** Create a `SELECT`-only account (see
Installation), run `pyfog info` to confirm credentials, FOG version and
schema version, then compare `pyfog tasks` and `pyfog multicast` with
the GUI's Active Tasks page during a deploy. `--debug` prints every SQL
statement to stderr, which is the fastest way to see why a column or
row looks different on your installation.

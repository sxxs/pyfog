# pyfog

Read-only command line view on a [FOG](https://fogproject.org) imaging
server. It reads FOG's MySQL tables directly (plus the process list and
the web server log on the FOG host) and shows what the web GUI makes tedious to
find out. It never writes to the database and never calls the FOG API.

Python 3.6+ and [PyMySQL](https://pypi.org/project/PyMySQL/), nothing
else (`apt install python3-pymysql` on Debian/Ubuntu).

## Built against

pyfog reads FOG's tables directly, so the FOG release it was written
against is a compatibility fact and not a footnote. Everything here was
built and tested against this combination:

| component | version |
|---|---|
| FOG | 1.5.10, branch `stable`, build 1.5.10.2253 |
| FOG client | 0.13 |
| database | MariaDB 10.11 |
| Python | 3.6 or newer, PyMySQL 0.9 or newer |
| FOG host | Debian/Ubuntu with apache2; the installers also know dnf, yum, pacman and httpd |

Every column name and every rule about what a value means was taken from
that release: `packages/web/commons/schema.php` and the
`$databaseFields` maps in `packages/web/lib/fog/*.class.php`.
`tests/fog-schema.sql` is that layout, dumped after running all 279 of
its migration steps, and the patch in `patches/` is a diff against its
source.

On a different FOG version pyfog still only ever issues `SELECT`, so the
worst case is a renamed column and an error message, not damage. Start
with `pyfog info`, which prints the server's own FOG version and schema
version, and use `--debug` to see the statement behind anything that
looks wrong.

This is finished work, kept as it is and not under active development.

## What is in this repo

Reading the database is the whole of pyfog. Three small extras sit next
to the command because they came out of running the same FOG server;
each one is optional and independent of the others:

* **`sql/lost-tasks.sql`** — pyfog only reads, but what it shows as lost
  has to be cleaned up somewhere: tasks that stay active in the database
  after FOG stopped listing them, and that block their host from new
  tasks. The script cancels them as the database root, and only reports
  unless told to apply. See [Cleaning up lost
  tasks](#cleaning-up-lost-tasks).
* **`patches/`** — two patches for FOG 1.5.10's web code, both applied
  on the server, neither touching the FOG client. One makes the multicast
  manager wait for the hosts instead of ending a session the moment
  `udp-sender` exits, while the receivers are still writing the image and
  their completion reports get refused: that race is the usual source of
  the lost imaging runs pyfog reports. The other narrows the random
  offset the server adds to every client's check-in interval from 1-91 to
  1-11 seconds. See [Patches for the FOG
  server](#patches-for-the-fog-server).
* **`systemd/`** — `fog.target` and `fog.slice`, one switch to start,
  stop and inspect FOG's seven services and its web server together
  instead of one unit at a time. It changes nothing about how FOG works.
  See [One unit for all FOG services](#one-unit-for-all-fog-services).

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
  quiet? FOG keeps no "last seen" column. And of the quiet ones: which
  are off, and which are running with a broken FOG client?
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
3. **Read only.** Only `SELECT`, through its own database account with
   `SELECT` on `fog.*`; FOG's own account is never used. Nothing on the
   network either, with one exception that has to be asked for by name:
   `pyfog clients --arping` sends ARP requests, because whether a machine
   is powered on is not a fact any table holds.
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
| `pyfog history`           | finished tasks with the times FOG recorded for them, newest first |
| `pyfog scheduled`         | delayed and cron tasks FOG will create later                    |
| `pyfog multicast`         | sessions, participants, the `udp-sender` processes and their udpcast log; orphaned senders |
| `pyfog clients`           | when each host's FOG client last called in; `--arping` also asks the hosts whether they are powered on |
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
info. `a` switches the ARP probe in the clients view on and off (see [Is
the machine on?](#is-the-machine-on)); it stays switched for the rest of
the session, so leaving the view and coming back keeps it, and the status
line says `pyfog clients arp` while it is on. `x` or Escape returns to
the dashboard, `q` quits. `<` and `>`
sort the view's table by the previous or next column, the way top does,
`r` reverses; the sorted column carries an arrow in its header, hosts
of a multicast session stay under their session, and empty cells sort
last. When the output is longer than the screen, the status line says
which lines are showing, and `j`/`k` or the arrow keys scroll by a line,
Page Up/Down or Ctrl-F/Ctrl-B by a page, Ctrl-D/Ctrl-U by half a page,
Home and End (or `G`) to the ends. The keys need a terminal on standard
input (`ssh -t` when running the command straight from ssh); without one
the dashboard only refreshes. With `--once`, or
when the output is not a terminal, it prints one screen and exits.
`--json` prints the same data as one dict. The web server access log is not
read, so "last seen" per client stays with `pyfog clients`.

```
$ pyfog tasks
Tasks: 6  (server time 2026-09-05 09:07:41, check-in timeout 600s)
Network  eno1  out 118.4 MiB/s  in 1.2 MiB/s  (1.0s sample)
 ID  HOST            IP         TYPE        STATE                    IMAGE      PROGRESS            ELAPSED      LEFT  NODE           CREATED           CHECK-IN  FLAGS
MC1  3 hosts: Lab-A  -          Multi-Cast  2 In-Progress, 1 Queued  Win11-Lab  30-31%                    -         -  -              2026-09-05 08:57         -  multicast
  1  pc01            10.0.0.11  Deploy      In-Progress              Win11-Lab  45% 10.2GB/22.5GB  00:05:12  00:06:00  DefaultMember  2026-09-05 08:55    2m 16s  wol
  2  pc02            10.0.0.12  Deploy      Checked In (stale)       Win11-Lab  -                         -         -  DefaultMember  2026-09-05 08:25   21m 46s  -
  3  pc03            10.0.0.13  Capture     Queued                   Win11-Lab  -                         -         -  DefaultMember  2026-09-05 09:03     never  forced

Imaging runs the hosts reported as started but not finished:
HOST  IP         IMAGE      KIND    STARTED                  AGE  TASK
pc01  10.0.0.11  Win11-Lab  deploy  2026-09-05 09:00:55   6m 46s  yes
pc04  10.0.0.14  Win11-Lab  deploy  2026-09-05 08:25:55  41m 46s  9 closed by server before the host reported; last report 2026-09-05 08:30
```

### Throughput

While a host is imaging, `pyfog tasks`, `pyfog multicast` and the
dashboard show what the server's interfaces are moving, in the direction
that tells them apart: a deploy is the server sending, a capture is the
server receiving.

```
Network  eno1  out 118.4 MiB/s  in 1.2 MiB/s  (1.0s sample)
```

The numbers are the kernel's own counters from `/proc/net/dev`, read
twice -- the same measurement `vnstat -l` makes, from the same place, so
neither vnstat nor any other daemon is needed for it. A single command
has nothing to compare its reading against and waits a second for the
second one; the dashboard compares two of its redraws instead, which
costs nothing and averages over a longer, steadier window (the sample
length is in the line). Under a multicast session the interface shown is
the one FOG told `udp-sender` to send on, and only while that sender is
running.

Nothing is measured on a server where nothing is being deployed or
captured -- no imaging task, no line, and no second spent taking a
reading.

### Is the machine on?

Everything `pyfog clients` shows by default is the FOG client talking, so
a machine that is up with a stopped, broken or never-installed client is
indistinguishable from one that is off. `--arping` asks the machines
themselves; the answer is a column in the same table.

```
$ pyfog clients --arping --stale 30
HOST  ARP         IP         MAC                IMAGE      LAST SEEN            AGE  SOURCE
pc01  up          10.0.0.11  00:11:22:33:44:01  Win11-Lab  2026-09-05 09:05  2m 16s  log
pc02  up          10.0.0.12  00:11:22:33:44:02  Win11-Lab  2026-09-05 08:25  42m 46s log
pc03  silent      10.0.0.13  00:11:22:33:44:03  Win11-Lab  2026-09-04 22:10  11h 02m token
pc04  other host  10.0.0.14  00:11:22:33:44:04  Win11-Lab  2026-09-01 08:31   4d 00h token
```

`up` is the host's own MAC answering. `other host` means that address
answered but a different machine holds it now, so the host has moved or
the record is stale -- FOG's `hostIP` is not maintained after
registration. `silent` is no answer: off, on another segment, or asleep.
`?` is a probe that could not be made at all, with the reason in the
heading (no `arping` installed, or no permission for a raw socket -- it
needs root or `CAP_NET_RAW`).

In the dashboard the same view is the `c` key, and `a` turns the probe
on and off while the screen is up -- that is where this is meant to be
used. `pyfog dashboard --arping` starts with it already on, and both
carry `--arping-timeout`.

This is the one command that sends something: one ARP request per host
listed, 32 in flight, one second each unless `--arping-timeout` says
otherwise, so a lab answers in about a second. In the dashboard that
second is part of every refresh while the probe is on, which is why it
is a key rather than the default. It never crosses a router (ARP is
local to the segment), and with `--only-stale` only the hosts still on
the list are asked. Outside the dashboard, `pyfog clients --watch
SECONDS` repeats the view on its own; it re-reads the access log every
round, so `--log-bytes` is worth lowering for a fast interval.

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
or pacman), copies the code to `/opt/pyfog`, links `/usr/local/bin/pyfog`,
creates the database account `fogread` with `SELECT` on `fog.*`, writes
its credentials to `/etc/pyfog.conf` (owner root, mode 0640) and ends
with `pyfog info` as a check. The account is not optional: pyfog never
logs in with FOG's own credentials, and the installer stops if it cannot
create the account, printing the SQL to run by hand. Options:

* `--password PASSWORD` for the account instead of a random one.
* `--root-password PASSWORD` when the database root cannot log in
  through the socket without one.
* `--group NAME` lets members of that group read `/etc/pyfog.conf`, so
  they can run pyfog without sudo.
* `--uninstall` removes the code, the command and the conf; the database
  account stays.

Running the installer again updates the code and keeps the password.
Nothing else is written anywhere: no service, no cron job.

Host and database name come from FOG's own `lib/fog/config.class.php`
(falling back to `/opt/fog/.fogsettings`), which also tells pyfog where
the web root and `udp-sender` are. User and password come from
`/etc/pyfog.conf` (`PYFOG_CONF` names another file). Both can be
overridden, with the environment variables `PYFOG_DB_HOST`,
`PYFOG_DB_NAME`, `PYFOG_DB_USER`, `PYFOG_DB_PASSWORD` (`PYFOG_CONFIG` for
FOG's config file) or the options `--db-host`, `--db-name`, `--db-user`,
`--db-password`, `--config`; `pyfog info` says where each value came
from. Without `install.sh`, `bin/pyfog` runs from any checkout with
`python3-pymysql` installed, and `pip install .` installs a `pyfog`
command into a venv; both then need the account in the environment or
on the command line.

`pyfog multicast` and `pyfog clients` read `/proc` and the web server
access log; both need to run on the FOG server itself (or the storage node
running the sender) to see those. `pyfog tasks`, `pyfog multicast` and the
dashboard also show the throughput of the server's interfaces while hosts
are imaging, from the same place: see [Throughput](#throughput).
`pyfog clients --arping` is the one thing here that puts packets on the
network rather than only reading: see [Is the machine
on?](#is-the-machine-on).

## Where the answers come from

FOG's web GUI goes through FOG's own PHP classes and the API; pyfog reads
the same tables the GUI writes, so a task that vanished from "Active Tasks"
but is still in `tasks` still shows up in pyfog. Column names and their meaning come from
FOG 1.5.10 (see [Built against](#built-against)); each item below names
the FOG file it was read from, so it can be checked against your own
installation.

* **Tasks** are `tasks` joined with `hosts`, `images`, `taskStates`,
  `taskTypes` and the storage node. A task is marked *stale* when its
  `taskCheckIn` is older than `FOG_CHECKIN_TIMEOUT` (minimum 180 s, as in
  `lib/fog/task.class.php`); FOG will re-queue it, while the host may
  well still be imaging.
* **Imaging runs** come from `imagingLog`, which the host itself opens at
  the start of imaging and closes at the end
  (`lib/reg-task/taskingelement.class.php`). An open row with no active
  task is not one fact but three, and pyfog tells them apart by the task
  that was current when the run started, because only one of them is a
  problem. **Cancelled**: someone stopped the task while the host was
  imaging; a cancelled host never reports a finish, so the row stays open
  by design -- nothing is running, and it is shown in grey and counted
  apart. **Complete but without the `taskLog` row** the host writes on
  completion: the server closed the task before the host could report
  (see [the multicast
  patch](#the-multicast-manager-ends-a-session-too-early)). **No task at
  all**: FOG lost track of a run that may well still be writing to the
  disk. The last two are what "imaging run without a task" counts.
* **Multicast**: FOG queues one task per participating host and links
  them to the session through `multicastSessionsAssoc`. pyfog folds
  them back into one entry. Those rows are the hosts in the session, not
  the ones receiving: a task is linked when the session is built (or when
  a host picks a named session from the PXE menu), long before
  `udp-sender` has anyone on the wire, so pyfog reports them as "in
  session" and leaves the receivers to the udpcast log below the summary.
  The count the sender waits for is FOG's own
  `max(linked tasks, msSessClients)` (`lib/service/multicasttask.class.php`),
  which is the `--min-receivers` on the process line. `msClients` is not
  read at all: it is a marker rather than a count -- `-2` while a named
  session takes unregistered clients, `0` once one is finished
  (`lib/service/multicastmanager.class.php`), and `0` throughout for the
  ordinary group deploy. The pid FOG stores in `msSenderPID` is the
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
* **Throughput**: the kernel's byte counters in `/proc/net/dev`, two
  readings and the time between them, which is what `vnstat -l` shows and
  where vnstat reads it from as well, so nothing has to be installed or
  kept running for the number. It appears only while a host is imaging
  (a task in-progress or checked in: a multicast task never advances past
  checked in, the session carries the progress). Under a multicast
  session it is the interface FOG told `udp-sender` to send on
  (`msInterface`), elsewhere the busiest interfaces the machine has, with
  loopback left out. See [Throughput](#throughput).
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
* **Powered on** (`pyfog clients --arping`): both proxies above are the
  FOG client talking, so a machine that is up with a stopped, broken or
  never-installed client looks exactly like one that is off. ARP is
  answered by the network stack, which does not care what runs on the
  host. The address asked is the one the kernel's ARP cache
  (`/proc/net/arp`) last saw that MAC at, and `hosts.hostIP` only when
  the cache has nothing on it; the answering MAC is compared with the
  host's, so a reply from whoever holds that address today is reported as
  "other host" and not as this one being up. See [Is the machine
  on?](#is-the-machine-on).
* **Time zone** (`pyfog info`): FOG writes every datetime through its PHP
  layer in the zone named by `FOG_TZ_INFO` (default UTC), whatever the
  database server's own time zone is. pyfog's reference "now" is therefore
  `UTC_TIMESTAMP()` put into FOG's zone, not the server's `NOW()`; using
  `NOW()` on a UTC FOG whose database server runs local time would make
  every age wrong by the offset, so running tasks would look stale and
  live hosts silent. `pyfog info` prints the reference time, its zone, and
  a warning when the server's own clock differs.
* **FOG client intervals** (`pyfog info`): the client asks the server for
  its configuration on every cycle (`lib/fog/fogpage.class.php`,
  `configure` and `requestClientInfo`), and the server answers with
  `FOG_CLIENT_CHECKIN_TIME` plus a random offset as the next sleep, and
  `FOG_GRACE_TIMEOUT` as the reboot countdown. Both are global settings;
  FOG keeps no per-host or per-group values for them. The offset is a
  literal in FOG's source (`mt_rand(1, 91)` as shipped, `mt_rand(1, 11)`
  with the [patch](#the-server-adds-up-to-91-seconds-to-every-check-in)),
  so pyfog reads the pair out of the web root instead of assuming it, and
  says so when the web root cannot be read. The client (fog-client 0.13)
  accepts a sleep of 30 to 7200 s and a countdown of 60 to 600 s and
  silently uses 60 s outside those ranges, so a countdown below a minute
  cannot be configured.
* **History**: `taskLog` gets a row when a task goes In-Progress and one
  when it completes, but neither carries the time of the state change:
  FOG writes both rows with the *task's creation time*
  (`taskLog()` in `lib/reg-task/taskingelement.class.php`). Read as
  start and end, every task in it lasts zero seconds, which is what
  `history` used to show. So `history` takes the start from
  `tasks.taskCheckIn` -- written once, when the host takes the task --
  and the end from the `imagingLog` row a deploy or capture writes
  itself, paired with the task by host and start time, the way FOG's own
  host history page does it. `taskLog` is still read for the one thing
  it does say: *that* the host reported the end (see
  [closed by server](#the-multicast-manager-ends-a-session-too-early)).
  A task that writes no imaging run -- an inventory, a wipe, a snapin
  job -- therefore has a start and a `reported, no end time logged`,
  because that is all the database holds; for snapins the times are in
  `pyfog snapins`. Snapin jobs also have no start: the FOG client
  overwrites `taskCheckIn` on every contact
  (`lib/client/snapinclient.class.php`), so for them it is the last
  report, not the beginning.
* **Snapins**: `snapinTasks` holds state, exit code and the details
  string per snapin per job; exit code 0 on a completed task counts as ok.
* **Deployments** are `imagingLog` rows; `ilType` `down` is a deploy,
  `up` a capture. `--current` compares the last finished deploy per host
  with the image assigned in `hosts.hostImage`.

## Cleaning up lost tasks

pyfog only reads, but what it shows as lost has to be cleaned up
somewhere: tasks FOG stopped listing while they stay active in the
database (and block the host from new tasks), multicast sessions whose
hosts are all gone, imaging runs without a finish time, snapin jobs
nobody will pick up. `sql/lost-tasks.sql` does that, as the database
root, and by default only reports:

```
mysql fog < sql/lost-tasks.sql                                          # report
mysql --init-command="SET @dry_run = 0" fog < sql/lost-tasks.sql        # apply
mysql --init-command="SET @hours = 3, @open_imaging = 'close'" fog < sql/lost-tasks.sql
```

(`mariadb` in place of `mysql` works the same; `--init-command` sets the
variables in the session before the file runs.)

`@hours` says how long something may stay silent before it counts as
lost (12 by default). Lost tasks become Cancelled with a `taskLog` row
naming the script, sessions Cancelled with a completion time, so FOG's
multicast service stops their `udp-sender`. Imaging runs without a
finish time are deleted, because nothing proves the host finished.

An imaging run whose task was **cancelled** is taken whatever `@hours`
says, and is always deleted rather than closed. Cancelling is someone
deciding that this run ends here, so there is nothing left to wait for,
and closing it would record a deployment that was called off and set the
host's deploy time to an image it never received. This is the case that
otherwise sits in `pyfog dashboard` for half a day after a cancelled
deploy: the hosts that had got as far as `partclone` keep their open row,
while `@hours` still waits for them.
`@open_imaging = 'close'` is for the case the section below describes,
where the hosts did finish and only their report was refused: the run
is closed with the host's last progress report as finish time, the
host's deploy time is set, and the task log gets the Complete row the
host could not write, so `pyfog deployments` and `pyfog history` show
the deploy. The comment at the top of the file has the exact rules;
`pyfog tasks` and `pyfog deployments` show the result.

## Patches for the FOG server

Two patches, both against FOG 1.5.10's PHP code in the web root, both
applied with `patch -p3` from there, and both independent of each other
and of pyfog itself. Neither touches the FOG client: the client is left
as it is, and only what the server sends it changes.

### The multicast manager ends a session too early

`patches/fog-multicast-grace-period.patch` fixes a race in FOG 1.5.10's
`FOGMulticastManager` that pyfog makes visible as imaging runs FOG lost
track of. `udp-sender` exits as soon as the data is out; the receivers
still write the tail of the image, resize partitions and only then
report completion. The manager, polling every 10 seconds, sees the
sender gone and completes the session at once
(`lib/service/multicastmanager.class.php`), which sets every host's task
to Complete before the host reports. Each later report then fails with
"No Active Task found for Host", the host retries and reboots, and the
imaging log, the host's deploy time and the task log stay unwritten.

With the patch the manager keeps the session open for `FOG_CHECKIN_TIMEOUT`
seconds after the sender is gone, ends it as soon as all hosts have
reported (that path existed already), and only after the timeout treats
the remaining hosts as gone, as before. Applied from the FOG web root:

```
cd /var/www/html/fog          # wherever lib/service/multicastmanager.class.php is
patch -p3 --dry-run < /path/to/pyfog/patches/fog-multicast-grace-period.patch
patch -p3 < /path/to/pyfog/patches/fog-multicast-grace-period.patch
systemctl restart FOGMulticastManager
```

The patch is against the `stable` branch at 1.5.10.2253 and applies
cleanly there; `--dry-run` tells you whether it does on yours. The
service log (`/opt/fog/log/multicast.log`) then shows "sender finished,
waiting up to N seconds for the hosts to report" at the end of a
session.

### The server adds up to 91 seconds to every check-in

`patches/fog-client-checkin-jitter.patch` narrows the random offset the
server puts on top of `FOG_CLIENT_CHECKIN_TIME`.

The client asks the server for its configuration on every cycle and is
told how long to sleep before the next one. FOG does not send the
configured value: `lib/fog/fogpage.class.php` answers with
`FOG_CLIENT_CHECKIN_TIME + mt_rand(1, 91)`, in both places the client can
ask (`configure()` for the plain-text answer, `requestClientInfo()` for
the JSON one). The offset spreads the hosts so that they do not all call
in at the same second, which matters for a site with thousands of them.
With a few dozen machines it buys nothing and costs up to a minute and a
half on every check-in, and with it every task pickup, which is the wait
that makes a queued task look stuck. The window is a literal in FOG's
source; there is no setting for it.

The patch replaces both with `mt_rand(1, 11)`, so a check-in time of 29 s
means a sleep of 30 to 40 s instead of 30 to 120 s. Change the 11 in the
patch before applying it for a different window.

```
cd /var/www/html/fog          # wherever lib/fog/fogpage.class.php is
patch -p3 --dry-run < /path/to/pyfog/patches/fog-client-checkin-jitter.patch
patch -p3 < /path/to/pyfog/patches/fog-client-checkin-jitter.patch
```

No service needs restarting; PHP picks the file up on the next request,
and each host takes the new value at its next check-in. `pyfog info`
reads the window out of the web root and reports it, so the line under
"FOG client" says what the server actually sends.

One bound comes from the client and stays: fog-client 0.13 discards a
sleep below 30 s (or above 7200 s) and uses 60 s instead, so
`FOG_CLIENT_CHECKIN_TIME` has to stay at 29 or more — a smaller check-in
time gets you slower check-ins, not faster ones. `pyfog info` marks that
in red when the setting is too low.

## One unit for all FOG services

FOG runs as seven systemd services (`FOGImageReplicator`, `FOGImageSize`,
`FOGMulticastManager`, `FOGPingHosts`, `FOGScheduler`, `FOGSnapinHash`,
`FOGSnapinReplicator`) next to the web server, each stopped and started
on its own. `systemd/install.sh` adds one switch for all of them:

```
sudo pyfog/systemd/install.sh
systemctl restart fog.target        # or start, stop, status
systemctl status fog.slice          # the process tree of every unit in it
```

It installs `fog.target`, which wants the seven services plus the web
server (`apache2` or `httpd`) and its PHP-FPM unit, and a drop-in
`/etc/systemd/system/<unit>.d/fog.conf` for each of them with
`PartOf=fog.target` (so stop and restart of the target reach them) and
`Slice=fog.slice` (so one status shows all their processes). At boot only
`fog.target` is enabled; the individual `FOG*` units are disabled, since
the target pulls them in. FOG's own installer copies its unit files to
`/lib/systemd/system` and enables them again on an upgrade; the drop-ins
in `/etc` are untouched by that and the double enable is harmless.

The installer restarts nothing. A running service joins the slice when it
next starts, `systemctl restart fog.target` does that for all of them at
once. `--uninstall` removes the target, the slice and the drop-ins and
enables the `FOG*` units again.

## Layout

```
bin/pyfog            launcher for running from a checkout
pyfog/config.py     credential discovery
pyfog/db.py         SELECT-only queries through PyMySQL
pyfog/local.py      /proc, interfaces and ARP, access log, udpcast log
pyfog/fog.py        data layer: plain dicts, no printing
pyfog/render.py     tables for the terminal
pyfog/cli.py        argument parsing and wiring
tests/               python3 -m unittest
install.sh           installer for the FOG server
sql/lost-tasks.sql   cleanup of tasks FOG lost track of, run as database root
patches/             two fixes for FOG's web code, applied on the FOG server
systemd/             fog.target, fog.slice: all FOG services and apache2 as one unit
Makefile             make test, make smoke, make dist
```

A web front end can build on `pyfog.fog.Fog` alone; every method returns
what `--json` prints.

## Verification

pyfog is only useful if it tells the truth, so check it in three stages.

**1. Unit tests, no database.** `python3 -m unittest` covers credential
parsing, the access log and udp-sender parsing, the multicast folding,
the interface and ARP readings (both arpings' output, a wrapped byte
counter, a probe with no address to ask at) and the argument handling.

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
`PYFOG_DB_USER=fogread`, `PYFOG_DB_PASSWORD=fogread`, `PYFOG_DB_NAME=fog`
at it (`tests/reader.sql` creates that account; root is `fog`).

Any other MariaDB or MySQL works the same way; the seed uses
`NOW()`-relative timestamps, so ages and stale markers come out
plausible whenever it is loaded. What to expect from the seed: task 1
running, task 2 checked in but silent (stale), task 3 queued, tasks 4
to 6 folded into multicast session 1, pc04 with an imaging run whose task
the server closed before the host reported (task 9), a failed snapin on
pc01, and pc02 silent for two days in `clients`.

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

**3. Against the FOG server.** Run `install.sh` (see Installation), then
`pyfog info` to confirm the account, FOG version and schema version, then compare `pyfog tasks` and `pyfog multicast` with
the GUI's Active Tasks page during a deploy. `--debug` prints every SQL
statement to stderr, which is the fastest way to see why a column or
row looks different on your installation.

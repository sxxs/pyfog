#!/bin/sh
# Runs every pyfog command against the database named by PYFOG_DB_*
# (see README "Verification"). Exits non-zero on the first failure.
set -e
cd "$(dirname "$0")/.."
run() { echo "### pyfog $*"; python3 -m pyfog --no-color "$@"; echo; }
for c in info "tasks" "tasks --expand --state all" "task 5" "task 1" "history" "scheduled" \
         "multicast --all" "clients --log tests/access.log --stale 60" \
         "deployments --days 7" "deployments --current" images "hosts pc0" groups \
         "snapins" "snapins --failed"; do
    run $c
done
for c in tasks multicast clients history info images hosts; do
    python3 -m pyfog "$c" --json | python3 -c "import json, sys; json.load(sys.stdin)"
    echo "json ok: $c"
done

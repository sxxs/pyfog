"""SELECT-only access to the FOG database through PyMySQL.

Rows come back as dicts with native types: int, str, datetime. FOG's
zero dates ("0000-00-00 00:00:00") arrive as strings; util.parse_dt maps
them to None.
"""

import sys

import pymysql
import pymysql.cursors


class DatabaseError(Exception):
    pass


class Database(object):
    def __init__(self, settings, debug=False):
        host, port = settings.hostport
        values = settings.values
        self.debug = debug
        try:
            self.conn = pymysql.connect(
                host=host, port=port or 3306, user=values["DATABASE_USERNAME"],
                password=values["DATABASE_PASSWORD"], database=values["DATABASE_NAME"],
                charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                # Without autocommit InnoDB's REPEATABLE READ pins every later
                # SELECT on this connection to the first one's snapshot, so a
                # watch loop would show the same rows forever.
                autocommit=True)
        except pymysql.MySQLError as exc:
            raise DatabaseError("cannot connect to the FOG database as %s@%s: %s"
                                % (values["DATABASE_USERNAME"], host, exc))

    def close(self):
        self.conn.close()

    def query(self, sql, params=()):
        """Run one SELECT with %s placeholders; returns a list of dicts."""
        sql = " ".join(sql.split())
        if not sql.lower().startswith("select"):
            raise DatabaseError("refusing to run a non-SELECT statement")
        if self.debug:
            sys.stderr.write("-- %s  %r\n" % (sql, tuple(params)))
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                return cursor.fetchall()
        except pymysql.MySQLError as exc:
            raise DatabaseError("query failed: %s" % exc)

    def one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=()):
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

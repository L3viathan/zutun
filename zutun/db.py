import os
import base64
import sys
import sqlite3

conn = sqlite3.connect(os.environ.get("ZUTUN_DB", "zutun.db"))
conn.row_factory = sqlite3.Row
orig_isolation_level, conn.isolation_level = conn.isolation_level, None


try:
    cur = conn.cursor()
    row = cur.execute("SELECT version FROM state").fetchone()
    version = row["version"]
except sqlite3.OperationalError:
    version = 0
cur.close()


def migration(number):
    def deco(fn):
        global version
        if number >= version:
            print("Running migration", fn.__name__)
            try:
                cur = conn.cursor()
                cur.execute("BEGIN")
                fn(cur)
                cur.execute("UPDATE state SET version = ?", (version + 1,))
                cur.execute("COMMIT")
                print("Migration successful")
                version += 1
            except sqlite3.OperationalError as e:
                print("Rolling back migration:", e)
                cur.execute("ROLLBACK")
                sys.exit(1)
            cur.close()
    return deco


@migration(0)
def initial(cur):
    cur.execute( """
        CREATE TABLE state (version INTEGER)
    """)
    cur.execute("""
        INSERT INTO state (version) VALUES (0)
    """)
    cur.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            summary TEXT NOT NULL,
            description TEXT,
            state TEXT,
            storypoints INTEGER,
            assignee TEXT
        )
    """)


@migration(1)
def add_comments(cur):
    cur.execute("""
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY,
            task_id INTEGER NOT NULL,
            text TEXT,
            created_at TIMESTAMP DEFAULT (datetime('now'))
        )
    """)


@migration(2)
def add_parent_task(cur):
    cur.execute("""
        ALTER TABLE tasks
        ADD COLUMN parent_task_id INTEGER
    """)


@migration(3)
def add_selected_flag(cur):
    cur.execute("""
        ALTER TABLE tasks
        ADD COLUMN location TEXT
    """)
    cur.execute("""
        UPDATE tasks
        SET location = 'selected' WHERE state IS NOT NULL AND state <> 'Closed'
    """)
    cur.execute("""
        UPDATE tasks
        SET state='ToDo', location = 'backlog' WHERE state IS NULL
    """)
    cur.execute("""
        UPDATE tasks
        SET state='Done', location = 'graveyard' WHERE state = 'Closed'
    """)


@migration(4)
def add_users(cur):
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            avatar TEXT,
            name TEXT
        )
    """)


@migration(5)
def reset_assignees(cur):
    # Old SQLite versions (like those on Debian stable) can't drop columns.
    # We'll just ignore it from now on.
    # cur.execute("""
    #     ALTER TABLE tasks
    #     DROP COLUMN assignee
    # """)
    cur.execute("""
        ALTER TABLE tasks
        ADD COLUMN assignee_id INTEGER
    """)


conn.isolation_level = orig_isolation_level

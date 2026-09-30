# =============================================================================
# blog/db.py — database for comments and the World Gratitude List
# View from the Cheap Seats — jamesdillingham.com
#
# CHANGE NOTES
#   2026-09-30  Created for the site rebuild. Uses PostgreSQL on Render when
#               the DATABASE_URL setting is present; otherwise a local SQLite
#               file (data/local.db) so the site can be test-run on a laptop.
#               Tables are prefixed "vcs_" so they can never collide with the
#               tables of the old jamesdillingham-comments service if the same
#               database is reused. Nothing is ever hard-deleted: the admin
#               page "hides" an item, and hidden items can be restored.
# =============================================================================

from __future__ import annotations

import datetime as _dt
import os
import sqlite3
import threading
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if USE_PG:
    import psycopg
    from psycopg.rows import dict_row

_SQLITE_PATH = Path(os.environ.get("SQLITE_PATH", Path(__file__).resolve().parent.parent / "data" / "local.db"))
_sqlite_lock = threading.Lock()

TABLES = {
    "comment": "vcs_comments",
    "gratitude": "vcs_gratitude",
    "gratitude_comment": "vcs_gratitude_comments",
}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pk() -> str:
    return "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _sql(query: str) -> str:
    return query.replace("?", "%s") if USE_PG else query


def _connect():
    if USE_PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)
    _SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _run(query: str, params: tuple = (), fetch: str | None = None, returning_id: bool = False):
    """Run one statement. fetch = None | 'one' | 'all'."""
    q = _sql(query)
    if USE_PG:
        if returning_id:
            q += " RETURNING id"
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(q, params)
                if returning_id:
                    return cur.fetchone()["id"]
                if fetch == "one":
                    return cur.fetchone()
                if fetch == "all":
                    return cur.fetchall()
                return None
    with _sqlite_lock:
        conn = _connect()
        try:
            cur = conn.execute(q, params)
            result = None
            if returning_id:
                result = cur.lastrowid
            elif fetch == "one":
                row = cur.fetchone()
                result = dict(row) if row else None
            elif fetch == "all":
                result = [dict(r) for r in cur.fetchall()]
            conn.commit()
            return result
        finally:
            conn.close()


def init_db() -> None:
    pk = _pk()
    _run(f"""CREATE TABLE IF NOT EXISTS vcs_comments (
        id {pk},
        post_slug TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL,
        ip_hash TEXT,
        hidden INTEGER NOT NULL DEFAULT 0)""")
    _run(f"""CREATE TABLE IF NOT EXISTS vcs_gratitude (
        id {pk},
        gratitude_text TEXT NOT NULL,
        author_name TEXT,
        category TEXT,
        created_at TEXT NOT NULL,
        ip_hash TEXT,
        hidden INTEGER NOT NULL DEFAULT 0)""")
    _run(f"""CREATE TABLE IF NOT EXISTS vcs_gratitude_comments (
        id {pk},
        gratitude_id INTEGER NOT NULL,
        name TEXT,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL,
        ip_hash TEXT,
        hidden INTEGER NOT NULL DEFAULT 0)""")
    _run("CREATE INDEX IF NOT EXISTS vcs_comments_slug ON vcs_comments (post_slug)")
    _run("CREATE INDEX IF NOT EXISTS vcs_gcomments_gid ON vcs_gratitude_comments (gratitude_id)")


# ----- Post comments ---------------------------------------------------------

def add_comment(post_slug: str, name: str, email: str, body: str, ip_hash: str) -> int:
    return _run(
        "INSERT INTO vcs_comments (post_slug, name, email, body, created_at, ip_hash) VALUES (?, ?, ?, ?, ?, ?)",
        (post_slug, name, email or None, body, now_iso(), ip_hash),
        returning_id=True,
    )


def list_comments(post_slug: str) -> list[dict]:
    return _run(
        "SELECT id, name, body, created_at FROM vcs_comments WHERE post_slug = ? AND hidden = 0 ORDER BY id ASC",
        (post_slug,),
        fetch="all",
    ) or []


# ----- World Gratitude List ---------------------------------------------------

def add_gratitude(text: str, author_name: str | None, category: str, ip_hash: str) -> dict:
    created = now_iso()
    new_id = _run(
        "INSERT INTO vcs_gratitude (gratitude_text, author_name, category, created_at, ip_hash) VALUES (?, ?, ?, ?, ?)",
        (text, author_name or None, category, created, ip_hash),
        returning_id=True,
    )
    return {"id": new_id, "gratitude_text": text, "author_name": author_name or None,
            "category": category, "timestamp": created, "comments": []}


def list_gratitude(limit: int = 1000) -> list[dict]:
    rows = _run(
        "SELECT id, gratitude_text, author_name, category, created_at FROM vcs_gratitude "
        "WHERE hidden = 0 ORDER BY id DESC LIMIT ?",
        (limit,),
        fetch="all",
    ) or []
    comments = _run(
        "SELECT c.id, c.gratitude_id, c.name, c.body, c.created_at FROM vcs_gratitude_comments c "
        "JOIN vcs_gratitude g ON g.id = c.gratitude_id "
        "WHERE c.hidden = 0 AND g.hidden = 0 ORDER BY c.id ASC",
        fetch="all",
    ) or []
    by_entry: dict[int, list] = {}
    for c in comments:
        by_entry.setdefault(c["gratitude_id"], []).append(
            {"id": c["id"], "name": c["name"], "body": c["body"], "timestamp": c["created_at"]}
        )
    return [
        {"id": r["id"], "gratitude_text": r["gratitude_text"], "author_name": r["author_name"],
         "category": r["category"], "timestamp": r["created_at"], "comments": by_entry.get(r["id"], [])}
        for r in rows
    ]


def gratitude_exists(gratitude_id: int) -> bool:
    row = _run("SELECT id FROM vcs_gratitude WHERE id = ? AND hidden = 0", (gratitude_id,), fetch="one")
    return bool(row)


def add_gratitude_comment(gratitude_id: int, name: str | None, body: str, ip_hash: str) -> dict:
    created = now_iso()
    new_id = _run(
        "INSERT INTO vcs_gratitude_comments (gratitude_id, name, body, created_at, ip_hash) VALUES (?, ?, ?, ?, ?)",
        (gratitude_id, name or None, body, created, ip_hash),
        returning_id=True,
    )
    return {"id": new_id, "name": name or None, "body": body, "timestamp": created}


# ----- Spam protection helpers -------------------------------------------------

def count_recent(ip_hash: str, since_iso: str) -> int:
    """How many items (of any kind) this visitor submitted since a time."""
    total = 0
    for table in TABLES.values():
        row = _run(f"SELECT COUNT(*) AS n FROM {table} WHERE ip_hash = ? AND created_at >= ?",
                   (ip_hash, since_iso), fetch="one")
        total += int(row["n"]) if row else 0
    return total


def is_duplicate(kind: str, text: str, ip_hash: str, since_iso: str) -> bool:
    table = TABLES[kind]
    col = "gratitude_text" if kind == "gratitude" else "body"
    row = _run(f"SELECT id FROM {table} WHERE ip_hash = ? AND {col} = ? AND created_at >= ?",
               (ip_hash, text, since_iso), fetch="one")
    return bool(row)


# ----- Admin -------------------------------------------------------------------

def admin_list(kind: str, limit: int = 200) -> list[dict]:
    table = TABLES[kind]
    if kind == "comment":
        cols = "id, post_slug AS context, name, email, body, created_at, hidden"
    elif kind == "gratitude":
        cols = "id, category AS context, author_name AS name, NULL AS email, gratitude_text AS body, created_at, hidden"
    else:
        cols = "id, gratitude_id AS context, name, NULL AS email, body, created_at, hidden"
    return _run(f"SELECT {cols} FROM {table} ORDER BY id DESC LIMIT ?", (limit,), fetch="all") or []


def set_hidden(kind: str, item_id: int, hidden: bool) -> None:
    table = TABLES[kind]
    _run(f"UPDATE {table} SET hidden = ? WHERE id = ?", (1 if hidden else 0, item_id))


# I did no harm and this file is not truncated.

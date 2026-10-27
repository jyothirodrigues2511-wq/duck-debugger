"""
db.py - SQLite Database Management for Duck Debugger
Manages persistent bug logs, analytics queries, and initial demo data.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "duck_debugger.db")


def get_connection() -> sqlite3.Connection:
    """Creates a database connection with dict-like row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed_samples: bool = True) -> None:
    """Initializes the bugs table and optionally seeds sample data if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                bug_type TEXT NOT NULL,
                scope TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                lesson TEXT NOT NULL,
                language TEXT NOT NULL,
                description TEXT DEFAULT '',
                code_snippet TEXT DEFAULT ''
            )
            """
        )
        conn.commit()

        # Check if table is empty and seed demo data
        if seed_samples:
            cursor.execute("SELECT COUNT(*) as count FROM bugs")
            row = cursor.fetchone()
            if row and row["count"] == 0:
                seed_initial_data(conn)


def seed_initial_data(conn: sqlite3.Connection) -> None:
    """Seeds sample bugs including four recent off-by-one errors for the demo."""
    cursor = conn.cursor()
    now = datetime.now()

    sample_bugs = [
        (
            (now - timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Iterated using <= len(items) instead of < len(items), raising IndexError on the last element.",
            "I need to remember Python range() stop is exclusive, but <= with len() causes array overflow.",
            "Python",
            "Um like so I was looping through this list of user tokens and it crashed at the very end saying index out of range even though all items were valid",
            "for i in range(len(tokens) + 1):\n    process(tokens[i])"
        ),
        (
            (now - timedelta(days=2, hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Subslice omitted the last character because string slicing end index is exclusive.",
            "String slicing `[start:end]` excludes `end`, so add +1 when the boundary index is inclusive.",
            "Python",
            "So basically like I needed to slice from index 0 up to the colon character but the colon was always chopped off",
            "colon_idx = text.find(':')\nreturn text[0:colon_idx]"
        ),
        (
            (now - timedelta(days=3, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Pagination loop ran 1 too many times when total items was an exact multiple of page size.",
            "Always use `ceil(total / page_size)` or check remainder before doing `total // page_size + 1`.",
            "JavaScript",
            "Yeah uh the pager kept requesting page 5 when there are only 4 pages and the server returned 404",
            "const pages = Math.floor(total / pageSize) + 1;"
        ),
        (
            (now - timedelta(days=4, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Binary search high pointer initialization used `len(arr)` instead of `len(arr) - 1`.",
            "Set binary search `high = len(arr) - 1` when using `while low <= high`.",
            "Python",
            "Like binary search was randomly dying with index out of bounds whenever searching for missing keys",
            "low, high = 0, len(nums)\nwhile low <= high:\n    mid = (low + high) // 2"
        ),
        (
            (now - timedelta(days=5, hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "Null/Undefined Reference",
            "runtime",
            "Accessed `.user.profile` before checking if the auth session payload was resolved.",
            "Always use optional chaining or guard clauses before nested property access.",
            "JavaScript",
            "It threw cannot read properties of undefined reading profile right when the app boots up",
            "const avatar = response.data.user.profile.avatarUrl;"
        ),
        (
            (now - timedelta(days=6, hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            "Type Coercion",
            "type error",
            "Added string input from form to an integer counter, resulting in string concatenation instead of addition.",
            "Explicitly cast numeric form inputs with `int()` or `Number()` before mathematical operations.",
            "Python",
            "Like the user typed 5 and instead of getting 15 points it gave 105 points in the database",
            "points = user_record['points'] + request_data['bonus']"
        )
    ]

    cursor.executemany(
        """
        INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sample_bugs
    )
    conn.commit()


def save_bug(
    bug_type: str,
    scope: str,
    root_cause: str,
    lesson: str,
    language: str,
    description: str = "",
    code_snippet: str = ""
) -> int:
    """Saves a new solved bug entry and returns its generated ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now_str, bug_type, scope, root_cause, lesson, language, description, code_snippet)
        )
        conn.commit()
        return cursor.lastrowid


def get_all_bugs(query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all bugs, optionally filtering by keyword across root_cause, lesson, and bug_type."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if query and query.strip():
            wildcard = f"%{query.strip()}%"
            cursor.execute(
                """
                SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
                FROM bugs
                WHERE root_cause LIKE ? OR lesson LIKE ? OR bug_type LIKE ? OR language LIKE ?
                ORDER BY id DESC
                """,
                (wildcard, wildcard, wildcard, wildcard)
            )
        else:
            cursor.execute(
                """
                SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
                FROM bugs
                ORDER BY id DESC
                """
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_bug_stats() -> Dict[str, Any]:
    """
    Computes bug type frequencies, weekly counts, and identifies the top weak spot.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Distribution across all bugs
        cursor.execute(
            """
            SELECT bug_type, COUNT(*) as count
            FROM bugs
            GROUP BY bug_type
            ORDER BY count DESC
            """
        )
        type_counts = {row["bug_type"]: row["count"] for row in cursor.fetchall()}

        # Weekly calculations (last 7 days)
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            SELECT bug_type, COUNT(*) as week_count
            FROM bugs
            WHERE timestamp >= ?
            GROUP BY bug_type
            ORDER BY week_count DESC
            """,
            (seven_days_ago,)
        )
        week_rows = cursor.fetchall()

        top_weak_spot = None
        top_weak_spot_count = 0
        if week_rows:
            top_weak_spot = week_rows[0]["bug_type"]
            top_weak_spot_count = week_rows[0]["week_count"]
        elif type_counts:
            top_weak_spot = list(type_counts.keys())[0]
            top_weak_spot_count = list(type_counts.values())[0]

        total_bugs = sum(type_counts.values())

        return {
            "total_bugs": total_bugs,
            "type_counts": type_counts,
            "top_weak_spot": top_weak_spot or "None yet",
            "top_weak_spot_count": top_weak_spot_count
        }

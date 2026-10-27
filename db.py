"""
db.py - SQLite Database Management for Duck Debugger
Manages persistent bug logs, analytics queries, and initial demo data.
Robust against concurrency, connection leaks, malformed files, and locked handles.
"""

import sqlite3
import os
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def _resolve_writable_db_path() -> str:
    """
    Resolves a writable database path for local and cloud environments.
    Supports DUCK_DEBUGGER_DB_PATH override, then default repo directory,
    falling back to user home or temp directory if repository directory is read-only.
    """
    custom = os.environ.get("DUCK_DEBUGGER_DB_PATH")
    if custom:
        target_dir = os.path.dirname(os.path.abspath(custom))
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        return os.path.abspath(custom)

    default_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        os.makedirs(default_dir, exist_ok=True)
        test_file = os.path.join(default_dir, ".write_test")
        with open(test_file, "a") as f:
            pass
        os.remove(test_file)
        return os.path.join(default_dir, "duck_debugger.db")
    except (OSError, PermissionError):
        pass

    import tempfile
    fallback_dir = os.path.join(tempfile.gettempdir(), "duck_debugger")
    os.makedirs(fallback_dir, exist_ok=True)
    return os.path.join(fallback_dir, "duck_debugger.db")


DB_PATH = _resolve_writable_db_path()
_INIT_LOCK = threading.Lock()
_DB_INITIALIZED = False


class ManagedConnection(sqlite3.Connection):
    """
    Subclass of sqlite3.Connection that ensures the connection and underlying
    OS file handle are explicitly closed when exiting a context manager block.
    Standard sqlite3.Connection.__exit__ only commits/rolls back transactions
    without closing the connection, causing severe resource and lock leaks on Windows.
    """
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


def _create_raw_connection(timeout: float = 15.0) -> sqlite3.Connection:
    """Creates a raw SQLite connection ensuring parent directory exists."""
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(
        DB_PATH,
        timeout=timeout,
        factory=ManagedConnection,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)};")
    return conn


def get_connection(timeout: float = 15.0) -> sqlite3.Connection:
    """
    Creates a database connection with dict-like row factory and auto-closing context manager.
    Configures busy timeout to prevent 'database is locked' errors under concurrent load.
    Ensures schema is initialized and seeded on first access.
    """
    global _DB_INITIALIZED
    if not _DB_INITIALIZED or not os.path.exists(DB_PATH):
        init_db(seed_samples=True)

    return _create_raw_connection(timeout=timeout)


def _configure_database_pragmas() -> None:
    """Enables Write-Ahead Logging (WAL) and normal synchronous mode for concurrency."""
    try:
        db_dir = os.path.dirname(os.path.abspath(DB_PATH))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        try:
            conn.isolation_level = None  # Autocommit mode required for journal_mode pragma
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("Could not configure WAL pragmas: %s", e)


def init_db(seed_samples: bool = True) -> None:
    """
    Initializes the bugs table, creates performance indexes, enables WAL mode,
    and seeds sample data if empty. Recovers gracefully if file corruption is detected.
    """
    with _INIT_LOCK:
        try:
            _init_db_core(seed_samples=seed_samples)
        except sqlite3.DatabaseError as e:
            logger.error("Database corruption detected at %s: %s. Quarantining and recreating.", DB_PATH, e)
            _quarantine_corrupted_db()
            _init_db_core(seed_samples=seed_samples)


def _quarantine_corrupted_db() -> None:
    """Quarantines corrupted database file to allow fresh initialization."""
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    corrupt_backup = f"{DB_PATH}.corrupted_{timestamp_str}"
    try:
        if os.path.exists(DB_PATH):
            os.replace(DB_PATH, corrupt_backup)
            logger.info("Quarantined corrupt database to %s", corrupt_backup)
    except OSError as e:
        logger.error("Failed to quarantine corrupt db file: %s", e)


def reset_demo_data() -> None:
    """Resets the bugs table to the clean demo baseline with 6 realistic bugs."""
    with _INIT_LOCK:
        with _create_raw_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bugs;")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='bugs';")
            conn.commit()
            seed_initial_data(conn)


def _init_db_core(seed_samples: bool = True) -> None:
    global _DB_INITIALIZED
    # Set WAL mode outside transaction first
    _configure_database_pragmas()

    with _create_raw_connection() as conn:
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_timestamp ON bugs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_bug_type ON bugs(bug_type);")
        conn.commit()

        # Check if table is empty and seed demo data
        if seed_samples:
            cursor.execute("SELECT COUNT(*) as count FROM bugs")
            row = cursor.fetchone()
            if row and row["count"] == 0:
                seed_initial_data(conn)

    _DB_INITIALIZED = True


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
    """
    Saves a new solved bug entry with parameter normalization and returns its generated ID.
    Ensures safe transaction commit and releases connections immediately.
    """
    clean_bug_type = str(bug_type or "").strip() or "General"
    clean_scope = str(scope or "").strip() or "logic"
    clean_root_cause = str(root_cause or "").strip() or "No root cause documented"
    clean_lesson = str(lesson or "").strip() or "No lesson documented"
    clean_language = str(language or "").strip() or "General"
    clean_description = str(description or "").strip()
    clean_code_snippet = str(code_snippet or "").strip()

    with get_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_str,
                clean_bug_type,
                clean_scope,
                clean_root_cause,
                clean_lesson,
                clean_language,
                clean_description,
                clean_code_snippet
            )
        )
        conn.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("Database error: failed to retrieve lastrowid for inserted bug.")
        return cursor.lastrowid


def get_all_bugs(query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all bugs, optionally filtering by keyword across root_cause, lesson,
    bug_type, and language. Safely escapes SQL LIKE wildcards (% and _) to avoid wildcard injection,
    strips null bytes, and bounds query length to avoid SQLite LIKE pattern complexity errors.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if query and isinstance(query, str) and query.strip():
                # Sanitize and bound query to 500 chars to avoid pattern-complexity limits
                clean_query = query.strip().replace("\x00", "")[:500]
                if not clean_query:
                    cursor.execute("SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet FROM bugs ORDER BY id DESC")
                    return [dict(row) for row in cursor.fetchall()]

                # Escape LIKE wildcards to prevent wildcard injection
                escaped = (
                    clean_query.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                wildcard = f"%{escaped}%"
                cursor.execute(
                    """
                    SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
                    FROM bugs
                    WHERE root_cause LIKE ? ESCAPE '\\'
                       OR lesson LIKE ? ESCAPE '\\'
                       OR bug_type LIKE ? ESCAPE '\\'
                       OR language LIKE ? ESCAPE '\\'
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
    except sqlite3.OperationalError as oe:
        logger.warning("SQLite operational warning during search: %s", oe)
        return []
    except sqlite3.Error as e:
        logger.error("Error executing get_all_bugs: %s", e)
        return []


def get_bug_stats() -> Dict[str, Any]:
    """
    Computes bug type frequencies, weekly counts, and identifies the top weak spot.
    Returns safe default structures if database is inaccessible or empty.
    """
    try:
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
    except sqlite3.Error as e:
        logger.error("Error retrieving bug stats: %s", e)
        return {
            "total_bugs": 0,
            "type_counts": {},
            "top_weak_spot": "None yet",
            "top_weak_spot_count": 0
        }

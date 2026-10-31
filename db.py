"""
db.py - SQLite Database Management for Duck Debugger
Manages persistent bug logs, analytics queries, and initial demo data.
Robust against concurrency, connection leaks, malformed files, and locked handles.
"""

import sqlite3
import os
import threading
import logging
import csv
import io
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
        with open(test_file, "a"):
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
                code_snippet TEXT DEFAULT '',
                turn_count INTEGER DEFAULT 1,
                duration_seconds REAL DEFAULT 0.0
            )
            """
        )
        cursor.execute("PRAGMA table_info(bugs);")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        if "turn_count" not in existing_cols:
            cursor.execute("ALTER TABLE bugs ADD COLUMN turn_count INTEGER DEFAULT 1;")
        if "duration_seconds" not in existing_cols:
            cursor.execute("ALTER TABLE bugs ADD COLUMN duration_seconds REAL DEFAULT 0.0;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_timestamp ON bugs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_bug_type ON bugs(bug_type);")
        conn.commit()

        # Check if table is empty and seed demo data
        seed_env = os.environ.get("DUCK_DEBUGGER_SEED", "1").strip().lower()
        allow_seed = seed_samples and (seed_env not in ("0", "false", "no"))
        if allow_seed:
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
            "for i in range(len(tokens) + 1):\n    process(tokens[i])",
            3,
            195.0
        ),
        (
            (now - timedelta(days=2, hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Subslice omitted the last character because string slicing end index is exclusive.",
            "String slicing `[start:end]` excludes `end`, so add +1 when the boundary index is inclusive.",
            "Python",
            "So basically like I needed to slice from index 0 up to the colon character but the colon was always chopped off",
            "colon_idx = text.find(':')\nreturn text[0:colon_idx]",
            2,
            140.0
        ),
        (
            (now - timedelta(days=3, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Pagination loop ran 1 too many times when total items was an exact multiple of page size.",
            "Always use `ceil(total / page_size)` or check remainder before doing `total // page_size + 1`.",
            "JavaScript",
            "Yeah uh the pager kept requesting page 5 when there are only 4 pages and the server returned 404",
            "const pages = Math.floor(total / pageSize) + 1;",
            4,
            260.0
        ),
        (
            (now - timedelta(days=4, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "Off-by-one",
            "logic",
            "Binary search high pointer initialization used `len(arr)` instead of `len(arr) - 1`.",
            "Set binary search `high = len(arr) - 1` when using `while low <= high`.",
            "Python",
            "Like binary search was randomly dying with index out of bounds whenever searching for missing keys",
            "low, high = 0, len(nums)\nwhile low <= high:\n    mid = (low + high) // 2",
            3,
            210.0
        ),
        (
            (now - timedelta(days=5, hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "Null/Undefined Reference",
            "runtime",
            "Accessed `.user.profile` before checking if the auth session payload was resolved.",
            "Always use optional chaining or guard clauses before nested property access.",
            "JavaScript",
            "It threw cannot read properties of undefined reading profile right when the app boots up",
            "const avatar = response.data.user.profile.avatarUrl;",
            2,
            120.0
        ),
        (
            (now - timedelta(days=6, hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            "Type Coercion",
            "type error",
            "Added string input from form to an integer counter, resulting in string concatenation instead of addition.",
            "Explicitly cast numeric form inputs with `int()` or `Number()` before mathematical operations.",
            "Python",
            "Like the user typed 5 and instead of getting 15 points it gave 105 points in the database",
            "points = user_record['points'] + request_data['bonus']",
            2,
            135.0
        )
    ]

    cursor.executemany(
        """
        INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet, turn_count, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    code_snippet: str = "",
    turn_count: int = 1,
    duration_seconds: float = 0.0
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
    safe_turn_count = max(1, int(turn_count or 1))
    safe_duration = max(0.0, float(duration_seconds or 0.0))

    with get_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet, turn_count, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_str,
                clean_bug_type,
                clean_scope,
                clean_root_cause,
                clean_lesson,
                clean_language,
                clean_description,
                clean_code_snippet,
                safe_turn_count,
                safe_duration
            )
        )
        conn.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("Database error: failed to retrieve lastrowid for inserted bug.")
        return cursor.lastrowid


def resolve_time_cutoff(time_range: Optional[str]) -> Optional[str]:
    """
    Resolves human and code time range descriptors into an ISO datetime string cutoff.
    Returns None for 'all' or unrecognized strings.
    """
    if not time_range:
        return None
    low = str(time_range).strip().lower()
    if low in ("30d", "last 30 days", "30 days", "last_30_days", "30"):
        return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    if low in ("quarter", "this quarter", "quarterly", "this_quarter", "90d", "90 days", "90"):
        return (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
    return None


def get_all_bugs(query: Optional[str] = None, time_range: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all bugs, optionally filtering by keyword across root_cause, lesson,
    bug_type, and language, and optionally by time_range ('30d', 'quarter', 'all').
    Safely escapes SQL LIKE wildcards (% and _) to avoid wildcard injection,
    strips null bytes, and bounds query length to avoid SQLite LIKE pattern complexity errors.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cutoff = resolve_time_cutoff(time_range)

            if query and isinstance(query, str) and query.strip():
                # Sanitize and bound query to 500 chars to avoid pattern-complexity limits
                clean_query = query.strip().replace("\x00", "")[:500]
                if not clean_query:
                    if cutoff:
                        cursor.execute(
                            "SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet FROM bugs WHERE timestamp >= ? ORDER BY id DESC",
                            (cutoff,)
                        )
                    else:
                        cursor.execute(
                            "SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet FROM bugs ORDER BY id DESC"
                        )
                    return [dict(row) for row in cursor.fetchall()]

                # Escape LIKE wildcards to prevent wildcard injection
                escaped = (
                    clean_query.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                wildcard = f"%{escaped}%"
                if cutoff:
                    cursor.execute(
                        """
                        SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
                        FROM bugs
                        WHERE (root_cause LIKE ? ESCAPE '\\'
                           OR lesson LIKE ? ESCAPE '\\'
                           OR bug_type LIKE ? ESCAPE '\\'
                           OR language LIKE ? ESCAPE '\\')
                          AND timestamp >= ?
                        ORDER BY id DESC
                        """,
                        (wildcard, wildcard, wildcard, wildcard, cutoff)
                    )
                else:
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
                if cutoff:
                    cursor.execute(
                        """
                        SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
                        FROM bugs
                        WHERE timestamp >= ?
                        ORDER BY id DESC
                        """,
                        (cutoff,)
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


def compute_bug_streak(target_date: Optional[datetime.date] = None) -> int:
    """
    Computes consecutive days with at least one solved bug.
    Counts backwards starting from target_date (defaults to today).
    If no bugs exist today or yesterday, active streak is 0.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT SUBSTR(timestamp, 1, 10) as day_str
                FROM bugs
                WHERE timestamp IS NOT NULL AND timestamp != ''
                ORDER BY day_str DESC
                """
            )
            rows = cursor.fetchall()
            if not rows:
                return 0

            days = set()
            for r in rows:
                try:
                    d = datetime.strptime(r["day_str"][:10], "%Y-%m-%d").date()
                    days.add(d)
                except Exception:
                    pass

            if not days:
                return 0

            ref_date = target_date or datetime.now().date()
            if ref_date in days:
                curr = ref_date
            elif (ref_date - timedelta(days=1)) in days:
                curr = ref_date - timedelta(days=1)
            else:
                return 0

            streak = 0
            while curr in days:
                streak += 1
                curr -= timedelta(days=1)

            return streak
    except Exception as e:
        logger.error("Error computing bug streak: %s", e)
        return 0


def get_bug_stats(time_range: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes bug type frequencies, weekly counts, streak, average turnaround,
    and scope breakdown directly from SQLite, optionally filtered by time_range ('30d', 'quarter', 'all').
    Returns safe default structures if database is inaccessible or empty.
    Never invents statistics.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cutoff = resolve_time_cutoff(time_range)

            if cutoff:
                cursor.execute("SELECT COUNT(*) as total FROM bugs WHERE timestamp >= ?", (cutoff,))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM bugs")
            total_bugs = cursor.fetchone()["total"]

            if total_bugs == 0:
                return {
                    "total_bugs": 0,
                    "type_counts": {},
                    "top_weak_spot": "No data yet",
                    "top_weak_spot_count": 0,
                    "top_weak_spot_pct": 0,
                    "streak": 0,
                    "avg_turns": 0.0,
                    "avg_duration_seconds": 0.0,
                    "logic_count": 0,
                    "runtime_count": 0,
                    "state_count": 0,
                    "logic_pct": 0,
                    "runtime_pct": 0,
                    "state_pct": 0,
                    "has_data": False
                }

            # Distribution across bugs
            if cutoff:
                cursor.execute(
                    """
                    SELECT bug_type, COUNT(*) as count
                    FROM bugs
                    WHERE timestamp >= ?
                    GROUP BY bug_type
                    ORDER BY count DESC
                    """,
                    (cutoff,)
                )
            else:
                cursor.execute(
                    """
                    SELECT bug_type, COUNT(*) as count
                    FROM bugs
                    GROUP BY bug_type
                    ORDER BY count DESC
                    """
                )
            type_counts = {row["bug_type"]: row["count"] for row in cursor.fetchall()}

            # Weekly calculations (last 7 days or cutoff)
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

            top_weak_spot_pct = int(round((top_weak_spot_count / total_bugs * 100))) if total_bugs > 0 else 0

            # Averages from SQLite
            if cutoff:
                cursor.execute(
                    "SELECT AVG(turn_count) as avg_t, AVG(duration_seconds) as avg_d FROM bugs WHERE timestamp >= ?",
                    (cutoff,)
                )
            else:
                cursor.execute("SELECT AVG(turn_count) as avg_t, AVG(duration_seconds) as avg_d FROM bugs")
            avg_row = cursor.fetchone()
            avg_turns = float(avg_row["avg_t"]) if avg_row and avg_row["avg_t"] is not None else 1.0
            avg_duration_seconds = float(avg_row["avg_d"]) if avg_row and avg_row["avg_d"] is not None else 0.0

            # Scope counts
            if cutoff:
                cursor.execute(
                    """
                    SELECT scope, COUNT(*) as sc_count
                    FROM bugs
                    WHERE timestamp >= ?
                    GROUP BY scope
                    """,
                    (cutoff,)
                )
            else:
                cursor.execute(
                    """
                    SELECT scope, COUNT(*) as sc_count
                    FROM bugs
                    GROUP BY scope
                    """
                )
            scope_rows = cursor.fetchall()
            logic_count = sum(r["sc_count"] for r in scope_rows if any(k in (r["scope"] or "").lower() for k in ("logic", "index", "syntax")))
            runtime_count = sum(r["sc_count"] for r in scope_rows if any(k in (r["scope"] or "").lower() for k in ("runtime", "null", "type")))
            state_count = max(0, total_bugs - (logic_count + runtime_count))

            logic_pct = int(round((logic_count / total_bugs * 100)))
            runtime_pct = int(round((runtime_count / total_bugs * 100)))
            state_pct = max(0, 100 - (logic_pct + runtime_pct))

            streak = compute_bug_streak()

            return {
                "total_bugs": total_bugs,
                "type_counts": type_counts,
                "top_weak_spot": top_weak_spot or "No data yet",
                "top_weak_spot_count": top_weak_spot_count,
                "top_weak_spot_pct": top_weak_spot_pct,
                "streak": streak,
                "avg_turns": round(avg_turns, 1),
                "avg_duration_seconds": round(avg_duration_seconds, 1),
                "logic_count": logic_count,
                "runtime_count": runtime_count,
                "state_count": state_count,
                "logic_pct": logic_pct,
                "runtime_pct": runtime_pct,
                "state_pct": state_pct,
                "has_data": True
            }
    except sqlite3.Error as e:
        logger.error("Error retrieving bug stats: %s", e)
        return {
            "total_bugs": 0,
            "type_counts": {},
            "top_weak_spot": "No data yet",
            "top_weak_spot_count": 0,
            "top_weak_spot_pct": 0,
            "streak": 0,
            "avg_turns": 0.0,
            "avg_duration_seconds": 0.0,
            "logic_count": 0,
            "runtime_count": 0,
            "state_count": 0,
            "logic_pct": 0,
            "runtime_pct": 0,
            "state_pct": 0,
            "has_data": False
        }


def export_bugs_csv(time_range: Optional[str] = None) -> str:
    """
    Exports all logged bugs (optionally filtered by time_range) as a CSV string.
    Includes bug identifier, timestamp, language, category, scope, root cause, and lesson.
    """
    bugs = get_all_bugs(time_range=time_range)
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "ID",
        "Timestamp",
        "Language",
        "Bug Type",
        "Scope",
        "Root Cause",
        "Lesson",
        "Turn Count",
        "Duration (s)",
        "Voice Description",
        "Code Snippet"
    ])
    for b in bugs:
        code_id = f"DBG-{8900 + b['id']}"
        writer.writerow([
            code_id,
            b.get("timestamp") or "",
            b.get("language") or "",
            b.get("bug_type") or "",
            b.get("scope") or "",
            b.get("root_cause") or "",
            b.get("lesson") or "",
            b.get("turn_count") or 1,
            b.get("duration_seconds") or 0.0,
            b.get("description") or "",
            b.get("code_snippet") or ""
        ])
    return output.getvalue()


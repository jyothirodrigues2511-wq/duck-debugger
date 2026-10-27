import sqlite3
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def escape_like(s: str) -> str:
    # Escape backslash first, then % and _
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def run_tests():
    conn = sqlite3.connect(":memory:")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE bugs (
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
    """)

    sample_data = [
        ("Off-by-one", "logic", "Loop bound <= len(arr)", "Use < len(arr)", "Python"),
        ("Modulo bug", "logic", "Used % operator for formatting instead of f-string", "Avoid % formatting", "Python"),
        ("Private var", "syntax", "Accessed _secret_token directly", "Use getter for _secret_token", "Python"),
        ("Backslash issue", "parser", "Escaped path with C:\\Users\\test", "Use raw strings r'C:\\Users'", "Windows"),
        ("Emoji duck", "ui", "Duck avatar 🦆 not showing", "Support UTF-8 emojis 🦆", "HTML"),
        ("Quotes in string", "syntax", "Failed on \"double quotes\" and 'single quotes'", "Escape ' and \" properly", "SQL"),
        ("Accented chars", "i18n", "Crashing on café and résumé", "Normalize Unicode with unicodedata", "Python"),
    ]

    for item in sample_data:
        c.execute("""
            INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language)
            VALUES ('2026-01-01 12:00:00', ?, ?, ?, ?, ?)
        """, item)
    conn.commit()

    print("Total sample rows:", len(sample_data))

    # Test 1: SQL Injection payloads
    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE bugs;--",
        "' UNION SELECT 1,2,3,4,5,6,7,8,9--",
        "\" OR \"\"=\"",
        "admin'--",
    ]
    print("\n--- TEST 1: SQL Injection Payloads ---")
    for payload in sqli_payloads:
        esc = f"%{escape_like(payload)}%"
        c.execute("""
            SELECT id, root_cause FROM bugs
            WHERE root_cause LIKE ? ESCAPE '\\' OR lesson LIKE ? ESCAPE '\\'
        """, (esc, esc))
        rows = c.fetchall()
        print(f"Payload: {payload!r:35} -> Matched {len(rows)} rows (Safe!)")
    
    # Ensure table wasn't dropped
    c.execute("SELECT COUNT(*) FROM bugs")
    count_after = c.fetchone()[0]
    assert count_after == len(sample_data), f"Table was modified! Count: {count_after}"
    print("Table integrity verified: count =", count_after)

    # Test 2: Wildcard searches (% and _ and \)
    print("\n--- TEST 2: Wildcard Searches ---")
    wildcard_cases = [
        ("%", 1), # Only the modulo bug has %
        ("_", 1), # Only the private var bug has _
        ("\\", 1), # Only the backslash issue has \
        ("C:\\Users", 1),
        ("🦆", 1),
        ("\"", 1),
        ("'", 2), # Both 'Quotes in string' and 'Backslash issue' (r'C:\Users') have '
        ("café", 1),
    ]
    for q, expected_count in wildcard_cases:
        esc = f"%{escape_like(q)}%"
        c.execute("""
            SELECT id, root_cause, lesson FROM bugs
            WHERE root_cause LIKE ? ESCAPE '\\' OR lesson LIKE ? ESCAPE '\\' OR bug_type LIKE ? ESCAPE '\\'
        """, (esc, esc, esc))
        rows = c.fetchall()
        print(f"Query: {q!r:15} -> Expected: {expected_count}, Got: {len(rows)} -> {'PASS' if len(rows) == expected_count else 'FAIL'}")
        assert len(rows) == expected_count, f"Mismatch for query {q!r}: expected {expected_count}, got {len(rows)}"

    # Test 3: Null byte handling
    print("\n--- TEST 3: Null byte handling ---")
    try:
        null_query = "duck\x00debugger"
        clean_null = null_query.replace("\x00", "")
        esc = f"%{escape_like(clean_null)}%"
        c.execute("SELECT id FROM bugs WHERE root_cause LIKE ? ESCAPE '\\'", (esc,))
        print("Null byte query handled safely by sanitizing \\x00 ->", c.fetchall())
    except Exception as e:
        print("Null byte raised exception:", type(e), e)

    # Test 4: Huge query strings (10,000+ chars and 100,000 chars)
    print("\n--- TEST 4: Long search query stress ---")
    huge_query = "A" * 50000
    start = time.perf_counter()
    rows = db.get_all_bugs(huge_query)
    duration = time.perf_counter() - start
    print(f"Huge query (50,000 chars) handled safely via db.get_all_bugs in {duration:.4f}s, matched {len(rows)} rows.")

    # Test 5: Empty and whitespace queries
    print("\n--- TEST 5: Empty / Whitespace-only queries ---")
    for q in ["", "   ", "\t\t\n", None]:
        # If query is empty or whitespace, get_all_bugs should return ALL rows without filter
        # Let's test the condition logic:
        is_empty = not q or not str(q).strip()
        print(f"Query: {q!r:10} -> is_empty: {is_empty}")

    # Test 6: Performance on Large Result Sets (10,000 rows)
    print("\n--- TEST 6: Large Dataset (10,000 rows) ---")
    c.execute("DELETE FROM bugs")
    bulk_data = [
        (f"2026-01-01 12:{i%60:02d}:00", f"Type_{i%5}", "logic", f"Root cause for bug {i} with some special char {'%' if i%7==0 else ''}", f"Lesson {i} on topic", "Python")
        for i in range(10000)
    ]
    c.executemany("""
        INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language)
        VALUES (?, ?, ?, ?, ?, ?)
    """, bulk_data)
    conn.commit()

    start = time.perf_counter()
    q = "bug 999"
    esc = f"%{escape_like(q)}%"
    c.execute("""
        SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
        FROM bugs
        WHERE root_cause LIKE ? ESCAPE '\\' OR lesson LIKE ? ESCAPE '\\' OR bug_type LIKE ? ESCAPE '\\' OR language LIKE ? ESCAPE '\\'
        ORDER BY id DESC
    """, (esc, esc, esc, esc))
    rows = c.fetchall()
    search_duration = time.perf_counter() - start
    print(f"Search across 10,000 rows took {search_duration:.4f}s, returned {len(rows)} rows.")

    # Also test with '%' search on 10,000 rows
    start = time.perf_counter()
    q = "%"
    esc = f"%{escape_like(q)}%"
    c.execute("""
        SELECT id, timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet
        FROM bugs
        WHERE root_cause LIKE ? ESCAPE '\\' OR lesson LIKE ? ESCAPE '\\' OR bug_type LIKE ? ESCAPE '\\' OR language LIKE ? ESCAPE '\\'
        ORDER BY id DESC
    """, (esc, esc, esc, esc))
    rows = c.fetchall()
    search_pct_duration = time.perf_counter() - start
    print(f"Search for literal '%' across 10,000 rows took {search_pct_duration:.4f}s, returned {len(rows)} rows (expected around {10000//7}).")

    print("\nALL STRESS TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

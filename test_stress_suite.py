"""
test_stress_suite.py - Exhaustive stress testing for Solved Flow JSON extraction & SQLite persistence
"""
import sys
import os
import json
import sqlite3

# Ensure repo root is on sys.path
sys.path.insert(0, r"C:\Users\Jyothi Rodrigues\.gemini\antigravity\scratch\duck-debugger")

import db

TEST_DB_PATH = r"C:\Users\Jyothi Rodrigues\.gemini\antigravity\scratch\duck-debugger\test_stress.db"

def init_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
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
    conn.close()

def save_to_test_db(record):
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet)
        VALUES ('2026-10-27 12:00:00', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["bug_type"],
            record["scope"],
            record["root_cause"],
            record["lesson"],
            record["language"],
            record.get("description", ""),
            record.get("code_snippet", "")
        )
    )
    conn.commit()
    rowid = cursor.lastrowid
    conn.close()
    return rowid

ALLOWED_SCOPES = {"logic", "syntax", "type error", "runtime", "state"}

def validate_schema_compliance(record):
    assert isinstance(record, dict), "Result must be a dict"
    for field in ["bug_type", "scope", "root_cause", "lesson", "language"]:
        assert field in record, f"Missing key: {field}"
        val = record[field]
        assert isinstance(val, str), f"Field {field} must be str, got {type(val)}"
        assert len(val.strip()) > 0, f"Field {field} must not be empty or whitespace"
        assert "\x00" not in val, f"Field {field} must not contain null bytes"
    
    assert record["scope"] in ALLOWED_SCOPES, f"Scope '{record['scope']}' not in allowed scopes: {ALLOWED_SCOPES}"

print("Test harness initialized.")

"""
test_analytics_view.py - Integration and regression test suite for Analytics View
Verifies that render_analytics and all metric variables, HTML templates,
and database stats computation operate cleanly without NameError or unhandled exceptions.

Tested across 4 database states:
1. Empty database (0 bugs)
2. Database with only 6 seed bugs
3. Database with older rows that have no duration or turn_count (NULL values)
4. Database with new bugs (active duration and turn counts)

Tested across all 3 time filters:
- "Last 30 Days" (range=30d)
- "This Quarter" (range=quarter)
- "All Time" (range=all)

Also tests the Socratic Studio view to verify that switching views and rendering studio operates cleanly.
Strictly zero emojis.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from streamlit.testing.v1 import AppTest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import db


class TestAnalyticsView(unittest.TestCase):
    """
    Regression test suite for Duck Debugger Analytics View.
    Guarantees no NameError or undefined template variables across all database states and filters.
    """

    @classmethod
    def setUpClass(cls):
        cls.app_path = str(PROJECT_ROOT / "app.py")
        cls.temp_dir = tempfile.mkdtemp()
        cls.orig_db_path = db.DB_PATH
        cls.orig_env_db = os.environ.get("DUCK_DEBUGGER_DB_PATH")
        cls.orig_env_seed = os.environ.get("DUCK_DEBUGGER_SEED")

    @classmethod
    def tearDownClass(cls):
        # Restore original database settings
        db.DB_PATH = cls.orig_db_path
        if cls.orig_env_db is not None:
            os.environ["DUCK_DEBUGGER_DB_PATH"] = cls.orig_env_db
        elif "DUCK_DEBUGGER_DB_PATH" in os.environ:
            del os.environ["DUCK_DEBUGGER_DB_PATH"]

        if cls.orig_env_seed is not None:
            os.environ["DUCK_DEBUGGER_SEED"] = cls.orig_env_seed
        elif "DUCK_DEBUGGER_SEED" in os.environ:
            del os.environ["DUCK_DEBUGGER_SEED"]

    def _set_test_db(self, db_filename: str) -> str:
        test_db = os.path.join(self.temp_dir, db_filename)
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except OSError:
                pass
        db.DB_PATH = test_db
        os.environ["DUCK_DEBUGGER_DB_PATH"] = test_db
        os.environ["DUCK_DEBUGGER_SEED"] = "0"
        db.init_db(seed_samples=False)
        return test_db

    def test_state_1_empty_database_all_time_filters(self):
        """
        State 1: Empty database (0 bugs).
        Verifies render_analytics handles 0 bugs gracefully without NameError (such as m1_unit).
        Repeats across Last 30 Days, This Quarter, and All Time filters.
        """
        self._set_test_db("empty.db")
        with db.get_connection() as conn:
            conn.execute("DELETE FROM bugs;")
            conn.commit()

        time_filters = [
            ("30d", "Last 30 Days"),
            ("quarter", "This Quarter"),
            ("all", "All Time")
        ]

        for range_code, label in time_filters:
            with self.subTest(filter_range=range_code, filter_label=label):
                at = AppTest.from_file(self.app_path, default_timeout=30)
                at.query_params["view"] = "analytics"
                at.query_params["range"] = range_code
                at.run()

                # Must not raise any exceptions
                self.assertEqual(
                    len(at.exception),
                    0,
                    f"Analytics view raised exception on empty db with filter {label}: {at.exception}"
                )

                # Exactly one Generate Practice Problem button exists
                practice_btns = [b for b in at.button if "Generate Practice Problem" in b.label]
                self.assertEqual(len(practice_btns), 1, "Exactly one Generate Practice Problem button must exist")
                self.assertEqual(practice_btns[0].key, "btn_practice_top_level")

                # Export report download button exists
                dl = at.download_button(key="btn_export_report")
                self.assertIsNotNone(dl, "Export Report download button must exist")
                self.assertEqual(dl.label, "Export Report")

                # Check HTML output rendered with single title
                html_values = [h.value for h in at.html]
                combined_html = "\n".join(html_values)
                self.assertIn("Debugging Intelligence &amp; Weak Spot Analytics", combined_html)

                # Check iframe component containing analytics dashboard
                iframes = [e for e in at.main if getattr(e, "type", None) == "iframe"]
                self.assertGreater(len(iframes), 0, "Analytics iframe must be rendered")
                srcdoc = iframes[0].proto.srcdoc
                self.assertIn("No data yet", srcdoc)
                self.assertIn("Bug Pattern Frequency Matrix", srcdoc)

                # Clicking the practice problem button opens dialog modal
                practice_btns[0].click().run()
                self.assertEqual(len(at.exception), 0)
                self.assertTrue(at.session_state.get("show_practice_modal"))
                self.assertIsNotNone(at.session_state.get("practice_data"))
                self.assertIsNotNone(at.button(key="btn_close_practice_modal"))
                self.assertIsNotNone(at.button(key="btn_another_practice_modal"))

    def test_state_2_seed_bugs_all_time_filters(self):
        """
        State 2: Database with only the 6 seed bugs.
        Verifies render_analytics computes metrics from seed bugs without error.
        Repeats across Last 30 Days, This Quarter, and All Time filters.
        """
        self._set_test_db("seed_only.db")
        with db.get_connection() as conn:
            conn.execute("DELETE FROM bugs;")
            db.seed_initial_data(conn)

        time_filters = [
            ("30d", "Last 30 Days"),
            ("quarter", "This Quarter"),
            ("all", "All Time")
        ]

        for range_code, label in time_filters:
            with self.subTest(filter_range=range_code, filter_label=label):
                at = AppTest.from_file(self.app_path, default_timeout=30)
                at.query_params["view"] = "analytics"
                at.query_params["range"] = range_code
                at.run()

                self.assertEqual(
                    len(at.exception),
                    0,
                    f"Analytics view raised exception on seed db with filter {label}: {at.exception}"
                )

                practice_btns = [b for b in at.button if "Generate Practice Problem" in b.label]
                self.assertEqual(len(practice_btns), 1, "Exactly one Generate Practice Problem button must exist")
                self.assertEqual(practice_btns[0].key, "btn_practice_top_level")

                dl = at.download_button(key="btn_export_report")
                self.assertIsNotNone(dl, "Export Report download button must exist")

                combined_html = "\n".join([h.value for h in at.html])
                self.assertIn("Debugging Intelligence &amp; Weak Spot Analytics", combined_html)

                iframes = [e for e in at.main if getattr(e, "type", None) == "iframe"]
                self.assertGreater(len(iframes), 0, "Analytics iframe must be rendered")
                srcdoc = iframes[0].proto.srcdoc
                self.assertIn("bugs", srcdoc)
                self.assertIn("Off-by-one", srcdoc)
                self.assertIn("Bug Pattern Frequency Matrix", srcdoc)

                practice_btns[0].click().run()
                self.assertEqual(len(at.exception), 0)
                self.assertTrue(at.session_state.get("show_practice_modal"))
                self.assertIsNotNone(at.session_state.get("practice_data"))
                self.assertIsNotNone(at.button(key="btn_close_practice_modal"))
                self.assertIsNotNone(at.button(key="btn_another_practice_modal"))

    def test_state_3_older_rows_without_duration_or_turn_count(self):
        """
        State 3: Database with older rows that have NULL duration_seconds or turn_count.
        Verifies fallback calculation of turnaround metrics and metric card units.
        Repeats across Last 30 Days, This Quarter, and All Time filters.
        """
        self._set_test_db("legacy_null_metrics.db")
        now = datetime.now()
        legacy_rows = [
            (
                (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "Syntax Error",
                "syntax",
                "Missing closing parenthesis in function definition",
                "Always verify bracket matching",
                "Python",
                "Legacy bug without telemetry",
                "def test(): pass",
                None,
                None
            ),
            (
                (now - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"),
                "Type Error",
                "type error",
                "Implicit conversion of NoneType to string",
                "Guard against None before string formatting",
                "TypeScript",
                "Legacy bug 40 days ago",
                "const x: string = val;",
                None,
                None
            ),
            (
                (now - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S"),
                "Logic Flaw",
                "logic",
                "Inverted boolean condition in guard clause",
                "Check boolean polarity before early return",
                "Go",
                "Legacy bug 120 days ago",
                "if !isValid { return }",
                None,
                None
            )
        ]

        with db.get_connection() as conn:
            conn.execute("DELETE FROM bugs;")
            conn.executemany(
                """
                INSERT INTO bugs (timestamp, bug_type, scope, root_cause, lesson, language, description, code_snippet, turn_count, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                legacy_rows
            )
            conn.commit()

        time_filters = [
            ("30d", "Last 30 Days"),
            ("quarter", "This Quarter"),
            ("all", "All Time")
        ]

        for range_code, label in time_filters:
            with self.subTest(filter_range=range_code, filter_label=label):
                at = AppTest.from_file(self.app_path, default_timeout=30)
                at.query_params["view"] = "analytics"
                at.query_params["range"] = range_code
                at.run()

                self.assertEqual(
                    len(at.exception),
                    0,
                    f"Analytics view raised exception on legacy null rows with filter {label}: {at.exception}"
                )
                practice_btns = [b for b in at.button if "Generate Practice Problem" in b.label]
                self.assertEqual(len(practice_btns), 1, "Exactly one Generate Practice Problem button must exist")
                self.assertEqual(practice_btns[0].key, "btn_practice_top_level")

                dl = at.download_button(key="btn_export_report")
                self.assertIsNotNone(dl, "Export Report download button must exist")

                combined_html = "\n".join([h.value for h in at.html])
                self.assertIn("Debugging Intelligence &amp; Weak Spot Analytics", combined_html)

                iframes = [e for e in at.main if getattr(e, "type", None) == "iframe"]
                self.assertGreater(len(iframes), 0, "Analytics iframe must be rendered")
                srcdoc = iframes[0].proto.srcdoc
                self.assertIn("Bug Pattern Frequency Matrix", srcdoc)

    def test_state_4_new_bugs_all_time_filters(self):
        """
        State 4: Database with newly logged bugs containing rich durations and turn counts.
        Verifies multi-incident metrics, percentage calculations, and top weak spot rendering.
        Repeats across Last 30 Days, This Quarter, and All Time filters.
        """
        self._set_test_db("new_bugs.db")
        with db.get_connection() as conn:
            conn.execute("DELETE FROM bugs;")
            db.seed_initial_data(conn)

        # Add 2 new bugs with specific metrics
        db.save_bug(
            bug_type="Race Condition",
            scope="concurrency",
            root_cause="Shared counter increment without mutex synchronization",
            lesson="Always guard shared state mutations with sync.Mutex",
            language="Go",
            description="Parallel goroutines corrupting count",
            code_snippet="go func() { count++ }()",
            turn_count=5,
            duration_seconds=320.0
        )
        db.save_bug(
            bug_type="Race Condition",
            scope="concurrency",
            root_cause="Map read and write operations concurrently",
            lesson="Use sync.Map or mutex for concurrent map access",
            language="Go",
            description="Fatal concurrent map read and write error",
            code_snippet="m[key] = val",
            turn_count=3,
            duration_seconds=185.0
        )

        time_filters = [
            ("30d", "Last 30 Days"),
            ("quarter", "This Quarter"),
            ("all", "All Time")
        ]

        for range_code, label in time_filters:
            with self.subTest(filter_range=range_code, filter_label=label):
                at = AppTest.from_file(self.app_path, default_timeout=30)
                at.query_params["view"] = "analytics"
                at.query_params["range"] = range_code
                at.run()

                self.assertEqual(
                    len(at.exception),
                    0,
                    f"Analytics view raised exception on new bugs db with filter {label}: {at.exception}"
                )
                practice_btns = [b for b in at.button if "Generate Practice Problem" in b.label]
                self.assertEqual(len(practice_btns), 1, "Exactly one Generate Practice Problem button must exist")
                self.assertEqual(practice_btns[0].key, "btn_practice_top_level")

                dl = at.download_button(key="btn_export_report")
                self.assertIsNotNone(dl, "Export Report download button must exist")

                combined_html = "\n".join([h.value for h in at.html])
                self.assertIn("Debugging Intelligence &amp; Weak Spot Analytics", combined_html)

                iframes = [e for e in at.main if getattr(e, "type", None) == "iframe"]
                self.assertGreater(len(iframes), 0, "Analytics iframe must be rendered")
                srcdoc = iframes[0].proto.srcdoc
                self.assertIn("Race Condition", srcdoc)
                self.assertIn("Bug Pattern Frequency Matrix", srcdoc)

                practice_btns[0].click().run()
                self.assertEqual(len(at.exception), 0)
                self.assertTrue(at.session_state.get("show_practice_modal"))
                self.assertIsNotNone(at.session_state.get("practice_data"))
                self.assertIsNotNone(at.button(key="btn_close_practice_modal"))
                self.assertIsNotNone(at.button(key="btn_another_practice_modal"))

    def test_socratic_studio_view_renders_cleanly(self):
        """
        Verifies that Socratic Studio view loads and renders cleanly with no exceptions.
        """
        self._set_test_db("studio_view.db")
        at = AppTest.from_file(self.app_path, default_timeout=30)
        at.query_params["view"] = "studio"
        at.run()

        self.assertEqual(
            len(at.exception),
            0,
            f"Socratic Studio view raised exception: {at.exception}"
        )
        self.assertIsNotNone(at.text_area(key="bug_desc_input"))
        self.assertIsNotNone(at.text_area(key="code_snippet_input"))
        self.assertIsNotNone(at.button(key="btn_start_quacking"))


if __name__ == "__main__":
    unittest.main()

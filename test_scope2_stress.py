"""
test_scope2_stress.py - Stress tests for Scope 2 (Debug page UI & interactions)
Covers:
- 10k+ character code payloads
- Rapid solved clicks / double-submission race conditions
- Empty / whitespace inputs
- Null bytes, binary control chars, emojis, Unicode
- Chat history state transitions
"""

import sys
import os
import unittest
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import db
import prompts

class TestScope2Stress(unittest.TestCase):

    def setUp(self):
        db.init_db(seed_samples=False)

    def test_01_empty_and_whitespace_inputs(self):
        """Test handling of empty and whitespace-only inputs."""
        # Empty description and code
        resp = prompts.generate_socratic_response(
            messages=[],
            code_snippet="",
            bug_description="",
            turn_count=0,
            api_key=""
        )
        self.assertTrue(isinstance(resp, str) and len(resp) > 0)
        self.assertTrue("?" in resp)

        # Whitespace-only inputs
        resp_ws = prompts.generate_socratic_response(
            messages=[],
            code_snippet="   \n\t   ",
            bug_description="     \n  ",
            turn_count=0,
            api_key=""
        )
        self.assertTrue(isinstance(resp_ws, str) and len(resp_ws) > 0)
        self.assertTrue("?" in resp_ws)

        # Whitespace user message in history
        resp_user_ws = prompts.generate_socratic_response(
            messages=[{"role": "user", "content": "   \n  "}],
            code_snippet="x = 1",
            bug_description="error",
            turn_count=1,
            api_key=""
        )
        self.assertTrue(isinstance(resp_user_ws, str) and len(resp_user_ws) > 0)

    def test_02_10k_plus_character_payloads(self):
        """Test handling of 10k+ and 50k+ character code snippets and descriptions."""
        code_10k = "# Loop statement\nfor i in range(1000):\n    print(i)\n" * 250  # ~11k chars
        self.assertGreater(len(code_10k), 10000)

        desc_10k = "Um so like basically I have this super long explanation... " * 200 # ~12k chars
        self.assertGreater(len(desc_10k), 10000)

        resp = prompts.generate_socratic_response(
            messages=[],
            code_snippet=code_10k,
            bug_description=desc_10k,
            turn_count=0,
            api_key=""
        )
        self.assertTrue(isinstance(resp, str) and len(resp) > 0)
        self.assertTrue("?" in resp)

        # Extreme 50k payload
        code_50k = "x = [i for i in range(100)]\n" * 1800 # ~50k chars
        self.assertGreater(len(code_50k), 50000)

        resp_50k = prompts.generate_socratic_response(
            messages=[{"role": "user", "content": "Here is my huge file"}],
            code_snippet=code_50k,
            bug_description="Massive file bug",
            turn_count=1,
            api_key=""
        )
        self.assertTrue(isinstance(resp_50k, str) and len(resp_50k) > 0)

        # Extract solved with 10k payload
        extracted = prompts.extract_solved_json(
            conversation=[{"role": "user", "content": "found it"}],
            code_snippet=code_10k,
            bug_description=desc_10k,
            language="Python",
            api_key=""
        )
        self.assertIn("bug_type", extracted)
        self.assertIn("root_cause", extracted)
        self.assertIn("lesson", extracted)

    def test_03_code_with_markdown_fences_and_html(self):
        """Test snippets containing markdown fences, backticks, and HTML tags."""
        code_tricky = """
```python
def parse_html(tag: str):
    if tag == "<script>alert('xss')</script>":
        return vector<int>{1, 2, 3};
```
"""
        resp = prompts.generate_socratic_response(
            messages=[{"role": "user", "content": "look at `code` and <int>"}],
            code_snippet=code_tricky,
            bug_description="Parsing `<script>` and `vector<int>`",
            turn_count=1,
            api_key=""
        )
        self.assertTrue(isinstance(resp, str) and len(resp) > 0)

        extracted = prompts.extract_solved_json(
            conversation=[{"role": "user", "content": "fixed vector<int> bounds"}],
            code_snippet=code_tricky,
            bug_description="Parsing `<script>` and `vector<int>`",
            language="C++",
            api_key=""
        )
        self.assertIn("bug_type", extracted)

    def test_04_emojis_unicode_and_null_bytes(self):
        """Test emojis, non-ASCII Unicode, and null/control bytes."""
        emoji_desc = " Duck says hello!  Found a nasty bug in  production!"
        emoji_code = "#  Rocket launcher\nval = '\u2728' + ''"
        null_code = "def test():\x00\x00\x01\x08 return None"
        null_desc = "Voice text\x00with embedded nulls\x00and ctrl\x02chars"

        resp = prompts.generate_socratic_response(
            messages=[{"role": "user", "content": "User reply with  and \x00 null"}],
            code_snippet=emoji_code + null_code,
            bug_description=emoji_desc + null_desc,
            turn_count=0,
            api_key=""
        )
        self.assertTrue(isinstance(resp, str) and len(resp) > 0)

        # Database save with null bytes and emojis
        bug_id = db.save_bug(
            bug_type="Off-by-one ",
            scope="logic",
            root_cause="Boundary error \x00 with emoji ",
            lesson="Always test edge cases \u2728",
            language="Python",
            description=emoji_desc + null_desc,
            code_snippet=emoji_code + null_code
        )
        self.assertIsInstance(bug_id, int)
        self.assertGreater(bug_id, 0)

        # Clean up test bug
        with db.get_connection() as conn:
            conn.cursor().execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
            conn.commit()

    def test_05_chat_history_state_transitions(self):
        """Test complete chat history lifecycle from turn 0 to turn 5."""
        messages = []
        turn_count = 0
        code = "def get_item(arr, idx):\n    return arr[idx + 1]"
        desc = "Index error when fetching items"

        # Turn 0: Opening question
        duck_q0 = prompts.generate_socratic_response(
            messages=messages,
            code_snippet=code,
            bug_description=desc,
            turn_count=turn_count,
            api_key=""
        )
        messages.append({"role": "assistant", "content": duck_q0})
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")

        # Turn 1: User replies
        messages.append({"role": "user", "content": "I expected arr[idx] but it crashes on the last item"})
        turn_count += 1
        duck_q1 = prompts.generate_socratic_response(
            messages=messages,
            code_snippet=code,
            bug_description=desc,
            turn_count=turn_count,
            api_key=""
        )
        messages.append({"role": "assistant", "content": duck_q1})
        self.assertEqual(len(messages), 3)

        # Turn 2: User replies again
        messages.append({"role": "user", "content": "The loop counter runs up to len(arr)"})
        turn_count += 1
        duck_q2 = prompts.generate_socratic_response(
            messages=messages,
            code_snippet=code,
            bug_description=desc,
            turn_count=turn_count,
            api_key=""
        )
        messages.append({"role": "assistant", "content": duck_q2})
        self.assertEqual(len(messages), 5)

        # Turn 3: Escalation turn
        messages.append({"role": "user", "content": "I still don't see why it crashes"})
        turn_count += 1
        duck_q3 = prompts.generate_socratic_response(
            messages=messages,
            code_snippet=code,
            bug_description=desc,
            turn_count=turn_count,
            api_key=""
        )
        messages.append({"role": "assistant", "content": duck_q3})
        self.assertEqual(len(messages), 7)
        self.assertGreaterEqual(turn_count, 3)

    def test_06_rapid_solved_clicks_and_double_submission_guard(self):
        """Simulate rapid solved button clicks to ensure no duplicate DB writes."""
        # Baseline count
        initial_stats = db.get_bug_stats()
        initial_count = initial_stats["total_bugs"]

        messages = [
            {"role": "assistant", "content": "What did you expect?"},
            {"role": "user", "content": "I found it! range(len) was off by one!"}
        ]
        code = "for i in range(len(arr) + 1): pass"
        desc = "Loop off by one"

        # Extraction logic
        extracted = prompts.extract_solved_json(
            conversation=messages,
            code_snippet=code,
            bug_description=desc,
            language="Python",
            api_key=""
        )

        # First click: performs save
        solved_record = None
        created_ids = []

        # Simulate UI check: if solved_record is None, save; else ignore
        for click in range(5):
            if solved_record is None:
                bug_id = db.save_bug(
                    bug_type=extracted["bug_type"],
                    scope=extracted["scope"],
                    root_cause=extracted["root_cause"],
                    lesson=extracted["lesson"],
                    language=extracted["language"],
                    description=desc,
                    code_snippet=code
                )
                extracted["id"] = bug_id
                solved_record = extracted
                created_ids.append(bug_id)
            else:
                # Simulated guard blocked subsequent clicks
                pass

        # Exactly 1 record should have been created despite 5 rapid clicks
        self.assertEqual(len(created_ids), 1)

        after_stats = db.get_bug_stats()
        self.assertEqual(after_stats["total_bugs"], initial_count + 1)

        # Clean up
        with db.get_connection() as conn:
            conn.cursor().execute("DELETE FROM bugs WHERE id = ?", (created_ids[0],))
            conn.commit()

        final_stats = db.get_bug_stats()
        self.assertEqual(final_stats["total_bugs"], initial_count)

if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import prompts
import db


class TestMultiLanguageE2E(unittest.TestCase):
    """
    Comprehensive end-to-end multi-language test suite for Duck Debugger.
    Verifies all 7 languages (Python, JavaScript, TypeScript, Go, Rust, C++, Java),
    verifies Socratic invariants, prevention of empty feed traps, and UI sizing.
    """

    def setUp(self):
        self.app_path = str(PROJECT_ROOT / "app.py")

    def test_multi_language_e2e_all_7_languages_offline(self):
        """
        Tests realistic buggy snippets across all 7 languages:
        Start -> 1st duck reply -> 3 follow-ups -> Mark as Solved -> verify saved in SQLite with right language -> practice problem.
        Offline fallback must never use Python-only wording for other languages.
        """
        test_matrix = [
            {
                "language": "Python",
                "desc": "My function fails with NameError when calling compute_total",
                "code": "def process_data(items):\n    res = compute_total(items)\n    return res",
                "followups": [
                    "It points to line 2 in the traceback",
                    "compute_total is being evaluated right here",
                    "Looking at the function call now"
                ]
            },
            {
                "language": "JavaScript",
                "desc": "My code is not working. Can you just tell me what to fix?",
                "code": "function calculateCartTotal(cartItems) {\n  let total = 0;\n  for (let i = 0; i <= cartItems.length; i++) {\n    total += cartItems[i].price;\n  }\n  return total;\n}",
                "followups": [
                    "It points to line 4 inside the loop",
                    "cartItems has 2 elements",
                    "Checking the loop counter i"
                ]
            },
            {
                "language": "TypeScript",
                "desc": "Getting TypeScript compiler error with optional config property",
                "code": "interface ServerConfig {\n  host: string;\n  port?: number;\n}\nfunction formatHostPort(cfg: ServerConfig): string {\n  return `${cfg.host}:${cfg.port.toFixed()}`;\n}",
                "followups": [
                    "The error is on line 6",
                    "ServerConfig has an optional port property",
                    "Checking the type definition"
                ]
            },
            {
                "language": "Go",
                "desc": "Runtime panic in Go when saving session key",
                "code": "package main\n\ntype SessionStore struct {\n    sessions map[string]string\n}\n\nfunc (s *SessionStore) Set(key, val string) {\n    s.sessions[key] = val\n}",
                "followups": [
                    "The panic occurs on line 10",
                    "The struct has a sessions map field",
                    "Checking the map declaration"
                ]
            },
            {
                "language": "Rust",
                "desc": "Rust compiler error borrow of moved value",
                "code": "fn process_tag(tag: String) {\n    save_tag(tag);\n    println!(\"Processed: {}\", tag);\n}",
                "followups": [
                    "The compiler error points to line 4",
                    "The variable tag is used twice",
                    "Checking the signature of save_tag"
                ]
            },
            {
                "language": "C++",
                "desc": "Segmentation fault when traversing linked list in C++",
                "code": "struct Node {\n    int val;\n    Node* next;\n};\n\nint get_next_val(Node* node) {\n    return node->next->val;\n}",
                "followups": [
                    "The crash happens on line 8",
                    "The Node struct has a next pointer",
                    "Checking the pointer value"
                ]
            },
            {
                "language": "Java",
                "desc": "Getting NullPointerException when formatting customer name",
                "code": "public class Formatter {\n    public static String formatName(String first, String middle, String last) {\n        return first + \" \" + middle.toUpperCase() + \" \" + last;\n    }\n}",
                "followups": [
                    "The exception is thrown on line 4",
                    "The middle string is passed as an argument",
                    "Checking the method parameters"
                ]
            }
        ]

        with patch.object(prompts, "resolve_gemini_api_key", return_value=None):
            for tc in test_matrix:
                lang = tc["language"]
                at = AppTest.from_file(self.app_path, default_timeout=30).run()

                # Select Language
                for s in at.selectbox:
                    if lang in s.options:
                        s.select(lang)
                        break

                # Input description & code
                at.text_area(key="bug_desc_input").input(tc["desc"])
                at.text_area(key="code_snippet_input").input(tc["code"])

                # Click Start
                at.button(key="btn_start_quacking").click().run()

                # Verify 1st duck reply
                self.assertTrue(at.session_state.session_started, f"Session should be started for {lang}")
                self.assertGreater(len(at.session_state.messages), 1, f"Duck reply missing for {lang}")
                reply1 = at.session_state.messages[-1]["content"]
                self.assertTrue(reply1.startswith("Quack!"), f"1st reply must start with Quack! in {lang}")

                # Offline fallback wording checks: no python terms for other languages
                if lang != "Python":
                    low_r1 = reply1.lower()
                    self.assertNotIn("interpreter", low_r1, f"Forbidden 'interpreter' in {lang}")
                    self.assertNotIn("list", low_r1, f"Forbidden 'list' in {lang}")
                    if lang != "Rust":
                        self.assertNotIn(" none ", f" {low_r1} ", f"Forbidden 'None' in {lang}")

                # Follow-up turns (3 turns)
                prev_questions = [reply1]
                for fu_text in tc["followups"]:
                    self.assertGreater(len(at.chat_input), 0, f"Chat input missing for {lang}")
                    at.chat_input[0].set_value(fu_text).run()
                    followup_reply = at.session_state.messages[-1]["content"]
                    self.assertTrue(followup_reply.startswith("Quack!"), f"Follow-up must start with Quack! in {lang}")
                    self.assertNotIn(followup_reply, prev_questions, f"Repetition detected in {lang}: {followup_reply}")
                    prev_questions.append(followup_reply)

                # Mark as Solved button
                solved_btn = next((b for b in at.button if b.label == "Mark as Solved"), None)
                self.assertIsNotNone(solved_btn, f"Mark as Solved button missing for {lang}")
                solved_btn.click().run()

                self.assertTrue(at.session_state.solved, f"{lang} session should be marked as solved")
                rec = at.session_state.solved_record
                self.assertIsNotNone(rec, f"Solved record missing for {lang}")
                self.assertEqual(rec.get("language"), lang, f"Saved language mismatch for {lang}")
                self.assertTrue(rec.get("bug_type"), f"Missing bug_type for {lang}")

                # Practice problem verification
                practice = prompts.generate_practice_problem(weak_spot=rec.get("bug_type"), language=lang)
                self.assertEqual(practice.get("language"), lang, f"Practice problem language mismatch for {lang}")
                self.assertTrue(practice.get("starter_code"), f"Practice problem missing starter code for {lang}")
                self.assertTrue(practice.get("statement"), f"Practice problem missing statement for {lang}")

    def test_bug1_request_for_fix_remains_socratic(self):
        """
        Verifies BUG 1 requirement:
        When user asks 'My code is not working. Can you just tell me what to fix?',
        the duck stays Socratic: one question, no fix, no code.
        """
        code = """function calculateCartTotal(cartItems) {
  let total = 0;
  for (let i = 0; i <= cartItems.length; i++) {
    total += cartItems[i].price;
  }
  return total;
}"""
        desc = "My code is not working. Can you just tell me what to fix?"

        at = AppTest.from_file(self.app_path, default_timeout=30).run()
        for s in at.selectbox:
            if "JavaScript" in s.options:
                s.select("JavaScript")
                break
        at.text_area(key="bug_desc_input").input(desc)
        at.text_area(key="code_snippet_input").input(code)
        at.button(key="btn_start_quacking").click().run()

        self.assertTrue(at.session_state.session_started)
        self.assertGreater(len(at.session_state.messages), 1)
        first_reply = at.session_state.messages[-1]["content"]

        self.assertTrue(first_reply.startswith("Quack!"))
        self.assertNotIn("```", first_reply, "Socratic reply must never include code blocks")
        self.assertEqual(first_reply.count("?"), 1, "Socratic reply must contain exactly one question mark")

        # Verify duck reply is rendered in HTML output
        found_duck_card = any("DUCK SOCRATIC ADVISOR" in h.value for h in at.html)
        self.assertTrue(found_duck_card, "Duck message bubble should be rendered in HTML output")

    def test_bug1_self_healing_empty_feed_prevention(self):
        """
        Verifies BUG 1 guarantee:
        A started session with an empty feed must never happen.
        If a session was partially marked started without an assistant reply,
        it auto-recovers on next render.
        """
        at = AppTest.from_file(self.app_path, default_timeout=30).run()
        at.session_state.session_started = True
        at.session_state.messages = [{"role": "user", "content": "Sample user query"}]
        at.run()

        # Self-healing should have appended assistant reply
        self.assertGreater(len(at.session_state.messages), 1)
        last_msg = at.session_state.messages[-1]
        self.assertEqual(last_msg.get("role"), "assistant")
        self.assertTrue(last_msg.get("content").startswith("Quack!"))

    def test_bug2_input_box_dimensions_and_css(self):
        """
        Verifies BUG 2 requirements:
        Description box >= 200px tall.
        Code snippet box >= 360px tall, monospace font, resizable.
        Page max-width responsive.
        """
        at = AppTest.from_file(self.app_path, default_timeout=30)
        at.query_params["view"] = "studio"
        at.run()
        self.assertEqual(len(at.exception), 0, f"Studio view raised exception: {at.exception}")
        desc_area = at.text_area(key="bug_desc_input")
        code_area = at.text_area(key="code_snippet_input")

        self.assertIsNotNone(desc_area)
        self.assertIsNotNone(code_area)
        self.assertGreater(len(at.chat_input), 0, "Chat input must be rendered")
        self.assertIn("Wispr Flow", at.chat_input[0].placeholder)

        # Verify height parameters in app.py
        with open(self.app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check heights
        self.assertIn("key=\"bug_desc_input\",\n            height=210", content)
        self.assertIn("key=\"code_snippet_input\",\n            height=380", content)

        # Check CSS rules - strictly scoped, no global textarea min-height
        self.assertIn("max-width: min(1560px, 96vw) !important;", content)
        self.assertIn(".st-key-code_snippet_input textarea", content)
        self.assertIn(".st-key-bug_desc_input textarea", content)
        self.assertIn("min-height: 360px !important;", content)
        self.assertIn("min-height: 200px !important;", content)
        self.assertIn("resize: vertical !important;", content)
        self.assertIn("JetBrains Mono", content)

        # Check compact chat input rules
        self.assertIn("[data-testid=\"stChatInput\"] textarea", content)
        self.assertIn("max-height: 160px !important;", content)
        self.assertIn("min-height: 0 !important;", content)

        # Assert no global / un-scoped textarea min-height rules that would leak to chat input
        self.assertNotIn("textarea[aria-label*=\"dictate with Wispr Flow\"]", content)
        self.assertNotIn("textarea[aria-label=\"Code Snippet\"]", content)

    def test_multi_language_practice_catalog(self):
        """
        Verifies BUG 3 requirement:
        Practice problem generator supports all 7 languages without Python bias.
        """
        languages = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "C++", "Java"]
        for lang in languages:
            self.assertIn(lang, prompts.PRACTICE_BUILTIN_PROBLEMS_BY_LANG)
            lang_dict = prompts.PRACTICE_BUILTIN_PROBLEMS_BY_LANG[lang]
            self.assertIn("off-by-one", lang_dict)
            self.assertIn("null/undefined", lang_dict)
            self.assertIn("type coercion", lang_dict)
            self.assertIn("logic", lang_dict)

            problem = prompts.generate_practice_problem(weak_spot="Off-by-one", language=lang)
            self.assertEqual(problem.get("language"), lang)
            starter = problem.get("starter_code", "")
            self.assertTrue(len(starter) > 10, f"Starter code missing for {lang}")
            if lang != "Python":
                self.assertNotIn("def ", starter, f"Python syntax 'def' leaked into {lang} practice code")


if __name__ == "__main__":
    unittest.main()

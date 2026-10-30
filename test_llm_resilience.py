"""
test_llm_resilience.py - Stress tests for Gemini LLM client resilience in prompts.py.
Tests network timeouts, HTTP 429 rate limits, 503 temporary errors, invalid API keys,
safety filter blocks, empty responses, and malformed SDK responses.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure target directory is in python path
from pathlib import Path
WORKSPACE_DIR = str(Path(__file__).resolve().parent)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import prompts
from google.genai import errors, types


class TestLLMClientResilience(unittest.TestCase):

    def setUp(self):
        # Speed up retry delays during tests
        if hasattr(prompts, "INITIAL_RETRY_DELAY"):
            self.orig_delay = prompts.INITIAL_RETRY_DELAY
            prompts.INITIAL_RETRY_DELAY = 0.01

    def tearDown(self):
        if hasattr(prompts, "INITIAL_RETRY_DELAY"):
            prompts.INITIAL_RETRY_DELAY = self.orig_delay

    # 1. Missing and Placeholder API Keys
    def test_missing_or_placeholder_api_key(self):
        """Verify missing, empty, or placeholder API keys return None client and trigger offline fallback."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GEMINI_KEY": ""}), \
             patch.object(prompts, "resolve_gemini_api_key", return_value=None):
            for bad_key in [None, "", "   ", "your_api_key_here", "YOUR_GEMINI_API_KEY", "TODO", "None", "null"]:
                client = prompts.get_gemini_client(api_key=bad_key)
                self.assertIsNone(client, f"Client should be None for bad key: {bad_key!r}")

                # Socratic response should work offline
                res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key=bad_key)
                self.assertIsInstance(res, str)
                self.assertTrue(len(res) > 0)
                self.assertIn("?", res)

                # JSON extraction should work offline
                data = prompts.extract_solved_json([], "x = 1", "off by one index bug", "Python", api_key=bad_key)
                self.assertIsInstance(data, dict)
                self.assertIn("bug_type", data)
                self.assertIn("root_cause", data)

                # Practice problem should work offline
                puzzle = prompts.generate_practice_problem("Off-by-one", "Python", api_key=bad_key)
                self.assertIsInstance(puzzle, str)
                self.assertIn("Rubber Duck", puzzle)

    # 2. Invalid API Key (Fast Fail, No Useless Retries)
    def test_invalid_api_key_fast_fail(self):
        """Simulate 400/403 API_KEY_INVALID error. Should fail fast and fall back gracefully."""
        mock_client = MagicMock()
        mock_err = errors.ClientError(400, {"error": {"message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}})
        mock_client.models.generate_content.side_effect = mock_err

        with patch("prompts.get_gemini_client", return_value=mock_client):
            # Socratic response
            res = prompts.generate_socratic_response([], "def foo(): pass", "crashes", 0, api_key="bad_key")
            self.assertIsInstance(res, str)
            self.assertIn("?", res)

            # Practice problem
            puzzle = prompts.generate_practice_problem("Recursion", "Python", api_key="bad_key")
            self.assertIsInstance(puzzle, str)
            self.assertTrue(len(puzzle) > 0)

            # JSON extraction
            extracted = prompts.extract_solved_json([], "def foo(): pass", "null pointer", "Python", api_key="bad_key")
            self.assertIsInstance(extracted, dict)
            self.assertEqual(extracted["bug_type"], "Null/Undefined Reference")

    # 3. HTTP 429 Rate Limiting with Exponential Backoff
    def test_rate_limit_429_retry_success(self):
        """Simulate HTTP 429 on first 2 calls, succeeding on 3rd attempt."""
        mock_client = MagicMock()
        err_429 = errors.ClientError(429, {"error": {"message": "Resource exhausted: quota exceeded", "status": "RESOURCE_EXHAUSTED"}})
        
        mock_success_response = MagicMock()
        mock_success_response.text = "Quack! Did you check the index bounds?"
        mock_success_response.candidates = [MagicMock(finish_reason="STOP")]

        mock_client.models.generate_content.side_effect = [err_429, err_429, mock_success_response]

        with patch("prompts.get_gemini_client", return_value=mock_client):
            res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key="valid_key")
            self.assertEqual(res, "Quack! Did you check the index bounds?")

    def test_rate_limit_429_exhaustion_fallback(self):
        """Simulate continuous HTTP 429. Exhausts retries and falls back cleanly without crashing."""
        mock_client = MagicMock()
        err_429 = errors.ClientError(429, {"error": {"message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}})
        mock_client.models.generate_content.side_effect = err_429

        with patch("prompts.get_gemini_client", return_value=mock_client):
            res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key="valid_key")
            self.assertIsInstance(res, str)
            self.assertTrue(len(res) > 0)
            self.assertIn("?", res)

    # 4. HTTP 503 / 500 Temporary Server Errors
    def test_server_error_503_retry_and_fallback(self):
        """Simulate HTTP 503 Unavailable. Should retry and fall back cleanly if exhausted."""
        mock_client = MagicMock()
        err_503 = errors.ServerError(503, {"error": {"message": "The service is temporarily unavailable", "status": "UNAVAILABLE"}})
        mock_client.models.generate_content.side_effect = err_503

        with patch("prompts.get_gemini_client", return_value=mock_client):
            res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key="valid_key")
            self.assertIsInstance(res, str)
            self.assertIn("?", res)

            extracted = prompts.extract_solved_json([], "x = 1", "bound error", "Python", api_key="valid_key")
            self.assertIsInstance(extracted, dict)
            self.assertEqual(extracted["bug_type"], "Off-by-one")

    # 5. Network Timeouts
    def test_network_timeout_handling(self):
        """Simulate network timeout exception. Should catch and fall back safely."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = TimeoutError("Request timed out after 25.0 seconds")

        with patch("prompts.get_gemini_client", return_value=mock_client):
            res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key="valid_key")
            self.assertIsInstance(res, str)
            self.assertIn("?", res)

            puzzle = prompts.generate_practice_problem("Off-by-one", "Python", api_key="valid_key")
            self.assertIsInstance(puzzle, str)
            self.assertIn("Rubber Duck", puzzle)

    # 6. Safety Filter Blockades (finish_reason = SAFETY, response.text throws or returns None)
    def test_safety_filter_blocked_response(self):
        """Simulate response blocked by safety filters."""
        mock_client = MagicMock()
        
        # Candidate with finish_reason = SAFETY
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = "SAFETY"
        mock_candidate.content = None

        mock_blocked_response = MagicMock()
        mock_blocked_response.candidates = [mock_candidate]
        mock_blocked_response.text = None  # in real SDK, .text is None or throws ValueError

        mock_client.models.generate_content.return_value = mock_blocked_response

        with patch("prompts.get_gemini_client", return_value=mock_client):
            res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key="valid_key")
            self.assertIsInstance(res, str)
            self.assertIn("?", res)

            extracted = prompts.extract_solved_json([], "x = 1", "index error", "Python", api_key="valid_key")
            self.assertIsInstance(extracted, dict)
            self.assertIn("bug_type", extracted)

            puzzle = prompts.generate_practice_problem("Logic Error", "Python", api_key="valid_key")
            self.assertIsInstance(puzzle, str)
            self.assertTrue(len(puzzle) > 0)

    # 7. Empty or Malformed SDK Responses
    def test_empty_candidates_and_text_none(self):
        """Simulate response with empty candidates list."""
        mock_client = MagicMock()
        mock_empty_resp = MagicMock()
        mock_empty_resp.candidates = []
        mock_empty_resp.text = None

        mock_client.models.generate_content.return_value = mock_empty_resp

        with patch("prompts.get_gemini_client", return_value=mock_client):
            res = prompts.generate_socratic_response([], "x = 1", "test bug", 0, api_key="valid_key")
            self.assertIsInstance(res, str)
            self.assertIn("?", res)

    # 8. Markdown-wrapped JSON and Messy Extraction
    def test_markdown_code_fenced_json_extraction(self):
        """Simulate LLM wrapping JSON output in markdown ```json ``` blocks."""
        mock_client = MagicMock()
        fenced_json = """```json
{
  "bug_type": "Race Condition",
  "scope": "state",
  "root_cause": "Shared variable accessed without mutex lock.",
  "lesson": "Always synchronize concurrent state access.",
  "language": "Go"
}
```"""
        mock_resp = MagicMock()
        mock_resp.text = fenced_json
        mock_resp.candidates = [MagicMock(finish_reason="STOP")]
        mock_client.models.generate_content.return_value = mock_resp

        with patch("prompts.get_gemini_client", return_value=mock_client):
            extracted = prompts.extract_solved_json([], "go func()", "race condition bug", "Go", api_key="valid_key")
            self.assertEqual(extracted["bug_type"], "Race Condition")
            self.assertEqual(extracted["scope"], "state")
            self.assertEqual(extracted["language"], "Go")


if __name__ == "__main__":
    unittest.main()

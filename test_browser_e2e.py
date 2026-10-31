import asyncio
import base64
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
import urllib.request
import websockets

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:8501/?view=studio"

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class ChromeCDPBrowser:
    def __init__(self):
        self.port = get_free_port()
        self.user_dir = tempfile.mkdtemp(prefix="duck_chrome_")
        self.proc = None
        self.ws = None
        self.msg_id = 0
        self.pending = {}
        self.console_logs = []

    async def start(self):
        cmd = [
            CHROME_EXE,
            "--headless=new",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--window-size=1280,1024",
            "about:blank"
        ]
        self.proc = subprocess.Popen(cmd)
        ws_url = None
        for _ in range(20):
            await asyncio.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2) as r:
                    tabs = json.loads(r.read().decode())
                if tabs:
                    pages = [t for t in tabs if t.get("type") == "page"]
                    target = pages[0] if pages else tabs[0]
                    ws_url = target.get("webSocketDebuggerUrl")
                    if ws_url:
                        break
            except Exception:
                pass

        if not ws_url:
            raise RuntimeError(f"Unable to connect to Chrome CDP on port {self.port}")

        self.ws = await websockets.connect(ws_url, max_size=50 * 1024 * 1024)
        asyncio.create_task(self._listen())
        await self.send("Console.enable")
        await self.send("Runtime.enable")
        await self.send("Page.enable")

    async def _listen(self):
        try:
            async for raw in self.ws:
                data = json.loads(raw)
                if "id" in data and data["id"] in self.pending:
                    fut = self.pending.pop(data["id"])
                    if not fut.done():
                        fut.set_result(data.get("result"))
                elif data.get("method") == "Runtime.consoleAPICalled":
                    args = [a.get("value", a.get("description", "")) for a in data.get("params", {}).get("args", [])]
                    self.console_logs.append(" ".join(str(x) for x in args))
        except Exception:
            pass

    async def send(self, method, params=None):
        self.msg_id += 1
        curr_id = self.msg_id
        fut = asyncio.get_event_loop().create_future()
        self.pending[curr_id] = fut
        payload = {"id": curr_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        return await fut

    async def evaluate(self, expr):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        if res and "result" in res:
            return res["result"].get("value")
        return None

    async def navigate(self, url):
        await self.send("Page.navigate", {"url": url})

    async def type_into_element(self, selector, text):
        await self.evaluate(f"document.querySelector('{selector}').focus()")
        await asyncio.sleep(0.1)
        await self.evaluate(f"document.querySelector('{selector}').select()")
        await asyncio.sleep(0.1)
        await self.send("Input.insertText", {"text": text})
        await asyncio.sleep(0.2)
        await self.evaluate(f"document.querySelector('{selector}').blur()")
        await asyncio.sleep(0.5)

    async def press_key(self, key, text="", code="", key_code=0):
        await self.send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": key,
            "text": text,
            "code": code,
            "windowsVirtualKeyCode": key_code,
            "nativeVirtualKeyCode": key_code
        })
        await self.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": key,
            "code": code,
            "windowsVirtualKeyCode": key_code,
            "nativeVirtualKeyCode": key_code
        })

    async def close(self):
        try:
            if self.ws:
                await self.ws.close()
        except Exception:
            pass
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                pass


TEST_CASES = [
    {
        "language": "Python",
        "code": "def find_min(values: list[int]) -> int:\n    min_val = values[0]\n    for v in values[1:]:\n        if v > min_val:\n            min_val = v\n    return min_val",
        "description": "My loop condition updates when value is greater instead of smaller. Can you guide me?"
    },
    {
        "language": "JavaScript",
        "code": "function processItems(items) {\n  for (let i = 0; i < items.length - 1; i++) {\n    console.log(items[i]);\n  }\n}",
        "description": "I have converted my function into JavaScript but my loop still stops at items.length - 1. Am I missing the final item in the array?"
    },
    {
        "language": "TypeScript",
        "code": "function filterActiveUsers<T extends { active: boolean }>(users: Array<T>): Array<T> {\n  return users.filter(u => !u.active);\n}",
        "description": "My generic filter with angle brackets is inverted and returns inactive users."
    },
    {
        "language": "Go",
        "code": "func sumSlice(vals []int) int {\n    total := 0\n    for i := 0; i <= len(vals); i++ {\n        total += vals[i]\n    }\n    return total\n}",
        "description": "My Go slice iteration panics on the terminal loop index."
    },
    {
        "language": "Rust",
        "code": "fn find_target<T: PartialEq>(items: &Vec<T>, target: &T) -> Option<usize> {\n    for i in 0..=items.len() {\n        if &items[i] == target { return Some(i); }\n    }\n    None\n}",
        "description": "Rust vector lookup panics on boundary condition with angle bracket generics."
    },
    {
        "language": "C++",
        "code": "#include <vector>\n#include <iostream>\ntemplate <typename T>\nvoid printLast(const std::vector<T>& vec) {\n    std::cout << vec[vec.size()] << std::endl;\n}",
        "description": "C++ vector terminal element access causes segmentation fault at boundary."
    },
    {
        "language": "Java",
        "code": "import java.util.List;\npublic class Searcher<T> {\n    public T getTerminal(List<T> list) {\n        return list.get(list.size());\n    }\n}",
        "description": "Java throws IndexOutOfBoundsException when retrieving terminal element from List<T>."
    }
]


class TestBrowserMultiLanguageE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify Streamlit server is running
        try:
            with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=3) as r:
                if r.status != 200:
                    raise RuntimeError("Streamlit health check did not return 200")
        except Exception as e:
            raise RuntimeError(f"Streamlit server must be running at http://localhost:8501: {e}")

    def test_all_7_languages_e2e(self):
        async def run_suite():
            results = []
            for tc in TEST_CASES:
                lang = tc["language"]
                code = tc["code"]
                desc = tc["description"]
                print(f"\n--- Testing language: {lang} ---")

                browser = ChromeCDPBrowser()
                await browser.start()
                try:
                    target_url = f"{BASE_URL}&lang={urllib.parse.quote(lang)}"
                    await browser.navigate(target_url)

                    # Wait for Studio textareas to load
                    loaded = False
                    for _ in range(40):
                        cnt = await browser.evaluate("document.querySelectorAll('textarea').length")
                        if cnt and cnt >= 2:
                            loaded = True
                            break
                        await asyncio.sleep(0.5)

                    if not loaded:
                        raise AssertionError(f"Studio textareas failed to load for {lang}")

                    # Type description and code
                    await browser.type_into_element(".st-key-bug_desc_input textarea", desc)
                    await browser.type_into_element(".st-key-code_snippet_input textarea", code)

                    # Verify button is visible and not covered
                    btn_check = await browser.evaluate("""
                    (() => {
                        const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Start Quacking with the Duck'));
                        if (!btn) return { found: false };
                        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                        const r = btn.getBoundingClientRect();
                        const topEl = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                        return {
                            found: true,
                            isCovered: topEl !== btn && !btn.contains(topEl)
                        };
                    })()
                    """)
                    if not btn_check or not btn_check.get("found"):
                        raise AssertionError(f"Start button not found for {lang}")
                    if btn_check.get("isCovered"):
                        raise AssertionError(f"Start button is covered by overlay for {lang}")

                    # Click Start button
                    await browser.evaluate("""
                    (() => {
                        const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Start Quacking with the Duck'));
                        if (btn) {
                            btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                            btn.click();
                        }
                    })()
                    """)

                    # Wait for duck message bubble (within 20 seconds)
                    reply_found = False
                    reply_text = ""
                    for _ in range(40):
                        await asyncio.sleep(0.5)
                        bubble = await browser.evaluate("""
                        (() => {
                            const b = document.querySelector('.duck-msg-bubble');
                            if (!b) return null;
                            const rect = b.getBoundingClientRect();
                            return {
                                text: b.innerText,
                                height: rect.height,
                                width: rect.width,
                                visible: rect.height > 0 && window.getComputedStyle(b).visibility !== 'hidden'
                            };
                        })()
                        """)
                        if bubble and bubble.get("visible") and bubble.get("text"):
                            reply_found = True
                            reply_text = bubble["text"]
                            break

                    if not reply_found:
                        raise AssertionError(f"Duck message bubble did not appear within 20 seconds for {lang}")

                    # Assert: contains exactly one question mark and no code fences
                    q_count = len(re.findall(r"\?(?:\s|$)", reply_text))
                    has_code = "```" in reply_text
                    if q_count != 1:
                        raise AssertionError(f"Duck reply should have exactly 1 question, got {q_count}: {reply_text}")
                    if has_code:
                        raise AssertionError(f"Duck reply leaked code fences: {reply_text}")

                    # Follow-up turn in chat input
                    chat_focused = await browser.evaluate("""
                    (() => {
                        const ta = document.querySelector('[data-testid="stChatInput"] textarea');
                        if (!ta) return false;
                        ta.focus();
                        return true;
                    })()
                    """)
                    if not chat_focused:
                        raise AssertionError(f"Chat input textarea not found for {lang}")

                    await asyncio.sleep(0.2)
                    await browser.send("Input.insertText", {"text": "I think the boundary condition is off by one."})
                    await asyncio.sleep(0.3)
                    await browser.press_key("Enter", text="\r", code="Enter", key_code=13)
                    await asyncio.sleep(0.5)

                    # Wait for second duck reply
                    second_reply_found = False
                    for _ in range(40):
                        await asyncio.sleep(0.5)
                        bubbles_cnt = await browser.evaluate("document.querySelectorAll('.duck-msg-bubble').length")
                        if bubbles_cnt and bubbles_cnt >= 2:
                            second_reply_found = True
                            break

                    if not second_reply_found:
                        raise AssertionError(f"Second duck reply did not appear for {lang}")

                    # Wait for Streamlit script runner to settle
                    for _ in range(20):
                        await asyncio.sleep(0.5)
                        running = await browser.evaluate("!!document.querySelector('[data-testid=\"stStatusWidgetRunningIcon\"], [data-testid=\"stStatusWidgetRunningManIcon\"]')")
                        if not running:
                            break

                    # Click "Mark as Solved"
                    await browser.evaluate("""
                    (() => {
                        const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Mark as Solved') && !b.disabled);
                        if (btns.length > 0) {
                            btns[0].scrollIntoView({ behavior: 'instant', block: 'center' });
                            btns[0].click();
                        }
                    })()
                    """)

                    # Assert breakthrough card appears with correct language
                    breakthrough_found = False
                    for i in range(60):
                        await asyncio.sleep(0.5)
                        card = await browser.evaluate("""
                        (() => {
                            const box = document.querySelector('.breakthrough-box');
                            if (!box) return null;
                            return {
                                text: box.innerText,
                                visible: box.clientHeight > 0
                            };
                        })()
                        """)
                        if card and card.get("visible") and "breakthrough unlocked" in card.get("text", "").lower():
                            breakthrough_found = True
                            if lang.lower() not in card.get("text", "").lower():
                                raise AssertionError(f"Breakthrough card text missing language {lang}: {card['text']}")
                            break

                        # Retry click after 4s if button is still present
                        if i == 8:
                            await browser.evaluate("""
                            (() => {
                                const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Mark as Solved') && !b.disabled);
                                if (btns.length > 0) {
                                    btns[0].scrollIntoView({ behavior: 'instant', block: 'center' });
                                    btns[0].click();
                                }
                            })()
                            """)

                    if not breakthrough_found:
                        raise AssertionError(f"Breakthrough card did not appear after Mark as Solved for {lang}")

                    results.append({
                        "language": lang,
                        "start_click": "PASS",
                        "first_reply_visible": "PASS",
                        "single_question": "PASS",
                        "followup_turn": "PASS",
                        "mark_as_solved": "PASS",
                        "breakthrough_card": "PASS"
                    })
                    print(f"PASS: {lang} verified end-to-end.")

                finally:
                    await browser.close()

            return results

        results = asyncio.run(run_suite())
        print("\n================== 7-LANGUAGE TEST RESULTS TABLE ==================")
        print(f"{'Language':<12} | {'Start Click':<11} | {'Reply Visible':<13} | {'1 Question':<10} | {'Followup':<8} | {'Solved':<6} | {'Card':<6}")
        print("-" * 75)
        for r in results:
            print(f"{r['language']:<12} | {r['start_click']:<11} | {r['first_reply_visible']:<13} | {r['single_question']:<10} | {r['followup_turn']:<8} | {r['mark_as_solved']:<6} | {r['breakthrough_card']:<6}")
        print("===================================================================")
        self.assertEqual(len(results), 7)


if __name__ == "__main__":
    unittest.main()

"""
prompts.py - Socratic Duck Prompts, JSON Extractor, and Gemini LLM Client
"""

import os
import json
import re
from typing import List, Dict, Any, Optional

SOCRATIC_SYSTEM_PROMPT = """You are Duck Debugger, an empathetic, inquisitive, and wise Rubber Duck 🦆.
Your sole purpose is to help programmers find bugs on their own using the Socratic method.

CRITICAL RULES:
1. NEVER reveal the bug fix or write corrected code under any circumstance.
2. Ask EXACTLY ONE question per response, with a maximum of TWO sentences total.
3. Start by clarifying what the user expected versus what actually happened.
4. If the user seems stuck (e.g. turn count >= 3), give a slightly stronger guided nudge or conceptual clue, but STILL end with a single question and NO code fix.
5. Handle messy voice-dictated input gracefully: ignore filler words ("um", "like", "uh", "you know", "and then"), extract the core symptom, and focus on the logical discrepancy.
6. Maintain a supportive, mildly quacky rubber duck tone (e.g., "Quack! Let's think: ...").

Keep your response tight, punchy, and strictly within 1-2 sentences. Exactly one question mark.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert code analyst for Duck Debugger.
Given the debugging session context (user bug description, code snippet, and conversation history),
extract a structured JSON object summarizing the resolved bug.

The output MUST be valid JSON adhering strictly to this schema:
{
  "bug_type": "<Short category, e.g., Off-by-one, Null/Undefined Reference, Type Coercion, State Mutation, Unhandled Exception, Logic Error, Syntax>",
  "scope": "<One of: logic, syntax, type error, runtime, state>",
  "root_cause": "<One clear sentence explaining the fundamental cause of the bug>",
  "lesson": "<One concise takeaway sentence framed in the developer's voice/words>",
  "language": "<Programming language, e.g., Python, JavaScript, TypeScript, Go, Java, C++, etc. Default to Python if unclear>"
}

Output ONLY the raw JSON string. Do not wrap in markdown quotes if possible, or use standard ```json blocks.
"""

PRACTICE_PROBLEM_PROMPT = """You are a senior programming mentor and Rubber Duck coach 🦆.
The user has a recurring weak spot with: "{weak_spot}".

Generate a short, fun, 3-minute practice puzzle in {language} that demonstrates a classic {weak_spot} bug.
Include:
1. A 1-sentence scenario.
2. A small buggy code snippet (5-10 lines).
3. A Socratic challenge question asking the user to spot what happens at the boundary or edge case.
Do NOT give away the answer or fix!
"""


def get_gemini_client(api_key: Optional[str] = None):
    """
    Initializes and returns the Gemini client if an API key is available.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key or not key.strip():
        return None

    try:
        from google import genai
        return genai.Client(api_key=key.strip())
    except Exception as e:
        # Fallback or initialization error
        print(f"Warning initializing google.genai: {e}")
        return None


def generate_socratic_response(
    messages: List[Dict[str, str]],
    code_snippet: str,
    bug_description: str,
    turn_count: int,
    api_key: Optional[str] = None
) -> str:
    """
    Generates the next Socratic question from Duck Debugger.
    """
    client = get_gemini_client(api_key)

    escalation_hint = ""
    if turn_count >= 3:
        escalation_hint = " The developer has answered 3 or more turns and is still stuck. Give a slightly stronger hint pointing toward the suspicious variable or boundary condition, but DO NOT provide code or the solution."

    full_system = f"{SOCRATIC_SYSTEM_PROMPT}\nTurn Count: {turn_count}.{escalation_hint}"

    context_prompt = f"""[BUG CONTEXT]
User Voice Description: {bug_description}
Code Snippet:
```
{code_snippet}
```

[CHAT HISTORY]
"""
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Rubber Duck"
        context_prompt += f"{role}: {msg['content']}\n"

    context_prompt += "\nRubber Duck (max 2 sentences, exactly 1 question, no fixes):"

    if client:
        try:
            # Using Gemini 2.5 Flash / Gemini 1.5 Flash
            model_name = "gemini-2.5-flash"
            response = client.models.generate_content(
                model=model_name,
                contents=context_prompt,
                config={
                    "system_instruction": full_system,
                    "temperature": 0.4,
                    "max_output_tokens": 150,
                }
            )
            text = response.text.strip()
            if text:
                return text
        except Exception as err:
            # Fallback to secondary model or graceful offline response
            try:
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=context_prompt,
                    config={
                        "system_instruction": full_system,
                        "temperature": 0.4,
                        "max_output_tokens": 150,
                    }
                )
                if response.text.strip():
                    return response.text.strip()
            except Exception:
                pass

    # Intelligent offline fallback if no API key or network failure
    return _generate_offline_socratic_response(turn_count, bug_description, code_snippet, messages)


def _generate_offline_socratic_response(
    turn_count: int,
    description: str,
    code: str,
    messages: List[Dict[str, str]]
) -> str:
    """Fallback heuristics to ensure interactive demo works even without an API key."""
    if turn_count == 0 or len(messages) <= 1:
        return "Quack! What exact value did you expect your code to produce at this step versus what actually printed or returned?"
    elif turn_count == 1:
        if "for" in code or "while" in code or "range" in code or "len" in code:
            return "Quack! If we trace that loop step-by-step, what is the value of your loop counter on the very first and very last iteration?"
        return "Quack! What specific variable holds the unexpected state right before the error triggers?"
    elif turn_count == 2:
        return "Quack! Have you checked whether the edge case or boundary index is inclusive or exclusive?"
    elif turn_count >= 3:
        return "Quack! Look closely at the comparison operator and boundaries in your code: is it checking one index too far?"
    return "Quack! What assumption did you make about this line that might not be 100% true at runtime?"


def extract_solved_json(
    conversation: List[Dict[str, str]],
    code_snippet: str,
    bug_description: str,
    language: str = "Python",
    api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Extracts structured bug insights via LLM when the user marks the bug as solved.
    """
    client = get_gemini_client(api_key)

    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in conversation])
    user_prompt = f"""Analyze this solved rubber-duck session and produce the JSON record:
User Voice Description: {bug_description}
Code Snippet:
{code_snippet}
Language: {language}
Debugging Conversation:
{history_str}
"""

    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config={
                    "system_instruction": EXTRACTION_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                }
            )
            raw = response.text.strip()
            data = json.loads(raw)
            return {
                "bug_type": data.get("bug_type", "Logic Error"),
                "scope": data.get("scope", "logic"),
                "root_cause": data.get("root_cause", "Unintended condition or boundary discrepancy."),
                "lesson": data.get("lesson", "Always verify boundaries and expectations."),
                "language": data.get("language", language)
            }
        except Exception as e:
            print(f"Extraction error with Gemini: {e}")

    # Fallback heuristic extraction
    inferred_type = "Logic Error"
    lower_desc = (bug_description + " " + code_snippet + " " + history_str).lower()
    if "index" in lower_desc or "one" in lower_desc or "range" in lower_desc or "bound" in lower_desc or "slice" in lower_desc:
        inferred_type = "Off-by-one"
        scope = "logic"
        root = "Boundary condition or iteration index was offset by one."
        lesson = "Check boundary conditions and inclusive vs exclusive range limits."
    elif "none" in lower_desc or "null" in lower_desc or "undefined" in lower_desc:
        inferred_type = "Null/Undefined Reference"
        scope = "runtime"
        root = "Attempted to access attribute or key on a None or undefined object."
        lesson = "Always validate existence before accessing nested properties."
    elif "type" in lower_desc or "int" in lower_desc or "str" in lower_desc:
        inferred_type = "Type Coercion"
        scope = "type error"
        root = "Mismatched data types during evaluation or assignment."
        lesson = "Explicitly cast data types before operations."
    else:
        inferred_type = "Logic Error"
        scope = "logic"
        root = "Runtime execution diverged from developer assumptions."
        lesson = "Double-check state transitions with step-by-step trace."

    return {
        "bug_type": inferred_type,
        "scope": scope,
        "root_cause": root,
        "lesson": lesson,
        "language": language
    }


def generate_practice_problem(
    weak_spot: str,
    language: str = "Python",
    api_key: Optional[str] = None
) -> str:
    """
    Generates a targeted mini practice problem based on the user's top weak spot.
    """
    client = get_gemini_client(api_key)
    prompt = PRACTICE_PROBLEM_PROMPT.format(weak_spot=weak_spot, language=language)

    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"temperature": 0.5, "max_output_tokens": 400}
            )
            if response.text.strip():
                return response.text.strip()
        except Exception as e:
            print(f"Practice problem error with Gemini: {e}")

    # Fallback curated practice problem
    return f"""### 🦆 Rubber Duck Quick Challenge: {weak_spot}

**Scenario:**
You are writing a function to grab the last `n` items from an activity log, but your QA tester says the oldest item in the window keeps disappearing!

```{language.lower()}
def get_recent_window(events, window_size):
    # What happens when len(events) == window_size?
    start_index = len(events) - window_size + 1
    return events[start_index:]
```

**Socratic Question:**
Quack! If `events` has 5 items and `window_size` is 5, what is `start_index`, and does the slice include the very first item?
"""

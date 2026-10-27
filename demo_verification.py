"""
demo_verification.py - End-to-end demonstration of the full Duck Debugger bug lifecycle.
"""
import db
import prompts

print("--- STEP 1: Voice Input & Code Snippet ---")
desc = "Um like so basically I was trying to iterate over user accounts and it crashes on the last item with IndexError"
code = "for i in range(len(users) + 1):\n    notify(users[i])"

print("--- STEP 2: Socratic Opening Question ---")
res1 = prompts.generate_socratic_response([], code, desc, 0)
print("Duck Question 1:", res1)
assert "?" in res1 and "```" not in res1

print("\n--- STEP 3: User Realization & Solved Flow ---")
conv = [
    {"role": "assistant", "content": res1},
    {"role": "user", "content": "Wait, range(len(users) + 1) produces an index equal to len(users), which is out of bounds!"}
]
extracted = prompts.extract_solved_json(conv, code, desc, "Python")
print("Extracted JSON:", extracted)
assert extracted["bug_type"] == "Off-by-one"

print("\n--- STEP 4: SQLite Persistence ---")
new_id = db.save_bug(
    bug_type=extracted["bug_type"],
    scope=extracted["scope"],
    root_cause=extracted["root_cause"],
    lesson=extracted["lesson"],
    language=extracted["language"],
    description=desc,
    code_snippet=code
)
print("Saved Bug ID:", new_id)

print("\n--- STEP 5: Dashboard Search & Analytics Verification ---")
stats = db.get_bug_stats()
print(f"Total bugs in DB: {stats['total_bugs']}")
print(f"Top weak spot: {stats['top_weak_spot']} ({stats['top_weak_spot_count']} times this week)")
matches = db.get_all_bugs("boundary")
print(f"Keyword search for 'boundary' matched {len(matches)} bugs")
assert new_id is not None
print("\n>>> ALL STEPS PASSED END-TO-END! <<<")

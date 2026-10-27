#  Duck Debugger

**Duck Debugger** is a rubber duck that talks back. It embraces messy, voice-dictated developer thoughts and snippets, guiding you strictly with **1-shot Socratic questions** (max 2 sentences, 1 question at a time) until you discover the bug yourself. It **never** reveals the fix or writes corrected code.

When you hit the **" I Solved It!"** button, it calls the Gemini LLM to extract a structured JSON summary (Bug Type, Scope, Root Cause, and Key Lesson) and saves it to a persistent SQLite database. The **Dashboard** then tracks your recurring blind spots (like *"Off-by-one errors (4 times this week)"*) and generates custom practice problems to sharpen your skills!

---

## ✨ Features

- **️ Voice Dictation-Friendly:** Accepts spoken-style rambling, filler words (*"um, like, basically"*), and messy syntax.
- ** Strictly Socratic:**
  - Never spoils the fix or writes corrected code.
  - Max 2 sentences and exactly 1 guided question per turn.
  - Focuses on what you *expected* vs. what *actually happened*.
  - Escalates gently with a subtle hint if you are stuck after 3 turns.
- ** SQLite Persistence (`duck_debugger.db`):**
  - Stores `id`, `timestamp`, `bug_type`, `scope`, `root_cause`, `lesson`, `language`, `description`, and `code_snippet`.
  - Comes pre-seeded with sample bugs for instant demo readiness.
- ** Interactive Analytics Dashboard (`pages/1__Dashboard.py`):**
  - **Top Weak Spot Banner:** Highlights your most frequent bug category this week (e.g., *"Off-by-one errors (4 times this week)"*).
  - **Bar Chart:** Frequency breakdown by bug type.
  - **Searchable Bug Log:** Instant keyword search across root causes and lessons.
  - ** Socratic Practice Problem Generator:** Generates a custom mini challenge targeted at your top blind spot.
- ** Gemini API Integration with Offline Fallback:**
  - Powered by Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`).
  - Seamlessly falls back to an offline heuristic duck if no API key is provided, ensuring zero-crash demos.

---

##  Quickstart & Setup

### 1. Navigate to the Project Folder
```bash
cd "C:\Users\Jyothi Rodrigues\.gemini\antigravity\scratch\duck-debugger"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Dependencies: `streamlit`, `google-genai`, `python-dotenv`, `pandas`)*

### 3. (Optional) Configure Gemini API Key
Create or edit your `.env` file:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
> *Note:* You can also enter or paste your Gemini API key directly into the sidebar text box in the running Streamlit web app! If no key is entered, the Duck runs in offline heuristic Socratic mode.

### 4. Run the Streamlit App

**Option A (Easiest - Double-click or run the launcher):**
Double-click `run.bat` or run:
```powershell
.\run.bat
```

**Option B (PowerShell / Command Prompt):**
```powershell
cd "C:\Users\Jyothi Rodrigues\.gemini\antigravity\scratch\duck-debugger"
$env:PYTHONUTF8=1
python -m streamlit run app.py
```
> **Tip for Windows:** Using `python -m streamlit run app.py` avoids PowerShell execution policy restrictions and PATH issues.

The web app will open automatically in your browser at `http://localhost:8501`.

---

##  Project Structure

```text
duck-debugger/
├── app.py                      # Main Rubber Duck Socratic debugging page
├── pages/
│   └── 1__Dashboard.py       # Analytics, weak spots, bug search & practice generator
├── db.py                       # SQLite database manager & pre-seeded demo bugs
├── prompts.py                  # Gemini LLM prompts, Socratic rules & JSON extraction
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment configuration
├── .env                        # Local environment file
├── duck_debugger.db            # SQLite database (auto-created on first run)
└── README.md                   # This documentation
```

---

##  How to Use

1. **Describe your bug:** Dictate or paste messy voice text into the description box (e.g., *"Um, like so I was looping through this list and it crashes at the very end"*).
2. **Paste your snippet:** Add your code in the code snippet box and select your language.
3. **Click " Start Quacking with the Duck":** The Duck will ask an opening question clarifying your expectation vs. reality.
4. **Chat back and forth:** Reply to each question. Watch the turn counter advance.
5. **Click " I Solved It!":** The Duck congratulates you with balloons, extracts the root cause and lesson into SQLite, and logs it.
6. **Visit the  Dashboard:** Open the sidebar, switch to the Dashboard, review your bug type distribution, search past lessons, and click **"Generate Practice Problem"** to drill your weak spot!

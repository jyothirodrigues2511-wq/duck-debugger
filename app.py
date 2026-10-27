"""
app.py - Duck Debugger: The Socratic Rubber Duck That Talks Back 🦆
Main debugging chat interface with voice-dictation support and SQLite persistence.
"""

import streamlit as st
import os
import sys

# Windows UTF-8 console output fix
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

import db
import prompts

# Page configuration
st.set_page_config(
    page_title="Duck Debugger 🦆",
    page_icon="🦆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database and seed sample bugs if first run
db.init_db()

# --- Custom Styling for Rubber Duck Theme ---
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #E68A00;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 20px;
    }
    .duck-card {
        background-color: #FFF8E7;
        border-left: 5px solid #FFA500;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        background-color: #FFE082;
        color: #4E342E;
        margin-right: 5px;
    }
    .solved-box {
        background-color: #E8F5E9;
        border: 2px solid #4CAF50;
        padding: 16px;
        border-radius: 10px;
        margin-top: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load Gemini API Key silently from .env
gemini_api_key = os.getenv("GEMINI_API_KEY", "")

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown("## 🦆 Duck Debugger")
    st.caption("A Rubber Duck that talks back — strictly Socratic.")

    st.markdown("### 🎙️ Voice Dictation Tips")
    st.markdown(
        """
        - Speak naturally with messy thoughts!
        - Include words like *"um, so basically..."*
        - The Duck parses the real discrepancy.
        - The Duck will **never** give away the answer!
        """
    )

    st.divider()

    # Session Stats
    stats = db.get_bug_stats()
    st.metric("Total Bugs Solved", stats["total_bugs"])
    if stats.get("top_weak_spot") and stats["top_weak_spot"] != "None yet":
        st.caption(f"Top focus: **{stats['top_weak_spot']}**")

    st.divider()
    if st.button("🔄 Start Fresh Debugging Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.bug_description = ""
        st.session_state.code_snippet = ""
        st.session_state.session_started = False
        st.session_state.solved = False
        st.session_state.is_saving = False
        st.session_state.turn_count = 0
        st.session_state.solved_record = None
        st.rerun()

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "solved" not in st.session_state:
    st.session_state.solved = False
if "is_saving" not in st.session_state:
    st.session_state.is_saving = False
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0
if "solved_record" not in st.session_state:
    st.session_state.solved_record = None
if "bug_description" not in st.session_state:
    st.session_state.bug_description = ""
if "code_snippet" not in st.session_state:
    st.session_state.code_snippet = ""
if "language" not in st.session_state:
    st.session_state.language = "Python"

# --- Main App Header ---
st.markdown('<div class="main-title">🦆 Duck Debugger</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Explain your bug out loud. Your rubber duck will guide you with 1-shot Socratic questions until you crack it yourself.</div>', unsafe_allow_html=True)

# --- Bug Setup Form (Before or during chat) ---
with st.expander("📝 Bug Description & Code Snippet", expanded=not st.session_state.session_started):
    col_lang, _ = st.columns([2, 3])
    with col_lang:
        selected_lang = st.selectbox(
            "Programming Language",
            ["Python", "JavaScript", "TypeScript", "Go", "Java", "C++", "Rust", "SQL", "Other"],
            index=0
        )
        st.session_state.language = selected_lang

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.markdown("**🎙️ Bug Description (Dictated or typed messy text)**")
        desc_input = st.text_area(
            "What's going wrong?",
            value=st.session_state.bug_description,
            placeholder="Um, so like basically I was looping through this user list and it's supposed to give me the last 5 active accounts, but like it crashes at the very end or omits the newest one and I don't know why...",
            height=200,
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**💻 Code Snippet**")
        code_input = st.text_area(
            "Paste your code snippet:",
            value=st.session_state.code_snippet,
            placeholder="def get_recent(users):\n    # paste snippet here\n    for i in range(len(users) + 1):\n        process(users[i])",
            height=200,
            label_visibility="collapsed"
        )

    if st.button("🦆 Start Quacking with the Duck", type="primary", use_container_width=True):
        if not desc_input.strip() and not code_input.strip():
            st.warning("Please provide at least a rough voice description or a code snippet to start debugging!")
        else:
            st.session_state.bug_description = desc_input
            st.session_state.code_snippet = code_input
            st.session_state.session_started = True

            # If brand new chat, generate the duck's initial Socratic opening question
            if not st.session_state.messages:
                with st.spinner("Duck is listening and inspecting your code..."):
                    opening_question = prompts.generate_socratic_response(
                        messages=[],
                        code_snippet=code_input,
                        bug_description=desc_input,
                        turn_count=0,
                        api_key=gemini_api_key
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": opening_question
                    })
            st.rerun()

# --- Active Debugging & Chat Section ---
if st.session_state.session_started:
    st.divider()

    # Context Header bar with Solved Action
    c_info, c_action = st.columns([3, 1], vertical_alignment="center")
    with c_info:
        st.markdown(
            f"""
            <div style="font-size:0.95rem;">
                <span class="badge-pill">🦆 Socratic Mode Active</span>
                <span class="badge-pill">Turn: {st.session_state.turn_count}</span>
                <span class="badge-pill">{st.session_state.language}</span>
                <span style="color:#777; margin-left:8px;">Rules: 1 question at a time. No code fixes allowed.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_action:
        if not st.session_state.solved and not st.session_state.is_saving:
            if st.button("🎉 I Solved It!", type="primary", use_container_width=True):
                st.session_state.is_saving = True
                with st.spinner("Quack! Analyzing the solution and extracting insights for your dashboard..."):
                    extracted = prompts.extract_solved_json(
                        conversation=st.session_state.messages,
                        code_snippet=st.session_state.code_snippet,
                        bug_description=st.session_state.bug_description,
                        language=st.session_state.language,
                        api_key=gemini_api_key
                    )
                    # Persist to SQLite
                    bug_id = db.save_bug(
                        bug_type=extracted["bug_type"],
                        scope=extracted["scope"],
                        root_cause=extracted["root_cause"],
                        lesson=extracted["lesson"],
                        language=extracted["language"],
                        description=st.session_state.bug_description,
                        code_snippet=st.session_state.code_snippet
                    )
                    extracted["id"] = bug_id
                    st.session_state.solved_record = extracted
                    st.session_state.solved = True
                    st.session_state.is_saving = False
                    st.balloons()
                st.rerun()

    # Solved summary card if already marked solved
    if st.session_state.solved and st.session_state.solved_record:
        rec = st.session_state.solved_record
        st.markdown(
            f"""
            <div class="solved-box">
                <h3 style="color:#2E7D32; margin-top:0;">🎉 Fantastic work! Bug #{rec.get('id', '')} Captured!</h3>
                <p><b>🏷️ Bug Type:</b> <span class="badge-pill">{rec.get('bug_type')}</span>
                   <b>🔍 Scope:</b> <span class="badge-pill">{rec.get('scope')}</span>
                   <b>💻 Language:</b> <span class="badge-pill">{rec.get('language')}</span>
                </p>
                <p><b>🎯 Root Cause:</b> {rec.get('root_cause')}</p>
                <p><b>💡 Key Lesson:</b> <i>"{rec.get('lesson')}"</i></p>
                <p style="color:#555; margin-bottom:0;">Saved to SQLite database! Head over to the <b>Dashboard</b> page in the sidebar to review your stats.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Display Chat History
    for message in st.session_state.messages:
        if message.get("role") == "user":
            with st.chat_message("user"):
                st.write(message.get("content", ""))
        else:
            with st.chat_message("assistant", avatar="🦆"):
                st.write(message.get("content", ""))

    # Chat Input (if not marked solved)
    if not st.session_state.solved:
        user_reply = st.chat_input("Talk back to your Rubber Duck (dictate or type your thoughts)...")
        if user_reply and user_reply.strip():
            clean_reply = user_reply.strip()
            # Append user message
            st.session_state.messages.append({"role": "user", "content": clean_reply})
            st.session_state.turn_count += 1

            # Get Duck's Socratic answer
            with st.chat_message("assistant", avatar="🦆"):
                with st.spinner("The Duck is thinking Socratically..."):
                    duck_reply = prompts.generate_socratic_response(
                        messages=st.session_state.messages,
                        code_snippet=st.session_state.code_snippet,
                        bug_description=st.session_state.bug_description,
                        turn_count=st.session_state.turn_count,
                        api_key=gemini_api_key
                    )
                    st.write(duck_reply)
                    st.session_state.messages.append({"role": "assistant", "content": duck_reply})
            st.rerun()
else:
    # Warm greeting when page first loads
    st.markdown(
        """
        <div class="duck-card">
            <h4>🦆 Welcome to Rubber Duck Debugging!</h4>
            <p>
                Legend says talking to a rubber duck on your desk helps you solve 90% of your bugs.
                <b>Duck Debugger</b> takes that to the next level:
            </p>
            <ul>
                <li><b>Voice-friendly:</b> Dictate your messy, rambling thoughts directly into the bug box.</li>
                <li><b>Pure Socratic guidance:</b> It will <i>never</i> just give you the answer. It asks questions to jog your brain.</li>
                <li><b>Insight logger:</b> When you hit the "I Solved It!" button, it summarizes the root cause and tracks your patterns in SQLite.</li>
            </ul>
            <p>Fill in your bug thoughts and snippet above, then click <b>Start Quacking with the Duck</b>!</p>
        </div>
        """,
        unsafe_allow_html=True
    )

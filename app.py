"""
app.py - Duck Debugger: The Socratic Rubber Duck That Talks Back
Full Google Stitch UI implementation powered by SQLite and Gemini AI.
Robust state machine, dual entry-point trigger, zero emojis.
"""

import streamlit as st
import os
import sys
import html
import logging

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

# Ensure parent directory is in sys.path
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

import db
import prompts

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Duck Debugger - Socratic Studio",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database
db.init_db()

# Load Gemini API Key silently from .env
gemini_api_key = os.getenv("GEMINI_API_KEY", "")

# --- Full-Bleed Stitch Styling & Chrome Stripping ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Hide Streamlit default top chrome and sidebar */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    .main .block-container {
        padding-top: 5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1280px !important;
        margin: 0 auto !important;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #0a122a !important;
        color: #dbe1ff !important;
    }

    code, pre, .font-mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Stitch Nav Header */
    .stitch-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 64px;
        background: rgba(10, 18, 42, 0.95);
        backdrop-filter: blur(16px);
        border-bottom: 1px solid #2c344d;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 2rem;
    }

    /* Custom Form & Input Styling */
    .stTextArea textarea {
        background-color: #131a33 !important;
        color: #dbe1ff !important;
        border: 1px solid #2c344d !important;
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
    .stTextArea textarea:focus {
        border-color: #9d4edd !important;
        box-shadow: 0 0 12px rgba(157, 78, 221, 0.3) !important;
    }

    /* Gradient buttons */
    .stButton > button {
        background: linear-gradient(90deg, #6b13af, #9d4edd) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        box-shadow: 0 0 16px rgba(157, 78, 221, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        opacity: 0.92 !important;
        transform: translateY(-1px) !important;
    }

    /* Socratic Duck Message Bubble */
    .duck-msg-bubble {
        background-color: #171e37;
        border-left: 4px solid #9d4edd;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 16px;
        color: #dbe1ff;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: 0 4px 20px rgba(5, 13, 37, 0.4);
    }

    /* User Message Bubble */
    .user-msg-bubble {
        background-color: #212942;
        border-right: 4px solid #d4a5ff;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #ffffff;
        font-size: 14px;
        line-height: 1.6;
    }

    /* Breakthrough Solved Card */
    .breakthrough-box {
        background: linear-gradient(135deg, #171e37 0%, #131a33 100%);
        border: 2px solid #9d4edd;
        border-radius: 16px;
        padding: 26px 30px;
        margin-top: 20px;
        margin-bottom: 24px;
        box-shadow: 0 0 32px rgba(157, 78, 221, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Top Navigation Bar ---
st.markdown(
    """
    <div class="stitch-nav">
      <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-size:1.15rem; font-weight:700; color:#dbe1ff; letter-spacing:-0.5px;">Duck Debugger</span>
        <span style="font-size:11px; text-transform:uppercase; padding:2px 10px; border-radius:9999px; background:#6b13af; color:#d4a5ff; border:1px solid rgba(157,78,221,0.4); font-family:'JetBrains Mono'; font-weight:600;">v2.4 Pro</span>
      </div>
      <div style="display:flex; align-items:center; gap:6px; background:#131a33; padding:4px 6px; border-radius:12px; border:1px solid #2c344d;">
        <a style="padding:6px 16px; border-radius:8px; font-size:13px; font-weight:600; text-decoration:none; background:#9d4edd; color:#ffffff; box-shadow:0 0 16px rgba(157,78,221,0.35);" href="/" target="_self">Socratic Studio</a>
        <a style="padding:6px 16px; border-radius:8px; font-size:13px; font-weight:500; text-decoration:none; color:#d0c2d5; transition:colors 0.2s;" href="/Dashboard" target="_self">Analytics & Weak Spots</a>
      </div>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="background:#212942; border:1px solid #2c344d; padding:4px 12px; border-radius:9999px; font-size:11px; font-family:'JetBrains Mono'; color:#e0b6ff;">
          14 Bug Streak
        </div>
        <div style="background:#131a33; border:1px solid #2c344d; padding:4px 12px; border-radius:9999px; font-size:11px; font-family:'JetBrains Mono'; color:#d0c2d5;">
          Ready
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

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
if "bug_desc_input" not in st.session_state:
    st.session_state.bug_desc_input = ""
if "code_snippet_input" not in st.session_state:
    st.session_state.code_snippet_input = ""
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "Python"

# --- Subheader / Session Status Bar ---
col_sub_left, col_sub_right = st.columns([3, 1], vertical_alignment="center")

with col_sub_left:
    status_mode = "Active" if len(st.session_state.messages) > 0 else "Standby"
    st.markdown(
        f"""
        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px;">
          <span style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:9999px; background:rgba(157,78,221,0.2); color:#e0b6ff; font-family:'JetBrains Mono'; font-size:11px; font-weight:600;">
            <span style="width:6px; height:6px; border-radius:9999px; background:#9d4edd;"></span>
            Socratic Mode: {status_mode}
          </span>
          <span style="background:#212942; padding:3px 10px; border-radius:9999px; color:#dbe1ff; font-family:'JetBrains Mono'; font-size:11px;">
            Turn Counter: {st.session_state.turn_count} / 6
          </span>
          <span style="background:#171e37; padding:3px 10px; border-radius:9999px; color:#e0b6ff; font-family:'JetBrains Mono'; font-size:11px;">
            {html.escape(st.session_state.selected_language)}
          </span>
          <span style="background:#050d25; padding:3px 10px; border-radius:9999px; color:#d0c2d5; font-family:'JetBrains Mono'; font-size:11px;">
            #DBG-8942
          </span>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_sub_right:
    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn1:
        if not st.session_state.solved and len(st.session_state.messages) > 0:
            if st.button("I Solved It!", use_container_width=True):
                st.session_state.is_saving = True
                with st.spinner("Extracting insights and logging to telemetry..."):
                    try:
                        extracted = prompts.extract_solved_json(
                            conversation=st.session_state.messages,
                            code_snippet=st.session_state.code_snippet_input,
                            bug_description=st.session_state.bug_desc_input,
                            language=st.session_state.selected_language,
                            api_key=gemini_api_key
                        )
                    except Exception as err:
                        logger.warning("Error extracting JSON, using fallback: %s", err)
                        extracted = {
                            "bug_type": "Logic",
                            "scope": "logic",
                            "root_cause": "Issue resolved through Socratic inquiry.",
                            "lesson": "Trace state mutations line-by-line.",
                            "language": st.session_state.selected_language
                        }
                    bug_id = db.save_bug(
                        bug_type=extracted.get("bug_type", "General"),
                        scope=extracted.get("scope", "logic"),
                        root_cause=extracted.get("root_cause", ""),
                        lesson=extracted.get("lesson", ""),
                        language=extracted.get("language", st.session_state.selected_language),
                        description=st.session_state.bug_desc_input,
                        code_snippet=st.session_state.code_snippet_input
                    )
                    extracted["id"] = bug_id
                    st.session_state.solved_record = extracted
                    st.session_state.solved = True
                    st.session_state.is_saving = False
                st.rerun()
    with c_btn2:
        if st.button("Reset", use_container_width=True):
            st.session_state.messages = []
            st.session_state.bug_desc_input = ""
            st.session_state.code_snippet_input = ""
            st.session_state.session_started = False
            st.session_state.solved = False
            st.session_state.is_saving = False
            st.session_state.turn_count = 0
            st.session_state.solved_record = None
            st.rerun()

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- Upper Input Section (Two-Column Responsive Split) ---
col_desc, col_code = st.columns([5, 7], gap="large")

with col_desc:
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-size:1.05rem; font-weight:600; color:#ffffff;">Bug Description</span>
            <span style="background:#212942; color:#e0b6ff; font-size:10px; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono';">Spoken Feed</span>
          </div>
          <span style="font-size:11px; color:#998d9e; font-family:'JetBrains Mono';">Natural Speech Friendly</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    desc_val = st.text_area(
        "Spoken description",
        key="bug_desc_input",
        placeholder="Talk or type out your thought process naturally... 'Um, basically I have a paginated while loop that never advances its cursor and freezes the browser thread with 100% CPU spike...'",
        height=220,
        label_visibility="collapsed"
    )

    # Audio Waveform Visualizer Bar
    st.markdown(
        """
        <div style="background:#0d152d; border:1px solid #2c344d; border-radius:10px; padding:8px 14px; margin-top:8px; display:flex; align-items:center; justify-content:space-between;">
          <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:24px; height:24px; border-radius:9999px; background:#9d4edd; display:flex; align-items:center; justify-content:center; color:#ffffff; font-size:11px; font-weight:700;">
              MIC
            </div>
            <div>
              <div style="font-size:11px; font-weight:600; color:#e0b6ff;">Voice Dictation Active</div>
              <div style="font-size:10px; color:#998d9e;">Speak freely with filler words</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:3px; height:18px;">
            <span style="width:3px; height:8px; background:#9d4edd; border-radius:9999px;"></span>
            <span style="width:3px; height:16px; background:#e0b6ff; border-radius:9999px;"></span>
            <span style="width:3px; height:12px; background:#9d4edd; border-radius:9999px;"></span>
            <span style="width:3px; height:18px; background:#e0b6ff; border-radius:9999px;"></span>
            <span style="width:3px; height:6px; background:#9d4edd; border-radius:9999px;"></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_code:
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-size:1.05rem; font-weight:600; color:#ffffff;">Code Snippet</span>
            <span style="background:#212942; color:#998d9e; font-size:10px; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono';">Monospace Inspector</span>
          </div>
          <span style="font-size:11px; color:#998d9e; font-family:'JetBrains Mono';">Ln 9, Col 13 • UTF-8</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    code_val = st.text_area(
        "Code snippet",
        key="code_snippet_input",
        placeholder="async function fetchAllActivity(initialCursor) {\n  let cursor = initialCursor;\n  while (cursor) {\n    const response = await api.getActivities({ cursor });\n    // paste buggy code here\n  }\n}",
        height=220,
        label_visibility="collapsed"
    )

    col_lang_sel, _ = st.columns([1, 2])
    with col_lang_sel:
        langs = ["Python", "JavaScript", "TypeScript", "Rust", "Go", "C++", "Java"]
        st.session_state.selected_language = st.selectbox(
            "Language",
            langs,
            index=langs.index(st.session_state.selected_language) if st.session_state.selected_language in langs else 0,
            label_visibility="collapsed"
        )

# Helper function to trigger Socratic Question
def trigger_socratic_turn(user_followup=None):
    safe_code = st.session_state.code_snippet_input.strip()
    safe_desc = st.session_state.bug_desc_input.strip()

    if user_followup:
        st.session_state.messages.append({"role": "user", "content": user_followup})
        st.session_state.turn_count += 1

    with st.spinner("Duck is analyzing and preparing Socratic guidance..."):
        try:
            duck_q = prompts.generate_socratic_response(
                messages=st.session_state.messages,
                code_snippet=safe_code,
                bug_description=safe_desc,
                turn_count=st.session_state.turn_count,
                api_key=gemini_api_key
            )
        except Exception as e:
            logger.warning("Gemini Socratic call exception: %s. Using heuristic.", e)
            duck_q = prompts._generate_offline_socratic_response(
                st.session_state.turn_count,
                safe_desc,
                safe_code,
                st.session_state.messages
            )

        if not duck_q or not duck_q.strip():
            duck_q = "Quack! Walk me through what value that variable actually holds at this exact step."

        st.session_state.messages.append({"role": "assistant", "content": duck_q})
        st.session_state.session_started = True

# Prominent "Start Quacking with the Duck" Button (always visible when no messages yet)
if len(st.session_state.messages) == 0:
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    if st.button("Start Quacking with the Duck", use_container_width=True):
        if not desc_val.strip() and not code_val.strip():
            st.warning("Please provide either a bug description or code snippet above to begin.")
        else:
            trigger_socratic_turn()
            st.rerun()

# --- Socratic Conversation Feed ---
if len(st.session_state.messages) > 0 or st.session_state.session_started:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="border-top:1px solid #212942; padding-top:16px; margin-bottom:12px;">
          <span style="font-size:12px; font-family:'JetBrains Mono'; text-transform:uppercase; color:#9d4edd; letter-spacing:0.5px;">
            Socratic Inquiry Stream
          </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    duck_avatar_url = "https://lh3.googleusercontent.com/aida-public/AB6AXuCZdqKekhQtz0z5H1BuXS1mpjSsqWAc9UTOtUy_1J_koxkq0OCYNtL-uoz9KlD_txSzOVgiLpV_6Ls3RJ2tt-v8vd7tjpa4uSvSF6zuHTZedMoF7aACtPTVlum8kCt7SWULp7dwghfT7bXtcQLZ0CV8uaNreL7MM03BaFfcN3n4qGEObfbVULTR_j3Z717TZor-GSb4VOBZDFvTFej0sECnXvotCP58mQ6-s11Y5XuZwAIfWLZDK4QQGQ"

    for msg in st.session_state.messages:
        content_safe = html.escape(msg.get("content", ""))
        if msg.get("role") == "assistant":
            st.markdown(
                f"""
                <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:16px;">
                  <div style="width:44px; height:44px; border-radius:12px; overflow:hidden; border:1px solid #9d4edd; flex-shrink:0; box-shadow:0 0 12px rgba(157,78,221,0.3);">
                    <img src="{duck_avatar_url}" style="width:100%; height:100%; object-fit:cover;" alt="Duck Mascot"/>
                  </div>
                  <div style="flex:1;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                      <span style="font-size:13px; font-weight:600; color:#e0b6ff;">Socratic Duck</span>
                      <span style="font-size:10px; font-family:'JetBrains Mono'; background:rgba(157,78,221,0.2); color:#e0b6ff; padding:1px 6px; border-radius:4px;">Guidance</span>
                    </div>
                    <div class="duck-msg-bubble">
                      {content_safe}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="display:flex; align-items:flex-start; justify-content:flex-end; gap:16px; margin-bottom:16px;">
                  <div style="flex:1; max-width:80%; text-align:right;">
                    <div style="font-size:13px; font-weight:600; color:#dbe1ff; margin-bottom:4px;">You (Engineer)</div>
                    <div class="user-msg-bubble" style="text-align:left;">
                      {content_safe}
                    </div>
                  </div>
                  <div style="width:40px; height:40px; border-radius:12px; background:#6b13af; color:#ffffff; font-weight:700; font-size:13px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    YOU
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Breakthrough Solved Celebration Card
    if st.session_state.solved and st.session_state.solved_record:
        rec = st.session_state.solved_record
        st.markdown(
            f"""
            <div class="breakthrough-box">
              <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span style="font-size:11px; text-transform:uppercase; background:#9d4edd; color:#ffffff; padding:2px 8px; border-radius:9999px; font-weight:600; font-family:'JetBrains Mono';">
                    Breakthrough Unlocked
                  </span>
                  <span style="font-family:'JetBrains Mono'; font-size:12px; color:#e0b6ff;">
                    Session #{rec.get('id', '8942')} Solved in {st.session_state.turn_count} Socratic cycles
                  </span>
                </div>
                <h2 style="font-size:1.5rem; font-weight:700; color:#ffffff; margin:0;">
                  Anomaly Solved by Socratic Reasoning
                </h2>
              </div>

              <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-bottom:20px;">
                <div style="background:#0d152d; border:1px solid #2c344d; border-radius:10px; padding:16px;">
                  <div style="font-size:12px; font-family:'JetBrains Mono'; color:#e0b6ff; font-weight:600; margin-bottom:6px;">Target Root Cause</div>
                  <p style="font-size:13px; color:#dbe1ff; margin:0; line-height:1.5;">{html.escape(rec.get('root_cause', ''))}</p>
                </div>
                <div style="background:#0d152d; border:1px solid #2c344d; border-radius:10px; padding:16px;">
                  <div style="font-size:12px; font-family:'JetBrains Mono'; color:#4ade80; font-weight:600; margin-bottom:6px;">Key Socratic Lesson</div>
                  <p style="font-size:13px; color:#dbe1ff; margin:0; line-height:1.5;">{html.escape(rec.get('lesson', ''))}</p>
                </div>
              </div>

              <div style="display:flex; justify-content:flex-end; gap:10px;">
                <a href="/Dashboard" target="_self" style="background:#9d4edd; color:#ffffff; padding:8px 18px; border-radius:8px; font-size:13px; font-weight:600; text-decoration:none; display:inline-block; box-shadow:0 0 16px rgba(157,78,221,0.4);">
                  View Analytics & Weak Spots
                </a>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Conversational Input Box (always active at the bottom)
if not st.session_state.solved:
    user_input = st.chat_input("Talk back to your Rubber Duck (dictate or type your thoughts)...")
    if user_input and user_input.strip():
        clean_text = user_input.strip()
        trigger_socratic_turn(user_followup=clean_text)
        st.rerun()

# --- Footer ---
st.markdown(
    """
    <div style="border-top:1px solid #171e37; padding-top:20px; margin-top:40px; display:flex; justify-content:space-between; font-size:11px; color:#998d9e; font-family:'JetBrains Mono';">
      <span>Duck Debugger Studio • Socratic Synthesis Engine • Zero Hallucination Mode Active</span>
      <span>Kernel 6.1-duck-rt • Telemetry: Nominal</span>
    </div>
    """,
    unsafe_allow_html=True
)

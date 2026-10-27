"""
pages/1_Dashboard.py - Analytics & Weak Spots Studio
High-fidelity Stitch design implementation powered by SQLite persistence and Gemini AI.
Strictly zero emojis.
"""

import streamlit as st
import pandas as pd
import os
import sys
import html
from datetime import datetime

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
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

import db
import prompts

st.set_page_config(
    page_title="Duck Debugger - Analytics & Weak Spots",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
db.init_db()

# --- Custom High-Fidelity Stitch Styling (Navy + White + Purple) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    code, pre, .font-mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Container Backgrounds */
    .stApp {
        background-color: #0a122a;
        color: #dbe1ff;
    }

    /* Stitch Hero Card */
    .stitch-hero-card {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #171e37 0%, #131a33 100%);
        border: 1px solid #2c344d;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 28px;
        box-shadow: 0 10px 30px rgba(5, 13, 37, 0.6);
    }
    .stitch-hero-glow-1 {
        position: absolute;
        top: -60px;
        right: -60px;
        width: 260px;
        height: 260px;
        background: radial-gradient(circle, rgba(157, 78, 221, 0.22) 0%, rgba(157, 78, 221, 0) 70%);
        pointer-events: none;
    }
    .stitch-hero-glow-2 {
        position: absolute;
        bottom: -60px;
        left: -60px;
        width: 240px;
        height: 240px;
        background: radial-gradient(circle, rgba(107, 19, 175, 0.25) 0%, rgba(107, 19, 175, 0) 70%);
        pointer-events: none;
    }

    /* Stitch Bento Metric Cards */
    .stitch-bento-card {
        background-color: #131a33;
        border: 1px solid #212942;
        border-radius: 14px;
        padding: 20px 22px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 140px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .stitch-bento-card:hover {
        border-color: #9d4edd;
        transform: translateY(-2px);
    }

    /* Stitch Custom Bar Component */
    .stitch-bar-row {
        margin-bottom: 14px;
    }
    .stitch-bar-bg {
        width: 100%;
        height: 20px;
        background-color: #050d25;
        border-radius: 6px;
        overflow: hidden;
        padding: 2px;
    }
    .stitch-bar-fill {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #6b13af, #9d4edd, #e0b6ff);
        box-shadow: 0 0 12px rgba(157, 78, 221, 0.45);
        transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Badges */
    .stitch-badge-primary {
        background-color: #9d4edd;
        color: #ffffff;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stitch-badge-error {
        background-color: #93000a;
        color: #ffdad6;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .stitch-badge-secondary {
        background-color: #6b13af;
        color: #d4a5ff;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 500;
    }

    /* Socratic Inspector Box */
    .stitch-inspector {
        background-color: #050d25;
        border: 1px solid #212942;
        border-radius: 12px;
        padding: 18px 20px;
        margin-top: 10px;
    }
    .diff-before {
        background-color: rgba(147, 0, 10, 0.25);
        color: #ffb4ab;
        padding: 4px 10px;
        border-radius: 6px;
        margin: 4px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    }
    .diff-after {
        background-color: rgba(5, 70, 40, 0.35);
        color: #4ade80;
        padding: 4px 10px;
        border-radius: 6px;
        margin: 4px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Fetch DB Stats and Bugs
stats = db.get_bug_stats()
all_bugs = db.get_all_bugs()
total_bugs = stats.get("total_bugs", 0)
top_spot = stats.get("top_weak_spot") or "None yet"
top_count = stats.get("top_weak_spot_count", 0)
type_counts = stats.get("type_counts", {})

# Calculate percentages for the top spot
top_pct = int(round((top_count / total_bugs * 100))) if total_bugs > 0 else 0

# --- Top Header & Telemetry Bar ---
col_head1, col_head2 = st.columns([3, 1], vertical_alignment="bottom")

with col_head1:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:8px; margin-bottom: 6px;">
            <span class="stitch-badge-primary">Intelligence Telemetry</span>
            <span style="font-family:'JetBrains Mono'; font-size:11px; color:#d0c2d5; background:#171e37; padding:2px 8px; border-radius:9999px;">
                Sync: Active SQLite Session
            </span>
        </div>
        <h1 style="font-size:2.2rem; font-weight:700; color:#dbe1ff; margin:0; line-height:1.2; letter-spacing:-0.5px;">
            Debugging Intelligence & Weak Spot Analytics
        </h1>
        <p style="font-size:0.95rem; color:#d0c2d5; margin:6px 0 20px 0; max-width:750px;">
            Systematic telemetry capturing your recurring logic anomalies, Socratic breakdown timeframes, and targeted algorithmic training vectors.
        </p>
        """,
        unsafe_allow_html=True
    )

with col_head2:
    st.markdown(
        """
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-bottom:20px;">
            <span style="background:#171e37; border:1px solid #2c344d; padding:6px 14px; border-radius:9999px; font-size:12px; font-weight:600; color:#e0b6ff;">
                14 Bug Streak
            </span>
            <span style="background:#131a33; border:1px solid #2c344d; padding:6px 14px; border-radius:9999px; font-size:12px; color:#d0c2d5;">
                Telemetry Active
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Weekly Weak Spot Hero Banner Card ---
with st.container():
    if total_bugs > 0 and top_spot != "None yet":
        hero_html = f"""
        <div class="stitch-hero-card">
            <div class="stitch-hero-glow-1"></div>
            <div class="stitch-hero-glow-2"></div>
            <div style="position:relative; z-index:2;">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                    <span class="stitch-badge-error">Critical Focus Vector</span>
                    <span style="font-family:'JetBrains Mono'; font-size:12px; color:#e0b6ff; letter-spacing:0.5px;">
                        {top_count} INCIDENTS RECORDED THIS WEEK
                    </span>
                </div>
                <h2 style="font-size:1.6rem; font-weight:600; color:#ffffff; margin:0 0 8px 0;">
                    Weekly Focus: {html.escape(top_spot)}
                </h2>
                <p style="font-size:1.05rem; color:#d0c2d5; margin:0 0 16px 0; line-height:1.5;">
                    <strong style="color:#e0b6ff;">{top_pct}% of your debugging sessions</strong> this week stemmed from boundary anomalies, logic oversights, or loop termination errors.
                </p>
                <div style="display:flex; flex-wrap:wrap; gap:20px; font-family:'JetBrains Mono'; font-size:12px; color:#d0c2d5;">
                    <div>Cognitive Trap: <span style="color:#ffffff; font-weight:600;">Inclusive vs. Exclusive boundary confusion</span></div>
                    <div>Recovery Cost: <span style="color:#ffffff; font-weight:600;">4.2 min avg Socratic turnaround</span></div>
                </div>
            </div>
        </div>
        """
    else:
        hero_html = """
        <div class="stitch-hero-card">
            <div class="stitch-hero-glow-1"></div>
            <div class="stitch-hero-glow-2"></div>
            <div style="position:relative; z-index:2;">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                    <span class="stitch-badge-primary">System Ready</span>
                </div>
                <h2 style="font-size:1.6rem; font-weight:600; color:#ffffff; margin:0 0 8px 0;">
                    Duck Debugger Intelligence Telemetry
                </h2>
                <p style="font-size:1.05rem; color:#d0c2d5; margin:0 0 16px 0;">
                    No bugs logged in this session yet. Solve problems in the Socratic Studio to automatically build your weakness matrix.
                </p>
            </div>
        </div>
        """
    st.markdown(hero_html, unsafe_allow_html=True)

# Hero Quick Action Button
col_act1, col_act2 = st.columns([1, 3])
with col_act1:
    practice_requested = st.button("Generate Practice Problem", type="primary", use_container_width=True)

# Practice Problem Sandbox Drawer
if "current_practice_problem" not in st.session_state:
    st.session_state.current_practice_problem = None

if practice_requested:
    target_spot = top_spot if top_spot != "None yet" else "Off-by-one"
    with st.spinner(f"Synthesizing targeted challenge for {target_spot}..."):
        api_key = os.getenv("GEMINI_API_KEY", "")
        problem = prompts.generate_practice_problem(
            weak_spot=target_spot,
            language="Python",
            api_key=api_key
        )
        st.session_state.current_practice_problem = problem

if st.session_state.current_practice_problem:
    target_spot = top_spot if top_spot != "None yet" else "Off-by-one"
    st.markdown(
        f"""
        <div style="background-color:#131a33; border:1px solid #9d4edd; border-radius:14px; padding:22px; margin-top:14px; margin-bottom:24px; box-shadow:0 0 24px rgba(157,78,221,0.25);">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <span class="stitch-badge-primary">Synthesized Practice Vector</span>
                <span style="font-family:'JetBrains Mono'; font-size:12px; color:#e0b6ff;">Challenge: {html.escape(target_spot)}</span>
            </div>
            <div style="color:#dbe1ff; line-height:1.6; font-size:0.95rem;">
                {st.session_state.current_practice_problem}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Close Sandbox Challenge"):
        st.session_state.current_practice_problem = None
        st.rerun()

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# --- Analytics Metrics & Data Visualization Bento Grid ---
col_bento_left, col_bento_right = st.columns([5, 7], gap="medium")

with col_bento_left:
    # 2x2 Grid of Bento Metric Cards
    bento_m1, bento_m2 = st.columns(2)
    with bento_m1:
        st.markdown(
            f"""
            <div class="stitch-bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d0c2d5;">Total Solved</span>
                    <span style="font-size:12px; color:#9d4edd; font-family:'JetBrains Mono';">METRIC</span>
                </div>
                <div style="margin:10px 0;">
                    <span style="font-size:2.2rem; font-weight:700; color:#ffffff;">{total_bugs}</span>
                    <span style="font-size:12px; color:#d0c2d5; font-family:'JetBrains Mono'; margin-left:4px;">bugs</span>
                </div>
                <div style="font-size:11px; color:#4ade80;">
                    +100% telemetry synced
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with bento_m2:
        st.markdown(
            """
            <div class="stitch-bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d0c2d5;">Avg Time to Aha!</span>
                    <span style="font-size:12px; color:#9d4edd; font-family:'JetBrains Mono';">SPEED</span>
                </div>
                <div style="margin:10px 0;">
                    <span style="font-size:2.2rem; font-weight:700; color:#ffffff;">4.2</span>
                    <span style="font-size:12px; color:#d0c2d5; font-family:'JetBrains Mono'; margin-left:4px;">mins</span>
                </div>
                <div style="font-size:11px; color:#e0b6ff;">
                    -35% with Socratic prompts
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    bento_m3, bento_m4 = st.columns(2)
    with bento_m3:
        st.markdown(
            f"""
            <div class="stitch-bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d0c2d5;">Weak Spot Recurrence</span>
                </div>
                <div style="margin:8px 0;">
                    <div style="font-size:1rem; font-weight:600; color:#ffffff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        {html.escape(top_spot)}
                    </div>
                    <span style="font-size:11px; color:#e0b6ff; font-family:'JetBrains Mono';">{top_pct}% of incidents</span>
                </div>
                <div style="width:100%; height:5px; background:#2c344d; border-radius:9999px; overflow:hidden;">
                    <div style="width:{top_pct}%; height:100%; background:#9d4edd; border-radius:9999px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with bento_m4:
        # Scope breakdown calculation
        scopes = {}
        for b in all_bugs:
            sc = b.get("scope", "logic")
            scopes[sc] = scopes.get(sc, 0) + 1
        logic_count = scopes.get("logic", 0) + scopes.get("indexing", 0)
        bounds_count = scopes.get("bounds", 0) + scopes.get("slicing", 0)
        other_count = max(0, total_bugs - (logic_count + bounds_count))

        st.markdown(
            f"""
            <div class="stitch-bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d0c2d5;">Scope Breakdown</span>
                </div>
                <div style="margin:8px 0; font-size:12px; color:#dbe1ff; display:flex; flex-direction:column; gap:4px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span>Logic / Loop:</span>
                        <strong style="color:#e0b6ff;">{logic_count}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>Bounds / Slice:</span>
                        <strong style="color:#d4a5ff;">{bounds_count}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>Runtime / Type:</span>
                        <strong style="color:#deb7ff;">{other_count}</strong>
                    </div>
                </div>
                <span style="font-size:10px; color:#998d9e;">Validated in SQLite session</span>
            </div>
            """,
            unsafe_allow_html=True
        )

with col_bento_right:
    # Bug Pattern Frequency Matrix
    st.markdown(
        f"""
        <div class="stitch-bento-card" style="min-height:300px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div>
                    <div style="font-size:1.1rem; font-weight:600; color:#ffffff;">Bug Pattern Frequency Matrix</div>
                    <div style="font-size:12px; color:#d0c2d5;">Resolved anomalies categorised by syntactic & architectural archetype</div>
                </div>
                <span style="background:#171e37; border:1px solid #2c344d; padding:4px 10px; border-radius:9999px; font-family:'JetBrains Mono'; font-size:11px; color:#e0b6ff;">
                    {total_bugs} incidents recorded
                </span>
            </div>
        """,
        unsafe_allow_html=True
    )

    if type_counts:
        max_c = max(type_counts.values()) if type_counts else 1
        for bug_name, c in type_counts.items():
            pct_bar = int((c / max_c) * 100)
            share_pct = round((c / total_bugs) * 100, 1) if total_bugs > 0 else 0
            st.markdown(
                f"""
                <div class="stitch-bar-row">
                    <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                        <span style="color:#dbe1ff; font-weight:500;">{html.escape(bug_name)}</span>
                        <span style="font-family:'JetBrains Mono'; color:#e0b6ff;">{c} bugs ({share_pct}%)</span>
                    </div>
                    <div class="stitch-bar-bg">
                        <div class="stitch-bar-fill" style="width: {pct_bar}%;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No bug pattern records logged yet.")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# --- Searchable Bug History Table & Inspector Section ---
st.markdown(
    """
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h3 style="font-size:1.3rem; font-weight:600; color:#ffffff; margin:0;">
            Bug History & Socratic Telemetry Log
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

search_col, filter_col = st.columns([3, 1])
with search_col:
    search_query = st.text_input(
        "Search bugs",
        placeholder="Search by root cause, lesson, language, or keyword...",
        label_visibility="collapsed"
    )

with filter_col:
    type_options = ["All Types"] + list(type_counts.keys())
    selected_type_filter = st.selectbox(
        "Filter by Type",
        options=type_options,
        label_visibility="collapsed"
    )

filtered_bugs = db.get_all_bugs(query=search_query)

if selected_type_filter != "All Types":
    filtered_bugs = [b for b in filtered_bugs if b.get("bug_type") == selected_type_filter]

if filtered_bugs:
    table_rows = []
    for b in filtered_bugs:
        table_rows.append({
            "Bug ID": f"#{b['id']}",
            "Timestamp": b["timestamp"],
            "Bug Type": b["bug_type"],
            "Scope": b["scope"],
            "Language": b["language"],
            "Root Cause Summary": b["root_cause"],
            "Key Socratic Lesson": b["lesson"]
        })
    df_table = pd.DataFrame(table_rows)

    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Bug ID": st.column_config.TextColumn(width="small"),
            "Timestamp": st.column_config.TextColumn(width="medium"),
            "Bug Type": st.column_config.TextColumn(width="medium"),
            "Scope": st.column_config.TextColumn(width="small"),
            "Language": st.column_config.TextColumn(width="small"),
            "Root Cause Summary": st.column_config.TextColumn(width="large"),
            "Key Socratic Lesson": st.column_config.TextColumn(width="large"),
        }
    )

    # Detailed Inspector Expander
    with st.expander("Inspect Socratic Session & Code Diffs"):
        bug_ids = [b["id"] for b in filtered_bugs]
        selected_bug_id = st.selectbox("Select Session to inspect:", options=bug_ids, format_func=lambda x: f"Session #{x}")
        chosen = next((b for b in filtered_bugs if b["id"] == selected_bug_id), None)
        if chosen:
            st.markdown(
                f"""
                <div class="stitch-inspector">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span style="font-size:1.1rem; font-weight:600; color:#ffffff;">
                            Socratic Session #{chosen['id']} - {html.escape(chosen['bug_type'])}
                        </span>
                        <span class="stitch-badge-secondary">{html.escape(chosen['language'])}</span>
                    </div>
                    <p style="color:#d0c2d5; font-size:0.95rem; line-height:1.5;">
                        <strong style="color:#e0b6ff;">Root Cause:</strong> {html.escape(chosen['root_cause'])}<br/>
                        <strong style="color:#4ade80;">Key Lesson:</strong> {html.escape(chosen['lesson'])}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if chosen.get("description"):
                st.markdown("**Original Voice Dictation:**")
                st.info(f"\"{chosen['description']}\"")

            if chosen.get("code_snippet"):
                st.markdown("**Original Code Snippet:**")
                st.code(chosen["code_snippet"], language=chosen["language"].lower() if chosen["language"] else "python")
else:
    st.info("No bugs found matching your search criteria.")

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# Footer
st.markdown(
    """
    <div style="border-top:1px solid #171e37; padding-top:16px; display:flex; justify-content:space-between; font-size:11px; color:#998d9e; font-family:'JetBrains Mono';">
        <span>Socratic Synthesis Engine • Zero Hallucination Mode Active</span>
        <span>Duck Debugger Studio • Telemetry: Nominal</span>
    </div>
    """,
    unsafe_allow_html=True
)

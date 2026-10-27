"""
pages/1_📊_Dashboard.py - Analytics, Weak Spot Tracker, and Practice Problem Generator
"""

import streamlit as st
import pandas as pd
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

# Ensure parent directory is in sys.path for direct or multi-page module imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

import db
import prompts

st.set_page_config(
    page_title="Duck Debugger - Dashboard 📊",
    page_icon="🦆",
    layout="wide"
)

# Initialize DB in case navigated directly
db.init_db()

# --- Custom Styling ---
st.markdown(
    """
    <style>
    .dash-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #E68A00;
        margin-bottom: 5px;
    }
    .weak-spot-card {
        background: linear-gradient(135deg, #FFF3E0, #FFE0B2);
        border: 2px solid #FF9800;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
    }
    .metric-badge {
        background-color: #E65100;
        color: white;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="dash-title">📊 Debugging Analytics & Weak Spots</div>', unsafe_allow_html=True)
st.caption("Review your debugging history, pinpoint your recurring blind spots, and drill with Socratic practice problems.")

# Fetch DB Stats
stats = db.get_bug_stats()
all_bugs = db.get_all_bugs()

# --- Top Weak Spot Banner ---
top_spot = stats.get("top_weak_spot") or "None yet"
top_count = stats.get("top_weak_spot_count", 0)

with st.container():
    col_banner, col_btn = st.columns([3, 1], vertical_alignment="center")
    with col_banner:
        if stats.get("total_bugs", 0) > 0 and top_spot != "None yet":
            st.markdown(
                f"""
                <div class="weak-spot-card">
                    <h3 style="margin:0; color:#BF360C;">🎯 Weekly Focus & Top Weak Spot</h3>
                    <p style="font-size:1.15rem; margin: 8px 0 0 0; color:#37474F;">
                        Your most frequent blind spot: <b>{top_spot}</b> (<span class="metric-badge">{top_count} times this week</span>)
                    </p>
                    <p style="font-size:0.9rem; color:#5D4037; margin:5px 0 0 0;">
                        💡 Frequent patterns happen! Turn this blind spot into your superpower with targeted practice.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="weak-spot-card">
                    <h3 style="margin:0; color:#BF360C;">🎯 Welcome to your Debugging Dashboard</h3>
                    <p style="font-size:1.1rem; margin: 8px 0 0 0; color:#37474F;">
                        No bugs recorded yet! Start debugging on the main page to populate your weekly analytics.
                    </p>
                    <p style="font-size:0.9rem; color:#5D4037; margin:5px 0 0 0;">
                        💡 You can click the practice button on the right to test your debugging intuition right now!
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
    with col_btn:
        st.markdown("**Drill this spot:**")
        practice_clicked = st.button("🧩 Generate Practice Problem", type="primary", use_container_width=True)

# --- Practice Problem Section ---
if "current_practice_problem" not in st.session_state:
    st.session_state.current_practice_problem = None

if practice_clicked:
    target_spot = top_spot if top_spot != "None yet" else "Off-by-one"
    with st.spinner(f"Quack! Generating a custom Socratic puzzle for {target_spot}..."):
        api_key = os.getenv("GEMINI_API_KEY", "")
        problem = prompts.generate_practice_problem(
            weak_spot=target_spot,
            language="Python",
            api_key=api_key
        )
        st.session_state.current_practice_problem = problem

if st.session_state.current_practice_problem:
    target_spot = top_spot if top_spot != "None yet" else "Off-by-one"
    with st.expander("🧩 Practice Challenge: " + target_spot, expanded=True):
        st.markdown(st.session_state.current_practice_problem)
        st.info("💡 Duck Tip: Try tracing the boundary conditions in your head or on scratch paper before writing code!")
        if st.button("Close Practice Problem"):
            st.session_state.current_practice_problem = None
            st.rerun()

st.divider()

# --- Analytics Row: Metrics & Distribution Chart ---
col_stats, col_chart = st.columns([1, 2], gap="large")

with col_stats:
    st.markdown("### 📈 Summary Metrics")
    st.metric("Total Bugs Solved", stats["total_bugs"])
    if top_spot != "None yet":
        st.metric("Top Weak Spot Count (This Week)", f"{top_count} issues", delta=f"{top_spot}", delta_color="inverse")
    else:
        st.metric("Top Weak Spot Count (This Week)", "0 issues")

    # Scope distribution
    if all_bugs:
        scopes = {}
        for b in all_bugs:
            sc = b.get("scope", "logic")
            scopes[sc] = scopes.get(sc, 0) + 1
        st.markdown("#### Bugs by Scope")
        for sc, cnt in scopes.items():
            st.write(f"- **{sc.capitalize()}:** {cnt}")

with col_chart:
    st.markdown("### 📊 Bug Type Counts")
    if stats["type_counts"]:
        df_chart = pd.DataFrame(
            list(stats["type_counts"].items()),
            columns=["Bug Type", "Count"]
        ).set_index("Bug Type")
        st.bar_chart(df_chart, color="#FFA500")
    else:
        st.info("No bug records found yet.")

st.divider()

# --- Search and Past Bugs Table ---
st.markdown("### 🔍 Past Bugs History")
st.caption("Search across root causes, lessons, and bug types using keywords.")

search_query = st.text_input(
    "Search bugs",
    placeholder="Type a keyword to filter (e.g. 'off-by-one', 'slice', 'undefined', 'boundary', 'cast')...",
    label_visibility="collapsed"
)

filtered_bugs = db.get_all_bugs(query=search_query)

if filtered_bugs:
    # Format table for display
    display_rows = []
    for b in filtered_bugs:
        display_rows.append({
            "ID": b["id"],
            "Timestamp": b["timestamp"],
            "Bug Type": b["bug_type"],
            "Scope": b["scope"],
            "Language": b["language"],
            "Root Cause": b["root_cause"],
            "Lesson Learned": b["lesson"]
        })
    df_display = pd.DataFrame(display_rows)
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Timestamp": st.column_config.TextColumn(width="medium"),
            "Bug Type": st.column_config.TextColumn(width="medium"),
            "Scope": st.column_config.TextColumn(width="small"),
            "Language": st.column_config.TextColumn(width="small"),
            "Root Cause": st.column_config.TextColumn(width="large"),
            "Lesson Learned": st.column_config.TextColumn(width="large"),
        }
    )

    # Detailed expandable view for each bug
    with st.expander("🔎 View Detailed Snippets & Voice Dictations"):
        selected_id = st.selectbox(
            "Select Bug ID to inspect full voice dictation and code snippet:",
            [b["id"] for b in filtered_bugs]
        )
        selected_bug = next((b for b in filtered_bugs if b["id"] == selected_id), None)
        if selected_bug:
            st.markdown(f"#### Bug #{selected_bug['id']} - {selected_bug['bug_type']} ({selected_bug['language']})")
            st.markdown(f"**Recorded at:** `{selected_bug['timestamp']}` | **Scope:** `{selected_bug['scope']}`")
            st.markdown(f"**Root Cause:** {selected_bug['root_cause']}")
            st.markdown(f"**Key Lesson:** *{selected_bug['lesson']}*")

            if selected_bug.get("description"):
                st.markdown("**Original Voice Dictation:**")
                st.info(f"🎙️ *\"{selected_bug['description']}\"*")

            if selected_bug.get("code_snippet"):
                st.markdown("**Original Code Snippet:**")
                st.code(selected_bug["code_snippet"], language=selected_bug["language"].lower() if selected_bug["language"] else "python")
else:
    st.info(f"No bugs found matching '{search_query}'.")

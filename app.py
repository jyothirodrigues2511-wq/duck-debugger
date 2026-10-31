"""
app.py - Duck Debugger: The Socratic Rubber Duck That Talks Back
Unified Google Stitch UI implementation with instant two-way routing,
hamburger navigation drawer, hover animations, responsive design,
and dynamic skeleton loading screen between views.
Strictly zero emojis.
"""

import streamlit as st
import os
import sys
import html
import logging
import time
import json
import base64
from typing import Optional

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
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Duck Debugger - Socratic Studio",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database
db.init_db()


def render_html_block(html_content: str, container=None) -> None:
    """
    Renders HTML safely without Markdown code block leaks.
    Strips indentation and blank lines using prompts.clean_html,
    and leverages st.html if supported by Streamlit, falling back to
    markdown(..., unsafe_allow_html=True).
    """
    cleaned = prompts.clean_html(html_content)
    target = container if container is not None else st
    if hasattr(target, "html"):
        target.html(cleaned)
    else:
        target.markdown(cleaned, unsafe_allow_html=True)


# Resolve active Gemini API key dynamically across st.secrets, .env, and environment
def get_current_api_key() -> str:
    return prompts.resolve_gemini_api_key() or ""

gemini_api_key = get_current_api_key()

# --- Active Route Detection ---
active_view = st.query_params.get("view", "studio")
if active_view not in ["studio", "analytics"]:
    active_view = "studio"

if "current_route" not in st.session_state:
    st.session_state.current_route = active_view

is_route_transition = (st.session_state.current_route != active_view)

# --- Full-Bleed Stitch Styling with Hover Animations & Responsive CSS ---
render_html_block(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

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
        max-width: min(1560px, 96vw) !important;
        margin: 0 auto !important;
    }

    /* Scoped Code Snippet Box (key: code_snippet_input) */
    .st-key-code_snippet_input textarea,
    div[data-testid="stTextArea"].st-key-code_snippet_input textarea {
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 0.92rem !important;
        line-height: 1.5 !important;
        resize: vertical !important;
        min-height: 360px !important;
    }

    /* Scoped Voice Description Box (key: bug_desc_input) */
    .st-key-bug_desc_input textarea,
    div[data-testid="stTextArea"].st-key-bug_desc_input textarea {
        resize: vertical !important;
        min-height: 200px !important;
    }

    /* Compact Bottom Chat Input (st.chat_input) */
    [data-testid="stChatInput"] {
        padding-bottom: 0 !important;
    }
    [data-testid="stChatInput"] textarea,
    textarea[data-testid="stChatInputTextArea"] {
        min-height: 0 !important;
        max-height: 160px !important;
        height: auto !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        line-height: 1.5 !important;
        resize: none !important;
        overflow-y: auto !important;
    }
    [data-testid="stChatInput"] button,
    button[data-testid="stChatInputSubmitButton"] {
        align-self: center !important;
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
        padding: 0 1.5rem;
    }

    /* Pure-CSS Hamburger Drawer */
    #nav-drawer-toggle:checked ~ #nav-drawer-backdrop {
        opacity: 1 !important;
        pointer-events: auto !important;
    }
    #nav-drawer-toggle:checked ~ #nav-drawer-panel {
        transform: translateX(0) !important;
    }

    /* Hover Animations */
    .hover-lift {
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease !important;
    }
    .hover-lift:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 0 24px rgba(157, 78, 221, 0.35) !important;
        border-color: #9d4edd !important;
    }

    .hover-pill {
        transition: all 0.2s ease !important;
    }
    .hover-pill:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 16px rgba(157, 78, 221, 0.4) !important;
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
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .stTextArea textarea:focus {
        border-color: #9d4edd !important;
        box-shadow: 0 0 14px rgba(157, 78, 221, 0.35) !important;
    }

    /* Monospace Code Input Area */
    .code-box textarea {
        background-color: #0d152d !important;
        color: #e0b6ff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        border: 1px solid #2c344d !important;
    }

    /* Gradient buttons with Hover Scaling */
    .stButton > button {
        background: linear-gradient(90deg, #6b13af, #9d4edd) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        box-shadow: 0 0 16px rgba(157, 78, 221, 0.35) !important;
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, opacity 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.03) !important;
        box-shadow: 0 0 24px rgba(157, 78, 221, 0.5) !important;
        opacity: 0.95 !important;
    }
    .stButton > button:active {
        transform: scale(0.97) !important;
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
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .duck-msg-bubble:hover {
        box-shadow: 0 0 20px rgba(157, 78, 221, 0.25);
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
        transition: transform 0.2s ease;
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

    /* Shimmer Skeleton Animation */
    @keyframes shimmerWave {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    .skeleton-shimmer {
        background: linear-gradient(90deg, #171e37 25%, #2c344d 50%, #171e37 75%);
        background-size: 200% 100%;
        animation: shimmerWave 1.8s infinite linear;
        border-radius: 8px;
    }

    /* Responsive Media Queries */
    @media (max-width: 768px) {
        .stitch-nav {
            padding: 0 1rem;
        }
        .main .block-container {
            padding-top: 4.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
    </style>
    """
)

# Navigation Pill Styles
studio_nav_style = (
    "background:#9d4edd; color:#ffffff; box-shadow:0 0 16px rgba(157,78,221,0.35); font-weight:600;"
    if active_view == "studio"
    else "color:#d0c2d5; font-weight:500;"
)
analytics_nav_style = (
    "background:#9d4edd; color:#ffffff; box-shadow:0 0 16px rgba(157,78,221,0.35); font-weight:600;"
    if active_view == "analytics"
    else "color:#d0c2d5; font-weight:500;"
)

drawer_studio_style = (
    "background:#9d4edd; color:#ffffff;"
    if active_view == "studio"
    else "background:#171e37; color:#d0c2d5;"
)
drawer_analytics_style = (
    "background:#9d4edd; color:#ffffff;"
    if active_view == "analytics"
    else "background:#171e37; color:#d0c2d5;"
)

# Real telemetry metrics for navigation header
header_stats = db.get_bug_stats()
header_total = header_stats.get("total_bugs", 0)
header_streak = header_stats.get("streak", 0)
if header_total == 0:
    streak_badge_text = "No data yet"
elif header_streak > 0:
    streak_badge_text = f"{header_streak} Day Streak"
else:
    streak_badge_text = "0 Day Streak"

# --- Top Navigation Bar & Pure-CSS Sliding Drawer ---
render_html_block(
    f"""
    <!-- Hidden Checkbox for Pure-CSS Drawer Toggle -->
    <input type="checkbox" id="nav-drawer-toggle" style="display:none;" />

    <!-- Navigation Header -->
    <div class="stitch-nav">
      <div style="display:flex; align-items:center; gap:12px;">
        <!-- Hamburger Button -->
        <label for="nav-drawer-toggle" class="hover-pill" style="cursor:pointer; display:flex; align-items:center; justify-content:center; width:38px; height:38px; border-radius:10px; background:#171e37; border:1px solid #2c344d; color:#dbe1ff;" title="Open Route Menu">
          <span class="material-symbols-outlined" style="font-size:22px;">menu</span>
        </label>
        <span style="font-size:1.15rem; font-weight:700; color:#dbe1ff; letter-spacing:-0.5px;">Duck Debugger</span>
        <span class="hover-pill" style="font-size:11px; text-transform:uppercase; padding:2px 10px; border-radius:9999px; background:#6b13af; color:#d4a5ff; border:1px solid rgba(157,78,221,0.4); font-family:'JetBrains Mono'; font-weight:600;">v2.4 Pro</span>
      </div>

      <!-- Navigation Center Switcher -->
      <div style="display:flex; align-items:center; gap:6px; background:#131a33; padding:4px 6px; border-radius:12px; border:1px solid #2c344d;">
        <a class="hover-pill" style="padding:6px 16px; border-radius:8px; font-size:13px; text-decoration:none; transition:all 0.2s ease; {studio_nav_style}" href="/?view=studio" target="_self">Socratic Studio</a>
        <a class="hover-pill" style="padding:6px 16px; border-radius:8px; font-size:13px; text-decoration:none; transition:all 0.2s ease; {analytics_nav_style}" href="/?view=analytics" target="_self">Analytics &amp; Weak Spots</a>
      </div>

      <!-- Telemetry Status Pills -->
      <div style="display:flex; align-items:center; gap:10px;">
        <div class="hover-pill" style="background:#212942; border:1px solid #2c344d; padding:4px 12px; border-radius:9999px; font-size:11px; font-family:'JetBrains Mono'; color:#e0b6ff;">
          {streak_badge_text}
        </div>
        <div class="hover-pill" style="background:#131a33; border:1px solid #2c344d; padding:4px 12px; border-radius:9999px; font-size:11px; font-family:'JetBrains Mono'; color:#d0c2d5; display:flex; align-items:center; gap:6px;">
          <span style="display:inline-block; width:6px; height:6px; border-radius:9999px; background:#9d4edd; box-shadow:0 0 8px #9d4edd;"></span>
          Telemetry Active
        </div>
      </div>
    </div>

    <!-- Sliding Drawer Backdrop -->
    <label for="nav-drawer-toggle" id="nav-drawer-backdrop" style="position:fixed; inset:0; z-index:998; background:rgba(5,13,37,0.7); backdrop-filter:blur(4px); opacity:0; pointer-events:none; transition:opacity 0.25s ease;"></label>

    <!-- Sliding Drawer Panel -->
    <aside id="nav-drawer-panel" style="position:fixed; top:0; left:0; bottom:0; z-index:999; width:310px; max-width:85vw; background:#131a33; border-right:1px solid #2c344d; box-shadow:0 0 32px rgba(5,13,37,0.8); transform:translateX(-100%); transition:transform 0.25s cubic-bezier(0.16, 1, 0.3, 1); display:flex; flex-direction:column;">
      <div style="height:64px; padding:0 20px; display:flex; align-items:center; justify-content:space-between; background:#171e37; border-bottom:1px solid #2c344d;">
        <div style="display:flex; flex-direction:column;">
          <span style="font-weight:700; color:#dbe1ff; font-size:15px; letter-spacing:-0.5px;">Duck Debugger</span>
          <span style="font-family:'JetBrains Mono'; font-size:11px; color:#e0b6ff;">Route Navigator</span>
        </div>
        <label for="nav-drawer-toggle" style="cursor:pointer; color:#d0c2d5; padding:6px; border-radius:8px; display:flex; align-items:center; justify-content:center;">
          <span class="material-symbols-outlined" style="font-size:22px;">close</span>
        </label>
      </div>

      <!-- Drawer Links -->
      <div style="flex:1; overflow-y:auto; padding:16px 12px; display:flex; flex-direction:column; gap:8px;">
        <a href="/?view=studio" target="_self" class="hover-lift" style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-radius:12px; {drawer_studio_style}; text-decoration:none;">
          <div style="display:flex; align-items:center; gap:12px;">
            <span class="material-symbols-outlined" style="font-size:20px; color:#e0b6ff;">psychology</span>
            <span style="font-size:14px; font-weight:600;">Socratic Studio</span>
          </div>
          <span class="material-symbols-outlined" style="font-size:18px; opacity:0.8;">chevron_right</span>
        </a>

        <a href="/?view=analytics" target="_self" class="hover-lift" style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-radius:12px; {drawer_analytics_style}; text-decoration:none;">
          <div style="display:flex; align-items:center; gap:12px;">
            <span class="material-symbols-outlined" style="font-size:20px; color:#e0b6ff;">query_stats</span>
            <span style="font-size:14px; font-weight:600;">Analytics &amp; Weak Spots</span>
          </div>
          <span class="material-symbols-outlined" style="font-size:18px; opacity:0.8;">chevron_right</span>
        </a>
      </div>

      <!-- Drawer Footer -->
      <div style="padding:16px; background:#171e37; border-top:1px solid #2c344d; display:flex; flex-direction:column; gap:8px;">
        <div style="display:flex; justify-content:space-between; font-size:11px; color:#d0c2d5; font-family:'JetBrains Mono';">
          <span>Engine Link</span>
          <span style="color:#e0b6ff; font-weight:600;">Nominal</span>
        </div>
        <div style="width:100%; height:4px; border-radius:9999px; background:#212942; overflow:hidden;">
          <div style="width:100%; height:100%; background:#9d4edd;"></div>
        </div>
        <span style="font-family:'JetBrains Mono'; font-size:10px; color:#998d9e;">Duck Kernel 6.1 • Zero Hallucination</span>
      </div>
    </aside>
    """
)

# --- Dynamic Skeleton Loading Screen Function ---
def render_full_skeleton_screen(route_name="socratic-studio.duck", label="Socratic Engine Syncing..."):
    markup = f"""
    <div style="margin: 16px 0 32px 0; display:flex; flex-direction:column; gap:20px;">
      <!-- Route Breadcrumb & Latency Bar -->
      <div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:16px; padding:8px 4px;">
        <div style="display:flex; align-items:center; gap:10px; font-family:'JetBrains Mono'; font-size:12px; color:#d0c2d5;">
          <span style="display:inline-flex; align-items:center; gap:6px; color:#e0b6ff; font-weight:600;">
            <span style="width:8px; height:8px; border-radius:9999px; background:#9d4edd; box-shadow:0 0 10px #9d4edd;"></span>
            ROUTE_TRANSITION
          </span>
          <span style="color:#4d4353;">/</span>
          <span style="color:#ffffff; font-weight:600;">{html.escape(route_name)}</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; background:#131a33; border:1px solid #2c344d; padding:4px 14px; border-radius:9999px; font-family:'JetBrains Mono'; font-size:11px; color:#d0c2d5;">
          <span style="width:7px; height:7px; border-radius:9999px; background:#9d4edd; display:inline-block;"></span>
          <span>Hydration: 42ms</span>
        </div>
      </div>

      <!-- Floating Socratic Center Badge (Pulse Loader) -->
      <div style="display:flex; justify-content:center; margin: 4px 0 16px 0;">
        <div class="hover-pill" style="display:flex; align-items:center; gap:14px; padding:10px 28px; border-radius:9999px; background:#171e37; border:1px solid #9d4edd; box-shadow:0 0 24px rgba(157,78,221,0.4);">
          <div style="display:flex; align-items:center; justify-content:center; width:24px; height:24px;">
            <span class="material-symbols-outlined" style="color:#e0b6ff; font-size:22px;">psychology</span>
          </div>
          <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-size:13px; font-weight:600; color:#dbe1ff; font-family:'Inter', sans-serif;">{html.escape(label)}</span>
            <div style="width:110px; height:6px; border-radius:9999px; background:#212942; overflow:hidden;">
              <div style="width:82%; height:100%; background:linear-gradient(90deg, #6b13af, #9d4edd, #e0b6ff); border-radius:9999px;"></div>
            </div>
          </div>
          <span style="font-family:'JetBrains Mono'; font-size:12px; font-weight:700; color:#e0b6ff;">88%</span>
        </div>
      </div>

      <!-- Hero Shimmer Skeleton Header -->
      <div style="padding:22px; border-radius:16px; background:#131a33; border:1px solid #2c344d; box-shadow:0 4px 20px rgba(5,13,37,0.5);">
        <div style="display:flex; flex-direction:column; gap:12px;">
          <div class="skeleton-shimmer" style="width:140px; height:20px;"></div>
          <div class="skeleton-shimmer" style="width:65%; height:26px;"></div>
          <div class="skeleton-shimmer" style="width:40%; height:14px;"></div>
        </div>
      </div>

      <!-- 2-Column Split Grid Shimmer -->
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:20px;">
        <!-- Left Skeleton Card: Dialogue Feed -->
        <div style="padding:22px; border-radius:16px; background:#131a33; border:1px solid #2c344d; display:flex; flex-direction:column; gap:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div class="skeleton-shimmer" style="width:160px; height:18px;"></div>
            <div class="skeleton-shimmer" style="width:70px; height:18px; border-radius:9999px;"></div>
          </div>
          <!-- Waveform Skeleton -->
          <div style="background:#050d25; border:1px solid #212942; border-radius:12px; padding:16px; height:65px; display:flex; align-items:center; justify-content:space-between; gap:6px;">
            <div class="skeleton-shimmer" style="width:6px; height:24px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:45px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:30px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:50px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:20px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:55px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:35px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:48px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:22px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:40px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:28px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:52px;"></div>
            <div class="skeleton-shimmer" style="width:6px; height:25px;"></div>
          </div>
          <!-- Dialogue Strips Skeleton -->
          <div style="display:flex; flex-direction:column; gap:12px; margin-top:4px;">
            <div style="display:flex; gap:10px; align-items:flex-start;">
              <div class="skeleton-shimmer" style="width:36px; height:36px; border-radius:10px; flex-shrink:0;"></div>
              <div style="flex:1; display:flex; flex-direction:column; gap:6px;">
                <div class="skeleton-shimmer" style="width:90px; height:12px;"></div>
                <div class="skeleton-shimmer" style="width:100%; height:44px; border-radius:10px;"></div>
              </div>
            </div>
            <div style="display:flex; gap:10px; align-items:flex-start;">
              <div class="skeleton-shimmer" style="width:36px; height:36px; border-radius:10px; flex-shrink:0;"></div>
              <div style="flex:1; display:flex; flex-direction:column; gap:6px;">
                <div class="skeleton-shimmer" style="width:70px; height:12px;"></div>
                <div class="skeleton-shimmer" style="width:85%; height:38px; border-radius:10px;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Skeleton Card: Code Editor Canvas -->
        <div style="padding:22px; border-radius:16px; background:#131a33; border:1px solid #2c344d; display:flex; flex-direction:column; gap:16px;">
          <!-- File Tabs Skeleton -->
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; gap:8px;">
              <div class="skeleton-shimmer" style="width:100px; height:26px; border-radius:8px;"></div>
              <div class="skeleton-shimmer" style="width:80px; height:26px; border-radius:8px;"></div>
            </div>
            <div class="skeleton-shimmer" style="width:24px; height:24px; border-radius:6px;"></div>
          </div>
          <!-- Monospace Lines Skeleton -->
          <div style="background:#050d25; border:1px solid #212942; border-radius:12px; padding:18px; display:flex; flex-direction:column; gap:12px; min-height:190px;">
            <div style="display:flex; gap:12px; align-items:center;">
              <div class="skeleton-shimmer" style="width:16px; height:10px;"></div>
              <div class="skeleton-shimmer" style="width:70px; height:12px;"></div>
              <div class="skeleton-shimmer" style="width:130px; height:12px;"></div>
            </div>
            <div style="display:flex; gap:12px; align-items:center; padding-left:20px;">
              <div class="skeleton-shimmer" style="width:16px; height:10px;"></div>
              <div class="skeleton-shimmer" style="width:50px; height:12px;"></div>
              <div class="skeleton-shimmer" style="width:180px; height:12px;"></div>
            </div>
            <!-- Highlight bug line -->
            <div style="display:flex; gap:12px; align-items:center; padding:6px 12px; background:rgba(157,78,221,0.15); border-radius:8px; border:1px solid rgba(157,78,221,0.4);">
              <div class="skeleton-shimmer" style="width:16px; height:10px;"></div>
              <div class="skeleton-shimmer" style="width:80px; height:12px; background:#9d4edd;"></div>
              <div class="skeleton-shimmer" style="width:140px; height:12px;"></div>
            </div>
            <div style="display:flex; gap:12px; align-items:center; padding-left:20px;">
              <div class="skeleton-shimmer" style="width:16px; height:10px;"></div>
              <div class="skeleton-shimmer" style="width:110px; height:12px;"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3 Bento Metric Shimmer Cards -->
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:18px;">
        <div style="background:#131a33; border:1px solid #212942; border-radius:14px; padding:18px; display:flex; flex-direction:column; gap:12px;">
          <div style="display:flex; justify-content:space-between;">
            <div class="skeleton-shimmer" style="width:100px; height:14px;"></div>
            <div class="skeleton-shimmer" style="width:20px; height:20px; border-radius:9999px;"></div>
          </div>
          <div class="skeleton-shimmer" style="width:60px; height:28px;"></div>
          <div class="skeleton-shimmer" style="width:80%; height:12px;"></div>
        </div>
        <div style="background:#131a33; border:1px solid #212942; border-radius:14px; padding:18px; display:flex; flex-direction:column; gap:12px;">
          <div style="display:flex; justify-content:space-between;">
            <div class="skeleton-shimmer" style="width:110px; height:14px;"></div>
            <div class="skeleton-shimmer" style="width:20px; height:20px; border-radius:9999px;"></div>
          </div>
          <div class="skeleton-shimmer" style="width:70px; height:28px;"></div>
          <div class="skeleton-shimmer" style="width:75%; height:12px;"></div>
        </div>
        <div style="background:#131a33; border:1px solid #212942; border-radius:14px; padding:18px; display:flex; flex-direction:column; gap:12px;">
          <div style="display:flex; justify-content:space-between;">
            <div class="skeleton-shimmer" style="width:130px; height:14px;"></div>
            <div class="skeleton-shimmer" style="width:20px; height:20px; border-radius:9999px;"></div>
          </div>
          <div class="skeleton-shimmer" style="width:80px; height:28px;"></div>
          <div class="skeleton-shimmer" style="width:90%; height:12px;"></div>
        </div>
      </div>
    </div>
    """
    return prompts.clean_html(markup)

# --- Route Transition Skeleton Screen Trigger ---
if is_route_transition:
    route_name = "analytics-weak-spots.duck" if active_view == "analytics" else "socratic-studio.duck"
    label_name = "Hydrating Telemetry & Analytics..." if active_view == "analytics" else "Socratic Engine Syncing..."
    trans_box = st.empty()
    render_html_block(render_full_skeleton_screen(route_name, label_name), trans_box)
    time.sleep(0.55)
    trans_box.empty()
    st.session_state.current_route = active_view

render_waveform_card = prompts.render_waveform_card


# ==============================================================================
# VIEW 1: SOCRATIC STUDIO
# ==============================================================================
def render_socratic_studio():
    # Session State Initialization
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
    if "turn_error" not in st.session_state:
        st.session_state.turn_error = None
    if "solved_record" not in st.session_state:
        st.session_state.solved_record = None
    if "bug_desc_input" not in st.session_state:
        st.session_state.bug_desc_input = ""
    if "code_snippet_input" not in st.session_state:
        st.session_state.code_snippet_input = ""
    if "selected_language" not in st.session_state:
        url_lang = st.query_params.get("lang")
        valid_langs = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "C++", "Java"]
        if url_lang and url_lang in valid_langs:
            st.session_state.selected_language = url_lang
        else:
            st.session_state.selected_language = "Python"
    if "session_start_time" not in st.session_state:
        st.session_state.session_start_time = time.time()
    active_key = prompts.resolve_gemini_api_key()
    if active_key:
        if st.session_state.get("ai_offline_error") in (
            "No valid GEMINI_API_KEY detected in parameters, st.secrets, or environment",
            "No GEMINI_API_KEY detected in Streamlit Secrets or environment"
        ):
            st.session_state.ai_offline = False
            st.session_state.ai_offline_error = None
        elif "ai_offline" not in st.session_state:
            st.session_state.ai_offline = False
            st.session_state.ai_offline_error = None
    else:
        st.session_state.ai_offline = True
        st.session_state.ai_offline_error = "No valid GEMINI_API_KEY detected in parameters, st.secrets, or environment"

    # Empty container for dynamic skeleton loading screen
    skeleton_placeholder = st.empty()
    has_duck_reply = any(m.get("role") == "assistant" for m in st.session_state.messages)

    # Session Breakthrough Persistence Engine
    def save_session_breakthrough():
        if st.session_state.get("solved") and st.session_state.get("solved_record"):
            return st.session_state.solved_record

        st.session_state.is_saving = True
        current_key = prompts.resolve_gemini_api_key()
        fallback_used = False
        extraction_error = None
        try:
            extracted = prompts.extract_solved_json(
                conversation=st.session_state.messages,
                code_snippet=st.session_state.code_snippet_input,
                bug_description=st.session_state.bug_desc_input,
                language=st.session_state.selected_language,
                api_key=current_key
            )
        except Exception as err:
            logger.warning("Error extracting JSON, using fallback: %s", err)
            fallback_used = True
            extraction_error = str(err)
            extracted = {
                "bug_type": "Logic",
                "scope": "logic",
                "root_cause": "Issue resolved through Socratic inquiry.",
                "lesson": "Trace state mutations line-by-line.",
                "language": st.session_state.selected_language
            }

        if not current_key or st.session_state.get("ai_offline"):
            fallback_used = True

        # Best-effort fields from conversation if generic
        if not extracted.get("root_cause") or extracted.get("root_cause") == "Issue resolved through Socratic inquiry.":
            last_user = next((m["content"] for m in reversed(st.session_state.messages) if m.get("role") == "user"), "")
            if last_user and len(last_user.strip()) > 3:
                extracted["root_cause"] = last_user.strip()[:200]

        turn_count_val = max(1, int(st.session_state.get("turn_count", 1)))
        start_t = st.session_state.get("session_start_time")
        duration_sec = max(0.0, round(time.time() - start_t, 1)) if start_t else 0.0

        bug_id = db.save_bug(
            bug_type=extracted.get("bug_type", "General"),
            scope=extracted.get("scope", "logic"),
            root_cause=extracted.get("root_cause", ""),
            lesson=extracted.get("lesson", ""),
            language=extracted.get("language", st.session_state.selected_language),
            description=st.session_state.bug_desc_input or "Debugging logic in session",
            code_snippet=st.session_state.code_snippet_input or "# No code snippet provided",
            turn_count=turn_count_val,
            duration_seconds=duration_sec
        )
        extracted["id"] = bug_id
        if fallback_used:
            extracted["fallback_notice"] = extraction_error or "AI engine offline, saved using conversational best-effort analysis."
        st.session_state.solved_record = extracted
        st.session_state.solved = True
        st.session_state.is_saving = False
        return extracted

    # Subheader / Session Status Bar
    col_sub_left, col_sub_right = st.columns([2.2, 1.8], vertical_alignment="center")
    with col_sub_left:
        status_mode = "Active" if len(st.session_state.messages) > 0 else "Standby"
        render_html_block(
            f"""
            <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:12px;">
              <span class="hover-pill" style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:9999px; background:rgba(157,78,221,0.2); color:#e0b6ff; font-family:'JetBrains Mono'; font-size:11px; font-weight:600;">
                <span style="width:6px; height:6px; border-radius:9999px; background:#9d4edd;"></span>
                Socratic Mode: {status_mode}
              </span>
              <span class="hover-pill" style="background:#212942; padding:3px 10px; border-radius:9999px; color:#dbe1ff; font-family:'JetBrains Mono'; font-size:11px;">
                Turn Counter: {st.session_state.turn_count} / 6
              </span>
              <span class="hover-pill" style="background:#171e37; padding:3px 10px; border-radius:9999px; color:#e0b6ff; font-family:'JetBrains Mono'; font-size:11px;">
                {html.escape(st.session_state.selected_language)}
              </span>
              <span class="hover-pill" style="background:#050d25; padding:3px 10px; border-radius:9999px; color:#d0c2d5; font-family:'JetBrains Mono'; font-size:11px;">
                #DBG-8942
              </span>
            </div>
            """
        )

        if st.session_state.get("ai_offline"):
            err_text = html.escape(str(st.session_state.get("ai_offline_error") or "AI engine offline, using basic mode"))
            render_html_block(
                f"""
                <div class="hover-lift" style="display:flex; align-items:center; gap:8px; padding:8px 14px; border-radius:10px; background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.35); color:#fca5a5; font-family:'JetBrains Mono'; font-size:11px; margin-bottom:12px;">
                  <span class="material-symbols-outlined" style="font-size:18px; color:#f87171;">cloud_off</span>
                  <div>
                    <span style="font-weight:700; color:#fecaca;">AI engine offline, using basic mode:</span>
                    <span style="color:#fca5a5; margin-left:6px;">{err_text}</span>
                  </div>
                </div>
                """
            )

    with col_sub_right:
        col_btn_solve, col_btn_new = st.columns([1.3, 1.0])
        with col_btn_solve:
            if has_duck_reply:
                if st.session_state.solved:
                    st.button("Saved", key="btn_mark_solved_top", disabled=True, use_container_width=True)
                else:
                    if st.button("Mark as Solved", key="btn_mark_solved_top", type="primary", use_container_width=True, help="Mark this debugging session as solved and record telemetry"):
                        render_html_block(render_full_skeleton_screen("socratic-studio.duck", "Synthesizing Telemetry & Post-Mortem..."), skeleton_placeholder)
                        save_session_breakthrough()
                        skeleton_placeholder.empty()
                        st.rerun()

        with col_btn_new:
            if st.session_state.session_started or len(st.session_state.messages) > 0:
                if st.button("New Session", key="btn_reset_session", use_container_width=True, help="Clear current dialectic dialogue"):
                    st.session_state.messages = []
                    st.session_state.session_started = False
                    st.session_state.solved = False
                    st.session_state.turn_count = 0
                    st.session_state.solved_record = None
                    st.session_state.bug_desc_input = ""
                    st.session_state.code_snippet_input = ""
                    st.session_state.session_start_time = time.time()
                    st.rerun()

    # Two-Column Main Layout
    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    _duck_svg_raw = (
        "<svg width='44' height='44' viewBox='0 0 44 44' fill='none' xmlns='http://www.w3.org/2000/svg'>"
        "<rect width='44' height='44' rx='12' fill='#131a33'/>"
        "<circle cx='22' cy='22' r='14' fill='#9d4edd' fill-opacity='0.25'/>"
        "<ellipse cx='22' cy='22' rx='10' ry='9' fill='#f59e0b'/>"
        "<circle cx='25' cy='19' r='1.8' fill='#1e1b4b'/>"
        "<circle cx='25.5' cy='18.5' r='0.6' fill='#ffffff'/>"
        "<path d='M28 21 C33 21 34 23 32 25 C30 25.5 28 23.5 28 22 Z' fill='#ea580c'/>"
        "<ellipse cx='17' cy='24' rx='5' ry='3.5' fill='#d97706'/>"
        "</svg>"
    )
    duck_avatar_uri = f"data:image/svg+xml;base64,{base64.b64encode(_duck_svg_raw.encode('utf-8')).decode('ascii')}"

    with col_left:
        render_html_block(
            """
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-symbols-outlined" style="color:#9d4edd; font-size:22px;">mic</span>
                <span style="font-size:1.1rem; font-weight:700; color:#dbe1ff;">Duck Dialogue Feed</span>
              </div>
              <span class="hover-pill" style="font-size:11px; font-family:'JetBrains Mono'; padding:2px 8px; border-radius:9999px; background:#131a33; color:#d0c2d5; border:1px solid #2c344d;">Voice input: dictate with Wispr Flow</span>
            </div>
            """
        )

        # Interactive Waveform Graph (Animates only while Duck is thinking)
        waveform_placeholder = st.empty()
        render_html_block(render_waveform_card(is_thinking=False), waveform_placeholder)

        st.text_area(
            "Say what is going wrong (dictate with Wispr Flow)",
            placeholder="Click here, hold your Wispr hotkey, and say what is going wrong. Example: my code is not running and I think I forgot to define a function.",
            key="bug_desc_input",
            height=210
        )

    with col_right:
        render_html_block(
            """
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-symbols-outlined" style="color:#9d4edd; font-size:22px;">code</span>
                <span style="font-size:1.1rem; font-weight:700; color:#dbe1ff;">Code Context &amp; Socratic Canvas</span>
              </div>
            </div>
            """
        )

        # Language Selector
        languages = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "C++", "Java"]
        curr_lang = st.session_state.get("selected_language", "Python")
        curr_idx = languages.index(curr_lang) if curr_lang in languages else 0
        chosen_lang = st.selectbox(
            "Active Target Language",
            languages,
            index=curr_idx,
            key="active_target_language_selector",
            label_visibility="collapsed"
        )
        st.session_state.selected_language = chosen_lang

        st.text_area(
            "Code Snippet",
            placeholder="# Paste your problematic function or code segment here\ndef process_items(items):\n    for i in range(len(items) - 1):\n        print(items[i])",
            key="code_snippet_input",
            height=380
        )

    # Socratic Turn Execution Engine
    def execute_socratic_turn(user_followup=None):
        safe_desc = (st.session_state.bug_desc_input or "").strip()
        safe_code = (st.session_state.code_snippet_input or "").strip()
        target_lang = (st.session_state.selected_language or "Python").strip()

        if user_followup:
            prospective_messages = list(st.session_state.messages) + [{"role": "user", "content": user_followup}]
            prospective_turn = st.session_state.turn_count + 1
        else:
            can_start, initial_prompt, notice = prompts.validate_session_start(safe_desc, safe_code)
            if not can_start:
                st.info(notice)
                return
            prospective_messages = [{"role": "user", "content": initial_prompt}]
            prospective_turn = 1

        # Check for user breakthrough or success without cause
        if user_followup:
            if prompts.is_user_success_without_cause(user_followup):
                st.session_state.messages = prospective_messages + [{"role": "assistant", "content": prompts.ROOT_CAUSE_QUESTION}]
                st.session_state.session_started = True
                st.session_state.turn_count = prospective_turn
                st.session_state.turn_error = None
                return

            if prompts.detect_user_breakthrough(user_followup, prospective_messages):
                st.session_state.messages = prospective_messages
                st.session_state.session_started = True
                st.session_state.turn_count = prospective_turn
                st.session_state.turn_error = None
                render_html_block(render_full_skeleton_screen("socratic-studio.duck", "Synthesizing Telemetry & Post-Mortem..."), skeleton_placeholder)
                save_session_breakthrough()
                skeleton_placeholder.empty()
                return

        # Animate waveform exclusively during active generation (loading state)
        render_html_block(render_waveform_card(is_thinking=True), waveform_placeholder)

        duck_q = None
        try:
            current_key = prompts.resolve_gemini_api_key()
            try:
                res = prompts.generate_socratic_response(
                    messages=prospective_messages,
                    code_snippet=safe_code,
                    bug_description=safe_desc,
                    turn_count=prospective_turn,
                    api_key=current_key,
                    language=target_lang,
                    return_details=True
                )
                duck_q = res.get("text", "")
                st.session_state.ai_offline = bool(res.get("is_fallback"))
                st.session_state.ai_offline_error = res.get("error")
                if st.session_state.ai_offline:
                    logger.warning("AI engine offline fallback active: %s", st.session_state.ai_offline_error)
            except Exception as e:
                logger.error("Gemini Socratic call exception: %s. Using fallback heuristic.", e, exc_info=True)
                st.session_state.ai_offline = True
                st.session_state.ai_offline_error = str(e)

            if not duck_q or not duck_q.strip():
                try:
                    duck_q = prompts._generate_offline_socratic_response(
                        prospective_turn,
                        safe_desc,
                        safe_code,
                        prospective_messages,
                        target_lang
                    )
                except Exception as offline_err:
                    logger.error("Offline Socratic generator error: %s", offline_err)
                    container_word = "slice" if target_lang == "Go" else ("vector or array" if target_lang in ("C++", "Rust") else "array")
                    duck_q = f"Quack! For an {container_word} of length N in {target_lang}, what index does your code evaluate on its final step?"
        finally:
            # Revert waveform to idle resting state after generation completes
            render_html_block(render_waveform_card(is_thinking=False), waveform_placeholder)

        if duck_q and duck_q.strip():
            # Atomically commit messages and turn state
            st.session_state.messages = prospective_messages + [{"role": "assistant", "content": duck_q.strip()}]
            st.session_state.session_started = True
            st.session_state.turn_count = prospective_turn
            st.session_state.turn_error = None
        else:
            st.session_state.turn_error = "Unable to formulate a Socratic question. Please click Retry."

    # Visible Error and Retry Button
    if st.session_state.get("turn_error"):
        st.error(f"Socratic Turn Error: {st.session_state.turn_error}")
        if st.button("Retry Socratic Turn", key="btn_retry_socratic_turn"):
            st.session_state.turn_error = None
            execute_socratic_turn()
            st.rerun()

    # Prominent "Start Quacking with the Duck" Button
    if len(st.session_state.messages) == 0:
        desc_val = st.session_state.bug_desc_input
        code_val = st.session_state.code_snippet_input
        if st.button("Start Quacking with the Duck", key="btn_start_quacking"):
            can_start, _, notice = prompts.validate_session_start(desc_val, code_val)
            if not can_start:
                st.info(notice)
            else:
                execute_socratic_turn()
                st.rerun()

    # Self-healing recovery: guarantee started session is never left with an empty feed
    if st.session_state.session_started and not any(m.get("role") == "assistant" for m in st.session_state.messages):
        recovery_q = prompts._generate_offline_socratic_response(
            st.session_state.turn_count or 1,
            st.session_state.bug_desc_input or "",
            st.session_state.code_snippet_input or "",
            st.session_state.messages,
            st.session_state.selected_language
        )
        if not recovery_q or not recovery_q.strip():
            rec_lang = st.session_state.selected_language or "Python"
            rec_container = "slice" if rec_lang == "Go" else ("vector or array" if rec_lang in ("C++", "Rust") else "array")
            recovery_q = f"Quack! For an {rec_container} of length N in {rec_lang}, what index does your code evaluate on its final step?"
        st.session_state.messages.append({"role": "assistant", "content": recovery_q})
        st.session_state.turn_error = None

    # Conversation Feed Display
    if len(st.session_state.messages) > 0 or st.session_state.session_started:
        render_html_block("<div style='margin-top:24px;'></div>")

        for i, msg in enumerate(st.session_state.messages):
            if i == 0 and msg.get("role") == "user" and not st.session_state.solved:
                continue

            content_safe = html.escape(msg.get("content", ""))

            if msg.get("role") == "assistant":
                render_html_block(
                    f"""
                    <div class="hover-lift" style="display:flex; align-items:flex-start; gap:16px; margin-bottom:16px; border-radius:14px; padding:4px;">
                      <div style="width:44px; height:44px; border-radius:12px; overflow:hidden; border:1px solid #9d4edd; flex-shrink:0; box-shadow:0 0 12px rgba(157,78,221,0.3);">
                        <img src="{duck_avatar_uri}" style="width:100%; height:100%; object-fit:cover;" alt="Duck Mascot"/>
                      </div>
                      <div style="flex:1;">
                        <div style="font-size:12px; color:#9d4edd; font-family:'JetBrains Mono'; font-weight:600; margin-bottom:4px;">
                          DUCK SOCRATIC ADVISOR
                        </div>
                        <div class="duck-msg-bubble">
                          {content_safe}
                        </div>
                      </div>
                    </div>
                    """
                )
            else:
                render_html_block(
                    f"""
                    <div class="hover-lift" style="display:flex; align-items:flex-start; justify-content:flex-end; gap:16px; margin-bottom:16px; border-radius:14px; padding:4px;">
                      <div style="max-width:75%; text-align:right;">
                        <div style="font-size:12px; color:#d0c2d5; font-family:'JetBrains Mono'; margin-bottom:4px;">
                          ENGINEER (YOU)
                        </div>
                        <div class="user-msg-bubble">
                          {content_safe}
                        </div>
                      </div>
                      <div style="width:40px; height:40px; border-radius:12px; background:#6b13af; color:#ffffff; font-weight:700; font-size:13px; display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 0 12px rgba(157,78,221,0.35);">
                        YOU
                      </div>
                    </div>
                    """
                )

        # Breakthrough Solved Card
        if st.session_state.solved and st.session_state.solved_record:
            rec = st.session_state.solved_record
            fallback_html = ""
            if rec.get("fallback_notice"):
                fallback_html = f"""
                <div style="font-size:12px; color:#fca5a5; background:rgba(239,68,68,0.12); padding:8px 12px; border-radius:8px; border:1px solid rgba(239,68,68,0.35); font-family:'JetBrains Mono'; margin-bottom:12px;">
                  Notice: {html.escape(rec['fallback_notice'])}
                </div>
                """
            render_html_block(
                f"""
                <div class="breakthrough-box hover-lift">
                  <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span class="hover-pill" style="font-size:11px; text-transform:uppercase; background:#9d4edd; color:#ffffff; padding:2px 8px; border-radius:9999px; font-weight:600; font-family:'JetBrains Mono';">
                        Breakthrough Unlocked
                      </span>
                      <span style="font-family:'JetBrains Mono'; font-size:12px; color:#e0b6ff;">
                        Anomaly #{rec.get('id', '8942')} Telemetry Logged
                      </span>
                    </div>
                    {fallback_html}
                    <div style="font-size:20px; font-weight:700; color:#ffffff;">
                      Aha! Moment Discovered
                    </div>
                    <div style="font-size:13px; color:#e0b6ff; font-family:'JetBrains Mono';">
                      <strong>Bug Type:</strong> {html.escape(rec.get('bug_type', 'Logic'))} ({html.escape(rec.get('language', st.session_state.selected_language))})
                    </div>
                    <div style="font-size:14px; color:#dbe1ff; line-height:1.6;">
                      <strong>Root Cause:</strong> {html.escape(rec.get('root_cause', 'Resolved'))}
                    </div>
                    <div style="font-size:13px; color:#d0c2d5; background:#0d152d; padding:12px 16px; border-radius:10px; border-left:3px solid #9d4edd; font-family:'JetBrains Mono';">
                      Key Takeaway: {html.escape(rec.get('lesson', 'Always question assumptions regarding boundary conditions.'))}
                    </div>
                  </div>

                  <div style="display:flex; justify-content:flex-end; gap:10px;">
                    <a href="/?view=analytics" target="_self" class="hover-pill" style="background:#9d4edd; color:#ffffff; padding:8px 18px; border-radius:8px; font-size:13px; font-weight:600; text-decoration:none; display:inline-block; box-shadow:0 0 16px rgba(157,78,221,0.4);">
                      View Analytics &amp; Weak Spots
                    </a>
                  </div>
                </div>
                """
            )

        # Feed Mark as Solved action button
        if has_duck_reply and not st.session_state.solved:
            solve_feed_l, solve_feed_r = st.columns([2.5, 1.5])
            with solve_feed_r:
                if st.button("Mark as Solved", key="btn_mark_solved_feed", type="primary", use_container_width=True, help="Mark this debugging session as solved"):
                    render_html_block(render_full_skeleton_screen("socratic-studio.duck", "Synthesizing Telemetry & Post-Mortem..."), skeleton_placeholder)
                    save_session_breakthrough()
                    skeleton_placeholder.empty()
                    st.rerun()

    # Chat Input Box
    if not st.session_state.solved:
        user_input = st.chat_input("Talk back to your Rubber Duck (dictate with Wispr Flow or type here)...")
        if user_input and user_input.strip():
            clean_text = user_input.strip()
            execute_socratic_turn(user_followup=clean_text)
            st.rerun()

# ==============================================================================
# VIEW 2: ANALYTICS & WEAK SPOTS
# ==============================================================================
@st.dialog("Synthesized Practice Challenge", width="large")
def show_practice_dialog(weak_spot: str, language: str = "Python"):
    """
    Renders the practice challenge inside a top-level Streamlit dialog modal.
    Fully scrollable, responsive, with loading spinner, problem statement,
    starter code with bug, expected output, hint, and hidden solution expander.
    """
    if st.session_state.get("practice_data") is None:
        with st.spinner("Synthesizing targeted practice challenge with Gemini..."):
            user_bugs = db.get_all_bugs()[:10]
            key = prompts.resolve_gemini_api_key()
            nonce = st.session_state.get("practice_nonce", 0)
            practice_data = prompts.generate_practice_problem(
                weak_spot=weak_spot,
                user_bugs=user_bugs,
                language=language,
                api_key=key,
                seed_offset=nonce
            )
            st.session_state.practice_data = practice_data

    data = st.session_state.get("practice_data")
    if not data:
        st.warning("Could not synthesize practice problem. Please try again.")
        return

    category_label = str(data.get("category", weak_spot or "Logic")).upper()
    render_html_block(
        f"""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
          <span style="background:#9d4edd; color:#ffffff; padding:3px 12px; border-radius:9999px; font-size:11px; font-weight:700; font-family:'JetBrains Mono';">
            FOCUS VECTOR: {html.escape(category_label)}
          </span>
          <span style="color:#d0c2d5; font-size:12px; font-family:'JetBrains Mono';">Targeting your verified error patterns</span>
        </div>
        """
    )

    if data.get("notice"):
        st.info(f"Notice: {data['notice']}")

    st.markdown(f"**Scenario:**\n\n{data['statement']}")

    st.markdown("**Starter Code (Contains Bug):**")
    st.code(data["starter_code"], language=language.lower())

    st.markdown(f"**Expected Output / Behavior:**\n\n`{data['expected_output']}`")

    st.info(f"**Hint:** {data['hint']}")

    with st.expander("Reveal solution", expanded=False):
        st.markdown("**Corrected Code:**")
        st.code(data["solution_code"], language=language.lower())
        st.markdown(f"**Why this works:** {data['solution_explanation']}")

    render_html_block("<div style='margin-top:16px;'></div>")
    col_close, col_another = st.columns([1, 1])
    with col_close:
        if st.button("Close", key="btn_close_practice_modal", use_container_width=True):
            st.session_state.show_practice_modal = False
            st.session_state.practice_data = None
            st.rerun()
    with col_another:
        if st.button("Another problem", key="btn_another_practice_modal", type="primary", use_container_width=True):
            st.session_state.practice_data = None
            st.session_state.practice_nonce = st.session_state.get("practice_nonce", 0) + 1
            st.rerun()


def render_analytics(time_filter: Optional[str] = None):
    if st.query_params.get("practice") in ("1", "true"):
        st.session_state.show_practice_modal = True
        st.session_state.practice_data = None
        st.query_params.pop("practice", None)

    # Resolve time filter from argument, session_state, or query params
    if not time_filter:
        time_filter = (
            st.session_state.get("analytics_time_filter")
            or st.session_state.get("time_filter")
            or st.query_params.get("range")
            or st.query_params.get("filter")
            or "All Time"
        )

    norm_filter = str(time_filter).strip().lower()
    if norm_filter in ("30d", "last 30 days", "30 days", "last_30_days", "30"):
        active_time_label = "Last 30 Days"
        filter_param = "30d"
    elif norm_filter in ("quarter", "this quarter", "this_quarter", "quarterly", "90d", "90"):
        active_time_label = "This Quarter"
        filter_param = "quarter"
    else:
        active_time_label = "All Time"
        filter_param = "all"

    stats = db.get_bug_stats(time_range=filter_param)
    all_bugs = db.get_all_bugs(time_range=filter_param)
    total_bugs = stats.get("total_bugs", 0)
    has_data = total_bugs > 0

    top_spot = stats.get("top_weak_spot") if has_data else "No data yet"
    top_count = stats.get("top_weak_spot_count", 0)
    type_counts = stats.get("type_counts", {})
    top_pct = stats.get("top_weak_spot_pct", 0) if has_data else 0

    logic_pct = stats.get("logic_pct", 0) if has_data else 0
    runtime_pct = stats.get("runtime_pct", 0) if has_data else 0
    state_pct = stats.get("state_pct", 0) if has_data else 0

    avg_turns = stats.get("avg_turns", 0.0)
    avg_duration_sec = stats.get("avg_duration_seconds", 0.0)

    def _get_cognitive_trap(spot: str) -> str:
        if not has_data or not spot or spot.lower() in ("no data yet", "none yet"):
            return "No data yet"
        low = spot.lower()
        if any(k in low for k in ("off-by-one", "bound", "fencepost", "index", "slice", "range")):
            return "Inclusive vs Exclusive bounds / Range fencepost"
        if any(k in low for k in ("null", "undefined", "none")):
            return "Unchecked dereference on missing properties / None"
        if any(k in low for k in ("type", "coercion", "cast")):
            return "Implicit string vs numeric conversions"
        if any(k in low for k in ("scope", "unbound", "local", "closure", "nameerror")):
            return "Variable shadowing & closure state retention"
        if any(k in low for k in ("syntax", "bracket", "parenthes", "colon")):
            return "Container delimiters & operator assignments"
        return "Logic edge conditions & branch evaluation"

    cognitive_trap_str = _get_cognitive_trap(top_spot)

    if not has_data:
        recovery_cost_str = "No data yet"
    elif avg_duration_sec >= 5.0:
        recovery_cost_str = f"{round(avg_duration_sec / 60.0, 1)} min avg turnaround"
    elif avg_turns > 0.0:
        recovery_cost_str = f"{avg_turns:.1f} turns avg turnaround"
    else:
        recovery_cost_str = "1.0 turns avg turnaround"

    # Metric card values computed from SQLite (strictly defined on ALL branches)
    m1_val = str(total_bugs) if has_data else "No data yet"
    m1_unit = "bugs" if has_data else ""
    m1_sub = f"{total_bugs} verified SQLite records" if has_data else "No data yet"

    if not has_data:
        m2_label = "Avg Turnaround"
        m2_val = "No data yet"
        m2_unit = ""
        m2_sub = "No data yet"
    elif avg_duration_sec >= 5.0:
        m2_label = "Avg Time to Aha!"
        m2_val = f"{round(avg_duration_sec / 60.0, 1)}"
        m2_unit = "mins"
        m2_sub = f"Across {total_bugs} solved sessions"
    else:
        m2_label = "Avg Turns to Aha!"
        m2_val = f"{avg_turns:.1f}" if avg_turns > 0.0 else "1.0"
        m2_unit = "turns"
        m2_sub = "Avg Socratic questions to breakthrough"

    m3_spot = html.escape(top_spot)
    m3_sub = f"{top_pct}% of total incidents" if has_data else "No data yet"
    m3_bar = f"{top_pct}%" if has_data else "0%"

    m4_logic = f"{logic_pct}%" if has_data else "No data yet"
    m4_runtime = f"{runtime_pct}%" if has_data else "No data yet"
    m4_state = f"{state_pct}%" if has_data else "No data yet"

    banner_title = f"Weekly Focus: {html.escape(top_spot)}"
    banner_incidents = f"{top_count} INCIDENTS RECORDED" if has_data else "0 INCIDENTS RECORDED"
    if has_data:
        banner_desc = f'<strong class="text-primary font-semibold">{top_pct}% of your debugging sessions</strong> stemmed from {html.escape(top_spot)} patterns, boundary mutations, or loop conditions.'
    else:
        banner_desc = "No debugging telemetry recorded in SQLite yet. Complete a Socratic session to populate analytics."

    # Pill styles for active filter
    pill_30d_style = (
        "background:#9d4edd; color:#ffffff; box-shadow:0 0 16px rgba(157,78,221,0.35); font-weight:600;"
        if active_time_label == "Last 30 Days"
        else "color:#d0c2d5; font-weight:500; background:transparent;"
    )
    pill_quarter_style = (
        "background:#9d4edd; color:#ffffff; box-shadow:0 0 16px rgba(157,78,221,0.35); font-weight:600;"
        if active_time_label == "This Quarter"
        else "color:#d0c2d5; font-weight:500; background:transparent;"
    )
    pill_all_style = (
        "background:#9d4edd; color:#ffffff; box-shadow:0 0 16px rgba(157,78,221,0.35); font-weight:600;"
        if active_time_label == "All Time"
        else "color:#d0c2d5; font-weight:500; background:transparent;"
    )

    # Top-Level Streamlit Header: Page Title rendered ONCE
    render_html_block(
        """
        <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:16px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:8px; background:#212942; color:#e0b6ff;">
              <span class="material-symbols-outlined" style="font-size:18px;">query_stats</span>
            </span>
            <span style="font-family:'JetBrains Mono', monospace; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:#e0b6ff; font-weight:600;">Intelligence Telemetry</span>
            <span style="display:inline-flex; align-items:center; gap:6px; padding:2px 8px; border-radius:9999px; background:#212942; color:#d0c2d5; font-size:11px; font-family:'JetBrains Mono', monospace;">
              <span style="width:6px; height:6px; border-radius:9999px; background:#34d399;"></span>
              Sync: SQLite Active
            </span>
          </div>
          <h1 style="font-size:1.85rem; font-weight:700; color:#dbe1ff; margin:6px 0 2px 0; letter-spacing:-0.02em;">
            Debugging Intelligence &amp; Weak Spot Analytics
          </h1>
          <p style="color:#d0c2d5; font-size:13px; margin:0; max-width:800px; line-height:1.5;">
            Systematic telemetry capturing your recurring logic anomalies, Socratic breakdown timeframes, and targeted algorithmic training vectors.
          </p>
        </div>
        """
    )

    # Filter Controls and Export Report Row
    col_filters, col_export = st.columns([3, 1], vertical_alignment="center")
    with col_filters:
        render_html_block(
            f"""
            <div style="display:flex; align-items:center; gap:6px; background:#131a33; border:1px solid #2c344d; padding:4px 6px; border-radius:12px; width:fit-content;">
              <a href="/?view=analytics&range=30d" target="_self" class="hover-pill" style="padding:6px 14px; border-radius:8px; font-size:12px; text-decoration:none; transition:all 0.2s ease; {pill_30d_style}">Last 30 Days</a>
              <a href="/?view=analytics&range=quarter" target="_self" class="hover-pill" style="padding:6px 14px; border-radius:8px; font-size:12px; text-decoration:none; transition:all 0.2s ease; {pill_quarter_style}">This Quarter</a>
              <a href="/?view=analytics&range=all" target="_self" class="hover-pill" style="padding:6px 14px; border-radius:8px; font-size:12px; text-decoration:none; transition:all 0.2s ease; {pill_all_style}">All Time</a>
            </div>
            """
        )
    with col_export:
        csv_data = db.export_bugs_csv(time_range=filter_param)
        st.download_button(
            label="Export Report",
            data=csv_data,
            file_name=f"duck_debugger_telemetry_{filter_param}.csv",
            mime="text/csv",
            key="btn_export_report",
            use_container_width=True,
        )

    # Weekly Weak Spot Hero Banner Card
    render_html_block(
        f"""
        <div style="position:relative; overflow:hidden; border-radius:16px; background:#171e37; border:1px solid #2c344d; padding:24px 28px; margin: 18px 0 12px 0; box-shadow:0 8px 32px rgba(5,13,37,0.5);">
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:9999px; background:#93000a; color:#ffdad6; font-size:11px; font-weight:700; font-family:'JetBrains Mono', monospace; text-transform:uppercase;">
                <span class="material-symbols-outlined" style="font-size:13px;">crisis_alert</span>
                Critical Focus Vector
              </span>
              <span style="font-size:11px; color:#e0b6ff; font-family:'JetBrains Mono', monospace; letter-spacing:0.05em;">{banner_incidents}</span>
            </div>
            <h2 style="font-size:1.45rem; font-weight:700; color:#dbe1ff; margin:2px 0 0 0;">
              {banner_title}
            </h2>
            <p style="font-size:13.5px; color:#d0c2d5; line-height:1.55; margin:0;">
              {banner_desc}
            </p>
            <div style="display:flex; flex-wrap:wrap; align-items:center; gap:20px; margin-top:4px; font-family:'JetBrains Mono', monospace; font-size:12px; color:#d0c2d5;">
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="material-symbols-outlined" style="font-size:16px; color:#9d4edd;">psychology</span>
                <span>Cognitive Trap: <strong style="color:#dbe1ff;">{cognitive_trap_str}</strong></span>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="material-symbols-outlined" style="font-size:16px; color:#e0b6ff;">timer</span>
                <span>Recovery Cost: <strong style="color:#dbe1ff;">{recovery_cost_str}</strong></span>
              </div>
            </div>
          </div>
        </div>
        """
    )

    # Exactly ONE Generate Practice Problem Button: Full Width, No Stray Caption
    if st.button("Generate Practice Problem", key="btn_practice_top_level", type="primary", use_container_width=True):
        st.session_state.show_practice_modal = True
        st.session_state.practice_data = None
        st.rerun()

    # Trigger Dialog Modal if active
    if st.session_state.get("show_practice_modal"):
        show_practice_dialog(weak_spot=top_spot, language=st.session_state.get("selected_language", "Python"))

    # Bug Pattern Frequency Bars
    max_type_val = max(type_counts.values()) if type_counts else 1
    bar_chart_html_parts = []
    for bug_type, count in list(type_counts.items())[:5]:
        pct_width = max(10, int((count / max_type_val) * 100))
        share = round((count / total_bugs) * 100, 1) if total_bugs > 0 else 0
        safe_type = html.escape(bug_type)
        bar_chart_html_parts.append(f"""
        <div class="group flex flex-col gap-1 cursor-pointer transition-all duration-200 hover:scale-[1.01] hover:translate-x-1" data-spot="{safe_type}" onclick="filterByWeakSpot(this.getAttribute('data-spot'))">
          <div class="flex items-center justify-between font-label-md text-label-md">
            <span class="text-on-surface font-medium group-hover:text-primary transition-colors flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[16px] text-primary">analytics</span>
              {safe_type}
            </span>
            <div class="flex items-center gap-2">
              <span class="font-mono text-primary font-bold">{count} bugs</span>
              <span class="px-1.5 py-0.2 rounded bg-surface-container text-on-surface-variant font-mono text-[10px]">{share}%</span>
            </div>
          </div>
          <div class="w-full h-5 rounded-lg bg-surface-container-lowest p-0.5">
            <div class="h-full rounded-md bg-gradient-to-r from-secondary-container via-primary-container to-primary transition-all duration-500 shadow-[0_0_12px_rgba(157,78,221,0.5)]" style="width: {pct_width}%;"></div>
          </div>
        </div>
        """)
    bars_html = "\n".join(bar_chart_html_parts)
    matrix_content_html = bars_html if (has_data and bars_html) else '<div class="py-6 text-center text-on-surface-variant font-mono text-xs">No pattern incidents recorded yet.</div>'

    # Bug Data Table Rows
    table_rows_parts = []
    bugs_lookup = {}
    for idx, b in enumerate(all_bugs):
        bug_id = b["id"]
        code_id = f"DBG-{8900 + bug_id}"
        safe_type = html.escape(b.get("bug_type") or "General")
        safe_scope = html.escape(b.get("scope") or "Logic")
        safe_root = html.escape(b.get("root_cause") or "Root cause not specified")
        safe_lesson = html.escape(b.get("lesson") or "Lesson not specified")
        ts = b.get("timestamp") or "Recent"

        bugs_lookup[code_id] = {
            "id": code_id,
            "type": b.get("bug_type") or "General",
            "scope": b.get("scope") or "Logic",
            "root": b.get("root_cause") or "Root cause not specified",
            "lesson": b.get("lesson") or "Lesson not specified",
            "desc": b.get("description") or "Voice transcript not recorded.",
            "code": b.get("code_snippet") or "# No code snippet recorded",
            "timestamp": ts
        }

        row_bg = "bg-surface-container-low" if idx % 2 == 0 else "bg-surface-container-lowest"
        table_rows_parts.append(f"""
        <tr class="bug-row {row_bg} hover:bg-surface-container hover:shadow-[0_0_12px_rgba(157,78,221,0.25)] transition-all duration-150 group cursor-pointer" data-id="{code_id}" data-type="{safe_type}" onclick="openDrawer('{code_id}')">
          <td class="py-3.5 px-4 font-mono font-semibold text-primary">#{code_id}</td>
          <td class="py-3.5 px-4 text-on-surface-variant whitespace-nowrap font-mono text-[12px]">{ts}</td>
          <td class="py-3.5 px-4">
            <span class="inline-flex items-center px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm">
              {safe_type}
            </span>
          </td>
          <td class="py-3.5 px-4">
            <span class="font-code-md text-code-md text-on-surface-variant">{safe_scope}</span>
          </td>
          <td class="py-3.5 px-4 text-on-surface font-medium max-w-xs truncate">
            {safe_root}
          </td>
          <td class="py-3.5 px-4 text-on-surface-variant max-w-sm truncate">
            {safe_lesson}
          </td>
          <td class="py-3.5 px-4 text-right whitespace-nowrap">
            <div class="inline-flex items-center gap-1">
              <button class="px-2.5 py-1 rounded bg-surface-container-high hover:bg-primary-container hover:text-on-primary-container text-on-surface text-label-sm font-label-sm font-medium transition-all duration-200 hover:scale-105 hover:shadow-[0_0_12px_rgba(157,78,221,0.3)]" type="button">
                Inspect Session
              </button>
            </div>
          </td>
        </tr>
        """)

    rows_html = "\n".join(table_rows_parts)
    table_content_html = rows_html if (has_data and rows_html) else '<tr><td colspan="7" class="py-6 px-4 text-center text-on-surface-variant font-mono text-xs">No debugging sessions recorded yet. Complete a session in Socratic Studio to log telemetry.</td></tr>'
    bugs_json_str = json.dumps(bugs_lookup).replace("<", "\\u003c")

    analytics_html = f"""<!DOCTYPE html>
    <html class="dark" lang="en">
    <head>
      <meta charset="utf-8"/>
      <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
      <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
      <style>
        @layer base {{
          html, body {{ margin: 0; padding: 0; background-color: #0a122a; color: #dbe1ff; font-family: 'Inter', sans-serif; }}
          body {{ overscroll-behavior: none; }}
        }}
        ::-webkit-scrollbar {{ display: none; }}
      </style>
      <script src="https://cdn.tailwindcss.com"></script>
      <script id="tailwind-config">
        tailwind.config = {{
          darkMode: "class",
          theme: {{
            extend: {{
              colors: {{
                "on-primary-fixed-variant": "#6a0baa",
                "on-error": "#690005",
                "on-tertiary": "#4c007b",
                "background": "#0a122a",
                "on-secondary-container": "#d4a5ff",
                "inverse-surface": "#dbe1ff",
                "outline-variant": "#4d4353",
                "primary-container": "#9d4edd",
                "surface": "#0a122a",
                "tertiary-container": "#9b53d2",
                "surface-container-highest": "#2c344d",
                "error": "#ffb4ab",
                "surface-dim": "#0a122a",
                "on-surface-variant": "#d0c2d5",
                "primary-fixed-dim": "#e0b6ff",
                "on-tertiary-fixed": "#2e004d",
                "surface-container": "#171e37",
                "on-tertiary-fixed-variant": "#691a9f",
                "error-container": "#93000a",
                "inverse-on-surface": "#282f49",
                "surface-container-low": "#131a33",
                "on-primary": "#4c007d",
                "on-background": "#dbe1ff",
                "primary": "#e0b6ff",
                "inverse-primary": "#8433c4",
                "on-secondary-fixed-variant": "#680eac",
                "on-secondary-fixed": "#2d0050",
                "surface-tint": "#e0b6ff",
                "on-primary-fixed": "#2e004e",
                "secondary-fixed": "#f1dbff",
                "tertiary": "#e1b6ff",
                "secondary-container": "#6b13af",
                "outline": "#998d9e",
                "tertiary-fixed": "#f2daff",
                "on-surface": "#dbe1ff",
                "on-secondary": "#4a007f",
                "surface-container-high": "#212942",
                "on-error-container": "#ffdad6",
                "on-primary-container": "#fffdff",
                "surface-bright": "#313852",
                "secondary": "#deb7ff",
                "tertiary-fixed-dim": "#e1b6ff",
                "primary-fixed": "#f2daff",
                "on-tertiary-container": "#fffdff",
                "secondary-fixed-dim": "#deb7ff",
                "surface-container-lowest": "#050d25",
                "surface-variant": "#2c344d"
              }},
              fontFamily: {{
                "code-lg": ["JetBrains Mono"],
                "headline-xl": ["Inter"],
                "code-md": ["JetBrains Mono"],
                "body-md": ["Inter"],
                "headline-md": ["Inter"],
                "headline-sm": ["Inter"],
                "headline-lg": ["Inter"],
                "label-sm": ["JetBrains Mono"],
                "body-lg": ["Inter"],
                "label-md": ["JetBrains Mono"],
                "body-sm": ["Inter"]
              }}
            }}
          }}
        }};
      </script>
    </head>
    <body class="bg-background font-body-md text-body-md text-on-surface antialiased">
      <main class="w-full px-2 max-w-7xl mx-auto flex flex-col gap-6 pb-16 pt-2">
        <!-- Analytics Metrics & Data Visualization Bento Grid with Hover Animations -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div class="lg:col-span-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Metric 1: Total Bugs Solved -->
            <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.3)] hover:border-primary/50 cursor-default">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Total Bugs Solved</span>
                <span class="material-symbols-outlined text-primary text-[20px]">task_alt</span>
              </div>
              <div class="my-3 flex items-baseline gap-2">
                <span class="text-4xl font-bold text-on-surface">{m1_val}</span>
                <span class="text-xs text-on-surface-variant font-mono">{m1_unit}</span>
              </div>
              <div class="flex items-center justify-between pt-1">
                <span class="inline-flex items-center gap-1 text-xs text-emerald-400 font-mono">
                  <span class="material-symbols-outlined text-[14px]">task_alt</span>
                  {m1_sub}
                </span>
                <svg class="w-16 h-5 overflow-visible" fill="none" viewBox="0 0 80 24">
                  <path d="M2 18 L18 16 L34 20 L50 9 L66 12 L78 3" stroke="#9d4edd" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5"></path>
                  <circle cx="78" cy="3" fill="#e0b6ff" r="2.5"></circle>
                </svg>
              </div>
            </div>

            <!-- Metric 2: Avg Time to Aha! -->
            <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.3)] hover:border-primary/50 cursor-default">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">{m2_label}</span>
                <span class="material-symbols-outlined text-primary text-[20px]">lightbulb</span>
              </div>
              <div class="my-3 flex items-baseline gap-2">
                <span class="text-4xl font-bold text-on-surface">{m2_val}</span>
                <span class="text-xs text-on-surface-variant font-mono">{m2_unit}</span>
              </div>
              <div class="flex items-center justify-between pt-1">
                <span class="inline-flex items-center gap-1 text-xs text-primary font-mono">
                  <span class="material-symbols-outlined text-[14px]">speed</span>
                  {m2_sub}
                </span>
              </div>
            </div>

            <!-- Metric 3: Top Weak Spot Frequency -->
            <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.3)] hover:border-primary/50 cursor-default">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Weak Spot Recurrence</span>
                <span class="material-symbols-outlined text-error text-[20px]">report</span>
              </div>
              <div class="my-2">
                <div class="text-lg font-bold text-on-surface truncate">{m3_spot}</div>
                <span class="text-xs text-primary font-mono">{m3_sub}</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
                <div class="bg-primary-container h-full rounded-full" style="width: {m3_bar};"></div>
              </div>
            </div>

            <!-- Metric 4: Scope Breakdown -->
            <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.3)] hover:border-primary/50 cursor-default">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Scope Distribution</span>
                <span class="material-symbols-outlined text-tertiary text-[20px]">pie_chart</span>
              </div>
              <div class="flex items-center gap-4 my-2">
                <div class="relative w-12 h-12 shrink-0">
                  <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" fill="none" r="14" stroke="#2c344d" stroke-width="4.5"></circle>
                    <circle cx="18" cy="18" fill="none" r="14" stroke="#9d4edd" stroke-dasharray="{logic_pct * 0.88} 88" stroke-dashoffset="0" stroke-width="4.5"></circle>
                    <circle cx="18" cy="18" fill="none" r="14" stroke="#6b13af" stroke-dasharray="{runtime_pct * 0.88} 88" stroke-dashoffset="-{logic_pct * 0.88}" stroke-width="4.5"></circle>
                  </svg>
                </div>
                <div class="flex flex-col gap-1 w-full text-xs font-mono">
                  <div class="flex items-center justify-between">
                    <span class="text-on-surface-variant">Logic:</span>
                    <span class="text-on-surface font-semibold">{m4_logic}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-on-surface-variant">Runtime:</span>
                    <span class="text-on-surface font-semibold">{m4_runtime}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-on-surface-variant">State:</span>
                    <span class="text-on-surface font-semibold">{m4_state}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right Column: Bug Pattern Frequency Matrix with Hover Interactions -->
          <div class="lg:col-span-7 p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm transition-all duration-200 hover:shadow-[0_0_20px_rgba(157,78,221,0.2)]">
            <div class="flex items-center justify-between mb-4">
              <div>
                <div class="text-lg font-bold text-on-surface">Bug Pattern Frequency Matrix</div>
                <div class="text-xs text-on-surface-variant">Resolved anomalies categorised by syntactic &amp; architectural archetype</div>
              </div>
              <span class="px-3 py-1 rounded-full bg-surface-container text-on-surface-variant font-mono text-xs">
                {banner_incidents}
              </span>
            </div>

            <div class="flex flex-col gap-4 py-2">
              {matrix_content_html}
            </div>

            <div class="pt-3 flex items-center justify-between text-on-surface-variant text-xs">
              <span>Click any pattern bar to isolate matching instances in the log stream below.</span>
              <button class="text-primary hover:underline font-mono" onclick="filterByWeakSpot('All')" type="button">Reset Filter</button>
            </div>
          </div>
        </div>

        <!-- Searchable Bug History Table & Inspector Section -->
        <div class="flex flex-col gap-4">
          <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            <div class="relative flex-1 max-w-lg">
              <span class="material-symbols-outlined absolute left-3 top-2.5 text-on-surface-variant text-[20px]">search</span>
              <input class="w-full bg-surface-container-low text-on-surface text-sm pl-10 pr-4 py-2.5 rounded-xl border border-surface-container-highest focus:outline-none focus:border-primary transition-all duration-200" id="bug-search-input" oninput="handleSearch(this.value)" placeholder="Search by root cause, lesson, code snippet, or keyword..." type="text"/>
            </div>
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <button class="type-pill px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container font-semibold transition-all duration-200 hover:scale-105 hover:shadow-[0_0_16px_rgba(157,78,221,0.35)]" onclick="filterByWeakSpot('All')" type="button">All Types</button>
              <button class="type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all duration-200 hover:scale-105" onclick="filterByWeakSpot('Off-by-one')" type="button">Off-by-one</button>
              <button class="type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all duration-200 hover:scale-105" onclick="filterByWeakSpot('Null Reference')" type="button">Null Reference</button>
              <button class="type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all duration-200 hover:scale-105" onclick="filterByWeakSpot('Type Coercion')" type="button">Type Coercion</button>
            </div>
          </div>

          <!-- Developer Data Table -->
          <div class="w-full overflow-x-auto rounded-2xl bg-surface-container-lowest border border-surface-container shadow-xl">
            <table class="w-full text-left border-collapse min-w-[1000px]" id="bug-table">
              <thead>
                <tr class="bg-surface-container text-xs font-semibold text-on-surface-variant uppercase tracking-wider">
                  <th class="py-3 px-4">Bug ID</th>
                  <th class="py-3 px-4">Timestamp</th>
                  <th class="py-3 px-4">Bug Type</th>
                  <th class="py-3 px-4">Scope</th>
                  <th class="py-3 px-4">Root Cause Summary</th>
                  <th class="py-3 px-4">Key Socratic Lesson</th>
                  <th class="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-surface-container-highest text-sm">
                {table_content_html}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Inspector Modal Overlay -->
        <div class="fixed inset-0 z-50 hidden bg-surface-container-lowest/80 backdrop-blur-md flex items-center justify-center p-4" id="inspector-modal">
          <div class="relative w-full max-w-4xl bg-surface-container rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-surface-container-highest">
            <div class="px-6 py-4 bg-surface-container-high flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container font-bold text-sm">
                  <span class="material-symbols-outlined text-[18px]">psychology</span>
                </span>
                <div>
                  <div class="flex items-center gap-2">
                    <h3 class="text-lg font-bold text-on-surface" id="modal-title">Socratic Session</h3>
                    <span class="px-2.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-xs font-mono" id="modal-badge">Pattern</span>
                  </div>
                  <p class="text-xs text-on-surface-variant font-mono" id="modal-meta">Telemetry verified</p>
                </div>
              </div>
              <button class="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-bright transition-all duration-200 hover:scale-105" onclick="closeDrawer()" type="button">
                <span class="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div class="p-6 overflow-y-auto max-h-[70vh] flex flex-col gap-6 text-on-surface">
              <div class="p-4 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <div class="flex items-center gap-2 text-primary font-semibold text-sm">
                  <span class="material-symbols-outlined text-[18px]">psychology_alt</span>
                  <span>Duck Reflection Summary</span>
                </div>
                <p class="text-on-surface-variant text-sm leading-relaxed whitespace-pre-line" id="modal-reflection">
                  Session reflection details.
                </p>
              </div>

              <div class="flex flex-col gap-2">
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-mono">Original Snippet / Code Trace</span>
                <pre class="rounded-xl bg-surface-container-lowest p-4 font-mono text-xs overflow-x-auto text-primary border border-surface-container-highest" id="modal-code">// Code snippet</pre>
              </div>

              <div class="flex flex-col gap-2">
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-mono">Original Spoken Dictation</span>
                <div class="p-3 rounded-lg bg-surface-container-high text-xs text-on-surface-variant italic font-serif" id="modal-dictation">
                  Voice transcript...
                </div>
              </div>
            </div>

            <div class="px-6 py-4 bg-surface-container-high flex items-center justify-between">
              <span class="font-mono text-xs text-on-surface-variant">Status: Telemetry Synchronized</span>
              <button class="px-4 py-1.5 rounded-lg bg-surface-container-lowest hover:bg-surface-bright text-on-surface text-xs font-semibold transition-all duration-200 hover:scale-105 active:scale-95" onclick="closeDrawer()" type="button">
                Close
              </button>
            </div>
          </div>
        </div>
      </main>

      <script>
        const BUGS_DATA = {bugs_json_str};

        function filterByWeakSpot(type) {{
          const rows = document.querySelectorAll('.bug-row');
          const pills = document.querySelectorAll('.type-pill');
          
          pills.forEach(pill => {{
            const pText = pill.innerText.trim().toLowerCase();
            const tLow = type.toLowerCase();
            if (pText.includes(tLow) || tLow.includes(pText) || (type === 'All' && pText === 'all types')) {{
              pill.className = "type-pill px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container font-semibold transition-all duration-200 hover:scale-105 hover:shadow-[0_0_16px_rgba(157,78,221,0.35)]";
            }} else {{
              pill.className = "type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all duration-200 hover:scale-105";
            }}
          }});

          rows.forEach(row => {{
            const rowType = (row.getAttribute('data-type') || '').toLowerCase();
            const tLow = type.toLowerCase();
            if (type === 'All' || rowType.includes(tLow) || tLow.includes(rowType)) {{
              row.style.display = '';
            }} else {{
              row.style.display = 'none';
            }}
          }});
        }}

        function handleSearch(query) {{
          const q = query.toLowerCase().trim();
          const rows = document.querySelectorAll('.bug-row');
          rows.forEach(row => {{
            const text = row.innerText.toLowerCase();
            if (!q || text.includes(q)) {{
              row.style.display = '';
            }} else {{
              row.style.display = 'none';
            }}
          }});
        }}

        function openDrawer(codeId) {{
          const modal = document.getElementById('inspector-modal');
          const title = document.getElementById('modal-title');
          const badge = document.getElementById('modal-badge');
          const meta = document.getElementById('modal-meta');
          const reflection = document.getElementById('modal-reflection');
          const code = document.getElementById('modal-code');
          const dictation = document.getElementById('modal-dictation');
          
          const bug = BUGS_DATA[codeId];
          if (modal && bug) {{
            if (title) title.textContent = `Socratic Session: #${{codeId}}`;
            if (badge) badge.textContent = bug.type;
            if (meta) meta.textContent = `Scope: ${{bug.scope}} • Recorded: ${{bug.timestamp}}`;
            if (reflection) reflection.textContent = `Root Cause: ${{bug.root}}\n\nKey Socratic Lesson: ${{bug.lesson}}`;
            if (code) code.textContent = bug.code;
            if (dictation) dictation.textContent = `"${{bug.desc}}"`;
            modal.classList.remove('hidden');
          }}
        }}

        function closeDrawer() {{
          const modal = document.getElementById('inspector-modal');
          if (modal) modal.classList.add('hidden');
        }}
      </script>
    </body>
    </html>
    """

    components.html(analytics_html, height=1050, scrolling=True)

# --- Render Selected View ---
if active_view == "analytics":
    render_analytics()
else:
    render_socratic_studio()

# --- Footer ---
render_html_block(
    """
    <div style="margin-top: 50px; padding: 24px 0; border-top: 1px solid #171e37; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: #998d9e;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="material-symbols-outlined" style="font-size: 16px; color: #9d4edd;">psychology</span>
        <span>Duck Debugger Studio • Socratic Synthesis Engine</span>
      </div>
      <div style="display: flex; align-items: center; gap: 16px;">
        <span>Zero Hallucination Mode Active</span>
        <span>Telemetry Synchronized</span>
      </div>
    </div>
    """
)

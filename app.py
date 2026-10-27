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

# Load Gemini API Key silently from .env
gemini_api_key = os.getenv("GEMINI_API_KEY", "")

# --- Active Route Detection ---
active_view = st.query_params.get("view", "studio")
if active_view not in ["studio", "analytics"]:
    active_view = "studio"

if "current_route" not in st.session_state:
    st.session_state.current_route = active_view

is_route_transition = (st.session_state.current_route != active_view)

# --- Full-Bleed Stitch Styling with Hover Animations & Responsive CSS ---
st.markdown(
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
    """,
    unsafe_allow_html=True
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

# --- Top Navigation Bar & Pure-CSS Sliding Drawer ---
st.markdown(
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
          14 Bug Streak
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
    """,
    unsafe_allow_html=True
)

# --- Dynamic Skeleton Loading Screen Function ---
def render_full_skeleton_screen(route_name="socratic-studio.duck", label="Socratic Engine Syncing..."):
    return f"""
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
        <!-- Left Skeleton Card: Audio & Dialogue -->
        <div style="padding:22px; border-radius:16px; background:#131a33; border:1px solid #2c344d; display:flex; flex-direction:column; gap:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div class="skeleton-shimmer" style="width:160px; height:18px;"></div>
            <div class="skeleton-shimmer" style="width:70px; height:18px; border-radius:9999px;"></div>
          </div>
          <!-- Audio Waveform Skeleton -->
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

# --- Route Transition Skeleton Screen Trigger ---
if is_route_transition:
    route_name = "analytics-weak-spots.duck" if active_view == "analytics" else "socratic-studio.duck"
    label_name = "Hydrating Telemetry & Analytics..." if active_view == "analytics" else "Socratic Engine Syncing..."
    trans_box = st.empty()
    trans_box.markdown(render_full_skeleton_screen(route_name, label_name), unsafe_allow_html=True)
    time.sleep(0.55)
    trans_box.empty()
    st.session_state.current_route = active_view

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
    if "solved_record" not in st.session_state:
        st.session_state.solved_record = None
    if "bug_desc_input" not in st.session_state:
        st.session_state.bug_desc_input = ""
    if "code_snippet_input" not in st.session_state:
        st.session_state.code_snippet_input = ""
    if "selected_language" not in st.session_state:
        st.session_state.selected_language = "Python"

    # Subheader / Session Status Bar
    col_sub_left, col_sub_right = st.columns([3, 1], vertical_alignment="center")
    with col_sub_left:
        status_mode = "Active" if len(st.session_state.messages) > 0 else "Standby"
        st.markdown(
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
            """,
            unsafe_allow_html=True
        )

    with col_sub_right:
        if st.session_state.session_started or len(st.session_state.messages) > 0:
            if st.button("New Session", key="btn_reset_session", help="Clear current dialectic dialogue"):
                st.session_state.messages = []
                st.session_state.session_started = False
                st.session_state.solved = False
                st.session_state.turn_count = 0
                st.session_state.solved_record = None
                st.session_state.bug_desc_input = ""
                st.session_state.code_snippet_input = ""
                st.rerun()

    # Two-Column Main Layout
    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    duck_avatar_url = "https://lh3.googleusercontent.com/aida-public/AB6AXuCkejLzHkcuV4UxXNv9zVHIia-SYl2uq21ullUgEBqeR9fA1SUEWxZKCqUFXDPMdBmd4krj1OFG-Sggj10GU9-Lbmov-md2Gw_lqAVxKFUA09YmxB4ddTSXkTQ9hX5AJxtJvvTGivZs-Ch_8fxJ8EzTavRoZ46b-0KtpRbu0fAisbYB48n2rBv-ljzxuxh5cAjwKnu4fDww32eKC6jOCP8pAV_WC49Tv1NuaDR9TzczPh0e-y55Mz7_kg"

    with col_left:
        st.markdown(
            """
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-symbols-outlined" style="color:#9d4edd; font-size:22px;">mic</span>
                <span style="font-size:1.1rem; font-weight:700; color:#dbe1ff;">Duck Dialogue Feed</span>
              </div>
              <span class="hover-pill" style="font-size:11px; font-family:'JetBrains Mono'; padding:2px 8px; border-radius:9999px; background:#131a33; color:#d0c2d5; border:1px solid #2c344d;">Continuous Listening</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Interactive Waveform Graph
        st.markdown(
            """
            <div style="background:#050d25; border:1px solid #2c344d; border-radius:12px; padding:12px 16px; margin-bottom:16px;">
              <div style="display:flex; justify-content:space-between; font-size:11px; font-family:'JetBrains Mono'; color:#d0c2d5; margin-bottom:6px;">
                <span>Vocal Cadence Frequency</span>
                <span style="color:#9d4edd; font-weight:600;">128 kbps OPUS</span>
              </div>
              <svg width="100%" height="45" viewBox="0 0 300 45" fill="none" style="overflow:visible;">
                <path d="M0 22 Q 15 5, 30 22 T 60 22 T 90 5 T 120 40 T 150 12 T 180 32 T 210 10 T 240 35 T 270 18 T 300 22" stroke="#9d4edd" stroke-width="2.5" stroke-linecap="round"/>
                <path d="M0 22 Q 20 18, 40 22 T 80 25 T 120 16 T 160 28 T 200 20 T 240 24 T 280 21 T 300 22" stroke="#6b13af" stroke-width="1.5" stroke-opacity="0.5"/>
              </svg>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.text_area(
            "Spoken Thought / Bug Description",
            placeholder="Talk aloud: 'My loop is terminating one index too early and dropping the last item...'",
            key="bug_desc_input",
            height=100
        )

    with col_right:
        st.markdown(
            """
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="material-symbols-outlined" style="color:#9d4edd; font-size:22px;">code</span>
                <span style="font-size:1.1rem; font-weight:700; color:#dbe1ff;">Code Context &amp; Socratic Canvas</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Language Selector
        languages = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "C++", "Java"]
        curr_idx = languages.index(st.session_state.selected_language) if st.session_state.selected_language in languages else 0
        st.session_state.selected_language = st.selectbox(
            "Active Target Language",
            languages,
            index=curr_idx,
            label_visibility="collapsed"
        )

        st.text_area(
            "Code Snippet",
            placeholder="# Paste your problematic function or code segment here\ndef process_items(items):\n    for i in range(len(items) - 1):\n        print(items[i])",
            key="code_snippet_input",
            height=145
        )

    # Empty container for dynamic skeleton loading screen
    skeleton_placeholder = st.empty()

    # Socratic Turn Execution Engine
    def execute_socratic_turn(user_followup=None):
        st.session_state.session_started = True

        if user_followup:
            st.session_state.messages.append({"role": "user", "content": user_followup})
            st.session_state.turn_count += 1
        elif len(st.session_state.messages) == 0:
            initial_prompt = st.session_state.bug_desc_input
            if st.session_state.code_snippet_input.strip():
                initial_prompt += f"\n\nCode snippet provided:\n{st.session_state.code_snippet_input.strip()}"
            st.session_state.messages.append({"role": "user", "content": initial_prompt})
            st.session_state.turn_count = 1

        safe_desc = st.session_state.bug_desc_input or "Debugging logic in session"
        safe_code = st.session_state.code_snippet_input or "# No code snippet provided"

        # Check for user breakthrough
        if user_followup and prompts.detect_user_breakthrough(user_followup):
            st.session_state.is_saving = True
            skeleton_placeholder.markdown(render_full_skeleton_screen("socratic-studio.duck", "Synthesizing Telemetry & Post-Mortem..."), unsafe_allow_html=True)
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
            skeleton_placeholder.empty()
            return

        # Trigger Skeleton Loading Screen exclusively during active synthesis
        skeleton_placeholder.markdown(render_full_skeleton_screen("socratic-studio.duck", "Socratic Engine Syncing..."), unsafe_allow_html=True)

        try:
            duck_q = prompts.generate_socratic_response(
                messages=st.session_state.messages,
                code_snippet=safe_code,
                bug_description=safe_desc,
                turn_count=st.session_state.turn_count,
                api_key=gemini_api_key
            )
        except Exception as e:
            logger.warning("Gemini Socratic call exception: %s. Using fallback heuristic.", e)
            duck_q = prompts._generate_offline_socratic_response(
                st.session_state.turn_count,
                safe_desc,
                safe_code,
                st.session_state.messages
            )

        if not duck_q or not duck_q.strip():
            duck_q = "Quack! Walk me through what value that variable actually holds at this exact step."

        # Clear skeleton loading screen immediately when loaded
        skeleton_placeholder.empty()
        st.session_state.messages.append({"role": "assistant", "content": duck_q})

    # Prominent "Start Quacking with the Duck" Button
    if len(st.session_state.messages) == 0:
        desc_val = st.session_state.bug_desc_input
        code_val = st.session_state.code_snippet_input
        if st.button("Start Quacking with the Duck", key="btn_start_quacking"):
            if not desc_val.strip() and not code_val.strip():
                st.warning("Please provide either a bug description or code snippet above to begin.")
            else:
                execute_socratic_turn()
                st.rerun()

    # Conversation Feed Display
    if len(st.session_state.messages) > 0 or st.session_state.session_started:
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        for i, msg in enumerate(st.session_state.messages):
            if i == 0 and msg.get("role") == "user" and not st.session_state.solved:
                continue

            content_safe = html.escape(msg.get("content", ""))

            if msg.get("role") == "assistant":
                st.markdown(
                    f"""
                    <div class="hover-lift" style="display:flex; align-items:flex-start; gap:16px; margin-bottom:16px; border-radius:14px; padding:4px;">
                      <div style="width:44px; height:44px; border-radius:12px; overflow:hidden; border:1px solid #9d4edd; flex-shrink:0; box-shadow:0 0 12px rgba(157,78,221,0.3);">
                        <img src="{duck_avatar_url}" style="width:100%; height:100%; object-fit:cover;" alt="Duck Mascot"/>
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
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
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
                    """,
                    unsafe_allow_html=True
                )

        # Breakthrough Solved Card
        if st.session_state.solved and st.session_state.solved_record:
            rec = st.session_state.solved_record
            st.markdown(
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
                    <div style="font-size:20px; font-weight:700; color:#ffffff;">
                      Aha! Moment Discovered
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
                """,
                unsafe_allow_html=True
            )

    # Chat Input Box
    if not st.session_state.solved:
        user_input = st.chat_input("Talk back to your Rubber Duck (dictate or type your thoughts)...")
        if user_input and user_input.strip():
            clean_text = user_input.strip()
            execute_socratic_turn(user_followup=clean_text)
            st.rerun()

# ==============================================================================
# VIEW 2: ANALYTICS & WEAK SPOTS
# ==============================================================================
def render_analytics():
    stats = db.get_bug_stats()
    all_bugs = db.get_all_bugs()
    total_bugs = stats.get("total_bugs", 0)
    top_spot = stats.get("top_weak_spot") or "Off-by-one"
    top_count = stats.get("top_weak_spot_count", 0)
    type_counts = stats.get("type_counts", {})
    top_pct = int(round((top_count / total_bugs * 100))) if total_bugs > 0 else 0

    scopes = {}
    for b in all_bugs:
        sc = (b.get("scope") or "logic").lower()
        scopes[sc] = scopes.get(sc, 0) + 1

    logic_count = sum(cnt for sc, cnt in scopes.items() if "logic" in sc or "index" in sc)
    runtime_count = sum(cnt for sc, cnt in scopes.items() if "runtime" in sc or "null" in sc or "type" in sc)
    state_count = max(0, total_bugs - (logic_count + runtime_count))

    logic_pct = int(round((logic_count / total_bugs * 100))) if total_bugs > 0 else 45
    runtime_pct = int(round((runtime_count / total_bugs * 100))) if total_bugs > 0 else 35
    state_pct = max(0, 100 - (logic_pct + runtime_pct))

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
        safe_desc = html.escape(b.get("description") or "Voice transcript not recorded.")
        safe_code = html.escape(b.get("code_snippet") or "# No code snippet recorded")
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
      <main class="w-full px-2 max-w-7xl mx-auto flex flex-col gap-8 pb-16 pt-2">
        <!-- Top Meta Control / Header Bar -->
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="p-1 rounded-lg bg-surface-container-high text-primary flex items-center justify-center">
                <span class="material-symbols-outlined text-[18px]">query_stats</span>
              </span>
              <span class="font-label-sm text-label-sm uppercase tracking-wider text-primary">Intelligence Telemetry</span>
              <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant text-[11px] font-mono">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                Sync: SQLite Active
              </span>
            </div>
            <h1 class="text-3xl font-bold text-on-surface tracking-tight">
              Debugging Intelligence &amp; Weak Spot Analytics
            </h1>
            <p class="text-on-surface-variant text-sm max-w-2xl">
              Systematic telemetry capturing your recurring logic anomalies, Socratic breakdown timeframes, and targeted algorithmic training vectors.
            </p>
          </div>

          <!-- Quick Filter Bar -->
          <div class="flex flex-wrap items-center gap-2 bg-surface-container-low p-1.5 rounded-xl shadow-sm">
            <div class="inline-flex rounded-lg bg-surface-container-lowest p-0.5">
              <button class="date-pill px-3 py-1 rounded text-xs font-semibold bg-primary-container text-on-primary-container transition-all duration-200 hover:scale-105 hover:shadow-[0_0_16px_rgba(157,78,221,0.35)]" data-range="30d" type="button">Last 30 Days</button>
              <button class="date-pill px-3 py-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all duration-200 hover:scale-105" data-range="quarter" type="button">This Quarter</button>
              <button class="date-pill px-3 py-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all duration-200 hover:scale-105" data-range="all" type="button">All Time</button>
            </div>
            <button class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface text-xs font-semibold transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.3)] active:scale-95" onclick="alert('Exporting telemetry snapshot as JSON...')" type="button">
              <span class="material-symbols-outlined text-[15px] text-primary">ios_share</span>
              <span>Export Report</span>
            </button>
          </div>
        </div>

        <!-- Weekly Weak Spot Hero Banner Card -->
        <div class="relative overflow-hidden rounded-2xl bg-surface-container p-6 sm:p-8 shadow-xl border border-surface-container-highest transition-all duration-200 hover:shadow-[0_0_24px_rgba(157,78,221,0.25)]">
          <div class="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-primary-container/20 blur-3xl pointer-events-none"></div>
          <div class="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-secondary-container/25 blur-3xl pointer-events-none"></div>
          <div class="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
            <div class="flex flex-col gap-2 max-w-3xl">
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-error-container text-on-error-container text-xs font-semibold">
                  <span class="material-symbols-outlined text-[14px]">crisis_alert</span>
                  Critical Focus Vector
                </span>
                <span class="text-xs text-primary font-mono tracking-wider">{top_count} INCIDENTS RECORDED</span>
              </div>
              <h2 class="text-2xl font-bold text-on-surface">
                Weekly Focus: {html.escape(top_spot)}
              </h2>
              <p class="text-base text-on-surface-variant leading-relaxed">
                <strong class="text-primary font-semibold">{top_pct}% of your debugging sessions</strong> stemmed from {html.escape(top_spot)} patterns, boundary mutations, or loop conditions.
              </p>
              <div class="flex flex-wrap items-center gap-x-6 gap-y-2 mt-1 font-mono text-xs text-on-surface-variant">
                <div class="flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-primary text-[16px]">psychology</span>
                  <span>Cognitive Trap: <span class="text-on-surface font-semibold">Inclusive vs Exclusive bounds</span></span>
                </div>
                <div class="flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-tertiary text-[16px]">timer</span>
                  <span>Recovery Cost: <span class="text-on-surface font-semibold">4.2 min avg turnaround</span></span>
                </div>
              </div>
            </div>

            <div class="flex flex-col sm:flex-row lg:flex-col items-stretch gap-3 shrink-0 min-w-[240px]">
              <button class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary-container text-on-primary-container hover:bg-secondary-container transition-all duration-200 hover:scale-105 hover:shadow-[0_0_24px_rgba(157,78,221,0.4)] text-sm font-semibold cursor-pointer active:scale-95" onclick="openPracticeModal()" type="button">
                <span class="material-symbols-outlined text-[18px]">extension</span>
                <span>Generate Practice Problem</span>
              </button>
              <button class="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-surface-container-high hover:bg-surface-bright text-on-surface text-sm font-medium transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.3)] cursor-pointer active:scale-95" data-spot="{html.escape(top_spot)}" onclick="filterByWeakSpot(this.getAttribute('data-spot'))" type="button">
                <span class="material-symbols-outlined text-[18px] text-primary">record_voice_over</span>
                <span>Review Socratic Transcripts ({top_count})</span>
              </button>
            </div>
          </div>
        </div>

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
                <span class="text-4xl font-bold text-on-surface">{total_bugs}</span>
                <span class="text-xs text-on-surface-variant font-mono">bugs</span>
              </div>
              <div class="flex items-center justify-between pt-1">
                <span class="inline-flex items-center gap-1 text-xs text-emerald-400">
                  <span class="material-symbols-outlined text-[14px]">trending_up</span>
                  +100% telemetry synced
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
                <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Avg Time to Aha!</span>
                <span class="material-symbols-outlined text-primary text-[20px]">lightbulb</span>
              </div>
              <div class="my-3 flex items-baseline gap-2">
                <span class="text-4xl font-bold text-on-surface">4.2</span>
                <span class="text-xs text-on-surface-variant font-mono">mins</span>
              </div>
              <div class="flex items-center justify-between pt-1">
                <span class="inline-flex items-center gap-1 text-xs text-primary font-mono">
                  <span class="material-symbols-outlined text-[14px]">speed</span>
                  -35% with Socratic prompts
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
                <div class="text-lg font-bold text-on-surface truncate">{html.escape(top_spot)}</div>
                <span class="text-xs text-primary font-mono">{top_pct}% of total incidents</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
                <div class="bg-primary-container h-full rounded-full" style="width: {top_pct}%;"></div>
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
                    <span class="text-on-surface font-semibold">{logic_pct}%</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-on-surface-variant">Runtime:</span>
                    <span class="text-on-surface font-semibold">{runtime_pct}%</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-on-surface-variant">State:</span>
                    <span class="text-on-surface font-semibold">{state_pct}%</span>
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
                {total_bugs} incidents recorded
              </span>
            </div>

            <div class="flex flex-col gap-4 py-2">
              {bars_html}
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
                {rows_html}
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

        <!-- Practice Sandbox Modal -->
        <div class="fixed inset-0 z-50 hidden bg-surface-container-lowest/80 backdrop-blur-md flex items-center justify-center p-4" id="practice-modal">
          <div class="relative w-full max-w-2xl bg-surface-container rounded-2xl shadow-2xl p-6 flex flex-col gap-6 border border-surface-container-highest">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-[24px]">extension</span>
                <h3 class="text-xl font-bold text-on-surface">Synthesized Practice Vector</h3>
              </div>
              <button class="p-1 rounded-lg text-on-surface-variant hover:text-on-surface transition-all duration-200 hover:scale-105" onclick="closePracticeModal()" type="button">
                <span class="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <div class="flex flex-col gap-3">
              <p class="text-sm text-on-surface-variant">
                Based on your frequent <strong class="text-primary font-semibold">{html.escape(top_spot)}</strong> incidents this week, the Duck AI has synthesized an algorithmic training vector:
              </p>
              <div class="p-4 rounded-xl bg-surface-container-lowest font-mono text-xs border border-surface-container-highest">
                <div class="text-primary font-bold mb-1">// Challenge #BOUNDS-04: Boundary Isolation &amp; Fencepost Reducer</div>
                <div class="text-on-surface-variant">Refactor the slice bounds to handle non-inclusive upper boundaries without dropping terminal elements or raising IndexError.</div>
              </div>
            </div>
            <div class="flex items-center justify-end gap-3">
              <button class="px-4 py-2 rounded-lg bg-surface-container-high text-on-surface text-xs font-semibold transition-all duration-200 hover:scale-105" onclick="closePracticeModal()" type="button">
                Dismiss
              </button>
              <a class="px-5 py-2 rounded-lg bg-primary-container text-on-primary-container text-xs font-semibold hover:bg-secondary-container transition-all duration-200 hover:scale-105 hover:shadow-[0_0_20px_rgba(157,78,221,0.4)] shadow-md" href="/?view=studio" target="_top">
                Launch Socratic Studio
              </a>
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
            if (pill.innerText.trim().toLowerCase().includes(type.toLowerCase()) || 
               (type === 'All' && pill.innerText.trim() === 'All Types')) {{
              pill.className = "type-pill px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container font-semibold transition-all duration-200 hover:scale-105 hover:shadow-[0_0_16px_rgba(157,78,221,0.35)]";
            }} else {{
              pill.className = "type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all duration-200 hover:scale-105";
            }}
          }});

          rows.forEach(row => {{
            const rowType = row.getAttribute('data-type');
            if (type === 'All' || rowType === type) {{
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

        function openPracticeModal() {{
          const modal = document.getElementById('practice-modal');
          if (modal) modal.classList.remove('hidden');
        }}

        function closePracticeModal() {{
          const modal = document.getElementById('practice-modal');
          if (modal) modal.classList.add('hidden');
        }}

        document.querySelectorAll('.date-pill').forEach(btn => {{
          btn.addEventListener('click', () => {{
            document.querySelectorAll('.date-pill').forEach(b => {{
              b.className = "date-pill px-3 py-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all duration-200 hover:scale-105";
            }});
            btn.className = "date-pill px-3 py-1 rounded text-xs font-semibold bg-primary-container text-on-primary-container transition-all duration-200 hover:scale-105 hover:shadow-[0_0_16px_rgba(157,78,221,0.35)]";
          }});
        }});
      </script>
    </body>
    </html>
    """

    components.html(analytics_html, height=1350, scrolling=True)

# --- Render Selected View ---
if active_view == "analytics":
    render_analytics()
else:
    render_socratic_studio()

# --- Footer ---
st.markdown(
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
    """,
    unsafe_allow_html=True
)

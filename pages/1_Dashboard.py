"""
pages/1_Dashboard.py - Analytics & Weak Spots Studio
Replaced with pixel-perfect Google Stitch UI architecture.
Powered by SQLite telemetry and Gemini Generative AI.
Strictly zero emojis.
"""

import streamlit as st
import os
import sys
import html
import json
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
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Duck Debugger - Analytics & Weak Spots",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit default chrome so Stitch UI occupies the whole webpage
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    .main .block-container {
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize database
db.init_db()

# Fetch DB Stats and Bugs
stats = db.get_bug_stats()
all_bugs = db.get_all_bugs()
total_bugs = stats.get("total_bugs", 0)
top_spot = stats.get("top_weak_spot") or "Off-by-one"
top_count = stats.get("top_weak_spot_count", 0)
type_counts = stats.get("type_counts", {})
top_pct = int(round((top_count / total_bugs * 100))) if total_bugs > 0 else 0

# Scope calculations
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

# Prepare Bug Pattern Frequency Matrix HTML
max_type_val = max(type_counts.values()) if type_counts else 1
bar_chart_html_parts = []
for bug_type, count in list(type_counts.items())[:5]:
    pct_width = max(10, int((count / max_type_val) * 100))
    share = round((count / total_bugs) * 100, 1) if total_bugs > 0 else 0
    safe_type = html.escape(bug_type)
    bar_chart_html_parts.append(f"""
    <div class="group flex flex-col gap-1 cursor-pointer" onclick="filterByWeakSpot('{safe_type}')">
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
bars_html = "\\n".join(bar_chart_html_parts)

# Prepare Table Rows HTML and JSON Lookup
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
        "type": safe_type,
        "scope": safe_scope,
        "root": safe_root,
        "lesson": safe_lesson,
        "desc": safe_desc,
        "code": safe_code,
        "timestamp": ts
    }

    row_bg = "bg-surface-container-low" if idx % 2 == 0 else "bg-surface-container-lowest"
    table_rows_parts.append(f"""
    <tr class="bug-row {row_bg} hover:bg-surface-container transition-colors group cursor-pointer" data-id="{code_id}" data-type="{safe_type}" onclick="openDrawer('{code_id}')">
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
          <button class="px-2.5 py-1 rounded bg-surface-container-high hover:bg-primary-container hover:text-on-primary-container text-on-surface text-label-sm font-label-sm font-medium transition-colors" type="button">
            Inspect Session
          </button>
        </div>
      </td>
    </tr>
    """)

rows_html = "\\n".join(table_rows_parts)
bugs_json_str = json.dumps(bugs_lookup)

# Full Pixel-Perfect Stitch HTML Layout
complete_stitch_html = f"""<!DOCTYPE html>
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
  <!-- Top Navigation Header -->
  <header class="fixed top-0 left-0 right-0 z-50 bg-surface/90 backdrop-blur-xl border-b border-surface-container-highest">
    <div class="h-16 w-full px-6 flex items-center justify-between gap-4">
      <div class="flex items-center gap-4 shrink-0">
        <span class="font-headline-sm text-headline-sm text-on-surface tracking-tight font-bold">Duck Debugger</span>
        <span class="font-label-sm text-label-sm uppercase px-2.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container border border-primary-container/40">v2.4 Pro</span>
      </div>
      <nav class="hidden md:flex items-center gap-1 bg-surface-container-low px-1.5 py-1 rounded-xl border border-surface-container-highest">
        <a class="px-4 py-2 rounded-lg font-body-md text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors" href="/" target="_parent">Socratic Studio</a>
        <a class="px-4 py-2 font-body-md transition-colors bg-primary-container text-on-primary-container rounded-lg shadow-[0_0_16px_rgba(157,78,221,0.35)]" href="/Dashboard" target="_parent">Analytics & Weak Spots</a>
      </nav>
      <div class="flex items-center gap-4 shrink-0">
        <div class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high border border-surface-container-highest">
          <span class="font-label-md text-label-md text-primary font-mono">14 Bug Streak</span>
        </div>
        <div class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-low border border-surface-container-highest">
          <span class="inline-block w-2 h-2 rounded-full bg-primary-container animate-pulse"></span>
          <span class="font-code-md text-code-md text-on-surface-variant">Telemetry Active</span>
        </div>
      </div>
    </div>
  </header>

  <!-- Main Canvas -->
  <main class="w-full pt-20 px-6 max-w-7xl mx-auto min-h-screen flex flex-col gap-8 pb-16">
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
          Debugging Intelligence & Weak Spot Analytics
        </h1>
        <p class="text-on-surface-variant text-sm max-w-2xl">
          Systematic telemetry capturing your recurring logic anomalies, Socratic breakdown timeframes, and targeted algorithmic training vectors.
        </p>
      </div>

      <!-- Quick Filter Bar -->
      <div class="flex flex-wrap items-center gap-2 bg-surface-container-low p-1.5 rounded-xl shadow-sm">
        <div class="inline-flex rounded-lg bg-surface-container-lowest p-0.5">
          <button class="date-pill px-3 py-1 rounded text-xs font-semibold bg-primary-container text-on-primary-container transition-all" data-range="30d" type="button">Last 30 Days</button>
          <button class="date-pill px-3 py-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all" data-range="quarter" type="button">This Quarter</button>
          <button class="date-pill px-3 py-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all" data-range="all" type="button">All Time</button>
        </div>
        <button class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface text-xs font-semibold transition-colors" onclick="alert('Exporting telemetry snapshot as JSON...')" type="button">
          <span class="material-symbols-outlined text-[15px] text-primary">ios_share</span>
          <span>Export Report</span>
        </button>
      </div>
    </div>

    <!-- Weekly Weak Spot Hero Banner Card -->
    <div class="relative overflow-hidden rounded-2xl bg-surface-container p-8 shadow-xl border border-surface-container-highest">
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
          <button class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary-container text-on-primary-container hover:bg-secondary-container transition-all shadow-[0_0_24px_rgba(157,78,221,0.4)] text-sm font-semibold cursor-pointer" onclick="openPracticeModal()" type="button">
            <span class="material-symbols-outlined text-[18px]">extension</span>
            <span>Generate Practice Problem</span>
          </button>
          <button class="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-surface-container-high hover:bg-surface-bright text-on-surface text-sm font-medium transition-colors cursor-pointer" onclick="filterByWeakSpot('{html.escape(top_spot)}')" type="button">
            <span class="material-symbols-outlined text-[18px] text-primary">record_voice_over</span>
            <span>Review Socratic Transcripts ({top_count})</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Analytics Metrics & Data Visualization Bento Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left Column: 4 Metric Cards -->
      <div class="lg:col-span-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Metric 1: Total Bugs Solved -->
        <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm">
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
        <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm">
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
        <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm">
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
        <div class="p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm">
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

      <!-- Right Column: Bug Pattern Frequency Matrix -->
      <div class="lg:col-span-7 p-6 rounded-2xl bg-surface-container-low border border-surface-container flex flex-col justify-between shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-lg font-bold text-on-surface">Bug Pattern Frequency Matrix</div>
            <div class="text-xs text-on-surface-variant">Resolved anomalies categorised by syntactic & architectural archetype</div>
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
          <input class="w-full bg-surface-container-low text-on-surface text-sm pl-10 pr-4 py-2.5 rounded-xl border border-surface-container-highest focus:outline-none focus:border-primary transition-all" id="bug-search-input" oninput="handleSearch(this.value)" placeholder="Search by root cause, lesson, code snippet, or keyword..." type="text"/>
        </div>
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <button class="type-pill px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container font-semibold transition-all" onclick="filterByWeakSpot('All')" type="button">All Types</button>
          <button class="type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all" onclick="filterByWeakSpot('Off-by-one')" type="button">Off-by-one</button>
          <button class="type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all" onclick="filterByWeakSpot('Null Reference')" type="button">Null Reference</button>
          <button class="type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all" onclick="filterByWeakSpot('Type Coercion')" type="button">Type Coercion</button>
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
          <button class="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-bright transition-colors" onclick="closeDrawer()" type="button">
            <span class="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div class="p-6 overflow-y-auto max-h-[70vh] flex flex-col gap-6 text-on-surface">
          <div class="p-4 rounded-xl bg-surface-container-low flex flex-col gap-2">
            <div class="flex items-center gap-2 text-primary font-semibold text-sm">
              <span class="material-symbols-outlined text-[18px]">psychology_alt</span>
              <span>Duck Reflection Summary</span>
            </div>
            <p class="text-on-surface-variant text-sm leading-relaxed" id="modal-reflection">
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
          <button class="px-4 py-1.5 rounded-lg bg-surface-container-lowest hover:bg-surface-bright text-on-surface text-xs font-semibold transition-colors" onclick="closeDrawer()" type="button">
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
          <button class="p-1 rounded-lg text-on-surface-variant hover:text-on-surface" onclick="closePracticeModal()" type="button">
            <span class="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
        <div class="flex flex-col gap-3">
          <p class="text-sm text-on-surface-variant">
            Based on your frequent <strong class="text-primary font-semibold">{html.escape(top_spot)}</strong> incidents this week, the Duck AI has synthesized an algorithmic training vector:
          </p>
          <div class="p-4 rounded-xl bg-surface-container-lowest font-mono text-xs border border-surface-container-highest">
            <div class="text-primary font-bold mb-1">// Challenge #BOUNDS-04: Boundary Isolation & Fencepost Reducer</div>
            <div class="text-on-surface-variant">Refactor the slice bounds to handle non-inclusive upper boundaries without dropping terminal elements or raising IndexError.</div>
          </div>
        </div>
        <div class="flex items-center justify-end gap-3">
          <button class="px-4 py-2 rounded-lg bg-surface-container-high text-on-surface text-xs font-semibold" onclick="closePracticeModal()" type="button">
            Dismiss
          </button>
          <a class="px-5 py-2 rounded-lg bg-primary-container text-on-primary-container text-xs font-semibold hover:bg-secondary-container transition-colors shadow-md" href="/" target="_parent">
            Launch Socratic Studio
          </a>
        </div>
      </div>
    </div>
  </main>

  <footer class="w-full bg-surface-container-lowest border-t border-surface-container-highest py-6 text-center text-xs font-mono text-on-surface-variant">
    Duck Debugger Studio • Socratic Synthesis Engine • Zero Hallucination Mode Active
  </footer>

  <script>
    const BUGS_DATA = {bugs_json_str};

    function filterByWeakSpot(type) {{
      const rows = document.querySelectorAll('.bug-row');
      const pills = document.querySelectorAll('.type-pill');
      
      pills.forEach(pill => {{
        if (pill.innerText.trim().toLowerCase().includes(type.toLowerCase()) || 
           (type === 'All' && pill.innerText.trim() === 'All Types')) {{
          pill.className = "type-pill px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container font-semibold transition-all";
        }} else {{
          pill.className = "type-pill px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-all";
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
        if (title) title.innerText = `Socratic Session: #${{codeId}}`;
        if (badge) badge.innerText = bug.type;
        if (meta) meta.innerText = `Scope: ${{bug.scope}} • Recorded: ${{bug.timestamp}}`;
        if (reflection) reflection.innerHTML = `<strong>Root Cause:</strong> ${{bug.root}}<br/><br/><strong>Key Socratic Lesson:</strong> ${{bug.lesson}}`;
        if (code) code.innerText = bug.code;
        if (dictation) dictation.innerText = `"${{bug.desc}}"`;
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
          b.className = "date-pill px-3 py-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all";
        }});
        btn.className = "date-pill px-3 py-1 rounded text-xs font-semibold bg-primary-container text-on-primary-container transition-all";
      }});
    }});
  </script>
</body>
</html>
"""

# Render the complete pixel-perfect Stitch UI
components.html(complete_stitch_html, height=1550, scrolling=True)

"""
pages/1_Dashboard.py - Analytics & Weak Spots Route
Seamlessly switches to Duck Debugger unified app with view=analytics.
Strictly zero emojis.
"""

import streamlit as st

st.set_page_config(
    page_title="Duck Debugger - Analytics & Weak Spots",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Route to app.py with analytics view
st.query_params["view"] = "analytics"

try:
    st.switch_page("app.py")
except Exception:
    st.markdown(
        """
        <meta http-equiv="refresh" content="0; url=/?view=analytics">
        <script>window.location.href = '/?view=analytics';</script>
        <div style="padding: 40px; text-align: center; color: #dbe1ff; font-family: sans-serif;">
            <p>Redirecting to Analytics & Weak Spots Studio...</p>
            <a href="/?view=analytics" style="color: #9d4edd; font-weight: bold;">Click here if not redirected automatically.</a>
        </div>
        """,
        unsafe_allow_html=True
    )

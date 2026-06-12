"""
Record Cataloging Dashboard — Streamlit app.

Run locally:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import time
import base64
import textwrap

from db_client import get_db
import record_store
import threading
from google.api_core.exceptions import ResourceExhausted

# ---------------------------------------------------------------------------
# Logo Processing (Base64 for inline embedding)
# ---------------------------------------------------------------------------
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""

LOGO_BASE64 = get_base64_of_bin_file('logo.png')
BG_BASE64 = get_base64_of_bin_file('background_pattern.png')

# Header Logos (Responsive)
LOGO_HTML_DESKTOP_BRAND = f'<div class="brand-logo-desktop"><img src="data:image/png;base64,{LOGO_BASE64}" style="width: 180px;"></div>' if LOGO_BASE64 else ""
LOGO_HTML_MOBILE_INLINE = f'<img class="mobile-logo-inline" src="data:image/png;base64,{LOGO_BASE64}" style="height: 35px; margin-left: 10px; vertical-align: middle;">' if LOGO_BASE64 else ""

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="אוסף התקליטים של ירון",
    layout="wide",
    initial_sidebar_state="expanded", # Ensure sidebar is visibly open by default
)

# Dense AirBnB UX, Centered Buttons, Clean Header
st.markdown(
    textwrap.dedent("""
    <link rel="manifest" href="/static/manifest.json">
    <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
          .then(reg => console.log('Service Worker registered', reg))
          .catch(err => console.error('Service Worker registration failed', err));
      });
    }
    </script>
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

    /* CSS Variables for Cool Pastel Blue Theme */
    :root {
        --color-bg-main: #F4F8FB;        /* Soft cool white */
        --color-bg-surface: #FFFFFF;     /* Pure White */
        --color-primary: #9DBCE3;        /* Pastel Light Blue */
        --color-primary-hover: #8AADD8;  /* Deeper pastel blue */
        --color-text-main: #3E4B59;      /* Cool charcoal gray */
        --color-text-muted: #8292A1;     /* Cool muted gray */
        --color-border: #E2EAF1;         /* Soft blue-gray */
        --shadow-sm: 0 1px 2px 0 rgba(115, 130, 140, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(115, 130, 140, 0.1), 0 2px 4px -1px rgba(115, 130, 140, 0.06);
        --shadow-hover: 0 10px 15px -3px rgba(115, 130, 140, 0.15), 0 4px 6px -2px rgba(115, 130, 140, 0.1);
        --radius-md: 16px;
        --radius-lg: 16px;
        --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Base Styling */
    body {
        font-family: 'Assistant', sans-serif !important;
        background-color: var(--color-bg-main) !important;
        color: var(--color-text-main);
    }
    
    .stApp {
        background-color: var(--color-bg-main) !important;
    }

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(244, 248, 251, 0.75) !important;
        backdrop-filter: blur(16px) !important;
        border-left: 1px solid rgba(226, 234, 241, 0.5) !important;
    }
    [data-testid="stSidebar"] > div {
        background: transparent !important;
    }

    /* Hide Unwanted Streamlit Elements safely, but keep Header for sidebar toggle */
    header { background-color: transparent !important; box-shadow: none !important; }
    footer { display: none !important; }
    [class^="viewerBadge"], [data-testid="stActionElements"], [data-testid="MainMenu"], .stAppDeployButton {
        display: none !important;
    }

    /* Maximize Density, adjust top padding to prevent header cut-off */
    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 0rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
        direction: rtl !important;
    }

    /* Typography Directions */
    h1, h2, h3, h4, p, label, .stMarkdown {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
        color: var(--color-text-main);
    }

    /* Header Typography Adjustment with Premium Gradient */
    .main-header {
        text-align: center;
        margin-bottom: 0;
    }
    .main-header h1 {
        font-family: 'Outfit', 'Assistant', sans-serif !important;
        font-size: 2.3rem !important;
        line-height: 1.1;
        font-weight: 900 !important;
        background: linear-gradient(135deg, #7199c7 0%, #a4c4eb 100%);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin-bottom: 0 !important;
        letter-spacing: -0.02em !important;
        text-align: center;
    }

    /* Brand Row (Desktop Flex) */
    div.element-container:has(#brand-row-anchor) { display: none !important; }
    
    .brand-row-container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        margin-bottom: 0px;
        direction: ltr !important; /* Force LTR for the header row to put logo on the left */
    }
    
    .brand-logo-desktop {
        flex: 0 0 180px;
        text-align: left;
    }
    
    .brand-row-center {
        flex: 1;
        text-align: center;
        direction: rtl !important;
    }
    
    .brand-spacer {
        flex: 0 0 180px;
    }

    /* Logo Visibility & Mobile Inline */
    .mobile-logo-inline {
        display: none;
    }

    @media (max-width: 640px) {
        .brand-row-container {
            display: block !important;
            text-align: center;
        }
        .brand-logo-desktop, .brand-spacer {
            display: none !important;
        }
    }

    /* Modern Button Styling (Corporate Blue & Glassmorphism) */
    [data-testid="stButton"] button {
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        background-color: rgba(255, 255, 255, 0.7) !important; 
        color: var(--color-text-main) !important;            
        border: 1px solid var(--color-border) !important;
        height: 38px !important;
        width: 100% !important;
        box-shadow: var(--shadow-sm) !important;
        transition: var(--transition) !important;
        margin-top: 0px !important;
        backdrop-filter: blur(4px) !important;
    }
    
    [data-testid="stButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-hover) !important; 
        border-color: var(--color-primary) !important;
        color: var(--color-primary) !important;
        background-color: rgba(235, 244, 250, 0.85) !important; 
    }
    
    [data-testid="stButton"] button:active {
        transform: translateY(0px) !important;
    }

    /* Reset button inside sidebar */
    #reset-filters-anchor + div [data-testid="stButton"] button {
        background-color: rgba(255, 255, 255, 0.5) !important;
        border-color: var(--color-border) !important;
        height: 38px !important;
        font-size: 0.85rem !important;
        box-shadow: none !important;
    }
    #reset-filters-anchor + div [data-testid="stButton"] button:hover {
        background-color: #fee2e2 !important; /* Subtle red for reset */
        color: #ef4444 !important;
        border-color: #fca5a5 !important;
    }

    /* Button Toolbar (Web) - Robust Flexbox Layout */
    div.element-container:has(#action-buttons-anchor) {
        display: none !important;
    }
    
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) {
        display: flex !important;
        flex-direction: row !important; 
        justify-content: flex-start !important; 
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        padding-bottom: 0px;
        direction: rtl !important;
    }
    
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container {
        width: auto !important;       
        flex: 0 0 auto !important;
        padding: 0 !important;
    }
    
    /* Color-coded buttons in the toolbar */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) [data-testid="stButton"] button {
        width: 140px !important;
        min-width: 140px !important;
        border-radius: 14px !important;
        font-family: 'Assistant', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        border: 1.5px solid var(--color-border) !important;
        box-shadow: var(--shadow-sm) !important;
        transition: var(--transition) !important;
        height: 38px !important;
    }

    /* Emerald Accent for Add Record */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(2) button {
        color: #10b981 !important;
        border-color: rgba(16, 185, 129, 0.25) !important;
        background-color: rgba(16, 185, 129, 0.02) !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(2) button:hover {
        background-color: #ecfdf5 !important;
        border-color: #10b981 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(16, 185, 129, 0.15) !important;
    }

    /* Rose Accent for Delete Record */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(3) button {
        color: #ef4444 !important;
        border-color: rgba(239, 68, 68, 0.25) !important;
        background-color: rgba(239, 68, 68, 0.02) !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(3) button:hover {
        background-color: #fff1f2 !important;
        border-color: #ef4444 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(239, 68, 68, 0.15) !important;
    }

    /* Blue Accent for Update Record */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(4) button {
        color: #3b82f6 !important;
        border-color: rgba(59, 130, 246, 0.25) !important;
        background-color: rgba(59, 130, 246, 0.02) !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(4) button:hover {
        background-color: #eff6ff !important;
        border-color: #3b82f6 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.15) !important;
    }

    /* Slate Accent for Upload CSV */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(5) button {
        color: #64748b !important;
        border-color: rgba(100, 116, 139, 0.25) !important;
        background-color: rgba(100, 116, 139, 0.02) !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div:nth-child(5) button:hover {
        background-color: #f8fafc !important;
        border-color: #64748b !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(100, 116, 139, 0.15) !important;
    }
    
    /* Square Download Button Styling */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) [data-testid="stDownloadButton"] button {
        width: 38px !important;
        min-width: 38px !important;
        height: 38px !important;
        padding: 0 !important;
        border-radius: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* Table Controls Row (Page Info + Checkbox) */
    div.element-container:has(#table-controls-anchor) { display: none !important; }
    
    div[data-testid="stVerticalBlock"]:has(> div.element-container #table-controls-anchor) {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
        width: 100% !important;
        direction: rtl !important;
        margin-top: 5px !important;
        margin-bottom: 2px !important;
    }
    
    div[data-testid="stVerticalBlock"]:has(> div.element-container #table-controls-anchor) > div.element-container {
        width: auto !important;
        flex: 0 0 auto !important;
    }

    /* Frosted-Glass Table Background + Surface Shadows */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stTable"] {
        background-color: rgba(255, 255, 255, 0.75) !important; 
        backdrop-filter: blur(8px) !important;
        border-radius: var(--radius-lg);
        border: 1px solid rgba(226, 234, 241, 0.7) !important;
        box-shadow: var(--shadow-md);
        margin-top: 0px;
        transition: var(--transition);
    }
    
    [data-testid="stDataFrame"]:hover, [data-testid="stDataEditor"]:hover {
        box-shadow: var(--shadow-hover);
    }
    
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td, 
    [data-testid="stDataEditor"] th, [data-testid="stDataEditor"] td,
    [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] * {
        text-align: right !important;
        font-family: 'Assistant', sans-serif !important;
    }

    /* Sidebar Stats - Floating accented cards */
    .sidebar-stats {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 1rem;
    }
    .sidebar-stat-card {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(157, 188, 227, 0.25) !important;
        border-right: 5px solid var(--color-primary) !important; /* Right border accent for RTL */
        border-radius: var(--radius-md) !important;
        padding: 0.6rem 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        direction: rtl;
        box-shadow: 0 4px 15px 0 rgba(115, 130, 140, 0.03) !important;
        transition: var(--transition) !important;
    }
    .sidebar-stat-card:hover {
        border-right-color: var(--color-primary-hover) !important;
        box-shadow: 0 10px 20px 0 rgba(157, 188, 227, 0.18) !important;
        transform: translateY(-3px) !important;
    }
    .sidebar-stat-card .num {
        font-family: 'Outfit', 'Assistant', sans-serif !important;
        font-size: 1.25rem !important;
        font-weight: 800;
        color: var(--color-primary-hover) !important;
    }
    .sidebar-stat-card .label {
        font-size: 0.82rem !important;
        font-weight: 600;
        color: var(--color-text-muted) !important;
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 640px) {
        .block-container {
            padding-top: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) {
            display: grid !important;
            grid-template-columns: repeat(2, 140px) !important;
            justify-content: center !important;
            margin: 0 auto !important;
            gap: 8px !important;
            direction: rtl !important;
        }
        
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container {
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            flex: none !important;
            padding: 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) [data-testid="stButton"] button {
            width: 100% !important;
            height: 40px !important;
            font-size: 0.85rem !important;
            min-width: 0 !important;
        }
        
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container:has([data-testid="stDownloadButton"]) {
            justify-self: end !important;
        }
        
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container:has([data-testid="stCheckbox"]) {
            justify-self: start !important;
            margin-top: 4px;
        }

        div.st-emotion-cache-1wmy9hl { width: 100% !important; gap: 0 !important; }
        
        .main-header { 
            margin-bottom: 0.2rem !important; 
        }
    }
    
    .stCheckbox label {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: var(--color-text-muted) !important;
        padding-right: 8px;
    }
    
    [data-testid="column"] {
        padding: 0 0.2rem !important;
    }
    
    .element-container { margin-bottom: 0 !important; }
    
    .table-toggle-wrapper {
        display: flex;
        justify-content: flex-end;
        padding-top: 0px;
        padding-bottom: 0px;
    }
    </style>
    """),
    unsafe_allow_html=True,
)

# Global Background Watermark — desktop only (hidden on mobile)
if BG_BASE64:
    st.markdown(
        f"""
        <style>
        @media (min-width: 768px) {{
            .stApp {{
                background-image: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), url("data:image/png;base64,{BG_BASE64}") !important;
                background-size: cover !important;
                background-position: center !important;
                background-attachment: fixed !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Init Form State Variables if they don't exist
# ---------------------------------------------------------------------------
if "search_input" not in st.session_state:
    st.session_state["search_input"] = ""
if "artist_select" not in st.session_state:
    st.session_state["artist_select"] = []
if "letter_select" not in st.session_state:
    st.session_state["letter_select"] = []
if "drawn_record" not in st.session_state:
    st.session_state["drawn_record"] = None
if "dialog_open" not in st.session_state:
    st.session_state["dialog_open"] = False
if "drawn_at" not in st.session_state:
    st.session_state["drawn_at"] = 0.0
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "detail_record" not in st.session_state:
    st.session_state["detail_record"] = None
if "selection_counter" not in st.session_state:
    st.session_state["selection_counter"] = 0

# ---------------------------------------------------------------------------
# Firebase connection (cached)
# ---------------------------------------------------------------------------
@st.cache_resource
def init_db():
    return get_db()

db = init_db()

# ---------------------------------------------------------------------------
# State helpers & Fetch
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400)
def _fetch_all_records():
    """Cached Firestore read — at most one round-trip per 24 hours per server instance.

    On ResourceExhausted (429) the cache stores an empty DataFrame so the UI
    stays alive with a warning rather than hard-crashing the app.

    Call st.cache_data.clear() before load_data() whenever data is mutated.
    """
    try:
        return record_store.get_all(init_db(), limit=None)
    except ResourceExhausted:
        _empty_cols = ["id", "sorting_key"] + record_store.FIELDS + record_store.EXTRA_FIELDS
        return pd.DataFrame(columns=_empty_cols)

def load_data():
    """Populate session state from the cache (or Firestore on first/post-mutation run)."""
    t0 = time.time()
    df = _fetch_all_records()
    print(f"load_data: Loaded {len(df)} records in {time.time()-t0:.4f} seconds", flush=True)
    st.session_state["df"] = df
    st.session_state["_quota_exhausted"] = df.empty and "id" in df.columns
    st.session_state["current_page"] = 0

def refresh():
    load_data()

def reset_all_filters():
    """Safe callback for the Reset button — runs before the script re-renders."""
    st.session_state["search_input"] = ""
    st.session_state["artist_select"] = []
    st.session_state["letter_select"] = []
    load_data()

def set_admin():
    """Callback: validate admin password and set is_admin flag."""
    entered = st.session_state.get("admin_input", "")
    correct = st.secrets.get("app_password", "")
    st.session_state["is_admin"] = (entered == correct) and bool(correct)

if "df" not in st.session_state or "current_page" not in st.session_state:
    load_data()

df = st.session_state["df"]

# Show a visible banner when the daily Firestore quota is exhausted so the
# app stays alive rather than crashing.  The banner auto-disappears once
# the quota resets and the cache is cleared.
if st.session_state.get("_quota_exhausted"):
    st.warning(
        "⚠️ מכסת הקריאות היומית של מסד הנתונים מוצתה (שגיאה 429). "
        "הטבלה תוצג שוב אוטומטית לאחר איפוס המכסה (בדרך כלל חצות שעון פסיפיק). "
        "אין צורך בפעולה נוספת.",
        icon=None,
    )



# ---------------------------------------------------------------------------
# Sidebar — Power Numbers & Filters (GLOBAL)
# ---------------------------------------------------------------------------

@st.dialog(" הגרלת תקליט")
def draw_record_dialog():
    if df.empty:
        st.warning("אין תקליטים בספרייה.")
        return

    if "spin_key" not in st.session_state:
        st.session_state["spin_key"] = 0

    # Draw a fresh record when opened
    if st.session_state["drawn_record"] is None:
        st.session_state["drawn_record"] = df.sample(1).iloc[0].to_dict()
        st.session_state["drawn_at"] = time.time()

    record   = st.session_state["drawn_record"]
    raw_artist = record.get("artist") or ""
    raw_name   = record.get("name")   or ""
    artist = raw_artist if str(raw_artist).lower() not in ("", "none") else "לא ידוע"
    name   = raw_name   if str(raw_name).lower()   not in ("", "none") else "לא ידוע"
    spin_key = st.session_state["spin_key"]
    vinyl_base64 = get_base64_of_bin_file('spinning_vinyl_asset.png')
    vinyl_src = f"data:image/png;base64,{vinyl_base64}" if vinyl_base64 else ""

    # If the animation has already completed, render final state instantly
    # (avoids text disappearing on Streamlit's periodic reruns)
    elapsed = time.time() - st.session_state.get("drawn_at", 0)
    animation_done = elapsed > 4.9  # 4s spin + 0.8s ghost fade + buffer

    if animation_done:
        # Render static final state: ghost vinyl + visible text, no animation
        st.markdown(
            f"""
            <style>
            #vwrap-{spin_key} {{
                position: relative;
                width: min(220px, 80vw); height: min(220px, 80vw);
                margin: 1.2rem auto 0.8rem;
                pointer-events: none;   /* prevents hover repaints on entire block */
            }}
            #vwrap-{spin_key} .v-img {{
                width: 100%; height: 100%;
                border-radius: 50%; display: block; opacity: 0.25;
            }}
            #vwrap-{spin_key} .v-shine {{
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                border-radius: 50%;
                background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.03) 20%, rgba(0,0,0,0.1) 60%, rgba(255,255,255,0.12) 80%, rgba(255,255,255,0) 100%);
                pointer-events: none;
                z-index: 2;
                opacity: 0.25;
            }}
            #vwrap-{spin_key} .v-top {{
                position: absolute; top: 9%; left: 0; right: 0;
                text-align: center;
                font-size: clamp(0.75rem, 4vw, 1.1rem); font-weight: 900; color: #ffffff;
                text-shadow: 0 2px 8px rgba(0,0,0,0.95), 0 0px 2px rgba(0,0,0,1);
                padding: 0 12%; line-height: 1.3;
                z-index: 3;
            }}
            #vwrap-{spin_key} .v-bottom {{
                position: absolute; bottom: 9%; left: 0; right: 0;
                text-align: center;
                font-size: clamp(0.65rem, 3.5vw, 0.95rem); font-weight: 800; color: #f0f0f0;
                text-shadow: 0 2px 6px rgba(0,0,0,0.95), 0 0px 2px rgba(0,0,0,1);
                padding: 0 12%; line-height: 1.3;
                z-index: 3;
            }}
            </style>
            <div id="vwrap-{spin_key}">
                <img class="v-img" src="{vinyl_src}" alt="vinyl" />
                <div class="v-shine"></div>
                <div class="v-top">{name}</div>
                <div class="v-bottom">{artist}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Full animation sequence
        st.markdown(
            f"""
            <style>
            @keyframes vinylDecel-{spin_key} {{
                0%   {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(1080deg); }}
            }}
            @keyframes vinylGhost-{spin_key} {{
                from {{ opacity: 1; }}
                to   {{ opacity: 0.25; }}
            }}
            @keyframes popIn-{spin_key} {{
                from {{ opacity: 0; }}
                to   {{ opacity: 1; }}
            }}
            #vwrap-{spin_key} {{
                position: relative;
                width: min(220px, 80vw); height: min(220px, 80vw);
                margin: 1.2rem auto 0.8rem;
                pointer-events: none;   /* prevents hover repaints that restart animation fill */
            }}
            #vwrap-{spin_key} .v-img {{
                width: 100%; height: 100%;
                border-radius: 50%; display: block;
                animation:
                    vinylDecel-{spin_key} 4s  cubic-bezier(0.05, 0, 0.3, 1) forwards,
                    vinylGhost-{spin_key} 0.8s ease-in 4s forwards;
            }}
            #vwrap-{spin_key} .v-shine {{
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                border-radius: 50%;
                background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.03) 20%, rgba(0,0,0,0.1) 60%, rgba(255,255,255,0.12) 80%, rgba(255,255,255,0) 100%);
                pointer-events: none;
                z-index: 2;
                animation: vinylGhost-{spin_key} 0.8s ease-in 4s forwards;
            }}
            #vwrap-{spin_key} .v-top {{
                position: absolute; top: 9%; left: 0; right: 0;
                text-align: center; opacity: 0;
                animation: popIn-{spin_key} 0.01s steps(1, end) 4.8s forwards;
                will-change: opacity;   /* isolates layer, prevents hover repaint reset */
                font-size: clamp(0.75rem, 4vw, 1.1rem); font-weight: 900; color: #ffffff;
                text-shadow: 0 2px 8px rgba(0,0,0,0.95), 0 0px 2px rgba(0,0,0,1);
                padding: 0 12%; line-height: 1.3;
                z-index: 3;
            }}
            #vwrap-{spin_key} .v-bottom {{
                position: absolute; bottom: 9%; left: 0; right: 0;
                text-align: center; opacity: 0;
                animation: popIn-{spin_key} 0.01s steps(1, end) 4.8s forwards;
                will-change: opacity;   /* isolates layer, prevents hover repaint reset */
                font-size: clamp(0.65rem, 3.5vw, 0.95rem); font-weight: 800; color: #f0f0f0;
                text-shadow: 0 2px 6px rgba(0,0,0,0.95), 0 0px 2px rgba(0,0,0,1);
                padding: 0 12%; line-height: 1.3;
                z-index: 3;
            }}
            </style>
            <div id="vwrap-{spin_key}">
                <img class="v-img" src="{vinyl_src}" alt="vinyl" />
                <div class="v-shine"></div>
                <div class="v-top">{name}</div>
                <div class="v-bottom">{artist}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_spin, col_close = st.columns(2)
    with col_spin:
        if st.button("סובב שוב", use_container_width=True):
            st.session_state["drawn_record"] = df.sample(1).iloc[0].to_dict()
            st.session_state["spin_key"] = spin_key + 1
            st.session_state["drawn_at"] = time.time()
            st.rerun()  # safe: dialog_open=True keeps dialog alive on rerun
    with col_close:
        if st.button("✕ סגור", use_container_width=True):
            st.session_state["drawn_record"] = None
            st.session_state["dialog_open"] = False
            st.rerun()

with st.sidebar:
    st.markdown('<h3 style="text-align: right; margin-top: 0;"><i class="fas fa-layer-group"></i> נתונים</h3>', unsafe_allow_html=True)
    
    total_records = len(df)
    total_artists = df["artist"].nunique() if not df.empty else 0

    st.markdown(
        f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat-card">
                <span class="label">סה״כ תקליטים</span>
                <span class="num">{total_records}</span>
            </div>
            <div class="sidebar-stat-card">
                <span class="label">סה״כ אמנים</span>
                <span class="num">{total_artists}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Draw Record Button ---
    st.markdown('<div style="margin: 0.5rem 0;">', unsafe_allow_html=True)
    if st.button(" הגרל תקליט", use_container_width=True):
        st.session_state["drawn_record"] = None
        st.session_state["spin_key"] = 0
        st.session_state["drawn_at"] = 0.0
        st.session_state["dialog_open"] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<h3 style="text-align: right; margin-top: 0.5rem;"><i class="fas fa-search"></i> סינון</h3>', unsafe_allow_html=True)

    st.text_input("חיפוש חופשי", placeholder="חיפוש חופשי (אמן, אלבום, הערות)...", key="search_input", label_visibility="collapsed")

    artists = sorted(df["artist"].dropna().unique()) if not df.empty else []
    st.multiselect("סנן לפי אמן", artists, key="artist_select")

    letters = sorted(df["id_letter"].dropna().unique()) if not df.empty else []
    st.multiselect("סנן לפי אות", letters, key="letter_select")

    # Reset Button — uses on_click callback to avoid StreamlitAPIException
    st.markdown('<div id="reset-filters-anchor"></div>', unsafe_allow_html=True)
    st.button("אפס סינונים ורענן", use_container_width=True, on_click=reset_all_filters)

    # ── Admin login (hidden at the bottom of sidebar) ───────────────────────
    st.markdown("<hr style='margin: 1.5rem 0 0.5rem; border-color: var(--color-border);'>", unsafe_allow_html=True)
    st.text_input(
        "🔐 כניסת מנהל",
        type="password",
        key="admin_input",
        on_change=set_admin,
        placeholder="סיסמת מנהל...",
        label_visibility="collapsed",
    )
    if st.session_state["is_admin"]:
        st.markdown("<p style='color:#22c55e; font-size:0.78rem; text-align:right; margin:0;'>✓ מצב מנהל פעיל</p>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Apply Global Filters to working dataset
# ---------------------------------------------------------------------------

filtered_df = df.copy()

sq = st.session_state["search_input"]
if sq:
    q = sq.lower()
    mask = filtered_df.apply(
        lambda row: q in str(row.get("artist", "")).lower() or 
                    q in str(row.get("name", "")).lower() or 
                    q in str(row.get("notes", "")).lower(), 
        axis=1
    )
    filtered_df = filtered_df[mask]

if st.session_state["artist_select"]:
    filtered_df = filtered_df[filtered_df["artist"].isin(st.session_state["artist_select"])]

if st.session_state["letter_select"]:
    filtered_df = filtered_df[filtered_df["id_letter"].isin(st.session_state["letter_select"])]

total_filtered_records = len(filtered_df)
MAX_PAGE = max(0, (total_filtered_records - 1) // 50)
if st.session_state["current_page"] > MAX_PAGE:
    st.session_state["current_page"] = MAX_PAGE


# ---------------------------------------------------------------------------
# Album detail popup — triggered by table row clicks
# ---------------------------------------------------------------------------

@st.dialog("🎧 פרטי האלבום")
def show_record_detail(record: dict) -> None:
    """
    Modular record detail popup.  Called with a full record dict
    (including image_url / image_synced if available).
    """
    import re
    import urllib.parse
    import pandas as pd

    try:
        if not isinstance(record, dict):
            st.error("לא ניתן להציג פרטים עבור רשומה זו.")
            return

        def safe_str(val) -> str:
            if val is None:
                return ""
            if isinstance(val, float) and pd.isna(val):
                return ""
            return str(val).strip()

        # Clean all input values safely
        image_raw = record.get("image_url")
        image_url = safe_str(image_raw)
        if not image_url:
            image_url = None

        artist     = safe_str(record.get("artist")) or "לא ידוע"
        name       = safe_str(record.get("name")) or "לא ידוע"
        id_letter  = safe_str(record.get("id_letter"))
        notes      = safe_str(record.get("notes"))
        
        # Handle box safely
        box_val = record.get("box")
        if box_val is None or (isinstance(box_val, float) and pd.isna(box_val)):
            box = "לא ידוע"
        else:
            try:
                box = str(int(float(box_val)))
            except Exception:
                box = str(box_val)

        # Convert standard Drive export URL to Google User Content direct image URL for reliable hotlinking
        if image_url and "drive.google.com" in image_url:
            try:
                parsed = urllib.parse.urlparse(image_url)
                qs = urllib.parse.parse_qs(parsed.query)
                file_id = qs.get("id", [None])[0]
                if file_id:
                    image_url = f"https://lh3.googleusercontent.com/d/{file_id}"
            except Exception:
                pass

        # ── Album cover ────────────────────────────────────────────────────────
        if image_url:
            try:
                col_img_left, col_img_center, col_img_right = st.columns([1, 2, 1])
                with col_img_center:
                    st.image(image_url, width=180)
            except Exception:
                st.info("לא קיימת תמונה לרשומה זו")
        else:
            st.info("לא קיימת תמונה לרשומה זו")

        # ── Metadata ───────────────────────────────────────────────────────────
        location = f"קופסא {box}"
        if id_letter:
            location += f" &nbsp;•&nbsp; אות {id_letter}"

        st.markdown(
            f"""
            <div style="direction:rtl; text-align:right; padding:0.4rem 0 0;">
                <h3 style="margin:0.4rem 0 0.1rem; color:#3E4B59;">{name}</h3>
                <p style="margin:0; color:#8292A1; font-size:0.9rem;"><strong>אמן:</strong> {artist}</p>
                <p style="margin:0.5rem 0 0; font-size:0.82rem; color:#64748b;">{location}</p>
                {f'<p style="margin:0.4rem 0 0; font-size:0.85rem;"><strong>הערות:</strong> {notes}</p>' if notes else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
        if st.button("✕ סגור", use_container_width=True):
            st.session_state["detail_record"] = None
            st.rerun()

    except Exception as e:
        st.error("ארעה שגיאה בהצגת פרטי האלבום.")
        st.caption(f"שגיאה: {e}")
        if st.button("✕ סגור", key="detail_err_close", use_container_width=True):
            st.session_state["detail_record"] = None
            st.rerun()


# ---------------------------------------------------------------------------
# Add record dialog
# ---------------------------------------------------------------------------
@st.dialog("הוספת תקליט חדש")
def add_record_dialog():
    if not st.session_state.get("is_admin", False):
        st.error("גישה נדחתה. עליך להתחבר כמנהל.")
        return
    with st.form("add_form", clear_on_submit=True):
        st.markdown("<p style='font-size: 0.85rem; color: #666;'>השדות המסומנים ב-* הינם חובה.</p>", unsafe_allow_html=True)
        new_artist = st.text_input("שם אומן *")
        new_name = st.text_input("שם התקליט *")
        new_notes = st.text_input("הערות נוספות")
        new_image_url = st.text_input("כתובת תמונת עטיפה (אופציונלי)", placeholder="https://i.discogs.com/...")
        col_box, col_letter = st.columns(2)
        with col_box:
            new_box = st.number_input("קופסא", min_value=1, step=1, value=1)
        with col_letter:
            new_id_letter = st.text_input("אות", max_chars=1)

        submitted = st.form_submit_button("הוסף", type="primary", use_container_width=True)
        if submitted:
            if not new_artist or not new_name:
                st.error("אנא מלא את השדות החובה.")
            else:
                new_doc_id = record_store.add(db, {
                    "box": int(new_box),
                    "id_letter": new_id_letter.strip(),
                    "artist": new_artist.strip(),
                    "name": new_name.strip(),
                    "notes": new_notes.strip(),
                    "image_url": new_image_url.strip() or None,
                    "image_synced": False,
                })
                st.cache_data.clear()  # Invalidate cache so next read hits Firestore
                load_data()
                # --- Auto-sync cover image to Drive ---
                if new_image_url.strip():
                    with st.spinner("מוריד תמונת עטיפה..."):
                        try:
                            from drive_backup import build_drive_service
                            from image_sync import sync_single_record
                            drive_svc = build_drive_service(dict(st.secrets["firebase"]))
                            covers_folder_id = st.secrets.get("gdrive_covers_folder_id", "")
                            if covers_folder_id:
                                sync_single_record(db, drive_svc, new_doc_id, new_image_url.strip(), covers_folder_id)
                                st.cache_data.clear()  # Refresh after image URL update
                                load_data()
                        except Exception:
                            pass  # Image sync failure is non-fatal
                # --- Auto-backup to Google Drive (background task) ---
                if st.secrets.get("enable_backup", True):
                    try:
                        from auto_backup import rotate_and_backup
                        firebase_secrets = dict(st.secrets["firebase"]) if "firebase" in st.secrets else None
                        threading.Thread(target=rotate_and_backup, args=(firebase_secrets,), daemon=True).start()
                    except Exception as e:
                        print(f"Auto-Backup: Thread spawn failed: {e}", flush=True)
                else:
                    print("Auto-Backup: Skipped background backup because enable_backup is set to False in secrets.", flush=True)
                st.rerun()

@st.dialog("מחיקת תקליט")
def delete_record_dialog():
    if not st.session_state.get("is_admin", False):
        st.error("גישה נדחתה. עליך להתחבר כמנהל.")
        return
    if filtered_df.empty:
         st.warning("אין תקליטים לחיתוך זה.")
         return
    delete_options = {
        f"{row['artist']} — {row['name']}": row["id"]
        for _, row in filtered_df.iterrows()
    }
    selected_delete = st.selectbox("בחר תקליט", list(delete_options.keys()))
    if st.button("מחק סופית", type="primary", use_container_width=True):
        record_store.delete(db, delete_options[selected_delete])
        st.cache_data.clear()  # Invalidate cache so next read hits Firestore
        load_data()
        # --- Auto-backup to Google Drive (background task) ---
        if st.secrets.get("enable_backup", True):
            try:
                from auto_backup import rotate_and_backup
                firebase_secrets = dict(st.secrets["firebase"]) if "firebase" in st.secrets else None
                threading.Thread(target=rotate_and_backup, args=(firebase_secrets,), daemon=True).start()
            except Exception as e:
                print(f"Auto-Backup: Thread spawn failed: {e}", flush=True)
        else:
            print("Auto-Backup: Skipped background backup because enable_backup is set to False in secrets.", flush=True)
        st.rerun()

@st.dialog("עדכון תקליט")
def update_record_dialog():
    if not st.session_state.get("is_admin", False):
        st.error("גישה נדחתה. עליך להתחבר כמנהל.")
        return
    if df.empty:
        st.warning("אין נתונים במסד.")
        return
        
    update_options = {
        f"{row['artist']} — {row['name']} (קופסא {row['box']})": row
        for _, row in df.iterrows()
    }
    
    selected_key = st.selectbox("חפש ובחר רשומה לעדכון:", list(update_options.keys()))
    selected_record = update_options[selected_key]
    
    with st.form("update_form"):
        st.markdown("<p style='font-size: 0.85rem; color: var(--color-text-muted);'>שנה את השדות הרצויים ולחץ על אישור לשמירה.</p>", unsafe_allow_html=True)
        
        updated_artist = st.text_input("אמן *", value=selected_record.get("artist", ""))
        updated_name = st.text_input("שם התקליט *", value=selected_record.get("name", ""))
        updated_notes = st.text_input("הערות נוספות", value=selected_record.get("notes", ""))
        updated_image_url = st.text_input(
            "כתובת תמונת עטיפה (אופציונלי)",
            value=selected_record.get("image_url") or "",
            placeholder="https://i.discogs.com/...",
        )
        
        col_box, col_letter = st.columns(2)
        with col_box:
            updated_box = st.number_input("קופסא", min_value=1, step=1, value=int(selected_record.get("box", 1)))
        with col_letter:
            updated_letter = st.text_input("אות (אופציונלי)", max_chars=1, value=selected_record.get("id_letter", ""))
            
        submitted = st.form_submit_button("אישור", type="primary", use_container_width=True)
        if submitted:
            if not updated_artist or not updated_name:
                st.error("אנא מלא את השדות החובה (אמן, שם התקליט).")
            else:
                changes = {
                    "artist": updated_artist.strip(),
                    "name": updated_name.strip(),
                    "notes": updated_notes.strip(),
                    "box": int(updated_box),
                }
                # Only update id_letter if explicitly provided
                if updated_letter.strip():
                     changes["id_letter"] = updated_letter.strip()
                # Update image_url if changed; mark as un-synced so bulk sync will re-process
                new_raw_url = updated_image_url.strip()
                old_raw_url = (selected_record.get("image_url") or "").strip()
                if new_raw_url != old_raw_url:
                    changes["image_url"] = new_raw_url or None
                    changes["image_synced"] = False
                     
                record_store.update(db, selected_record["id"], changes)
                st.success("הרשומה עודכנה בהצלחה!")
                time.sleep(0.8)
                st.cache_data.clear()  # Invalidate cache so next read hits Firestore
                load_data()
                # --- Auto-sync updated cover image to Drive ---
                if new_raw_url and new_raw_url != old_raw_url:
                    with st.spinner("מוריד תמונת עטיפה..."):
                        try:
                            from drive_backup import build_drive_service
                            from image_sync import sync_single_record
                            drive_svc = build_drive_service(dict(st.secrets["firebase"]))
                            covers_folder_id = st.secrets.get("gdrive_covers_folder_id", "")
                            if covers_folder_id:
                                sync_single_record(db, drive_svc, selected_record["id"], new_raw_url, covers_folder_id)
                                st.cache_data.clear()
                                load_data()
                        except Exception:
                            pass  # Image sync failure is non-fatal
                # --- Auto-backup to Google Drive (background task) ---
                if st.secrets.get("enable_backup", True):
                    try:
                        from auto_backup import rotate_and_backup
                        firebase_secrets = dict(st.secrets["firebase"]) if "firebase" in st.secrets else None
                        threading.Thread(target=rotate_and_backup, args=(firebase_secrets,), daemon=True).start()
                    except Exception as e:
                        print(f"Auto-Backup: Thread spawn failed: {e}", flush=True)
                else:
                    print("Auto-Backup: Skipped background backup because enable_backup is set to False in secrets.", flush=True)
                st.rerun()

@st.dialog("העלאת קובץ")
def upload_csv_dialog():
    if not st.session_state.get("is_admin", False):
        st.error("גישה נדחתה. עליך להתחבר כמנהל.")
        return
    st.info("כלי העלאת CSV כרגע לא פעיל בממשק.")

# ---------------------------------------------------------------------------
# Invoke dialogs at top level so st.rerun() inside them keeps them alive
# ---------------------------------------------------------------------------
if st.session_state.get("dialog_open", False):
    draw_record_dialog()

if st.session_state.get("detail_record") is not None:
    show_record_detail(st.session_state["detail_record"])
    st.session_state["detail_record"] = None

# ---------------------------------------------------------------------------
# Main Layout
# ---------------------------------------------------------------------------

# Update Sidebar explicitly referencing the Current View (Density)
st.sidebar.markdown(
    f"""
    <div class="sidebar-stat-card" style="background:#f8fafc; margin-top: -10px;">
        <span class="label">שורות בתצוגה (אחרי סינון)</span>
        <span class="num">{total_filtered_records}</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Row 1: Brand (Title centered, Logo on left)
with st.container():
    st.markdown('<div id="brand-row-anchor"></div>', unsafe_allow_html=True)
    header_html = f"""
    <div class="brand-row-container">
        <div class="brand-logo-desktop">
            <img src="data:image/png;base64,{LOGO_BASE64}" style="width: 180px;">
        </div>
        <div class="brand-row-center">
            <div class="main-header">
                <h1>אוסף התקליטים של ירון</h1>
            </div>
        </div>
        <div class="brand-spacer"></div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)



# Row 3: Action Toolbar — admin-only
if st.session_state.get("is_admin", False):
    with st.container():
        st.markdown('<div id="action-buttons-anchor"></div>', unsafe_allow_html=True)
        if st.button("הוסף רשומה"):
            add_record_dialog()
        if st.button("מחק רשומה"):
            delete_record_dialog()
        if st.button("עדכון רשומה"):
            update_record_dialog()
        if st.button("העלאת קובץ"):
            upload_csv_dialog()

        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️",
            data=csv_data,
            file_name="records_backup.csv",
            mime="text/csv"
        )

# Row 4: Data Info & Checkbox (Table Controls Line)
with st.container():
    st.markdown('<div id="table-controls-anchor"></div>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:0.8rem; color: #64748b;font-weight:600; margin:0;">מציג נתונים — עמוד {st.session_state["current_page"] + 1}</p>', unsafe_allow_html=True)
    show_box = st.checkbox("הצג עמודת קופסא", value=False)

# Display Sub-Count neatly above table
# Redundant line removed to avoid duplication with Row 4

# ---------------------------------------------------------------------------
# Minimalist Table Interface (index hidden)
# ---------------------------------------------------------------------------

if filtered_df.empty:
    st.info("לא נמצאו תקליטים תחת חיפוש זה.")
else:
    START_IDX = st.session_state["current_page"] * 50
    END_IDX = START_IDX + 50
    page_df = filtered_df.iloc[START_IDX:END_IDX]

    # Convert image URLs for ImageColumn rendering
    import urllib.parse
    def clean_drive_url(url):
        if not url or not isinstance(url, str):
            return None
        if "drive.google.com" in url:
            try:
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query)
                file_id = qs.get("id", [None])[0]
                if file_id:
                    return f"https://lh3.googleusercontent.com/d/{file_id}"
            except Exception:
                pass
        return url

    # Explicit column ordering (Notes leftmost, Box rightmost structurally because Canvas Grid ignores RTL flips!)
    display_cols = ["notes", "name", "artist", "box"] if show_box else ["notes", "name", "artist"]
    display_df = page_df[display_cols].copy()
    display_df.insert(0, "עטיפה", page_df["image_url"].apply(clean_drive_url))
    
    column_config = {
        "עטיפה": st.column_config.ImageColumn("עטיפה", width="small", help="עטיפת האלבום"),
        "notes": st.column_config.TextColumn("הערות"),
        "name": st.column_config.TextColumn("שם התקליט"),
        "artist": st.column_config.TextColumn("אמן"),
        "box": st.column_config.NumberColumn("קופסא", min_value=1, step=1),
    }

    if st.session_state.get("is_admin", False):
        # Admin: editable table with save + row-click detail popup workaround
        editor_key = f"editor_{st.session_state['current_page']}_{hash(st.session_state['search_input'])}_sel_{st.session_state['selection_counter']}"
        
        # Data Isolation: Create a clean copy of the paginated dataframe for editing
        admin_cols = ["notes", "name", "artist", "box"] if show_box else ["notes", "name", "artist"]
        df_for_editing = page_df[admin_cols].copy()
        df_for_editing.insert(0, "עטיפה", page_df["image_url"].apply(clean_drive_url))
        df_for_editing.insert(0, "צפה", False)
        
        # Reset index to contiguous integers. This prevents the Streamlit TypeError caused by serializing non-contiguous pandas indices.
        df_for_editing = df_for_editing.reset_index(drop=True)
        
        # Cleanup: Force plain Python types on the editing dataframe
        df_for_editing["notes"] = df_for_editing["notes"].fillna("").astype(str)
        df_for_editing["name"] = df_for_editing["name"].fillna("").astype(str)
        df_for_editing["artist"] = df_for_editing["artist"].fillna("").astype(str)
        if "box" in df_for_editing.columns:
            df_for_editing["box"] = df_for_editing["box"].fillna(1).astype(int)
            
        # Column Configuration: Explicitly define types to prevent guessing and serializer issues
        admin_config = {
            "צפה": st.column_config.CheckboxColumn("צפה", default=False, width="small", help="הצג פרטים ועטיפה"),
            "עטיפה": st.column_config.ImageColumn("עטיפה", width="small", help="עטיפת האלבום"),
            "notes": st.column_config.TextColumn("הערות"),
            "name": st.column_config.TextColumn("שם התקליט"),
            "artist": st.column_config.TextColumn("אמן"),
            "box": st.column_config.NumberColumn("קופסא", min_value=1, step=1) if show_box else None,
        }
        # Remove None configs
        admin_config = {k: v for k, v in admin_config.items() if v is not None}

        edited_df = st.data_editor(
            df_for_editing,
            column_config=admin_config,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=320,
            disabled=["עטיפה"],
            key=editor_key,
        )

        # Check if any row's "צפה" checkbox was checked to trigger the details dialog workaround
        _editor_state = st.session_state.get(editor_key, {})
        _edited_rows = _editor_state.get("edited_rows", {})
        if _edited_rows:
            for row_idx_str, row_changes in list(_edited_rows.items()):
                if row_changes.get("צפה") is True:
                    row_idx = int(row_idx_str)
                    _rec = page_df.iloc[row_idx].to_dict()
                    st.session_state["detail_record"] = _rec
                    st.session_state["selection_counter"] += 1
                    st.rerun()

        if not df_for_editing.equals(edited_df):
            if st.button("שמור שינויים", type="primary"):
                if not st.session_state.get("is_admin", False):
                    st.error("פעולה זו מורשית למנהלים בלבד.")
                    st.rerun()
                for idx in edited_df.index:
                    original_row = df_for_editing.loc[idx]
                    edited_row = edited_df.loc[idx]
                    if not original_row.equals(edited_row):
                        # Map contiguous index back to Firestore document using page_df.iloc
                        doc_id = page_df.iloc[idx]["id"]
                        changes = edited_row.to_dict()
                        if "עטיפה" in changes:
                            del changes["עטיפה"]
                        if "צפה" in changes:
                            del changes["צפה"]
                        if "box" in changes:
                            changes["box"] = int(changes["box"])
                        record_store.update(db, doc_id, changes)
                st.cache_data.clear()  # Invalidate cache so next read hits Firestore
                load_data()
                # --- Auto-backup to Google Drive (background task) ---
                if st.secrets.get("enable_backup", True):
                    try:
                        from auto_backup import rotate_and_backup
                        firebase_secrets = dict(st.secrets["firebase"]) if "firebase" in st.secrets else None
                        threading.Thread(target=rotate_and_backup, args=(firebase_secrets,), daemon=True).start()
                    except Exception as e:
                        print(f"Auto-Backup: Thread spawn failed: {e}", flush=True)
                else:
                    print("Auto-Backup: Skipped background backup because enable_backup is set to False in secrets.", flush=True)
                st.rerun()
    else:
        # Public: read-only table with row-click detail popup
        df_key = f"df_{st.session_state['current_page']}_{hash(st.session_state['search_input'])}_sel_{st.session_state['selection_counter']}"
        event = st.dataframe(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=320,
            key=df_key,
            on_select="rerun",
            selection_mode="single-row",
        )
        _pub_rows = event.selection.rows
        if _pub_rows:
            _rec = page_df.iloc[_pub_rows[0]].to_dict()
            st.session_state["detail_record"] = _rec
            st.session_state["selection_counter"] += 1
            st.rerun()

# Footer Paginators tightly grouped
paginator_col_next, paginator_col_pos, paginator_col_prev = st.columns([1, 4, 1])
with paginator_col_next:
    if st.session_state["current_page"] > 0:
        if st.button("הקודם ←"):
             st.session_state["current_page"] -= 1
             st.rerun()
             
with paginator_col_prev:
    if st.session_state["current_page"] < MAX_PAGE:
        if st.button("→ הבא"):
             st.session_state["current_page"] += 1
             st.rerun()

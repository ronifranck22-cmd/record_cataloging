"""
Record Cataloging Dashboard — Streamlit app.

Run locally:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import time
import base64

from db_client import get_db
import record_store

# ---------------------------------------------------------------------------
# Logo Processing (Base64 for inline embedding)
# ---------------------------------------------------------------------------
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""

LOGO_BASE64 = get_base64_of_bin_file('logo.png')
# Login logo (Prominent)
LOGO_HTML_LOGIN = f'<div style="text-align: center; width: 100%; margin-top: 5vh; margin-bottom: -12vh;"><img src="data:image/png;base64,{LOGO_BASE64}" style="width: 320px;"></div>' if LOGO_BASE64 else ""

# Header Logos (Responsive)
LOGO_HTML_HEADER_LEFT = f'<div class="header-logo-left"><img src="data:image/png;base64,{LOGO_BASE64}" style="width: 180px;"></div>' if LOGO_BASE64 else ""
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
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;500;600;700;800&display=swap');
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

    /* Hide Unwanted Streamlit Elements safely, but keep Header for sidebar toggle */
    header { background-color: transparent !important; box-shadow: none !important; }
    footer { display: none !important; }
    [class^="viewerBadge"], [data-testid="stActionElements"], [data-testid="MainMenu"], .stAppDeployButton {
        display: none !important;
    }

    /* Maximize Density, adjust top padding to prevent header cut-off */
    .block-container {
        padding-top: 2rem !important;
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

    /* Header Typography Adjustment */
    .main-header {
        text-align: center;
        width: 100%;
        margin-bottom: 0.2rem;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--color-primary);
        margin-bottom: 0 !important;
        letter-spacing: -0.02em;
    }

    /* Brand Row Alignment (Desktop) */
    div.element-container:has(#brand-row-anchor) { display: none !important; }
    
    .header-logo-left {
        display: block;
        text-align: left;
    }

    /* Logo Visibility & Mobile Inline */
    .mobile-logo-inline {
        display: none;
    }

    @media (max-width: 640px) {
        .header-logo-left {
            display: none !important;
        }
        .mobile-logo-inline {
            display: inline-block !important;
        }
    }

    /* Modern Button Styling (Corporate Blue & Glassmorphism) */
    [data-testid="stButton"] button {
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        background-color: var(--color-bg-surface) !important; 
        color: var(--color-text-main) !important;            
        border: 1px solid var(--color-border) !important;
        height: 38px !important;
        width: 100% !important;
        box-shadow: var(--shadow-sm) !important;
        transition: var(--transition) !important;
        margin-top: 0px !important;
    }
    
    [data-testid="stButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-hover) !important; 
        border-color: var(--color-primary) !important;
        color: var(--color-primary) !important;
        background-color: #EBF4FA !important; /* Soft pastel blue on hover */
    }
    
    [data-testid="stButton"] button:active {
        transform: translateY(0px) !important;
    }

    /* Reset button inside sidebar */
    #reset-filters-anchor + div [data-testid="stButton"] button {
        background-color: var(--color-bg-main) !important;
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
    /* Hide the anchor container so it doesn't disrupt Flexbox or Grid packing */
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
        direction: rtl !important; /* Standard RTL for action buttons */
    }
    
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container {
        width: auto !important;       
        flex: 0 0 auto !important;
        padding: 0 !important;
    }
    
    /* Ensure buttons maintain uniform size and Corporate Blue aesthetic */
    div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) [data-testid="stButton"] button {
        width: 140px !important;
        min-width: 140px !important;
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

    /* Clean White Table Background + Surface Shadows */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stTable"] {
        background-color: var(--color-bg-surface) !important; 
        border-radius: var(--radius-lg);
        padding: 0.3rem;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-md);
        margin-top: 0px;
        direction: rtl !important;
        text-align: right !important;
        transition: var(--transition);
        max-height: 52vh !important; /* Slightly reduced to account for 4th row */
        overflow-y: auto !important;
    }
    
    [data-testid="stDataFrame"]:hover, [data-testid="stDataEditor"]:hover {
        box-shadow: var(--shadow-hover);
    }
    
    /* Force table headings and cells to align right */
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td, 
    [data-testid="stDataEditor"] th, [data-testid="stDataEditor"] td,
    [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] * {
        text-align: right !important;
        font-family: 'Assistant', sans-serif !important;
    }

    /* Sidebar Stats - Clean Corporate Cards */
    .sidebar-stats {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 1rem;
    }
    .sidebar-stat-card {
        background: var(--color-bg-surface);
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-sm);
        border-radius: var(--radius-md);
        padding: 0.6rem 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        direction: rtl;
        transition: var(--transition);
    }
    .sidebar-stat-card:hover {
        border-color: var(--color-primary);
        box-shadow: var(--shadow-hover);
        transform: translateY(-2px);
    }
    .sidebar-stat-card .num {
        font-size: 1.15rem;
        font-weight: 800;
        color: var(--color-primary);
    }
    .sidebar-stat-card .label {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--color-text-muted);
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 640px) {
        .block-container {
            padding-top: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* Force Mobile 2x2 Grid Layout */
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

        /* Responsive buttons for the grid */
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) [data-testid="stButton"] button {
            width: 100% !important;
            height: 40px !important;
            font-size: 0.85rem !important;
            min-width: 0 !important;
        }
        
        /* Mobile styling for the 3rd row elements (Download & Checkbox) */
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container:has([data-testid="stDownloadButton"]) {
            justify-self: end !important; /* Push square button toward the center */
        }
        
        div[data-testid="stVerticalBlock"]:has(> div.element-container #action-buttons-anchor) > div.element-container:has([data-testid="stCheckbox"]) {
            justify-self: start !important; /* Push checkbox toward the center */
            margin-top: 4px;
        }

        div.st-emotion-cache-1wmy9hl { width: 100% !important; gap: 0 !important; }
        
        /* Height Reduction: Minimize margins to bring table above the fold */
        .main-header h1 { 
            font-size: 1.5rem !important; 
            margin-bottom: 0 !important; 
        }
        .main-header { 
            margin-bottom: 0.2rem !important; 
        }
    }
    
    /* Toggle Switch Size Reduction */
    .stCheckbox label {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: var(--color-text-muted) !important;
        padding-right: 8px;
    }
    
    /* Removes the padding from stColumns to tightly hug the layout */
    [data-testid="column"] {
        padding: 0 0.2rem !important;
    }
    
    /* Tightly wrap elements vertically */
    .element-container { margin-bottom: 0 !important; }
    
    /* Small wrapper alignment for minimalist right alignment of toggle */
    .table-toggle-wrapper {
        display: flex;
        justify-content: flex-end; /* RTL: right */
        padding-top: 0px;
        padding-bottom: 0px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Password Authentication
# ---------------------------------------------------------------------------

def check_password():
    def password_entered():
        correct_password = st.secrets.get("app_password", "admin123")
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Inject CSS to center the login screen (ONLY runs when not authenticated)
    st.markdown(
        """
        <style>
        /* Push the password input down and center it horizontally safely */
        [data-testid="stTextInput"] {
            margin-top: 15vh !important;
            margin-left: auto !important;
            margin-right: auto !important;
            width: 350px !important;
            max-width: 90% !important;
        }
        /* Ensure the label is visible and right-aligned */
        [data-testid="stTextInput"] label {
            text-align: right !important;
            display: block !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if LOGO_HTML_LOGIN:
        st.markdown(LOGO_HTML_LOGIN, unsafe_allow_html=True)

    st.text_input("הזינו סיסמא", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("סיסמא שגויה, נסו שוב")
        
    return False

if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Init Form State Variables if they don't exist
# ---------------------------------------------------------------------------
if "search_input" not in st.session_state:
    st.session_state["search_input"] = ""
if "artist_select" not in st.session_state:
    st.session_state["artist_select"] = []
if "letter_select" not in st.session_state:
    st.session_state["letter_select"] = []

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
def load_data():
    df = record_store.get_all(db)
    st.session_state["df"] = df
    st.session_state["current_page"] = 0

def refresh():
    load_data()

if "df" not in st.session_state or "current_page" not in st.session_state:
    load_data()

df = st.session_state["df"]

# ---------------------------------------------------------------------------
# Sidebar — Power Numbers & Filters (GLOBAL)
# ---------------------------------------------------------------------------

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
    
    st.markdown('<h3 style="text-align: right; margin-top: 0.5rem;"><i class="fas fa-search"></i> סינון</h3>', unsafe_allow_html=True)

    st.text_input("", placeholder="חיפוש חופשי (אמן, אלבום, הערות)...", key="search_input")

    artists = sorted(df["artist"].dropna().unique()) if not df.empty else []
    st.multiselect("סנן לפי אמן", artists, key="artist_select")

    letters = sorted(df["id_letter"].dropna().unique()) if not df.empty else []
    st.multiselect("סנן לפי אות", letters, key="letter_select")

    # Reset Button via State
    st.markdown('<div id="reset-filters-anchor"></div>', unsafe_allow_html=True)
    if st.button("אפס סינונים ורענן", use_container_width=True):
        st.session_state["search_input"] = ""
        st.session_state["artist_select"] = []
        st.session_state["letter_select"] = []
        refresh()
        st.rerun()

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
# Dialog modals
# ---------------------------------------------------------------------------

@st.dialog("הוספת תקליט חדש")
def add_record_dialog():
    with st.form("add_form", clear_on_submit=True):
        st.markdown("<p style='font-size: 0.85rem; color: #666;'>השדות המסומנים ב-* הינם חובה.</p>", unsafe_allow_html=True)
        new_artist = st.text_input("שם אומן *")
        new_name = st.text_input("שם התקליט *")
        new_notes = st.text_input("הערות נוספות")
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
                record_store.add(db, {
                    "box": int(new_box),
                    "id_letter": new_id_letter.strip(),
                    "artist": new_artist.strip(),
                    "name": new_name.strip(),
                    "notes": new_notes.strip(),
                })
                load_data()
                st.rerun()

@st.dialog("מחיקת תקליט")
def delete_record_dialog():
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
        load_data()
        st.rerun()

@st.dialog("עדכון תקליט")
def update_record_dialog():
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
                     
                record_store.update(db, selected_record["id"], changes)
                st.success("הרשומה עודכנה בהצלחה!")
                time.sleep(0.8)
                load_data()
                st.rerun()

@st.dialog("העלאת קובץ")
def upload_csv_dialog():
    st.info("כלי העלאת CSV כרגע לא פעיל בממשק.")

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

# Row 1: Brand (Title centered, Logo left)
with st.container():
    st.markdown('<div id="brand-row-anchor"></div>', unsafe_allow_html=True)
    col_logo, col_title, col_empty = st.columns([1, 2, 1])
    with col_logo:
        if LOGO_HTML_HEADER_LEFT:
            st.markdown(LOGO_HTML_HEADER_LEFT, unsafe_allow_html=True)
    with col_title:
        st.markdown(f'<div class="main-header"><h1>{LOGO_HTML_MOBILE_INLINE}אוסף התקליטים של ירון</h1></div>', unsafe_allow_html=True)

# Row 2: Spacer
st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)

# Row 3: Action Toolbar (The Original 5)
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

    # Explicit column ordering (Notes leftmost, Box rightmost structurally because Canvas Grid ignores RTL flips!)
    display_cols = ["notes", "name", "artist", "box"] if show_box else ["notes", "name", "artist"]
    display_df = page_df[display_cols]
    
    column_config = {
        "notes": st.column_config.TextColumn("הערות"),
        "name": st.column_config.TextColumn("שם התקליט"),
        "artist": st.column_config.TextColumn("אמן"),
        "box": st.column_config.NumberColumn("קופסא", min_value=1, step=1),
    }

    # hide_index=True strips the Serial Number exactly as requested.
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,  
        num_rows="fixed",
        height=360,  # Reduced heavily to ensure no page scroll on 100% zoom
        key=f"editor_{st.session_state['current_page']}_{hash(st.session_state['search_input'])}",
    )

    if not display_df.equals(edited_df):
        if st.button("שמור שינויים", type="primary"):
            for idx in edited_df.index:
                original_row = display_df.loc[idx]
                edited_row = edited_df.loc[idx]
                if not original_row.equals(edited_row):
                    doc_id = filtered_df.loc[idx, "id"]
                    changes = edited_row.to_dict()
                    if "box" in changes:
                        changes["box"] = int(changes["box"])
                    record_store.update(db, doc_id, changes)
            load_data()  
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

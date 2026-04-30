"""
Record Cataloging Dashboard — Streamlit app.

Run locally:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd

from db_client import get_db
import record_store

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
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;500;600;700&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

    body {
        font-family: 'Assistant', sans-serif;
    }

    /* Top-level background */
    .stApp {
        background-color: #f1f5f9 !important;
    }

    /* Hide footer */
    footer {
        display: none !important;
    }
    /* Hide top-right icons (Edit, Share, Fork, Menu, Deploy) without touching the sidebar or header */
    [class^="viewerBadge"],
    [data-testid="stActionElements"],
    [data-testid="MainMenu"],
    .stAppDeployButton {
        display: none !important;
    }
    
    /* Maximize Density, adjust top padding to prevent header cut-off */
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
        direction: rtl !important;
    }

    h1, h2, h3, h4, p, label, .stMarkdown {
        direction: rtl;
        text-align: right;
        margin-bottom: 0px !important;
    }

    /* Modern Button Styling (Glassmorphism Light) */
    [data-testid="stButton"] button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        background-color: #f8fafc !important; 
        color: #475569 !important;            
        border: 1px solid #e2e8f0 !important;
        height: 48px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        margin-top: 0px !important;
    }
    
    [data-testid="stButton"] button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; 
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
    }
    
    [data-testid="stButton"] button[kind="primary"], [data-testid="stButton"] button[kind="secondary"] {
        background-color: #f8fafc !important; 
        color: #475569 !important;            
        border-color: #e2e8f0 !important;
    }

    /* Reset button inside sidebar */
    #reset-filters-anchor + div [data-testid="stButton"] button {
        background-color: #f1f5f9 !important;
        color: #475569 !important;
        border-color: #cbd5e1 !important;
        height: 38px !important;
    }

    /* Button Grid (Web) - Right aligned tight layout */
    div:has(> #action-buttons-anchor) + div.element-container [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: flex-start !important;
        direction: rtl !important;
        gap: 0.25rem !important;
        padding-bottom: 0px;
    }
    div:has(> #action-buttons-anchor) + div.element-container [data-testid="column"] {
        flex: 0 0 140px !important;    /* Force exact width, no stretching */
        width: 140px !important;       
        min-width: 140px !important;
        max-width: 140px !important;
    }

    /* Clean White Table Background + Padding to pop off the container */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stTable"] {
        background-color: #ffffff !important; 
        border-radius: 12px;
        padding: 0.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        margin-top: 5px;
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* Force table headings and cells to align right */
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td, 
    [data-testid="stDataEditor"] th, [data-testid="stDataEditor"] td,
    [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] * {
        text-align: right !important;
    }

    /* Sidebar Stats - Compact Mode */
    .sidebar-stats {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        margin-bottom: 0.8rem;
    }
    .sidebar-stat-card {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        direction: rtl;
    }
    .sidebar-stat-card .num {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .sidebar-stat-card .label {
        font-size: 0.75rem;
        color: #64748b;
    }

    /* Mobile Responsive Buttons (2x2 Grid) */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 2rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Modifying the Button Grid specifically for mobile */
        div:has(> #action-buttons-anchor) + div.element-container [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.5rem !important;
            justify-content: flex-start !important;
            direction: rtl !important;
        }
        div:has(> #action-buttons-anchor) + div.element-container [data-testid="column"] {
            flex: 0 0 calc(50% - 0.25rem) !important;
            width: calc(50% - 0.25rem) !important;
            min-width: calc(50% - 0.25rem) !important;
            max-width: calc(50% - 0.25rem) !important;
        }

        div.st-emotion-cache-1wmy9hl { width: 100% !important; gap: 0 !important; }
        .main-header h1 { font-size: 1.5rem !important; }
    }
    
    /* Toggle Switch Size Reduction */
    .stCheckbox label {
        font-size: 0.8rem !important;
        color: #64748b !important;
        padding-right: 5px;
    }
    
    /* Removes the padding from stColumns to tightly hug the layout */
    [data-testid="column"] {
        padding: 0 0.2rem !important;
    }
    
    /* Tightly wrap elements vertically */
    .element-container { margin-bottom: 0 !important; }
    
    /* Header Typography Adjustment */
    .main-header {
        text-align: center;
        width: 100%;
        margin-bottom: 0.5rem;
    }
    .main-header h1 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #111;
        margin-bottom: 0.5rem !important;
    }
    
    /* Small wrapper alignment for minimalist right alignment of toggle */
    .table-toggle-wrapper {
        display: flex;
        justify-content: flex-end; /* RTL: right */
        padding-top: 5px;
        padding-bottom: 5px;
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

    if "password_correct" not in st.session_state:
        st.text_input("נא להזין סיסמת גישה", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("נא להזין סיסמת גישה", type="password", on_change=password_entered, key="password")
        st.error("סיסמה שגויה")
        return False
    return True

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
    st.info("כלי זה מיועד לעדכון מהיר בעתיד. קיימת עריכה ישירה בטבלה.")

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

st.markdown('<div class="main-header"><h1>אוסף התקליטים של ירון</h1></div>', unsafe_allow_html=True)

# 4-Button Row Hook (Centered Toolset Width)
st.markdown('<div id="action-buttons-anchor"></div>', unsafe_allow_html=True)
btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
with btn_c1:
    if st.button("הוסף רשומה"):
        add_record_dialog()
with btn_c2:
    if st.button("מחק רשומה"):
        delete_record_dialog()
with btn_c3:
    if st.button("עדכון רשומה"):
        update_record_dialog()
with btn_c4:
    if st.button("העלאת קובץ"):
        upload_csv_dialog()

# Minimalist Toggle (Positioned Right, tightly placed before the grid)
st.markdown('<div class="table-toggle-wrapper">', unsafe_allow_html=True)
show_box = st.checkbox("הצג עמודת קופסא", value=False)
st.markdown('</div>', unsafe_allow_html=True)

# Display Sub-Count neatly above table
st.markdown(f'<div style="text-align: right; margin-top:-5px; margin-bottom:5px;"><p style="font-size:0.8rem; color: #64748b;font-weight:600;">מציג נתונים — עמוד {st.session_state["current_page"] + 1}</p></div>', unsafe_allow_html=True)

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
        "notes": st.column_config.TextColumn("הערות", alignment="right"),
        "name": st.column_config.TextColumn("שם התקליט", alignment="right"),
        "artist": st.column_config.TextColumn("אמן", alignment="right"),
        "box": st.column_config.NumberColumn("קופסא", min_value=1, step=1, alignment="right"),
    }

    # hide_index=True strips the Serial Number exactly as requested.
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,  
        num_rows="fixed",
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

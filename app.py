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
    page_title="אוסף התקליטים",
    layout="wide",
    initial_sidebar_state="expanded",
)

# AirBnB Style + FontAwesome + Left Sidebar
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

    /* Global Font & Text Align adjustments for Hebrew RTL without moving layout */
    body {
        font-family: 'Rubik', sans-serif;
    }

    h1, h2, h3, h4, p, label, .stMarkdown {
        direction: rtl;
        text-align: right;
    }

    /* Buttons - AirBnB style 12px rounded edges */
    [data-testid="stButton"] button {
        border-radius: 12px !important;
        font-weight: 600;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #eaeaea;
        transition: all 0.2s ease-in-out;
    }
    
    [data-testid="stButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    /* Primary button customized to Pastel Green */
    [data-testid="stButton"] button[kind="primary"] {
        background-color: #e5f5e0 !important;
        color: #2e7d32 !important;
        border-color: #a5d6a7 !important;
    }

    /* Target specific buttons via partial class selection or Streamlit hacks */
    /* Delete action styling -> Pastel Red */
    div.delete-btn-container [data-testid="stButton"] button {
        background-color: #ffebee !important;
        color: #c62828 !important;
        border-color: #ef9a9a !important;
    }

    /* Styled Dummy Buttons (Update & Upload) */
    .dummy-btn-blue {
        background-color: #e3f2fd !important;
        color: #1565c0 !important;
        border-color: #90caf9 !important;
    }
    .dummy-btn-grey {
        background-color: #f5f5f5 !important;
        color: #424242 !important;
        border-color: #e0e0e0 !important;
    }

    /* Data Editor Tables - Very Light Pastel Blue Background */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background-color: #F8FAFC !important; 
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    
    /* Ensure Data editor cells reflect RTL orientation correctly */
    [data-testid="stDataEditor"] {
        direction: rtl;
    }

    /* Stat Cards Sidebar */
    .sidebar-stats {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
        margin-bottom: 2rem;
    }
    .sidebar-stat-card {
        background: #ffffff;
        border: 1px solid #eaeaea;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        direction: rtl;
    }
    .sidebar-stat-card .num {
        font-size: 1.6rem;
        font-weight: 700;
        color: #3f51b5;
    }
    .sidebar-stat-card .label {
        font-size: 0.85rem;
        color: #757575;
        margin-top: 0.2rem;
    }

    /* Header */
    .main-header {
        text-align: center;
        padding: 1.2rem 0 0.6rem;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        color: #111;
    }
    .main-header p {
        color: #666;
        font-size: 1rem;
    }
    
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Password Authentication
# ---------------------------------------------------------------------------

def check_password():
    """Returns `True` if the user had the correct password."""
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
    """Fetch all records to support Global String Searching logic."""
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
    st.markdown('<h2 style="text-align: right;"><i class="fas fa-chart-pie"></i> נתונים כלליים</h2>', unsafe_allow_html=True)
    
    total_records = len(df)
    total_artists = df["artist"].nunique() if not df.empty else 0

    # Display Global Stats immediately
    st.markdown(
        f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat-card">
                <div class="num">{total_records}</div>
                <div class="label">סה"כ תקליטים באוסף</div>
            </div>
            <div class="sidebar-stat-card">
                <div class="num">{total_artists}</div>
                <div class="label">אמנים בספרייה</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown('<h2 style="text-align: right;"><i class="fas fa-search"></i> סינון גלובלי</h2>', unsafe_allow_html=True)

    search_query = st.text_input("", placeholder="חיפוש חופשי (אמן, אלבום, הערות)...")

    artists = sorted(df["artist"].dropna().unique()) if not df.empty else []
    selected_artists = st.multiselect("סנן לפי אמנים", artists)

    letters = sorted(df["id_letter"].dropna().unique()) if not df.empty else []
    selected_letters = st.multiselect("סנן לפי אות זיהוי (A-Z, א-ת)", letters)

    st.divider()
    if st.button("רענן מול המסד", use_container_width=True):
        refresh()
        st.rerun()

# ---------------------------------------------------------------------------
# Apply Global Filters to working dataset
# ---------------------------------------------------------------------------

filtered_df = df.copy()

if search_query:
    q = search_query.lower()
    # Search across 3 columns
    mask = filtered_df.apply(
        lambda row: q in str(row.get("artist", "")).lower() or 
                    q in str(row.get("name", "")).lower() or 
                    q in str(row.get("notes", "")).lower(), 
        axis=1
    )
    filtered_df = filtered_df[mask]

if selected_artists:
    filtered_df = filtered_df[filtered_df["artist"].isin(selected_artists)]

if selected_letters:
    filtered_df = filtered_df[filtered_df["id_letter"].isin(selected_letters)]

# Reset pagination automatically if filters eliminate the current page
total_filtered_records = len(filtered_df)
MAX_PAGE = max(0, (total_filtered_records - 1) // 50)
if st.session_state["current_page"] > MAX_PAGE:
    st.session_state["current_page"] = MAX_PAGE

# ---------------------------------------------------------------------------
# Header & Action Buttons (Main Page)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="main-header">'
    '<h1><i class="fas fa-record-vinyl"></i> אוסף התקליטים של ירון</h1>'
    '<p>ניהול אלפביתי וצפייה מינימליסטית באוסף הסאונד</p>'
    '</div>',
    unsafe_allow_html=True,
)


@st.dialog("אישור מחיקה")
def confirm_deletion(record_id, record_desc):
    st.warning(f"האם אתה בטוח שברצונך למחוק את {record_desc}?")
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("כן, מחק", type="primary", use_container_width=True):
            record_store.delete(db, record_id) # Delete remote
            # We don't remove from session_state directly, we just reload data so memory is synced
            load_data() 
            st.success("התקליט נמחק בהצלחה.")
            st.rerun()
    with col_n:
        if st.button("ביטול", use_container_width=True):
            st.rerun()

# Layout Add & Delete sections 
col1, col2 = st.columns(2)

with col1:
    with st.expander("הוספת תקליט חדש", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            st.markdown("<b>פרטי ההקלטה</b>", unsafe_allow_html=True)
            new_artist = st.text_input("שם אומן (נחוץ) *")
            new_name = st.text_input("שם התקליט (נחוץ) *")
            new_notes = st.text_input("הערות נוספות")
            new_box = st.number_input("קופסא (מיקום פיזי)", min_value=1, step=1, value=1)
            new_id_letter = st.text_input("אות זיהוי / סידור", max_chars=1)

            submitted = st.form_submit_button("הוסף תקליט ➕", type="primary", use_container_width=True)
            if submitted:
                if not new_artist or not new_name:
                    st.error("אנא מלא את שדות החובה.")
                else:
                    record_store.add(db, {
                        "box": int(new_box),
                        "id_letter": new_id_letter.strip(),
                        "artist": new_artist.strip(),
                        "name": new_name.strip(),
                        "notes": new_notes.strip(),
                    })
                    load_data()
                    st.success("התקליט נוסף בהצלחה!")
                    st.rerun()

with col2:
    if not filtered_df.empty:
        with st.expander("מחיקת תקליט", expanded=False):
            delete_options = {
                f"{row['artist']} — {row['name']} (קופסא {row['box']})": row["id"]
                for _, row in filtered_df.iterrows()
            }
            selected_delete = st.selectbox("בחר תקליט למחיקה מהרשימה", list(delete_options.keys()))
            
            st.markdown('<div class="delete-btn-container">', unsafe_allow_html=True)
            if st.button("מחק לצמיתות 🗑️", use_container_width=True):
                confirm_deletion(delete_options[selected_delete], selected_delete)
            st.markdown('</div>', unsafe_allow_html=True)


# Layout Placeholder Soft Buttons (Updates Array)
st.markdown("<br/>", unsafe_allow_html=True)
btn_col1, btn_col2, btn_col3 = st.columns([1,1,4])
with btn_col1:
    st.markdown('<div class="dummy-btn-container">', unsafe_allow_html=True)
    st.button("עדכן רשומה", help="Placeholder Update Functionality", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with btn_col2:
    st.markdown('<div class="dummy-btn-container">', unsafe_allow_html=True)
    st.button("העלה CSV", help="Placeholder Upload Functionality", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Manual Pagination using Streamlit subsets and Editable table
# ---------------------------------------------------------------------------

st.markdown('<hr style="border: 1px solid #f0f0f0;" />', unsafe_allow_html=True)
head_col1, head_col2 = st.columns([8, 2])

with head_col1:
    st.markdown('<h3 style="text-align: right;"><i class="fas fa-list"></i> רשימת תקליטים לפי מדד מיון</h3>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: right; color:#888;">מציג 50 מתוך {total_filtered_records} שנמצאו תחת הסינונים.</p>', unsafe_allow_html=True)

with head_col2:
    # State controlled toggle to show/hide box column
    show_box = st.toggle("הצג עמודת קופסא", value=True)

if filtered_df.empty:
    st.info("לא נמצאו תקליטים תחת הסינון הנוכחי.")
else:
    # Pagination Cut
    START_IDX = st.session_state["current_page"] * 50
    END_IDX = START_IDX + 50
    page_df = filtered_df.iloc[START_IDX:END_IDX]

    # Clean display configuration mapping logic (Dropping ID and Id_Letter for minimalism)
    drop_cols = ["id", "sorting_key", "id_letter"]
    if not show_box:
        drop_cols.append("box")
        
    display_df = page_df.drop(columns=drop_cols, errors="ignore")
    
    column_config = {
        "artist": st.column_config.TextColumn("אמן"),
        "name": st.column_config.TextColumn("שם התקליט"),
        "notes": st.column_config.TextColumn("הערות"),
        "box": st.column_config.NumberColumn("קופסא (מיקום)", min_value=1, step=1),
    }

    # Ensure display handles RTL natively gracefully
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",
        key=f"editor_{st.session_state['current_page']}_{hash(search_query)}",
    )

    if not display_df.equals(edited_df):
        if st.button("שמור שינויים למסד", type="primary"):
            for idx in edited_df.index:
                original_row = display_df.loc[idx]
                edited_row = edited_df.loc[idx]
                if not original_row.equals(edited_row):
                    doc_id = filtered_df.loc[idx, "id"]
                    changes = edited_row.to_dict()
                    if "box" in changes:
                        changes["box"] = int(changes["box"])
                    record_store.update(db, doc_id, changes)
            st.success("השינויים נשמרו בצורה מלאה בהצלחה.")
            load_data()  # reload entirely post-save
            st.rerun()

st.markdown("<br/>", unsafe_allow_html=True)

# Footer Paginators
paginator_col_next, paginator_col_pos, paginator_col_prev = st.columns([2, 6, 2])
with paginator_col_next:
    if st.session_state["current_page"] > 0:
        if st.button("הקודם", use_container_width=True):
             st.session_state["current_page"] -= 1
             st.rerun()
             
with paginator_col_prev:
    if st.session_state["current_page"] < MAX_PAGE:
        if st.button("הבא", use_container_width=True):
             st.session_state["current_page"] += 1
             st.rerun()

with paginator_col_pos:
    st.markdown(f'<p style="text-align: center; color: #888;">עמוד {st.session_state["current_page"] + 1} מתוך {MAX_PAGE + 1}</p>', unsafe_allow_html=True)

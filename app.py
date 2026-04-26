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
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# RTL + custom styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap');

    /* Global Font */
    body {
        font-family: 'Rubik', sans-serif;
    }

    /* RTL Layout Fix for Streamlit Sidebar without breaking Mobile Collapse */
    .block-container, [data-testid="stSidebarContent"], [data-testid="stHeader"] {
        direction: rtl;
    }
    
    /* Move sidebar to the right natively */
    [data-testid="stSidebar"] {
        right: 0 !important;
        left: auto !important;
        transform: none !important; /* Prevents center-stretching on mobile when closed */
    }
    
    /* Hide sidebar when closed via native Streamlit aria attributes */
    [data-testid="stSidebar"][aria-expanded="false"] {
        right: -100% !important;
        transform: translateX(100%) !important;
    }
    
    /* Move sidebar collapse button to the right */
    [data-testid="collapsedControl"] {
        right: 1rem !important;
        left: auto !important;
    }

    /* Header */
    .main-header {
        text-align: center;
        padding: 1.2rem 0 0.6rem;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .main-header p {
        color: #888;
        font-size: 1rem;
    }

    /* Stat cards */
    .stat-row {
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
        margin-bottom: 1.2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1rem 1.6rem;
        min-width: 140px;
        flex: 1 1 200px;
        text-align: center;
    }
    .stat-card .num {
        font-size: 1.8rem;
        font-weight: 700;
        color: #7c8aff;
    }
    .stat-card .label {
        font-size: 0.82rem;
        color: #aaa;
        margin-top: 0.15rem;
    }

    /* Data editor tweaks */
    [data-testid="stDataEditor"] {
        direction: rtl;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
    }

    /* Sidebar power numbers */
    .sidebar-stats {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
        margin-bottom: 2rem;
    }
    .sidebar-stat-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .sidebar-stat-card .num {
        font-size: 1.6rem;
        font-weight: 700;
        color: #7c8aff;
    }
    .sidebar-stat-card .label {
        font-size: 0.85rem;
        color: #aaa;
        margin-top: 0.2rem;
    }

    /* --- MOBILE RESPONSIVENESS --- */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.8rem;
        }
        .main-header p {
            font-size: 0.9rem;
        }
        
        /* Adjust native Streamlit spacing for mobile screens */
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 1rem !important;
            max-width: 100vw !important;
            overflow-x: hidden !important;
        }

        /* Force Data Editor Table to restrict its width and handle its own scrollbar */
        div[data-testid="stDataEditor"] {
            width: 100% !important;
            max-width: 100vw !important;
        }

        /* Force columns to stack vertically on all devices under 768px */
        div[data-testid="column"] {
            min-width: 100% !important;
            width: 100% !important;
            margin-bottom: 0.5rem;
        }

        /* Stop headers and elements from breaking layout */
        h1, h2, h3, h4, span, div {
            max-width: 100vw;
            box-sizing: border-box;
        }
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
# State helpers
# ---------------------------------------------------------------------------

def load_page(page_num=0):
    """Fetch paginated records from Firestore."""
    if page_num == 0:
        df, last_doc = record_store.get_page(db, limit=50)
        st.session_state["df"] = df
        st.session_state["last_docs"] = [last_doc]
        st.session_state["current_page"] = 0
    else:
        prev_idx = page_num - 1
        if prev_idx >= 0 and prev_idx < len(st.session_state["last_docs"]):
             start_after_doc = st.session_state["last_docs"][prev_idx]
        else:
             start_after_doc = None
             
        df, last_doc = record_store.get_page(db, limit=50, start_after=start_after_doc)
        st.session_state["df"] = df
        
        if len(st.session_state["last_docs"]) <= page_num:
            st.session_state["last_docs"].append(last_doc)
        else:
            st.session_state["last_docs"][page_num] = last_doc
        
        st.session_state["current_page"] = page_num

def refresh():
    """Clear cached page data so the next run re-fetches."""
    st.session_state["last_docs"] = []
    load_page(0)

if "df" not in st.session_state or "current_page" not in st.session_state:
    st.session_state["last_docs"] = []
    load_page(0)

df = st.session_state["df"]

# ---------------------------------------------------------------------------
# Sidebar — Power Numbers & Filters
# ---------------------------------------------------------------------------

total_records = len(df)
total_boxes = df["box"].nunique() if not df.empty else 0
total_artists = df["artist"].nunique() if not df.empty else 0

with st.sidebar:
    st.header("📋 נתונים לעמוד נוכחי")
    st.markdown(
        f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat-card">
                <div class="num">{total_records}</div>
                <div class="label">תקליטים מוצגים</div>
            </div>
            <div class="sidebar-stat-card">
                <div class="num">{total_boxes}</div>
                <div class="label">קופסאות בשורות אלו</div>
            </div>
            <div class="sidebar-stat-card">
                <div class="num">{total_artists}</div>
                <div class="label">אמנים בעמוד זה</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.header("🔍 סינון בעמוד זה")

    search_query = st.text_input("חיפוש אמן או שם אלבום", placeholder="הקלד טקסט לחיפוש בעמוד...")

    artists = sorted(df["artist"].dropna().unique()) if not df.empty else []
    selected_artists = st.multiselect("סנן לפי אמן (מתוך עמוד זה)", artists)

    boxes = sorted(df["box"].dropna().unique()) if not df.empty else []
    selected_boxes = st.multiselect("סנן לפי מספר קופסה", [int(b) for b in boxes])

    st.divider()
    if st.button("🔄 חזור לעמוד הראשון / רענן", use_container_width=True):
        refresh()
        st.rerun()

# ---------------------------------------------------------------------------
# Apply filters (In memory, over the loaded 50 batch)
# ---------------------------------------------------------------------------

filtered = df.copy()

if search_query:
    q = search_query.lower()
    mask = filtered.apply(
        lambda row: q in str(row.get("artist", "")).lower() or q in str(row.get("name", "")).lower(), 
        axis=1
    )
    filtered = filtered[mask]

if selected_artists:
    filtered = filtered[filtered["artist"].isin(selected_artists)]

if selected_boxes:
    filtered = filtered[filtered["box"].isin(selected_boxes)]

# ---------------------------------------------------------------------------
# Header & Action Buttons (Main Page)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="main-header">'
    "<h1>🎵אוסף התקליטים🎵</h1>"
    "<p>ניהול אלפביתי וצפייה באוסף התקליטים של ירון</p>"
    "</div>",
    unsafe_allow_html=True,
)

@st.dialog("אישור מחיקה")
def confirm_deletion(record_id, record_desc):
    st.warning(f"האם אתה בטוח שברצונך למחוק את {record_desc}?")
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("כן, מחק", type="primary", use_container_width=True):
            record_store.delete(db, record_id)
            st.success("✅ התקליט נמחק!")
            refresh()
            st.rerun()
    with col_n:
        if st.button("ביטול", use_container_width=True):
            st.rerun()

col1, col2 = st.columns(2)

with col1:
    with st.expander("➕ הוספת תקליט חדש"):
        with st.form("add_form", clear_on_submit=True):
            new_box = st.number_input("מספר קופסה *", min_value=1, step=1, value=1)
            new_id_letter = st.text_input("אות זיהוי (למיונים)", max_chars=1)
            new_artist = st.text_input("אמן *")
            new_name = st.text_input("שם התקליט *")
            new_notes = st.text_input("הערות")

            submitted = st.form_submit_button("הוסף תקליט", type="primary", use_container_width=True)
            if submitted:
                if not new_artist or not new_name:
                    st.error("אנא מלא את שדות החובה (אמן ושם התקליט).")
                else:
                    record_store.add(db, {
                        "box": int(new_box),
                        "id_letter": new_id_letter.strip(),
                        "artist": new_artist.strip(),
                        "name": new_name.strip(),
                        "notes": new_notes.strip(),
                    })
                    st.success(f"✅ התקליט '{new_name}' נוסף בהצלחה!")
                    refresh()
                    st.rerun()

with col2:
    if not filtered.empty:
        with st.expander("🗑️ מחיקת תקליט"):
            delete_options = {
                f"{row['artist']} — {row['name']} (קופסה {row['box']})": row["id"]
                for _, row in filtered.iterrows()
            }
            selected_delete = st.selectbox("בחר תקליט למחיקה", list(delete_options.keys()))
            if st.button("מחק", type="secondary", use_container_width=True):
                confirm_deletion(delete_options[selected_delete], selected_delete)

# ---------------------------------------------------------------------------
# Editable table
# ---------------------------------------------------------------------------

st.subheader("📀 רשימת תקליטים - עמוד ממוין")

if filtered.empty:
    st.info("לא נמצאו תקליטים בעמוד זה. הוסף תקליטים חדשים או נווט בעמודים.")
else:
    display_df = filtered.drop(columns=["id", "sorting_key"], errors="ignore")
    column_config = {
        "box": st.column_config.NumberColumn("קופסה", min_value=1, step=1),
        "id_letter": st.column_config.TextColumn("אות זיהוי"),
        "artist": st.column_config.TextColumn("אמן"),
        "name": st.column_config.TextColumn("שם התקליט"),
        "notes": st.column_config.TextColumn("הערות"),
    }
    
    table_key = f"record_table_{st.session_state['current_page']}_{hash(search_query)}"

    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",
        key=table_key,
    )

    if not display_df.equals(edited_df):
        if st.button("💾 שמור שינויים בטבלה", type="primary"):
            for idx in edited_df.index:
                original_row = display_df.loc[idx]
                edited_row = edited_df.loc[idx]
                if not original_row.equals(edited_row):
                    doc_id = filtered.loc[idx, "id"]
                    changes = edited_row.to_dict()
                    changes["box"] = int(changes["box"])
                    record_store.update(db, doc_id, changes)
            st.success("✅ השינויים נשמרו!")
            refresh()
            st.rerun()

st.divider()

col_prev, _, col_next = st.columns([1, 2, 1])
with col_next:
    if st.button("עמוד הבא ⬅️", use_container_width=True):
         if not df.empty and len(df) == 50:
             load_page(st.session_state["current_page"] + 1)
             st.rerun()
             
with col_prev:
    if st.button("➡️ עמוד קודם", use_container_width=True):
         if st.session_state["current_page"] > 0:
             load_page(st.session_state["current_page"] - 1)
             st.rerun()

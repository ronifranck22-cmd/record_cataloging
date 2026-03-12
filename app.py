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

def load_records() -> pd.DataFrame:
    """Fetch records from Firestore."""
    return record_store.get_all(db)

def refresh():
    """Clear cached data so the next run re-fetches from Firestore."""
    st.cache_data.clear()
    if "df" in st.session_state:
        del st.session_state["df"]

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

if "df" not in st.session_state:
    st.session_state["df"] = load_records()

df = st.session_state["df"]

# ---------------------------------------------------------------------------
# Sidebar — Power Numbers & Filters
# ---------------------------------------------------------------------------

total_records = len(df)
total_boxes = df["box"].nunique() if not df.empty else 0
total_artists = df["artist"].nunique() if not df.empty else 0

with st.sidebar:
    st.header("� נתונים כלליים")
    
    # Power Numbers in Sidebar
    st.markdown(
        f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat-card">
                <div class="num">{total_records}</div>
                <div class="label">תקליטים</div>
            </div>
            <div class="sidebar-stat-card">
                <div class="num">{total_boxes}</div>
                <div class="label">קופסאות</div>
            </div>
            <div class="sidebar-stat-card">
                <div class="num">{total_artists}</div>
                <div class="label">אמנים שונים</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.header("�🔍 סינון וחיפוש")

    search_query = st.text_input("חיפוש אמן או שם אלבום", placeholder="הקלד טקסט לחיפוש...")

    artists = sorted(df["artist"].dropna().unique()) if not df.empty else []
    selected_artists = st.multiselect("סנן לפי אמן", artists)

    boxes = sorted(df["box"].dropna().unique()) if not df.empty else []
    selected_boxes = st.multiselect("סנן לפי מספר קופסה", [int(b) for b in boxes])

    st.subheader("מיון")
    
    # Map friendly Hebrew names to actual columns to make sorting functional and responsive
    sort_options = {
        "מספר קופסה": "box",
        "אמן": "artist",
        "שם התקליט": "name",
        "תגית (מחיר/טקסט)": "tag",
        "גרסה": "version"
    }
    
    sort_label = st.selectbox("מיין לפי", list(sort_options.keys()), index=0)
    sort_col = sort_options[sort_label]
    sort_asc = st.toggle("סדר עולה (א→ת / 1→9)", value=True)

    st.divider()
    if st.button("🔄 רענן נתונים", use_container_width=True):
        refresh()
        st.rerun()

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------

filtered = df.copy()

if search_query:
    q = search_query.lower()
    # Free-text search by Artist or Album Name specifically
    mask = filtered.apply(
        lambda row: q in str(row.get("artist", "")).lower() or q in str(row.get("name", "")).lower(), 
        axis=1
    )
    filtered = filtered[mask]

if selected_artists:
    filtered = filtered[filtered["artist"].isin(selected_artists)]

if selected_boxes:
    filtered = filtered[filtered["box"].isin(selected_boxes)]

# Apply sorting
if sort_col == "box":
    filtered = filtered.sort_values(by=["box", "artist"], ascending=[sort_asc, True], ignore_index=True)
else:
    filtered = filtered.sort_values(by=sort_col, ascending=sort_asc, ignore_index=True)

# ---------------------------------------------------------------------------
# Header & Action Buttons (Main Page)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="main-header">'
    "<h1>🎵אוסף התקליטים🎵</h1>"
    "<p>ניהול וצפייה באוסף התקליטים של ירון</p>"
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

# Put Action Buttons directly under the main header
col1, col2 = st.columns(2)

with col1:
    with st.expander("➕ הוספת תקליט חדש"):
        with st.form("add_form", clear_on_submit=True):
            new_artist = st.text_input("אמן *")
            new_name = st.text_input("שם התקליט *")
            new_version = st.text_input("גרסה", value="אלבום")
            new_box = st.number_input("מספר קופסה *", min_value=1, step=1, value=1)
            new_tag = st.text_input("תגית (מחיר/טקסט)", value="0")

            submitted = st.form_submit_button("הוסף תקליט", type="primary", use_container_width=True)
            if submitted:
                if not new_artist or not new_name:
                    st.error("אנא מלא את שדות החובה (אמן ושם התקליט).")
                else:
                    record_store.add(db, {
                        "box": int(new_box),
                        "artist": new_artist.strip(),
                        "name": new_name.strip(),
                        "version": new_version.strip(),
                        "tag": new_tag.strip(),
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

st.subheader("📀 רשימת תקליטים")

if filtered.empty:
    st.info("לא נמצאו תקליטים. הוסף תקליטים חדשים למעלה או שנה את הסינון.")
else:
    display_df = filtered.drop(columns=["id"])
    column_config = {
        "box": st.column_config.NumberColumn("קופסה", min_value=1, step=1),
        "artist": st.column_config.TextColumn("אמן"),
        "name": st.column_config.TextColumn("שם התקליט"),
        "version": st.column_config.TextColumn("גרסה"),
        "tag": st.column_config.TextColumn("תגית (מחיר/טקסט)"),
    }
    
    # We use a dynamic format for the key. If the user changes sort order or search, the table key changes.
    # This completely overrides Streamlit's built-in frontend state memory, fixing unresponsive sorting.
    table_key = f"record_table_{sort_col}_{sort_asc}_{hash(search_query)}"

    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",
        key=table_key,
    )

    # Detect edits
    if not display_df.equals(edited_df):
        if st.button("💾 שמור שינויים בטבלה", type="primary"):
            for idx in edited_df.index:
                original_row = display_df.loc[idx]
                edited_row = edited_df.loc[idx]
                if not original_row.equals(edited_row):
                    doc_id = filtered.loc[idx, "id"]
                    changes = edited_row.to_dict()
                    # Ensure correct types
                    changes["box"] = int(changes["box"])
                    record_store.update(db, doc_id, changes)
            st.success("✅ השינויים נשמרו!")
            refresh()
            st.rerun()

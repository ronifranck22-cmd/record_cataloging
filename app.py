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
)

# RTL + custom styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap');

    /* Global RTL */
    html, body, [class*="stApp"] {
        direction: rtl;
        font-family: 'Rubik', sans-serif;
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

    /* Sidebar */
    section[data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
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
        # Get password from st.secrets
        # We use a default here just in case it's not set up yet, but you should change it!
        correct_password = st.secrets.get("app_password")
        
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password in session
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
# Header
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="main-header">'
    "<h1>🎵 אוסף התקליטים</h1>"
    "<p>ניהול וצפייה באוסף התקליטים המשפחתי</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

if "df" not in st.session_state:
    st.session_state["df"] = load_records()

df = st.session_state["df"]

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🔍 סינון")

    search_query = st.text_input("חיפוש חופשי", placeholder="הקלד טקסט לחיפוש...")

    artists = sorted(df["artist"].dropna().unique()) if not df.empty else []
    selected_artists = st.multiselect("אמן", artists)

    boxes = sorted(df["box_number"].dropna().unique()) if not df.empty else []
    selected_boxes = st.multiselect("מספר קופסה", [int(b) for b in boxes])

    st.divider()
    sort_col = st.selectbox("מיין לפי", record_store.FIELDS, index=1)
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
    mask = filtered.apply(
        lambda row: search_query in " ".join(str(v) for v in row.values), axis=1
    )
    filtered = filtered[mask]

if selected_artists:
    filtered = filtered[filtered["artist"].isin(selected_artists)]

if selected_boxes:
    filtered = filtered[filtered["box_number"].isin(selected_boxes)]

filtered = filtered.sort_values(by=sort_col, ascending=sort_asc, ignore_index=True)

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

total_records = len(filtered)
total_boxes = filtered["box_number"].nunique() if not filtered.empty else 0
total_value = int(filtered["estimated_price_ils"].sum()) if not filtered.empty else 0

st.markdown(
    f"""
    <div class="stat-row">
        <div class="stat-card">
            <div class="num">{total_records}</div>
            <div class="label">תקליטים</div>
        </div>
        <div class="stat-card">
            <div class="num">{total_boxes}</div>
            <div class="label">קופסאות</div>
        </div>
        <div class="stat-card">
            <div class="num">₪{total_value:,}</div>
            <div class="label">שווי משוער</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Editable table
# ---------------------------------------------------------------------------

st.subheader("📀 רשימת תקליטים")

if filtered.empty:
    st.info("לא נמצאו תקליטים. הוסף תקליטים חדשים למטה או שנה את הסינון.")
else:
    display_df = filtered.drop(columns=["id"])
    column_config = {
        "box_number": st.column_config.NumberColumn("קופסה", min_value=1, step=1),
        "artist": st.column_config.TextColumn("אמן"),
        "name": st.column_config.TextColumn("שם התקליט"),
        "version": st.column_config.TextColumn("גרסה"),
        "estimated_price_ils": st.column_config.NumberColumn("מחיר משוער (₪)", min_value=0, step=10),
    }
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",
        key="record_table",
    )

    # Detect edits
    if not display_df.equals(edited_df):
        if st.button("💾 שמור שינויים", type="primary", use_container_width=True):
            for idx in edited_df.index:
                original_row = display_df.loc[idx]
                edited_row = edited_df.loc[idx]
                if not original_row.equals(edited_row):
                    doc_id = filtered.loc[idx, "id"]
                    changes = edited_row.to_dict()
                    # Ensure correct types
                    changes["box_number"] = int(changes["box_number"])
                    changes["estimated_price_ils"] = int(changes["estimated_price_ils"])
                    record_store.update(db, doc_id, changes)
            st.success("✅ השינויים נשמרו!")
            refresh()
            st.rerun()

# ---------------------------------------------------------------------------
# Delete record
# ---------------------------------------------------------------------------

if not filtered.empty:
    with st.expander("🗑️ מחיקת תקליט"):
        delete_options = {
            f"{row['artist']} — {row['name']} (קופסה {row['box_number']})": row["id"]
            for _, row in filtered.iterrows()
        }
        selected_delete = st.selectbox("בחר תקליט למחיקה", list(delete_options.keys()))
        if st.button("מחק", type="secondary"):
            record_store.delete(db, delete_options[selected_delete])
            st.success("✅ התקליט נמחק!")
            refresh()
            st.rerun()

# ---------------------------------------------------------------------------
# Add record
# ---------------------------------------------------------------------------

with st.expander("➕ הוספת תקליט חדש"):
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_artist = st.text_input("אמן *")
            new_name = st.text_input("שם התקליט *")
            new_version = st.text_input("גרסה", value="אלבום")
        with col2:
            new_box = st.number_input("מספר קופסה *", min_value=1, step=1, value=1)
            new_price = st.number_input("מחיר משוער (₪)", min_value=0, step=10, value=0)

        submitted = st.form_submit_button("הוסף תקליט", type="primary", use_container_width=True)
        if submitted:
            if not new_artist or not new_name:
                st.error("אנא מלא את שדות החובה (אמן ושם התקליט).")
            else:
                record_store.add(db, {
                    "box_number": int(new_box),
                    "artist": new_artist.strip(),
                    "name": new_name.strip(),
                    "version": new_version.strip(),
                    "estimated_price_ils": int(new_price),
                })
                st.success(f"✅ התקליט '{new_name}' נוסף בהצלחה!")
                refresh()
                st.rerun()

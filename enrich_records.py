import pandas as pd
import discogs_client
import requests
from bs4 import BeautifulSoup
import time
import re

# ---------------------------------------------------------------------------
# 1. הגדרות
# ---------------------------------------------------------------------------
DISCOGS_USER_TOKEN = "QdmqnJOgqYvlMPpkzCmroWPWtKBzGmdeqsVqfgxX"

INPUT_FILE  = "test.csv"
OUTPUT_FILE = "enriched_test.csv"
ROW_LIMIT   = None    # None = כל הקובץ | מספר = רק N שורות (לבדיקה)
DELAY       = 1.5     # שניות בין שורות

# ---------------------------------------------------------------------------
# 2. תיקון שגיאות כתיב ידועות (לפני כל חיפוש)
# ---------------------------------------------------------------------------
TYPO_FIX = {
    "חווה אלבשרטיין": "חווה אלברשטיין",
    "חווה אלבשרטיין והפלטינה": "חווה אלברשטיין והפלטינה",
    # הוסיפי כאן שגיאות נוספות לפי הצורך
}

# ---------------------------------------------------------------------------
# 3. מיפוי עברית → אנגלית לאמנים ישראלים מרכזיים
# ---------------------------------------------------------------------------
HEBREW_TO_ENGLISH = {
    "חווה אלברשטיין":          "Chava Alberstein",
    "חווה אלברשטיין והפלטינה": "Chava Alberstein Platina",
    "שלום חנוך":               "Shalom Hanoch",
    "אריק איינשטיין":          "Arik Einstein",
    "יהודית רביץ":             "Yehudit Ravitz",
    "ריטה":                    "Rita",
    "אביב גפן":                "Aviv Geffen",
    "יוסי בנאי":               "Yossi Banai",
    "משינה":                   "Mashina",
    "שלמה ארצי":               "Shlomo Artzi",
    "נורית גלרון":             "Nurit Galron",
    "דני ליטני":               "Dani Litani",
    "דודו אלהרר":              "Dudu Elharar",
    "גדי אלון":                "Gadi Alon",
    "גבע אלון":                "Geva Alon",
    "אלג'יר":                  "Aljir",
    "כוורת":                   "Kaveret",
    'להקת הנח"ל':              "Nahal Brigade",
    "תיסלם":                   "Teislem",
    "יהורם גאון":              "Yehoram Gaon",
    "נחמה הנדל":               "Nachama Hendel",
    "אהוד מנור":               "Ehud Manor",
    "אהוד בנאי":               "Ehud Banai",
    "דני רובס":                "Danny Robas",
    "שייקה לוי":               "Shaike Levi",
    "הדג נחש":                 "Hadag Nahash",
    "אסתר עופרים":             "Esther Ofarim",
    "ז'אן ז'אק לורן":         "Jean-Jacques Laurent",
    "ברי סחרוף":               "Berry Sakharof",
    # Amdursky family
    "אסף אמדורסקי":            "Assaf Amdursky",
    "בני אמדורסקי":            "Benny Amdursky",
    # More Israeli artists
    "דני סנדרסון":             "Danny Sanderson",
    "שי גבסו":                 "Shay Gabso",
    "איוב":                    "Iyov",
    "אביהו מדינה":             "Avihu Medina",
    "זוהר ארגוב":              "Zohar Argov",
    "מוסי":                    "Musi",
    "מוסי כץ":                 "Musi Katz",
    "מיקי גבריאלוב":           "Miki Gabrielov",
    "חיים מוסקוביץ":           "Haim Moskovitz",
    "אורי זוהר":               "Uri Zohar",
    "להקת פיקוד המרכז":        "Pikud Hamerkaz",
}

# ---------------------------------------------------------------------------
# 4. מילות רעש להסרה מהחיפוש
# ---------------------------------------------------------------------------
NOISE_RE = re.compile(
    r'\b(\d+|דיסקים|דיסק|CD|מארז|LP|EP|תקליט|תקליטים|תקליטון|'
    r'סינגל|אלבום|Vol\.?|Volume|הופעה\s*פומבית|הקלטה\s*חיה|'
    r'מהדורה|מהדורת|מיוחד|מיוחדת|ספרדית|יידיש)\b',
    flags=re.IGNORECASE | re.UNICODE,
)

# מילים שמעידות על אלבום בכורה / עצמי — ניסיון חיפוש על שם האמן בלבד
DEBUT_WORDS = {"בכורה", "ראשון", "ראשונה", "עצמי", "עצמאי", "debut"}

# ---------------------------------------------------------------------------
# Discogs client
# ---------------------------------------------------------------------------
d = discogs_client.Client('RecordEnricher/1.0', user_token=DISCOGS_USER_TOKEN)

# ---------------------------------------------------------------------------
# פונקציות עזר
# ---------------------------------------------------------------------------

def clean(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("none", "nan", "n/a", "") else s


def apply_typo_fix(artist: str) -> str:
    a = artist.strip()
    return TYPO_FIX.get(a, a)


def remove_noise(text: str) -> str:
    return re.sub(r'\s+', ' ', NOISE_RE.sub('', text)).strip()


def first_n_words(text: str, n: int) -> str:
    return ' '.join(text.split()[:n])


def get_price(release) -> str | None:
    """
    ניסיון רב-שלבי לקבלת מחיר:
      1. marketplace_stats ישירות על אובייקט התוצאה
      2. שליפת release מלאה לפי ID + marketplace_stats
      3. master release marketplace_stats
      4. price_suggestions (ממוצע עסקאות עבר) כ-fallback
    """
    release_id = getattr(release, 'id', None)

    # ── Method 1: marketplace_stats על תוצאת החיפוש ──────────────────────
    try:
        ms = release.marketplace_stats
        if ms and ms.lowest_price:
            v, c = ms.lowest_price.value, ms.lowest_price.currency
            print(f"    💰 Price Found: {v} {c}")
            return f"{v} {c}"
    except Exception:
        pass

    # ── Method 2: שליפת release מלאה לפי ID ─────────────────────────────
    if release_id:
        try:
            full = d.release(release_id)
            ms = full.marketplace_stats
            if ms and ms.lowest_price:
                v, c = ms.lowest_price.value, ms.lowest_price.currency
                print(f"    💰 Price Found (full fetch): {v} {c}")
                return f"{v} {c}"
        except Exception:
            pass

    # ── Method 3: master release ──────────────────────────────────────────
    try:
        master = getattr(release, 'master', None)
        if master:
            ms = master.marketplace_stats
            if ms and ms.lowest_price:
                v, c = ms.lowest_price.value, ms.lowest_price.currency
                print(f"    💰 Price Found (master): ~{v} {c}")
                return f"~{v} {c}"
    except Exception:
        pass

    # ── Method 4: price_suggestions (ממוצע עסקאות עבר) ──────────────────
    if release_id:
        try:
            full = d.release(release_id)
            suggestions = full.price_suggestions
            if suggestions:
                for condition in [
                    'Near Mint (NM or M-)',
                    'Very Good Plus (VG+)',
                    'Very Good (VG)',
                    'Good Plus (G+)',
                ]:
                    if condition in suggestions:
                        p = suggestions[condition]
                        short = condition.split('(')[1].rstrip(')')
                        print(f"    💰 Price Found (suggested {short}): ~{p.value} {p.currency}")
                        return f"~{p.value} {p.currency} ({short})"
        except Exception:
            pass

    print("    ℹ No active listings on Marketplace")
    return None


def discogs_search_once(query: str, label: str, artist_hint: str = ""):
    """
    מחפש פעם אחת בדיסקוגס.
    בודק עד 3 תוצאות ראשונות — מחזיר את הראשונה שמכילה את שם האמן.
    מחזיר (image_url, price_str) או (None, None).
    """
    print(f'    [{label}] שולח לדיסקוגס: "{query}"')
    try:
        results = d.search(query, type='release')
        count = results.count
        print(f'    ← {count} תוצאות')
        if count == 0:
            return None, None

        # בדוק עד 3 תוצאות; עדיף תוצאה שמכילה את שם האמן
        hint_lower = artist_hint.lower()
        best_release = None
        for i in range(min(3, count)):
            rel = results[i]
            if best_release is None:
                best_release = rel  # תמיד שמור לפחות את הראשונה
            # בדוק אם שם האמן מופיע בנתוני התוצאה
            artists_str = " ".join(
                a.get("name", "").lower()
                for a in (getattr(rel, "data", {}).get("artists") or [])
            )
            if hint_lower and hint_lower in artists_str:
                best_release = rel
                break  # מצאנו התאמה טובה

        img       = best_release.thumb or None
        price_str = get_price(best_release)

        return img, price_str

    except Exception as e:
        print(f'    ⚠ שגיאת Discogs: {e}')
        return None, None


def get_discogs_data(artist: str, album: str):
    """
    Fuzzy Multi-Try:
      Pass 0 (debut)  — אמן בלבד אם האלבום מכיל מילת בכורה
      Pass 1 (Hebrew) — עברית מלאה (מנוקה)
      Pass 2 (English)— אנגלית (אם יש מיפוי) + אלבום
      Pass 3 (Broad)  — אמן + 2 מילות האלבום הראשונות
      Pass 4 (artist) — אמן בלבד (last resort)
    """
    cleaned_album  = remove_noise(album)
    cleaned_artist = remove_noise(artist)
    english_artist = HEBREW_TO_ENGLISH.get(artist.strip())
    hint           = english_artist or artist  # hint לזיהוי שם אמן בתוצאות

    # Pass 0: אלבום בכורה / עצמי — נסה אמן בלבד תחילה
    is_debut = bool(DEBUT_WORDS & set(album.split()))

    queries = []
    if is_debut:
        queries.append((cleaned_artist, "Pass 0 בכורה"))

    queries += [
        # Pass 1: עברית מלאה
        (f"{cleaned_artist} {cleaned_album}".strip(), "Pass 1 עברית"),
        # Pass 2: אנגלית (אם קיים מיפוי)
        (
            f"{english_artist} {remove_noise(album)}".strip() if english_artist else None,
            "Pass 2 אנגלית",
        ),
        # Pass 3: אמן + 2 מילות האלבום
        (
            f"{cleaned_artist} {first_n_words(cleaned_album, 2)}".strip(),
            "Pass 3 מצומצם",
        ),
        # Pass 4: אמן בלבד
        (cleaned_artist, "Pass 4 אמן-בלבד"),
    ]

    for query, label in queries:
        if not query:
            continue
        img, price = discogs_search_once(query, label, artist_hint=hint)
        if img or price:
            return img, price

    return None, None


# ---------------------------------------------------------------------------
# Fallback — Stereo-Ve-Mono
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

def scrape_stereo_ve_mono(artist: str, album: str) -> str | None:
    # מחפש בשם העברי המקורי (הכי רלוונטי לאתר הישראלי הזה)
    query = f"{artist} {album}".strip()
    if not query:
        return None

    print(f'    [Stereo-Ve-Mono] מחפש: "{query}"')
    try:
        resp = requests.get(
            "https://stereo-ve-mono.com/",
            params={"s": query},
            headers=HEADERS,
            timeout=12,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        img_tag = (
            soup.select_one(".products .attachment-woocommerce_thumbnail")
            or soup.select_one(".woocommerce-loop-product__link img")
            or soup.select_one(".wp-post-image")
            or soup.select_one("article img")
        )
        if img_tag:
            src = img_tag.get("src") or img_tag.get("data-src", "")
            if src.startswith("http"):
                print(f"    ← תמונה נמצאה ב-Stereo-Ve-Mono")
                return src

    except Exception as e:
        print(f'    ⚠ שגיאת Stereo-Ve-Mono: {e}')

    return None


# ---------------------------------------------------------------------------
# הרצה ראשית
# ---------------------------------------------------------------------------

df_full = pd.read_csv(INPUT_FILE, dtype=str)
df = df_full.head(ROW_LIMIT).copy() if ROW_LIMIT else df_full.copy()
total = len(df)

if 'image_url'    not in df.columns: df['image_url']    = ""
if 'market_price' not in df.columns: df['market_price'] = ""

print(f"🚀 מתחיל הרצה על {total} רשומות מתוך '{INPUT_FILE}'")
print(f"   פלט: {OUTPUT_FILE}\n")

for idx, row in df.iterrows():
    row_num = idx + 1
    raw_artist = clean(row.get('artist'))
    album      = clean(row.get('name'))

    # תיקון שגיאות כתיב
    artist = apply_typo_fix(raw_artist)
    if artist != raw_artist:
        print(f"  [תיקון כתיב] '{raw_artist}' → '{artist}'")

    print(f"\nשורה {row_num}/{total}: {artist} — {album}")

    # ── Three-Strikes בדיסקוגס ─────────────────────────────────────────
    img, price = get_discogs_data(artist, album)

    # ── Fallback: Stereo-Ve-Mono ────────────────────────────────────────
    if not img:
        img = scrape_stereo_ve_mono(raw_artist, album)  # שם עברי מקורי

    # ── שמירה ──────────────────────────────────────────────────────────
    df.at[idx, 'image_url']    = img   if img   else "Not Found"
    df.at[idx, 'market_price'] = price if price else "N/A"

    img_icon   = "✅" if img   else "❌"
    price_icon = "✅" if price else "❌"
    print(f"    תמונה {img_icon}  |  מחיר {price_icon} {price or 'N/A'}")

    # שמירה אחרי כל שורה — כדי שלא תאבדי נתונים אם הסקריפט נקטע
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    time.sleep(DELAY)

# ── סיכום ──────────────────────────────────────────────────────────────────
found_img   = (df['image_url']    != "Not Found").sum()
found_price = (df['market_price'] != "N/A").sum()
print(f"\n✨ סיימתי! {OUTPUT_FILE} מוכן.")
print(f"   תמונות נמצאו : {found_img}/{total}")
print(f"   מחירים נמצאו : {found_price}/{total}")
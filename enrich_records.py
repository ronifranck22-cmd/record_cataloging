import pandas as pd
import discogs_client
import requests
from bs4 import BeautifulSoup
import time
import re

# ---------------------------------------------------------------------------
# 1. הגדרות - הדביקי כאן את הטוקן שלך
# ---------------------------------------------------------------------------
DISCOGS_USER_TOKEN = "QdmqnJOgqYvlMPpkzCmroWPWtKBzGmdeqsVqfgxX"

INPUT_FILE   = "test.csv"
OUTPUT_FILE  = "enriched_test.csv"
ROW_LIMIT    = None   # None = כל הקובץ | מספר = רק N שורות ראשונות (לבדיקה)
DELAY        = 1.5    # שניות בין שורות (Discogs מגביל 60 בקשות/דקה)

# מילות רעש שמורידות את איכות החיפוש
NOISE_WORDS = re.compile(
    r'\b(דיסקים|CD|מארז|LP|תקליט|תקליטים|סינגל|אלבום|Vol\.?|Volume)\b',
    flags=re.IGNORECASE | re.UNICODE,
)

# ---------------------------------------------------------------------------
# התחברות לדיסקוגס
# ---------------------------------------------------------------------------
d = discogs_client.Client('RecordEnricher/1.0', user_token=DISCOGS_USER_TOKEN)

# ---------------------------------------------------------------------------
# פונקציות עזר
# ---------------------------------------------------------------------------

def clean(val) -> str:
    """מנקה ערך — מחזיר מחרוזת ריקה עבור nan/None/ריק."""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("none", "nan", "n/a", "") else s


def remove_noise(text: str) -> str:
    """מסיר מילות רעש וחותך רווחים כפולים."""
    return re.sub(r'\s+', ' ', NOISE_WORDS.sub('', text)).strip()


def broad_query(artist: str, album: str) -> str:
    """שלושת המילים הראשונות של האלבום + אמן — לחיפוש מרוחב."""
    first_words = ' '.join(album.split()[:3])
    return f"{artist} {first_words}".strip()


# ---------------------------------------------------------------------------
# חיפוש בדיסקוגס — Smart Search עם fallback מרוחב
# ---------------------------------------------------------------------------

def get_discogs_data(artist: str, album: str):
    """
    מחזיר (image_url, price_str) או (None, None) אם לא נמצא.
    אסטרטגיה:
      1. query מלא: "{artist} {album}" ← מחקה את שורת החיפוש של האתר
      2. אם 0 תוצאות → broad query: artist + 3 מילות האלבום הראשונות
    """
    for attempt, query in enumerate([
        remove_noise(f"{artist} {album}").strip(),
        remove_noise(broad_query(artist, album)),
    ], start=1):
        if not query:
            continue

        label = "מלא" if attempt == 1 else "מרוחב"
        print(f'    [{label}] שולח לדיסקוגס: "{query}"')

        try:
            results = d.search(query, type='release')
            count = results.count
            print(f'    ← {count} תוצאות')

            if count == 0:
                continue  # מנסה את ה-fallback

            release = results[0]
            img = release.thumb or None

            # מחיר: marketplace_stats
            price_str = None
            try:
                stats = release.fetch('stats') or {}
                lp = stats.get('lowest_price') or {}
                val = lp.get('value') if isinstance(lp, dict) else None
                cur = lp.get('currency', '') if isinstance(lp, dict) else ''
                if val is not None:
                    price_str = f"{val} {cur}".strip()
            except Exception:
                pass

            return img, price_str

        except Exception as e:
            print(f'    ⚠ שגיאת Discogs: {e}')
            continue

    return None, None   # שני הניסיונות נכשלו


# ---------------------------------------------------------------------------
# Fallback — גירוד מ-Stereo-Ve-Mono
# ---------------------------------------------------------------------------

def scrape_stereo_ve_mono(artist: str, album: str) -> str | None:
    """מחפש תמונה ב-stereo-ve-mono.com."""
    query = remove_noise(f"{artist} {album}").strip()
    if not query:
        return None

    try:
        resp = requests.get(
            "https://stereo-ve-mono.com/",
            params={"s": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        img_tag = (
            soup.select_one(".products .attachment-woocommerce_thumbnail")
            or soup.select_one(".woocommerce-loop-product__link img")
            or soup.select_one("article img")
        )
        if img_tag:
            src = img_tag.get("src") or img_tag.get("data-src", "")
            if src.startswith("http"):
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

print(f"🚀 מתחיל הרצה על {total} רשומות...")
print(f"   קובץ קלט:  {INPUT_FILE}")
print(f"   קובץ פלט:  {OUTPUT_FILE}\n")

for idx, row in df.iterrows():
    row_num = idx + 1
    artist  = clean(row.get('artist'))
    album   = clean(row.get('name'))
    print(f"\nשורה {row_num}/{total}: {artist} — {album}")

    # ── ניסיון 1: Discogs ──────────────────────────────────────────────────
    img, price = get_discogs_data(artist, album)

    # ── ניסיון 2: Stereo-Ve-Mono (אם אין תמונה) ───────────────────────────
    if not img:
        print("    → אין תמונה בדיסקוגס, מנסה Stereo-Ve-Mono...")
        img = scrape_stereo_ve_mono(artist, album)
        if img:
            print(f"    ← תמונה נמצאה ב-Stereo-Ve-Mono")

    # ── עדכון ─────────────────────────────────────────────────────────────
    df.at[idx, 'image_url']    = img    if img    else "Not Found"
    df.at[idx, 'market_price'] = price  if price  else "N/A"

    img_icon   = "✅" if img    else "❌"
    price_icon = "✅" if price  else "❌"
    print(f"    תמונה {img_icon}  |  מחיר {price_icon} {price or 'N/A'}")

    # שמירה אחרי כל שורה — כדי שלא תאבדי נתונים אם הסקריפט נקטע
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    time.sleep(DELAY)

# סיכום סופי
found_img   = (df['image_url']    != "Not Found").sum()
found_price = (df['market_price'] != "N/A").sum()
print(f"\n✨ סיימתי! {OUTPUT_FILE} מוכן.")
print(f"   תמונות נמצאו : {found_img}/{total}")
print(f"   מחירים נמצאו : {found_price}/{total}")
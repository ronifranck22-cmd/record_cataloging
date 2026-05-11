"""
enrich_records.py — Vinyl Record Data Enrichment Script
========================================================
Reads test.csv, enriches each row with:
  - image_url   : album cover from Discogs (or Stereo-Ve-Mono fallback)
  - market_price: lowest marketplace price from Discogs (or "N/A")

Output: enriched_test.csv (all original columns preserved)

Setup:
  pip install discogs-client pandas requests beautifulsoup4
  Then paste your Discogs Personal Access Token below.
"""

import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
import discogs_client

# ---------------------------------------------------------------------------
# CONFIG — paste your Discogs Personal Access Token here
# ---------------------------------------------------------------------------
DISCOGS_USER_TOKEN = "YOUR_DISCOGS_TOKEN_HERE"

INPUT_FILE  = "test.csv"
OUTPUT_FILE = "enriched_test.csv"

DELAY_SECONDS = 1.5          # stay well under 60 req/min
REQUEST_TIMEOUT = 8          # seconds before giving up on a web request
MAX_DISCOGS_RESULTS = 3      # how many Discogs results to inspect before giving up

# ---------------------------------------------------------------------------
# Discogs client init
# ---------------------------------------------------------------------------
d = discogs_client.Client(
    "VinylEnricher/1.0",
    user_token=DISCOGS_USER_TOKEN,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(val) -> str:
    """Return a clean string or empty string for None/NaN values."""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("none", "nan", "n/a") else s


def search_discogs(artist: str, album: str) -> tuple[str, str]:
    """
    Search Discogs for artist+album.
    Returns (image_url, market_price) — both "N/A" if nothing found.
    """
    image_url    = "N/A"
    market_price = "N/A"

    if not artist and not album:
        return image_url, market_price

    query = f"{artist} {album}".strip()

    try:
        results = d.search(query, type="release")
        for i, release in enumerate(results):
            if i >= MAX_DISCOGS_RESULTS:
                break

            # --- Image ---
            if image_url == "N/A":
                thumb = getattr(release, "thumb", None)
                if thumb and thumb.startswith("http"):
                    # Prefer the full image over the 150px thumb
                    images = getattr(release.data, "get", lambda k, d=None: d)("images", [])
                    if images and isinstance(images, list) and images[0].get("uri"):
                        image_url = images[0]["uri"]
                    elif thumb:
                        image_url = thumb

            # --- Price ---
            if market_price == "N/A":
                try:
                    stats = release.marketplace_stats
                    if stats and stats.lowest_price:
                        market_price = f"{stats.lowest_price.value} {stats.lowest_price.currency}"
                except Exception:
                    pass

            if image_url != "N/A" and market_price != "N/A":
                break  # got everything we need

    except Exception as e:
        print(f"    ⚠ Discogs error: {e}")

    return image_url, market_price


def search_stereo_ve_mono(artist: str, album: str) -> str:
    """
    Fallback: scrape https://stereo-ve-mono.com/ for an image URL.
    Returns image URL string or "N/A".
    """
    query = f"{artist} {album}".strip()
    if not query:
        return "N/A"

    try:
        resp = requests.get(
            "https://stereo-ve-mono.com/",
            params={"s": query},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "VinylEnricher/1.0"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Site uses standard WooCommerce / WordPress structure
        # Try product thumbnails first, then any <img> inside an article
        img_tag = (
            soup.select_one(".products .attachment-woocommerce_thumbnail")
            or soup.select_one("article img")
            or soup.select_one(".post img")
        )
        if img_tag:
            src = img_tag.get("src") or img_tag.get("data-src", "")
            if src.startswith("http"):
                return src

    except Exception as e:
        print(f"    ⚠ Stereo-Ve-Mono error: {e}")

    return "N/A"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)
    total = len(df)
    print(f"Loaded {total} rows from '{INPUT_FILE}'.\n")

    image_urls    = []
    market_prices = []

    for idx, row in df.iterrows():
        row_num = idx + 1
        artist = _clean(row.get("artist"))
        album  = _clean(row.get("name"))
        label  = f"{artist} — {album}" if artist or album else "(no data)"

        print(f"Row {row_num}/{total}: Searching for {label} ...")

        # --- Primary: Discogs ---
        img, price = search_discogs(artist, album)

        # --- Fallback image: Stereo-Ve-Mono ---
        if img == "N/A":
            print(f"    → No Discogs image, trying Stereo-Ve-Mono ...")
            img = search_stereo_ve_mono(artist, album)

        # --- Result summary ---
        img_status   = "✓ image"   if img   != "N/A" else "✗ no image"
        price_status = f"✓ {price}" if price != "N/A" else "✗ no price"
        print(f"    {img_status}  |  {price_status}")

        image_urls.append(img)
        market_prices.append(price)

        time.sleep(DELAY_SECONDS)

    df["image_url"]    = image_urls
    df["market_price"] = market_prices

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ Done. Output saved to '{OUTPUT_FILE}'.")

    # Quick summary
    found_img   = sum(1 for v in image_urls    if v != "N/A")
    found_price = sum(1 for v in market_prices if v != "N/A")
    print(f"   Images found  : {found_img}/{total}")
    print(f"   Prices found  : {found_price}/{total}")


if __name__ == "__main__":
    main()

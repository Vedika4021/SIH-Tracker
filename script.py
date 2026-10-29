"""
SIH 2026 Submission Tracker — script.py
Tracks SIH26264 submission count hourly via Playwright (headless Chromium).

Why Playwright?
  sih.gov.in/sih2026PS is fully JavaScript-rendered. Plain requests +
  BeautifulSoup only sees the static HTML shell — no PS IDs, no counts.
  Playwright waits for the dynamic table to load before we read the data.

Output: data/sih_history.csv — one clean row appended per run.
Columns: Timestamp, PS_ID, Title, Submissions
"""

import csv
import os
import re
import sys
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
TARGET_PS_ID  = "SIH26264"   # full ID with prefix as shown on the live page
TARGET_PS_NUM = "26264"      # numeric part used for HTML text search
URL           = "https://sih.gov.in/sih2026PS"
CSV_PATH      = "data/sih_history.csv"
CSV_COLUMNS   = ["Timestamp", "PS_ID", "Title", "Submissions"]
PAGE_TIMEOUT  = 60_000       # ms — 60 s for slow govt servers
LOAD_WAIT     = 8_000        # ms — extra wait after networkidle

# Confirmed title — used as fallback if scraper can't extract it from the page
KNOWN_TITLE = (
    "Integrated Dashboard for Monitoring and Tracking "
    "Institution-Related Complaint Cases Across AICTE Bureaus/Cells"
)
# ─────────────────────────────────────────────────────────────────────────────



def scrape_with_playwright() -> dict | None:
    """
    Opens the SIH PS page with headless Chromium, waits for JS to render,
    then locates the row/card for TARGET_PS_NUM and returns:
        { "title": str, "submissions": str }
    Returns None if the PS is not found.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("ERROR: playwright not installed.")
        print("  Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        print(f"-> Opening {URL} ...")
        try:
            page.goto(URL, wait_until="networkidle", timeout=PAGE_TIMEOUT)
        except PWTimeout:
            print("  (networkidle timeout - proceeding with whatever loaded)")

        # Extra buffer to let lazy-loaded data tables fully render
        page.wait_for_timeout(LOAD_WAIT)

        html = page.content()
        browser.close()

    # ── Parse the rendered HTML ──────────────────────────────────────────────
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: standard HTML table rows
    result = _find_in_table(soup)
    if result:
        return result

    # Strategy 2: card / div layout
    result = _find_in_cards(soup)
    if result:
        return result

    print(f"  PS {TARGET_PS_ID} not found in rendered page.")
    return None


def _find_in_table(soup) -> dict | None:
    """Look for TARGET_PS_NUM in any <tr> and extract Title + Submissions."""
    for row in soup.find_all("tr"):
        row_text = row.get_text(" ", strip=True)
        if TARGET_PS_NUM not in row_text:
            continue

        cols = [td.get_text(" ", strip=True) for td in row.find_all("td")]
        if len(cols) < 2:
            continue

        title       = "N/A"
        submissions = "N/A"

        for col in cols:
            # Submission count: "42/500", "42 / 500", or bare "42"
            if re.match(r"^\d+\s*/\s*\d+$", col) or re.match(r"^\d+$", col):
                submissions = col.replace(" ", "")
            elif len(col) > 15 and TARGET_PS_NUM not in col:
                title = col

        if title != "N/A" or submissions != "N/A":
            print(f"  [table] PS {TARGET_PS_ID} -> title='{title[:60]}', subs='{submissions}'")
            return {"title": title, "submissions": submissions}

    return None


def _find_in_cards(soup) -> dict | None:
    """
    Fallback: find any text node containing TARGET_PS_NUM, walk up to a
    card container, and extract title + submission count from it.
    """
    candidates = soup.find_all(string=re.compile(r"\b" + TARGET_PS_NUM + r"\b"))
    for tag_str in candidates:
        parent = tag_str.parent
        if parent is None:
            continue

        container = parent
        for _ in range(6):
            if container is None:
                break
            container = container.parent
            container_text = container.get_text(" ", strip=True)

            count_match = re.search(r"\b(\d+)\s*/\s*(\d+)\b", container_text)
            submissions = count_match.group(0).replace(" ", "") if count_match else "N/A"

            title = "N/A"
            for child in container.find_all(["h5", "h6", "p", "span", "td", "div"]):
                child_text = child.get_text(" ", strip=True)
                if (
                    len(child_text) > 20
                    and TARGET_PS_NUM not in child_text
                    and not re.match(r"^[\d\s/]+$", child_text)
                ):
                    title = child_text[:200]
                    break

            if submissions != "N/A" or title != "N/A":
                print(f"  [card]  PS {TARGET_PS_ID} -> title='{title[:60]}', subs='{submissions}'")
                return {"title": title, "submissions": submissions}

    return None


def append_to_csv(ps_data: dict | None) -> None:
    """
    Append exactly ONE clean row to the CSV.
    Creates the file with a header row if it does not yet exist.
    Uses csv.QUOTE_ALL so titles containing commas never break the layout.
    """
    os.makedirs("data", exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if ps_data is None:
        title, submissions = KNOWN_TITLE, "N/A"
        print(f"  PS not found by scraper — writing row with known title")
    else:
        title       = " ".join(ps_data["title"].split())      # collapse whitespace
        submissions = ps_data["submissions"]
        # If scraper couldn't extract title, use the confirmed one
        if title in ("N/A", "", "NOT_FOUND"):
            title = KNOWN_TITLE

    row = {
        "Timestamp":   timestamp,
        "PS_ID":       TARGET_PS_ID,
        "Title":       title,
        "Submissions": submissions,
    }

    file_is_new = not os.path.isfile(CSV_PATH) or os.path.getsize(CSV_PATH) == 0

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_ALL)
        if file_is_new:
            writer.writeheader()
        writer.writerow(row)

    print(f"Appended row -> {CSV_PATH}")
    print(f"  {row}")


if __name__ == "__main__":
    print(f"=== SIH Tracker | {datetime.now(timezone.utc).isoformat()} ===")
    data = scrape_with_playwright()
    append_to_csv(data)
    print("=== Done ===")
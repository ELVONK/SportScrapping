"""
app.py  –  Odibets vs Flashscore time‑checker

• Scrapes fixtures with headless Selenium (Chrome; falls back to Edge if Chrome
  isn’t installed).
• Waits for the fixture rows to load and clicks cookie banners if present.
• Compares kick‑off times and writes an Excel report (auto‑increments filename
  if the previous one is open/locked).

Dependencies  (install once):
    python -m pip install selenium webdriver-manager beautifulsoup4 pandas xlsxwriter
"""

import os, requests
from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup
from xlsxwriter.exceptions import FileCreateError
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException

# ----- Selenium driver managers & options -----------------------------------
from selenium.webdriver.chrome.options import Options as ChromeOpts
from selenium.webdriver.chrome.service import Service as ChromeSvc
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.edge.options import Options as EdgeOpts
from selenium.webdriver.edge.service import Service as EdgeSvc
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# ----- Selenium support for waits & clicks ----------------------------------
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------------------------------------------------------- #
def make_driver() -> webdriver.Remote:
    """Return a headless driver. Try Chrome first, fall back to Edge."""
    try:
        return _make_chrome()
    except WebDriverException as e:
        if "cannot find Chrome binary" in str(e):
            print("[!] Chrome not found – falling back to Microsoft Edge")
            return _make_edge()
        raise

def _make_chrome() -> webdriver.Chrome:
    opts = ChromeOpts()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    service = ChromeSvc(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

def _make_edge() -> webdriver.Edge:
    opts = EdgeOpts()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    service = EdgeSvc(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=opts)

# --------------------------------------------------------------------------- #
TIMEZONE_OFFSET = timedelta(hours=3)            # Africa/Nairobi (EAT)
TODAY = datetime.now() + TIMEZONE_OFFSET

def _accept_cookies(driver):
    """Click the cookie/GDPR banner if it shows up."""
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        btn.click()
    except TimeoutException:
        pass                                     # no banner

# --------------------------------------------------------------------------- #
def get_odibets_matches() -> list[dict]:
    drv = make_driver()
    drv.get("https://odibets.com/ke/oditoday")   # ensure Kenya endpoint
    _accept_cookies(drv)

    WebDriverWait(drv, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".match-event"))
    )
    soup = BeautifulSoup(drv.page_source, "html.parser")
    drv.quit()

    rows = []
    for row in soup.select(".match-event"):
        try:
            team = row.select_one(".event-title").get_text(strip=True)
            tstr = row.select_one(".event-time").get_text(strip=True)   # HH:MM
            t    = datetime.strptime(tstr, "%H:%M").replace(
                     year=TODAY.year, month=TODAY.month, day=TODAY.day
                   ) + TIMEZONE_OFFSET
            rows.append({"team": team, "time": t})
        except Exception:
            continue
    return rows

# --------------------------------------------------------------------------- #
def get_flashscore_matches() -> list[dict]:
    drv = make_driver()
    drv.get("https://www.flashscore.com/football/")      # football list page
    _accept_cookies(drv)

    WebDriverWait(drv, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".event__match"))
    )
    soup = BeautifulSoup(drv.page_source, "html.parser")
    drv.quit()

    rows = []
    for row in soup.select(".event__match"):
        try:
            home = row.select_one(".event__participant--home").get_text(strip=True)
            away = row.select_one(".event__participant--away").get_text(strip=True)
            team = f"{home} vs {away}"
            tstr = row.select_one(".event__time").get_text(strip=True)
            t    = datetime.strptime(tstr, "%H:%M").replace(
                     year=TODAY.year, month=TODAY.month, day=TODAY.day
                   ) + TIMEZONE_OFFSET
            rows.append({"team": team, "time": t})
        except Exception:
            continue
    return rows

# --------------------------------------------------------------------------- #
def compare_matches(odi, flash):
    now  = TODAY
    fmap = {m["team"].lower(): m["time"] for m in flash}
    today, yest = [], []
    for m in odi:
        if (t := fmap.get(m["team"].lower())):
            if t < now:
                today.append(m)            # late on Odibets
        else:
            yest.append(m)                 # maybe played yesterday
    return pd.DataFrame(today), pd.DataFrame(yest)

# --------------------------------------------------------------------------- #
def save_excel(sheets, base="match_report.xlsx"):
    """Write each non‑empty DataFrame in *sheets* to Excel."""
    if all(df.empty for df in sheets.values()):
        print("[-] No data to write – Excel not generated.")
        return
    fname, idx = base, 0
    while True:
        try:
            with pd.ExcelWriter(fname, engine="xlsxwriter") as w:
                for name, df in sheets.items():
                    if not df.empty:
                        df.to_excel(w, sheet_name=name[:31], index=False)
            print(f"[+] Report saved → {os.path.abspath(fname)}")
            break
        except FileCreateError:
            idx += 1
            fname = base.replace(".xlsx", f"_{idx}.xlsx")

# --------------------------------------------------------------------------- #
def run_cli():
    print("Fetching fixtures…\n")
    odi   = get_odibets_matches()
    flash = get_flashscore_matches()
    print(f"[debug] Scraped {len(odi)} Odibets rows; {len(flash)} Flashscore rows")

    today_df, yest_df = compare_matches(odi, flash)

    print("=== TODAY TIME DISCREPANCIES ===")
    if today_df.empty: print("‒ none ‒")
    else:
        for _, r in today_df.iterrows():
            print(f"{r.team} — {r.time}")

    print("\n=== POSSIBLY PLAYED YESTERDAY ===")
    if yest_df.empty: print("‒ none ‒")
    else:
        for _, r in yest_df.iterrows():
            print(f"{r.team} — {r.time}")

    save_excel({
        "Today Discrepancies": today_df,
        "Possibly Played Yesterday": yest_df
    })

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    run_cli()

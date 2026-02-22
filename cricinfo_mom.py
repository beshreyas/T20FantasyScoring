"""Fetch Player Of The Match from ESPN Cricinfo MVP / match-impact-player page."""

import re
import time
import requests
from bs4 import BeautifulSoup

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _fetch_mvp_page_selenium(url, headless=True, debug_save_path=None):
    """Load ESPN match-impact-player (MVP) page in Chrome; return HTML or None.
    Set headless=False to see the browser window. Optionally save HTML to debug_save_path.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
    except ImportError:
        return None
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1200")
    options.add_argument("--user-agent=" + CHROME_USER_AGENT)
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        if not headless:
            time.sleep(3)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ds-text-overline-2"))
            )
        except Exception:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/cricketers/']"))
            )
        time.sleep(2.5)
        html = driver.page_source
        if debug_save_path and html:
            with open(debug_save_path, "w", encoding="utf-8") as f:
                f.write(html)
        if not headless:
            print("Browser will close in 15 seconds...")
            time.sleep(15)
        return html
    except Exception:
        if debug_save_path and driver:
            try:
                with open(debug_save_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except Exception:
                pass
        return None
    finally:
        if driver:
            driver.quit()


def _parse_mom_from_html(html):
    """Find 'Player Of The Match' block and return the player name from the anchor."""
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    # Method 1: div with class ds-text-overline-2 containing the label
    for div in soup.find_all("div", class_=lambda c: c and "ds-text-overline-2" in str(c)):
        if "Player Of The Match" not in div.get_text():
            continue
        parent = div.find_parent("div")
        if parent:
            link = parent.find("a", href=re.compile(r"/cricketers/"))
            if link:
                return link.get_text(strip=True)
        link = div.find("a", href=re.compile(r"/cricketers/"))
        if link:
            return link.get_text(strip=True)
    # Method 2: any element containing "Player Of The Match", link in parent or grandparent
    for tag in soup.find_all(string=re.compile(r"Player\s+Of\s+The\s+Match", re.I)):
        parent = tag.find_parent("div")
        if not parent:
            continue
        link = parent.find("a", href=re.compile(r"/cricketers/"))
        if link:
            return link.get_text(strip=True)
        grand = parent.find_parent("div")
        if grand:
            link = grand.find("a", href=re.compile(r"/cricketers/"))
            if link:
                return link.get_text(strip=True)
    # Method 3: label and link are siblings - from label's parent, find any /cricketers/ link
    for tag in soup.find_all(string=re.compile(r"Player\s+Of\s+The\s+Match", re.I)):
        wrapper = tag.find_parent("div")
        if wrapper:
            for _ in range(3):
                if not wrapper:
                    break
                link = wrapper.find("a", href=re.compile(r"/cricketers/"))
                if link:
                    return link.get_text(strip=True)
                wrapper = wrapper.find_parent("div")
    # Method 4: regex on raw HTML - first "Player Of The Match" then first /cricketers/ link
    zone = re.search(
        r"Player\s+Of\s+The\s+Match(.{0,2000}?)</a>",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if zone:
        block = zone.group(1)
        m = re.search(
            r"<a\s+[^>]*href=[\"']/cricketers/[^\"']*[\"'][^>]*>(?:<[^>]+>)*([^<]+)",
            block,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
    return None


def get_man_of_the_match(cricinfo_url, headless=True, debug_save_path=None):
    """Get Player Of The Match name from Cricinfo.
    Opens the MVP page (match-impact-player) and parses the player name.
    Returns the player name string or None.
    Set headless=False to see the browser. Set debug_save_path to save page HTML.
    """
    if not cricinfo_url or "/full-scorecard" not in cricinfo_url:
        return None
    mvp_url = cricinfo_url.replace("/full-scorecard", "/match-impact-player")

    html = _fetch_mvp_page_selenium(mvp_url, headless=headless, debug_save_path=debug_save_path)
    if not html:
        try:
            resp = requests.get(mvp_url, timeout=15, headers={"User-Agent": CHROME_USER_AGENT})
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return None
    return _parse_mom_from_html(html)


if __name__ == "__main__":
    import os
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    url = (args[0] if args else "").strip()
    if not url:
        print("Usage: python cricinfo_mom.py <cricinfo_full_scorecard_url> [--visible] [--save-html]")
        print("  --visible    Open browser window so you can see the Cricinfo page load")
        print("  --save-html  Save the MVP page HTML to mvp_page_debug.html")
        sys.exit(1)
    visible = "--visible" in flags
    save_html = "--save-html" in flags
    debug_path = os.path.join(os.path.dirname(__file__), "mvp_page_debug.html") if save_html else None
    if visible:
        print("Opening browser (visible). Waiting for page to load...")
    mom = get_man_of_the_match(url, headless=not visible, debug_save_path=debug_path)
    if debug_path and os.path.isfile(debug_path):
        print("Saved page HTML to:", debug_path)
    print("Man of the match:", mom or "(not found)")

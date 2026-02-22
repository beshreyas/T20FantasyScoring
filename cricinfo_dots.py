"""Fetch dot-ball counts (0s) from ESPNcricinfo full-scorecard page.
Uses the bowling table '0s' column for accurate per-bowler dots.
ESPN scorecard is JS-rendered; we use Selenium when requests returns no tables.
"""

import re
import time
import requests
from bs4 import BeautifulSoup

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _normalize_bowler_name(name):
    """Match bowling.py: strip (c)/(wk), collapse spaces."""
    if not name:
        return ""
    name = re.sub(r"\s*\(c\)\s*", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(wk\)\s*", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*†\s*", " ", name)
    return " ".join(name.split()).strip()


def _fetch_scorecard_selenium(url):
    """Load ESPN full-scorecard in headless Chrome; return page HTML or None."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
    except ImportError:
        return None
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1200")
    options.add_argument("--user-agent=" + CHROME_USER_AGENT)
    for attempt in range(2):
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            try:
                WebDriverWait(driver, 25).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//th[contains(normalize-space(), '0s')]")
                    )
                )
            except Exception:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                )
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            html = driver.page_source
            driver.quit()
            return html
        except Exception:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            if attempt == 0:
                time.sleep(2)
    return None


def _parse_dots_from_soup(soup):
    """Parse the two bowling tables by finding two <th>0s</th> (ESPN class).
    Picks player name and 0s value for all rows in both tables.
    """
    dots = {}
    # Find two <th> with text "0s" (ESPN bowling tables); prefer the one with ds class
    all_th = soup.find_all("th")
    th_0s_list = [th for th in all_th if th.get_text(strip=True).lower() == "0s"]
    th_0s_list = th_0s_list[:2]

    for th_0s in th_0s_list:
        table = th_0s.find_parent("table")
        if not table:
            continue
        header_cells = table.find("thead")
        if header_cells:
            header_cells = header_cells.find_all("th")
        else:
            first_tr = table.find("tr")
            header_cells = first_tr.find_all("th") if first_tr else []
        try:
            idx_0s = [i for i, th in enumerate(header_cells) if th is th_0s][0]
        except IndexError:
            idx_0s = next(
                (i for i, th in enumerate(header_cells) if th.get_text(strip=True).lower() == "0s"),
                -1,
            )
        if idx_0s < 0:
            continue
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else []
        for row in rows:
            row_class = row.get("class") or []
            if "ds-hidden" in " ".join(str(c) for c in row_class):
                continue
            cells = row.find_all("td", recursive=False)
            if len(cells) <= idx_0s:
                continue
            first = cells[0]
            link = first.find("a", href=re.compile(r"/cricketers/"))
            bowler_name = (
                link.get_text(strip=True) if link else first.get_text(strip=True)
            )
            bowler_name = _normalize_bowler_name(bowler_name)
            if not bowler_name:
                continue
            try:
                count = int(cells[idx_0s].get_text(strip=True))
            except (ValueError, TypeError):
                continue
            if bowler_name not in dots:
                dots[bowler_name] = 0
            dots[bowler_name] += count
    return dots


def get_dots_by_bowler_cricinfo(full_scorecard_url):
    """Fetch ESPN full-scorecard; return dict bowler_name -> dot count (0s column).
    ESPN is JS-rendered so we try Selenium first, then requests as fallback.
    """
    if not full_scorecard_url or "/full-scorecard" not in full_scorecard_url:
        return {}
    html = _fetch_scorecard_selenium(full_scorecard_url)
    if not html:
        try:
            resp = requests.get(
                full_scorecard_url,
                timeout=15,
                headers={"User-Agent": CHROME_USER_AGENT},
            )
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException:
            return {}
    soup = BeautifulSoup(html, "lxml")
    return _parse_dots_from_soup(soup)

import sys
import json
sys.path.append('.')
from cricinfo_dots import _fetch_scorecard_selenium, _parse_dots_from_soup
from bs4 import BeautifulSoup
url = "https://www.espncricinfo.com/series/icc-men-s-t20-world-cup-2025-26-1502138/india-vs-south-africa-43rd-match-super-eights-group-1-1512761/full-scorecard"
html = _fetch_scorecard_selenium(url)
soup = BeautifulSoup(html, "lxml")
all_th = soup.find_all("th")
th_0s_list = [th for th in all_th if th.get_text(strip=True).lower() == "0s"]
print(f"Found {len(th_0s_list)} '0s' columns")
for th in th_0s_list[:2]:
    table = th.find_parent("table")
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else []
    print(f"Table has {len(rows)} rows")
    for row in rows:
        cells = row.find_all("td", recursive=False)
        if len(cells) > 0:
            print("Row:", [c.get_text(strip=True) for c in cells])
dots = _parse_dots_from_soup(soup)
print(f"Parsed dots: {dots}")

import sys
sys.path.append('.') # Add current directory to Python path
from cricinfo_dots import get_dots_by_bowler_cricinfo
url = "https://www.espncricinfo.com/series/icc-men-s-t20-world-cup-2024-1411166/india-vs-south-africa-final-1415755/full-scorecard"
try:
    dots = get_dots_by_bowler_cricinfo(url)
    print(f"Dot balls: {dots}")
except Exception as e:
    import traceback
    traceback.print_exc()

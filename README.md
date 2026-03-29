<H2>Cricket Hub - Cricket API 2.0</H2>
This is a simple Flask web application that provides an API and a user-friendly website to retrieve Player Stats, Live Scores, Fixtures, Tables, and Results data of Cricket Matches (ODI, T20, Test, and IPL) from Cricbuzz and ESPN Cricinfo.

<h2>Website Features</h2>
<p>The application now includes a website accessible with the following features:</p>
<ul>
  <li>🎯 <strong>Live Scores:</strong> View live scores of ongoing matches with real-time updates.</li>
  <li>📅 <strong>Schedule:</strong> Check the schedule of upcoming matches, including dates and teams.</li>
  <li>👤 <strong>Player Stats:</strong> Search for player statistics, including batting and bowling career summaries.</li>
  <li>⚖️ <strong>Compare Players:</strong> Compare two players' stats side by side for better insights.</li>
</ul>

<h2>API Endpoints</h2>
<p>The application provides the following API endpoints:</p>

<h3>GET  /players/{player_name}</h3>
<p>This endpoint retrieves information about a cricket player with the given name. The player name should be provided as a URL parameter.</p>
<p>The API returns a JSON object with the following structure:</p>
<pre><code>[
    {
        "Player Name": "Player Name",
        "Country": "Country",
        "Role": "Role",
        "Batting Career Summary 1": {
            "Mode1": "Test",
            "Matches": "Matches",
            "Runs": "Runs",
            "HS": "HS",
            "Avg": "Avg",
            "SR": "SR",
            "100s": "100s",
            "50s": "50s"
        },
        "Batting Career Summary2": {
            "Mode2": "ODI",
            "Matches": "Matches",
            "Runs": "Runs",
            "HS": "HS",
            "Avg": "Avg",
            "SR": "SR",
            "100s": "100s",
            "50s": "50s"
        },
        "Batting Career Summary3": {
            "Mode2": "T20I",
            "Matches": "Matches",
            "Runs": "Runs",
            "HS": "HS",
            "Avg": "Avg",
            "SR": "SR",
            "100s": "100s",
            "50s": "50s"
        }
    }
]</code></pre>

<h3>GET /schedule</h3>
<p>The API returns a JSON array containing the details of upcoming matches, including date, teams, and tournament.</p>
<p>The API returns a JSON object with the following structure:</p>
<pre><code>
[
    "India vs South Africa, 1st ODI",
    "India vs South Africa, 2nd ODI",
    // ... additional matches
]
</code></pre>

<h3>GET /live</h3>
<p>The API returns a JSON array containing the details of live matches, including team names, scores, and overs played.</p>
<p>The API returns a JSON object with the following structure:</p>
<pre><code>
[
    "RCB196-7 (20 Ovs) CSK9-2 (2.3 Ovs) Chennai Super Kings need 188 runs",
    // ... additional live matches
]
</code></pre>

<h3>GET /t/&lt;slug&gt;/match/&lt;match_id&gt;?series_id=&lt;id&gt;</h3>
<p>Returns completed match data (batting, bowling with dots, fielding, man_of_the_match) from the <strong>ESPN Cricinfo API</strong>. All data comes from a single API call — no Selenium or Chrome needed.</p>
<ul>
  <li><strong>series_id</strong> – ESPN Cricinfo series ID (query param, or set <code>CRICINFO_SERIES_ID</code> in <code>.env</code>).</li>
  <li><strong>match_id</strong> – ESPN Cricinfo match ID (numeric, from the URL path).</li>
</ul>
<p>Example: <code>GET /t/wt20_2026/match/1512760?series_id=1502138</code></p>
<p>See <strong>SETUP.md</strong> for details on finding series and match IDs.</p>

<h2>Live Score</h2>
<ul>
  <li>Live Score of all the Matches Going on present</li>
</ul>

<h2>Schedule</h2>
<ul>
  <li>Schedule of the next Upcoming Matches</li>
</ul>

<h2>Individual Player Stats</h2>
<ul>
  <li>Example: Stats of Virat Kohli | You can use the common name of the Players as well to retrieve the details</li>
</ul>

<h2>Player Comparison</h2>
<ul>
  <li>Compare two players' batting and bowling statistics side by side.</li>
</ul>

<h2>Update 🚀</h2>
<p>The API and website have been enhanced with new features and improvements:</p>
<ul>
  <li>🎯 Added a user-friendly UI website for interacting with live scores, player stats, schedule, and player comparison.</li>
  <li>⚡ Optimized the codebase for better performance and reliability.</li>
  <li>🔄 Rebased and updated to ensure compatibility with the latest dependencies.</li>
  <li>📊 <strong>Match endpoint</strong> – All match data (batting, bowling with dots, fielding, man_of_the_match) now comes from the <strong>ESPN Cricinfo API</strong> in a single call. No Selenium or Chrome needed.</li>
  <li>🗑️ <strong>Removed</strong> – Cricbuzz scorecard scraping, Selenium-based Cricinfo scrapers (<code>batting.py</code>, <code>bowling.py</code>, <code>fielding.py</code>, <code>cricinfo_dots.py</code>, <code>cricinfo_mom.py</code>).</li>
</ul>
<p>Enjoy the latest version of the Cricket API and website! 🏏</p>

<h2>For maintainers / next steps</h2>
<ul>
  <li>See <strong>SETUP.md</strong> for setup, match endpoint behaviour, and Cricinfo API details.</li>
  <li>All match data comes from ESPN Cricinfo's <code>hs-consumer-api</code> (undocumented). If this API changes, update <code>scrape_match.py</code>.</li>
  <li>Match and series IDs come from Cricinfo URLs &mdash; see <code>CRICBUZZ_MATCH_URLS.md</code> for details.</li>
</ul>

<H2>Disclaimer ⚠️</H2>
This project is strictly for educational purposes. Not intended for production use. The frontend HTML was generated using GPT
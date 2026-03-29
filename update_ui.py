import re

with open("templates/index.html", "r") as f:
    content = f.read()

# Replace root variables
content = re.sub(
    r":root \{\s+--primary: #0d6efd;\s+--accent: #00c9a7;\s+--dark-bg: #0b0f19;\s+--card-bg: rgba\(255, 255, 255, 0\.06\);\s+--card-border: rgba\(255, 255, 255, 0\.08\);\s+--glow: 0 0 30px rgba\(0, 201, 167, \.15\);\s+\}",
    """:root {
            --primary: #fafafa;
            --accent: #22d3ee;
            --dark-bg: #09090b;
            --card-bg: #18181b;
            --card-border: #27272a;
            --glow: none;
            --text-main: #fafafa;
            --text-muted: #a1a1aa;
        }""",
    content
)

# Replace body styles
content = content.replace("color: #e2e8f0;", "color: var(--text-main);\n            -webkit-font-smoothing: antialiased;")

# Update navbar
nav_css_old = r"""        .navbar {
            background: rgba(11, 15, 25, .85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
        }

        .navbar-brand {
            font-weight: 800;
            font-size: 1.35rem;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            cursor: pointer;
        }

        .nav-link {
            color: #94a3b8 !important;
            font-weight: 600;
            transition: color .2s;
        }

        .nav-link:hover,
        .nav-link.active {
            color: #fff !important;
        }"""
nav_css_new = """        .navbar {
            background: rgba(9, 9, 11, .85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            padding: 0.75rem 0;
            display: flex;
            align-items: center;
        }

        .navbar-brand {
            font-weight: 600;
            font-size: 1.15rem;
            color: var(--text-main) !important;
            letter-spacing: -0.02em;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .nav-tabs-container {
            display: flex;
            gap: 0.25rem;
            background: #18181b;
            padding: 0.35rem;
            border-radius: 9999px;
            border: 1px solid var(--card-border);
            margin: 0 auto;
        }

        .nav-link {
            color: var(--text-muted) !important;
            font-weight: 500;
            font-size: 0.85rem;
            padding: 0.35rem 1.25rem !important;
            border-radius: 9999px;
            transition: all 0.2s ease;
            cursor: pointer;
        }

        .nav-link:hover {
            color: var(--text-main) !important;
        }

        .nav-link.active {
            color: #09090b !important;
            background-color: var(--text-main) !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }"""
content = content.replace(nav_css_old, nav_css_new)


hero_css_old = r"""        .hero {
            padding: 4.5rem 0 3rem;
            text-align: center;
            background: radial-gradient(ellipse at 50% 0%, rgba(13, 110, 253, .12) 0%, transparent 70%);
        }

        .hero h1 {
            font-weight: 800;
            font-size: 2.6rem;
        }

        .hero h1 span {
            background: linear-gradient(135deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero p {
            color: #94a3b8;
            max-width: 520px;
            margin: .75rem auto 0;
        }"""
hero_css_new = """        .hero { display: none; }
        .hero h1 { display: none; }
        .hero h1 span { display: none; }
        .hero p { display: none; }"""
content = content.replace(hero_css_old, hero_css_new)

# Clean up buttons
btn_old = r"""        .btn-accent {
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border: none;
            color: #fff;
            font-weight: 600;
            border-radius: 12px;
            padding: .65rem 1.5rem;
            transition: opacity .2s;
        }

        .btn-accent:hover {
            opacity: .88;
            color: #fff;
        }"""
btn_new = """        .btn-accent {
            background: #fafafa;
            border: 1px solid #fafafa;
            color: #09090b;
            font-weight: 500;
            font-size: 0.85rem;
            border-radius: 8px;
            padding: .5rem 1rem;
            transition: opacity .2s;
        }

        .btn-accent:hover {
            opacity: .85;
            color: #09090b;
        }"""
content = content.replace(btn_old, btn_new)

view_anim = """.view-section {
            display: none;
            opacity: 0;
            animation: fadeIn 0.3s ease forwards;
        }

        @keyframes fadeIn {
            to { opacity: 1; }
        }

        .view-section.active {
            display: block;
        }"""
content = content.replace(".view-section {\n            display: none;\n        }\n\n        .view-section.active {\n            display: block;\n        }", view_anim)


glass_card_old = r"""        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: transform .25s, box-shadow .25s;
        }

        .glass-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--glow);
        }

        .glass-card h5 {
            font-weight: 700;
            margin-bottom: .75rem;
        }

        .section-title {
            font-weight: 700;
            font-size: 1.35rem;
            margin-bottom: 1.25rem;
        }"""
glass_card_new = """        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: border-color .2s;
        }

        .glass-card:hover {
            border-color: #3f3f46;
        }

        .glass-card h5 {
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: .75rem;
            color: var(--text-main);
        }

        .section-title {
            font-weight: 600;
            font-size: 1.15rem;
            margin-bottom: 1.25rem;
            letter-spacing: -0.01em;
            color: var(--text-main);
        }"""
content = content.replace(glass_card_old, glass_card_new)

tourn_card_old = r"""        /* Tournament cards */
        .tournament-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            cursor: pointer;
            transition: transform .25s, box-shadow .25s, border-color .25s;
        }

        .tournament-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--glow);
            border-color: var(--accent);
        }

        .tournament-card h5 {
            font-weight: 700;
            margin-bottom: .5rem;
        }"""
tourn_card_new = """        /* Tournament cards */
        .tournament-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            cursor: pointer;
            transition: border-color .2s, background .2s;
        }

        .tournament-card:hover {
            background: #27272a;
            border-color: #3f3f46;
        }

        .tournament-card h5 {
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: .5rem;
            color: var(--text-main);
        }"""
content = content.replace(tourn_card_old, tourn_card_new)

nav_html_old = r"""    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg sticky-top">
        <div class="container">
            <a class="navbar-brand" onclick="goHome()">🏏 T20 Fantasy Hub</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navContent">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navContent">
                <!-- Tournament dropdown -->
                <div class="tournament-dropdown ms-3 dropdown">
                    <button class="btn dropdown-toggle" type="button" data-bs-toggle="dropdown"
                        id="tournamentDropdownBtn">
                        Select Tournament
                    </button>
                    <ul class="dropdown-menu" id="tournamentDropdownMenu">
                        <li><span class="dropdown-item text-secondary" style="font-size:.82rem;">Loading…</span></li>
                    </ul>
                </div>

                <ul class="navbar-nav ms-auto" id="navLinks" style="display:none;">
                    <li class="nav-item"><a class="nav-link" href="#"
                            onclick="showView('main'); return false;">Standings</a></li>
                    <li class="nav-item"><a class="nav-link" href="#"
                            onclick="showView('players'); loadRoster(); return false;">Players</a></li>
                    <li class="nav-item"><a class="nav-link" href="#"
                            onclick="showView('addMatch'); loadExistingMatches(); return false;">Matches</a></li>
                </ul>
            </div>
        </div>
    </nav>"""
nav_html_new = """    <!-- Navbar -->
    <nav class="navbar sticky-top">
        <div class="container d-flex flex-wrap align-items-center justify-content-between">
            <a class="navbar-brand" onclick="goHome()">🏏 T20 Hub</a>
            
            <div class="d-flex align-items-center" id="navContent" style="display:none !important;">
                <ul class="nav-tabs-container mb-0 ps-0" id="navLinks" style="list-style:none;">
                    <li><a class="nav-link tab-link active" href="#" onclick="showView('main', this); return false;">Standings</a></li>
                    <li><a class="nav-link tab-link" href="#" onclick="showView('players', this); loadRoster(); return false;">Players</a></li>
                    <li><a class="nav-link tab-link" href="#" onclick="showView('addMatch', this); loadExistingMatches(); return false;">Matches</a></li>
                </ul>
            </div>

            <div class="tournament-dropdown dropdown ms-3">
                <button class="btn dropdown-toggle text-white" type="button" data-bs-toggle="dropdown" id="tournamentDropdownBtn" style="font-size: 0.85rem; font-weight: 500; border: 1px solid var(--card-border); background: #18181b;">
                    Tournament
                </button>
                <ul class="dropdown-menu dropdown-menu-end" id="tournamentDropdownMenu" style="background:#18181b; border: 1px solid var(--card-border);">
                    <li><span class="dropdown-item text-secondary shrink" style="font-size:.82rem;">Loading…</span></li>
                </ul>
            </div>
        </div>
    </nav>"""
content = content.replace(nav_html_old, nav_html_new)


showview_js_old = r"""        /* ========== View Navigation ========== */
        function showView(viewName) {
            document.querySelectorAll('.view-section').forEach(v => v.classList.remove('active'));
            const el = document.getElementById(viewName + 'View');
            if (el) el.classList.add('active');
            window.scrollTo(0, 0);
        }

        function goHome() {
            tournamentSlug = null;
            hideEl(document.getElementById('navLinks'));
            document.getElementById('tournamentDropdownBtn').textContent = 'Select Tournament';
            showView('tournamentPicker');
            loadTournaments();
        }

        function selectTournament(slug, name) {
            tournamentSlug = slug;
            document.getElementById('tournamentDropdownBtn').textContent = name;
            showEl(document.getElementById('navLinks'));
            showView('main');
            fetchTeamsData();
            fetchLeaderboardData();
            // highlight active in dropdown
            document.querySelectorAll('#tournamentDropdownMenu .dropdown-item.tournament-option').forEach(el => {
                el.classList.toggle('active', el.dataset.slug === slug);
            });
        }"""
showview_js_new = """        /* ========== View Navigation ========== */
        function showView(viewName, tabEl = null) {
            document.querySelectorAll('.view-section').forEach(v => {
                v.classList.remove('active');
            });
            const el = document.getElementById(viewName + 'View');
            if (el) el.classList.add('active');

            if (tabEl) {
                document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
                tabEl.classList.add('active');
            }
            window.scrollTo(0, 0);
        }

        function goHome() {
            tournamentSlug = null;
            document.getElementById('navContent').setAttribute('style', 'display:none !important');
            document.getElementById('tournamentDropdownBtn').textContent = 'Tournament';
            showView('tournamentPicker');
            loadTournaments();
        }

        function selectTournament(slug, name) {
            tournamentSlug = slug;
            document.getElementById('tournamentDropdownBtn').textContent = name;
            document.getElementById('navContent').setAttribute('style', '');
            showView('main', document.querySelector('#navLinks .nav-link'));
            fetchTeamsData();
            fetchLeaderboardData();
            // highlight active in dropdown
            document.querySelectorAll('#tournamentDropdownMenu .dropdown-item.tournament-option').forEach(el => {
                el.classList.toggle('active', el.dataset.slug === slug);
            });
        }"""

content = content.replace(showview_js_old, showview_js_new)


with open("templates/index.html", "w") as f:
    f.write(content)

print("updated successfully")

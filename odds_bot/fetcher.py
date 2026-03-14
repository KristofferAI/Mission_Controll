"""
Fetches fixture and odds data from API-Football v3.
Falls back to realistic Norwegian mock data when API_FOOTBALL_KEY is not set.
"""
import requests
from odds_bot.config import API_FOOTBALL_KEY, API_FOOTBALL_HOST, LEAGUE_IDS, SEASON

_BASE_URL = f"https://{API_FOOTBALL_HOST}"
_HEADERS = {
    "x-rapidapi-key": API_FOOTBALL_KEY,
    "x-rapidapi-host": API_FOOTBALL_HOST,
}

# ── Mock data ──────────────────────────────────────────────────────────────────
_MOCK_FIXTURES = [
    {
        "fixture_id": 9001,
        "home_team": "Brann",
        "away_team": "Molde",
        "league_id": 103,
        "date": "2025-06-01T18:00:00+00:00",
        "status": "NS",
    },
    {
        "fixture_id": 9002,
        "home_team": "Rosenborg",
        "away_team": "Viking",
        "league_id": 103,
        "date": "2025-06-01T18:00:00+00:00",
        "status": "NS",
    },
    {
        "fixture_id": 9003,
        "home_team": "Bodø/Glimt",
        "away_team": "Lillestrøm",
        "league_id": 103,
        "date": "2025-06-02T16:00:00+00:00",
        "status": "NS",
    },
]

_MOCK_ODDS = {
    # Brann vs Molde — bookmaker slightly generous on Over 1.5 & BTTS
    9001: {
        "Match Winner": {"Home": 1.85, "Draw": 3.40, "Away": 4.00},
        "Goals Over/Under": {"Over 1.5": 1.62, "Under 1.5": 2.50},  # generous Over 1.5
        "Both Teams Score": {"Yes": 1.92, "No": 1.90},               # generous BTTS Yes
    },
    # Rosenborg vs Viking — bookmaker generous on Away & Over 1.5
    9002: {
        "Match Winner": {"Home": 2.10, "Draw": 3.20, "Away": 3.80},  # generous Away
        "Goals Over/Under": {"Over 1.5": 1.58, "Under 1.5": 2.55},  # generous Over 1.5
        "Both Teams Score": {"Yes": 1.88, "No": 1.94},
    },
    # Bodø/Glimt vs Lillestrøm — strong favourite, generous on Home & Over 1.5
    9003: {
        "Match Winner": {"Home": 1.60, "Draw": 3.60, "Away": 5.50},
        "Goals Over/Under": {"Over 1.5": 1.42, "Under 1.5": 3.10},  # generous Over 1.5
        "Both Teams Score": {"Yes": 1.75, "No": 2.05},
    },
}

_MOCK_RESULTS = {
    9001: {"fixture_id": 9001, "home_goals": 2, "away_goals": 1, "status": "FT",
           "home_team": "Brann", "away_team": "Molde"},
    9002: {"fixture_id": 9002, "home_goals": 1, "away_goals": 1, "status": "FT",
           "home_team": "Rosenborg", "away_team": "Viking"},
    9003: {"fixture_id": 9003, "home_goals": 3, "away_goals": 0, "status": "FT",
           "home_team": "Bodø/Glimt", "away_team": "Lillestrøm"},
}


def _use_mock() -> bool:
    return not API_FOOTBALL_KEY


def get_fixtures(league_id: int, next_n: int = 10) -> list:
    """Return upcoming fixtures for a league."""
    if _use_mock():
        return [f for f in _MOCK_FIXTURES if f["league_id"] == league_id][:next_n]

    resp = requests.get(
        f"{_BASE_URL}/fixtures",
        headers=_HEADERS,
        params={"league": league_id, "season": SEASON, "next": next_n},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    fixtures = []
    for item in data.get("response", []):
        f = item.get("fixture", {})
        teams = item.get("teams", {})
        fixtures.append({
            "fixture_id": f.get("id"),
            "home_team": teams.get("home", {}).get("name", ""),
            "away_team": teams.get("away", {}).get("name", ""),
            "league_id": league_id,
            "date": f.get("date", ""),
            "status": f.get("status", {}).get("short", "NS"),
        })
    return fixtures


def get_odds(fixture_id: int) -> dict:
    """Return parsed odds dict for a fixture."""
    if _use_mock():
        return _MOCK_ODDS.get(fixture_id, {})

    resp = requests.get(
        f"{_BASE_URL}/odds",
        headers=_HEADERS,
        params={"fixture": fixture_id},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    result = {}
    for book in data.get("response", []):
        for bookie in book.get("bookmakers", []):
            for market in bookie.get("bets", []):
                market_name = market.get("name", "")
                values = {}
                for v in market.get("values", []):
                    try:
                        values[v["value"]] = float(v["odd"])
                    except (KeyError, ValueError):
                        pass
                if values:
                    result[market_name] = values
            break  # only first bookie
        break  # only first response item
    return result


def get_fixture_result(fixture_id: int) -> dict:
    """Return final result for a fixture."""
    if _use_mock():
        return _MOCK_RESULTS.get(fixture_id, {
            "fixture_id": fixture_id,
            "home_goals": None,
            "away_goals": None,
            "status": "NS",
            "home_team": "",
            "away_team": "",
        })

    resp = requests.get(
        f"{_BASE_URL}/fixtures",
        headers=_HEADERS,
        params={"id": fixture_id},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    for item in data.get("response", []):
        f = item.get("fixture", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        return {
            "fixture_id": fixture_id,
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "status": f.get("status", {}).get("short", "NS"),
            "home_team": teams.get("home", {}).get("name", ""),
            "away_team": teams.get("away", {}).get("name", ""),
        }
    return {"fixture_id": fixture_id, "home_goals": None, "away_goals": None,
            "status": "NS", "home_team": "", "away_team": ""}


def get_all_upcoming_fixtures(next_n: int = 10) -> list:
    """Return upcoming fixtures from all configured leagues."""
    all_fixtures = []
    for league_id in LEAGUE_IDS:
        all_fixtures.extend(get_fixtures(league_id, next_n=next_n))
    return all_fixtures

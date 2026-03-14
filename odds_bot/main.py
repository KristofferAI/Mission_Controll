"""
OddsBot main orchestrator.

Usage:
  python -m odds_bot.main --run       # Full pipeline: fetch → analyze → build parlays → paper trade → notify
  python -m odds_bot.main --settle    # Settle open parlays from results
  python -m odds_bot.main --notify    # Send Telegram summary only (uses last built parlays)
  python -m odds_bot.main --register  # Register bot only
"""
import sys
import os
import argparse

# Ensure project root is on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db import init_db, list_bots, add_bot
from odds_bot.fetcher import get_all_upcoming_fixtures, get_odds
from odds_bot.analyzer import analyze_match
from odds_bot.parlay_builder import build_parlays
from odds_bot.paper_trader import PaperTrader
from odds_bot.telegram_notifier import send_daily_summary
from odds_bot.result_tracker import check_and_settle

BOT_NAME = "OddsBot"
BOT_TYPE = "odds_football"
BOT_DESCRIPTION = "Football EV parlay bot — Eliteserien & 1.divisjon"


def get_or_register_bot() -> int:
    """Return existing OddsBot ID or register a new one."""
    bots = list_bots()
    for b in bots:
        if b["name"] == BOT_NAME:
            print(f"[OddsBot] Found existing bot: id={b['id']}")
            return b["id"]
    # Register new bot
    add_bot(name=BOT_NAME, bot_type=BOT_TYPE, description=BOT_DESCRIPTION)
    bots = list_bots()
    for b in bots:
        if b["name"] == BOT_NAME:
            print(f"[OddsBot] Registered new bot: id={b['id']}")
            return b["id"]
    raise RuntimeError("Failed to register OddsBot")


def run_full(bot_id: int):
    """Full pipeline: fetch fixtures → analyze → build parlays → paper trade → notify."""
    print("[OddsBot] Starting full pipeline...")

    # 1. Fetch upcoming fixtures
    print("[OddsBot] Fetching upcoming fixtures...")
    fixtures = get_all_upcoming_fixtures(next_n=10)
    print(f"[OddsBot] Found {len(fixtures)} fixtures.")

    if not fixtures:
        print("[OddsBot] No fixtures found. Exiting.")
        return

    # 2. Analyze each fixture for value bets
    all_value_bets = []
    for fixture in fixtures:
        fid = fixture.get("fixture_id")
        odds = get_odds(fid)
        if not odds:
            print(f"[OddsBot]  → No odds for fixture {fid}, skipping.")
            continue
        value_bets = analyze_match(fixture, odds)
        if value_bets:
            print(f"[OddsBot]  → {fixture['home_team']} vs {fixture['away_team']}: {len(value_bets)} value bet(s).")
        all_value_bets.extend(value_bets)

    print(f"[OddsBot] Total value bets found: {len(all_value_bets)}")

    if not all_value_bets:
        print("[OddsBot] No value bets found today. Nothing to parlay.")
        return

    # 3. Build parlays
    parlays = build_parlays(all_value_bets)
    print(f"[OddsBot] Built {len(parlays)} parlay(s).")

    if not parlays:
        print("[OddsBot] No valid parlays built (check constraints).")
        return

    # 4. Paper trade
    trader = PaperTrader(bot_id=bot_id)
    for p in parlays:
        pid = trader.place_parlay(p)
        print(f"[OddsBot]  → Placed parlay '{p['name']}' (id={pid}, odds={p['combined_odds']:.2f}x, stake={p['stake']})")

    # 5. Telegram notification
    print("[OddsBot] Sending Telegram notification...")
    send_daily_summary(parlays)

    print("[OddsBot] Pipeline complete! ✅")


def main():
    init_db()

    parser = argparse.ArgumentParser(description="OddsBot orchestrator")
    parser.add_argument("--run", action="store_true", help="Full pipeline")
    parser.add_argument("--settle", action="store_true", help="Settle open parlays")
    parser.add_argument("--notify", action="store_true", help="Send Telegram notification only")
    parser.add_argument("--register", action="store_true", help="Register bot only")
    args = parser.parse_args()

    bot_id = get_or_register_bot()

    if args.register:
        print(f"[OddsBot] Bot registered/found. ID={bot_id}")

    elif args.run:
        run_full(bot_id)

    elif args.settle:
        print("[OddsBot] Settling open parlays...")
        check_and_settle()

    elif args.notify:
        print("[OddsBot] Sending notification for current open parlays...")
        trader = PaperTrader(bot_id=bot_id)
        open_parlays = trader.get_open_parlays()
        # Convert DB rows to parlay-like dicts with legs for notification
        from src.db import list_parlay_legs
        enriched = []
        for p in open_parlays:
            legs = list_parlay_legs(p["id"])
            enriched.append({
                "name": p["name"],
                "combined_odds": p["combined_odds"],
                "stake": p["stake"],
                "combined_ev": 0.0,
                "reasoning": p.get("reasoning", ""),
                "legs": [
                    {
                        "home_team": leg["home_team"],
                        "away_team": leg["away_team"],
                        "selection": leg["selection"],
                        "odds": leg["odds"],
                    }
                    for leg in legs
                ],
            })
        send_daily_summary(enriched)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

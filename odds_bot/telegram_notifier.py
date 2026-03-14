"""
Telegram notification module for OddsBot daily summaries.
"""
import requests
from odds_bot.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def format_parlay_message(parlays: list) -> str:
    """Format top parlays into a readable Telegram message with emojis."""
    if not parlays:
        return "⚽ *OddsBot Daily Report*\n\nNo value parlays found today. Sit tight! 🔍"

    lines = ["⚽ *OddsBot Daily Parlays* 🎯\n"]
    for i, p in enumerate(parlays, 1):
        lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🏆 *Parlay #{i}* — {p['name']}")
        lines.append(f"📊 Combined Odds: `{p['combined_odds']:.2f}x`")
        lines.append(f"💰 Stake: `NOK {p['stake']:.0f}`")
        lines.append(f"💡 Potential Payout: `NOK {p['stake'] * p['combined_odds']:.0f}`")
        lines.append(f"📈 Combined EV: `{p['combined_ev']:.3f}`")
        lines.append("")
        lines.append("*Legs:*")
        for leg in p.get("legs", []):
            lines.append(
                f"  • {leg['home_team']} vs {leg['away_team']} — "
                f"_{leg['selection']}_ @ `{leg['odds']}`"
            )
        lines.append(f"\n📝 _{p.get('reasoning', '')[:120]}_")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Paper trading only. Not financial advice._")
    return "\n".join(lines)


def send_daily_summary(parlays: list):
    """Send formatted message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TelegramNotifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping.")
        return

    message = format_parlay_message(parlays)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"[TelegramNotifier] Message sent successfully (msg_id={resp.json().get('result', {}).get('message_id')})")
    except requests.RequestException as e:
        print(f"[TelegramNotifier] Failed to send message: {e}")

#!/usr/bin/env python3
"""
Telegram Bot for Sports-Bets.

Funksjoner:
- Nytt bet plassert (automatisk)
- Bet vunnet/tapt (automatisk)
- Daglig sammendrag (automatisk)
- Kommandoer: /status, /balance, /today, /history, /help

Oppsett:
1. Opprett bot med @BotFather på Telegram
2. Få bot token og legg til i .env: TELEGRAM_BOT_TOKEN=your_token
3. Finn chat ID og legg til i .env: TELEGRAM_CHAT_ID=your_chat_id
4. Start bot: python odds_bot/telegram_bot.py
"""
import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta

# Legg til prosjektrot i path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_ROOT, '.env'))

# Logging
log_dir = os.path.join(_ROOT, 'data')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'telegram_bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Sjekk om python-telegram-bot er installert
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    PTB_AVAILABLE = True
except ImportError:
    PTB_AVAILABLE = False
    logger.warning("python-telegram-bot ikke installert. Kun notifikasjonsfunksjoner tilgjengelig.")


# ── Kommando-handlers ─────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start kommando."""
    welcome_message = """
🎯 *Velkommen til Sports-Bets Bot!*

Jeg holder deg oppdatert på dine bets automatisk.

*Tilgjengelige kommandoer:*
/status - Se scheduler status og dagens bets
/balance - Se nåværende bankroll
/today - Dagens anbefalinger og resultater
/history - Siste 10 resultater
/stats - Performance statistikk
/help - Denne hjelpen

_Bot vil automatisk varsle om:_
• Nye bets som plasseres
• Seier eller tap på bets
• Daglig sammendrag kl 22:00
"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help kommando."""
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /status kommando."""
    try:
        from src.db import get_scheduler_status, get_daily_stats, get_balance
        
        scheduler = get_scheduler_status()
        daily = get_daily_stats()
        balance = get_balance()
        
        status_emoji = "🟢" if scheduler.get('is_running') else "🔴"
        
        message = f"""
{status_emoji} *Scheduler Status*

💰 Bankroll: {balance:.0f} NOK
📅 Dagens bets: {daily['bets_placed']} plassert
✅ Seire: {daily['bets_won']} | ❌ Tap: {daily['bets_lost']}
📊 Dagens PnL: {daily['daily_pnl']:+.0f} NOK

*Scheduler:* {'Kjører' if scheduler.get('is_running') else 'Stoppet'}
"""
        if scheduler.get('last_run'):
            last = scheduler['last_run'][:16] if scheduler['last_run'] else 'Aldri'
            message += f"_Siste run: {last}_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Feil i status: {e}")
        await update.message.reply_text("❌ Kunne ikke hente status. Sjekk loggene.")


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /balance kommando."""
    try:
        from src.db import get_balance, get_recommendation_summary
        
        balance = get_balance()
        summary = get_recommendation_summary()
        
        message = f"""
💰 *Bankroll*

Nåværende: {balance:.0f} NOK
Total PnL: {summary['total_pnl']:+.0f} NOK
ROI: {summary['roi_pct']:+.1f}%

*Historikk:*
Seire: {summary['win_count']} | Tap: {summary['total_count'] - summary['win_count']}
Win Rate: {summary['win_rate']:.1f}%
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Feil i balance: {e}")
        await update.message.reply_text("❌ Kunne ikke hente bankroll.")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /today kommando."""
    try:
        from src.db import list_recommendations, get_daily_stats
        
        today = datetime.now().strftime('%Y-%m-%d')
        daily = get_daily_stats()
        recs = list_recommendations(date_from=today, date_to=today)
        
        message = f"""
📅 *Dagens Bets ({today})*

Plassert: {daily['bets_placed']}
Resultater: ✅ {daily['bets_won']} | ❌ {daily['bets_lost']}
PnL: {daily['daily_pnl']:+.0f} NOK
"""
        
        if recs:
            message += "\n*Aktive bets:*\n"
            for r in recs[:5]:  # Vis maks 5
                status = "🟡" if r['status'] == 'open' else ("✅" if r['status'] == 'won' else "❌")
                message += f"{status} {r['match']}: {r['selection']} @ {r['odds']:.2f}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Feil i today: {e}")
        await update.message.reply_text("❌ Kunne ikke hente dagens bets.")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /history kommando."""
    try:
        from src.db import list_recommendations
        
        history = list_recommendations(status='won') + list_recommendations(status='lost')
        history.sort(key=lambda x: x['created_at'], reverse=True)
        
        if not history:
            await update.message.reply_text("Ingen historikk ennå.")
            return
        
        message = "📋 *Siste 10 Resultater*\n\n"
        
        for r in history[:10]:
            status = "✅" if r['status'] == 'won' else "❌"
            pnl = r['pnl']
            sign = "+" if pnl > 0 else ""
            message += f"{status} {r['match']}: {sign}{pnl:.0f} NOK\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Feil i history: {e}")
        await update.message.reply_text("❌ Kunne ikke hente historikk.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats kommando."""
    try:
        from src.db import get_recommendation_summary, get_performance_summary
        
        summary = get_recommendation_summary()
        perf = get_performance_summary()
        
        message = f"""
📊 *Performance Stats*

*Totalt:*
Bets: {perf['total_bets']}
Win Rate: {perf['win_rate']:.1f}%
ROI: {perf['roi_pct']:+.1f}%
PnL: {perf['total_pnl']:+.0f} NOK

*Anbefalinger:*
Plassert: {summary['total_count']}
Seire: {summary['win_count']}
Tap: {summary['total_count'] - summary['win_count']}
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Feil i stats: {e}")
        await update.message.reply_text("❌ Kunne ikke hente statistikk.")


async def cmd_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /fetch kommando - manuell fetch."""
    await update.message.reply_text("🔄 Henter odds...")
    
    try:
        from odds_bot.main import run_pipeline
        count = run_pipeline(auto_place=False)  # Manuell mode
        await update.message.reply_text(f"✅ Fant {count} bets. Sjekk dashboard for detaljer.")
    except Exception as e:
        logger.error(f"Feil i fetch: {e}")
        await update.message.reply_text(f"❌ Feil: {e}")


async def cmd_settle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /settle kommando - manuell settle."""
    await update.message.reply_text("🔍 Sjekker resultater...")
    
    try:
        from odds_bot.main import settle_bets
        count = settle_bets(send_notifications=False)  # Ikke dobbel notifikasjon
        await update.message.reply_text(f"✅ Settlet {count} bets.")
    except Exception as e:
        logger.error(f"Feil i settle: {e}")
        await update.message.reply_text(f"❌ Feil: {e}")


# ── Bot Setup ────────────────────────────────────────────────────────────────
def setup_bot() -> Application:
    """Sett opp og returner bot application."""
    if not PTB_AVAILABLE:
        raise ImportError("python-telegram-bot er ikke installert")
    
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN ikke satt i .env")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Legg til handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CommandHandler("today", cmd_today))
    application.add_handler(CommandHandler("history", cmd_history))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("fetch", cmd_fetch))
    application.add_handler(CommandHandler("settle", cmd_settle))
    
    return application


def run_bot():
    """Start bot i polling mode."""
    if not PTB_AVAILABLE:
        print("❌ python-telegram-bot ikke installert.")
        print("   Kjør: pip install python-telegram-bot")
        return
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN ikke satt i .env")
        return
    
    print("🚀 Starter Telegram Bot...")
    
    try:
        application = setup_bot()
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Feil i bot: {e}", exc_info=True)
        print(f"❌ Feil: {e}")


# ── Notifikasjons-funksjoner (brukes av main.py) ────────────────────────────
def send_telegram_notification(message: str) -> bool:
    """
    Send notifikasjon til Telegram (brukes av andre moduler).
    
    Args:
        message: Melding å sende
    
    Returns:
        True hvis sendt, False ellers
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("Telegram ikke konfigurert")
        return False
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Kunne ikke sende Telegram melding: {e}")
        return False


def notify_bet_placed(bet: dict, stake: float, is_auto: bool = False, paper: bool = True):
    """Send varsel om nytt bet (kalles fra main.py)."""
    mode = "🤖 AUTO" if is_auto else "👤 MANUELL"
    paper_str = "📄 PAPER" if paper else "💰 REAL"
    
    message = f"""🎯 *Nytt Bet Plassert*

🏆 {bet.get('league', 'N/A')}
⚽ {bet.get('match', 'N/A')}
🎯 {bet.get('selection', 'N/A')} @ {bet.get('odds', 0):.2f}
📊 Edge: {bet.get('edge_pct', 0):.1f}%
💰 Stake: {stake:.0f} NOK

{mode} | {paper_str}"""
    
    return send_telegram_notification(message)


def notify_bet_result(match: str, selection: str, won: bool, pnl: float, actual: str):
    """Send varsel om bet resultat (kalles fra main.py)."""
    emoji = "✅ VUNNET" if won else "❌ TAPT"
    sign = "+" if pnl > 0 else ""
    
    message = f"""{emoji} *Bet Resultat*

⚽ {match}
🎯 {selection}
🏁 Resultat: {actual}
💰 PnL: {sign}{pnl:.0f} NOK"""
    
    return send_telegram_notification(message)


def notify_daily_summary():
    """Send daglig sammendrag (kalles fra main.py)."""
    try:
        from src.db import get_recommendation_summary, get_balance, get_daily_stats
        
        summary = get_recommendation_summary()
        balance = get_balance()
        daily = get_daily_stats()
        today = datetime.now().strftime('%Y-%m-%d')
        
        message = f"""📊 *Daglig Sammendrag - {today}*

💰 Bankroll: {balance:.0f} NOK
📈 Total PnL: {summary['total_pnl']:+.0f} NOK
🎯 Win Rate: {summary['win_rate']:.1f}%
📊 Dagens PnL: {daily['daily_pnl']:+.0f} NOK

✅ {daily['bets_won']} seire | ❌ {daily['bets_lost']} tap

_God dag for betting!_ 🚀"""
        
        return send_telegram_notification(message)
    except Exception as e:
        logger.error(f"Feil ved sending av daily summary: {e}")
        return False


# ── Hoved-funksjon ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Telegram Bot for Sports-Bets')
    parser.add_argument('--test', action='store_true', help='Send test melding')
    parser.add_argument('--notify', type=str, help='Send melding: --notify "Din melding"')
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 Sender test melding...")
        success = send_telegram_notification("🧪 *Test*\n\nTelegram bot fungerer! ✅")
        print(f"{'✅ Sendt!' if success else '❌ Feil'}")
    elif args.notify:
        print(f"📤 Sender: {args.notify}")
        success = send_telegram_notification(args.notify)
        print(f"{'✅ Sendt!' if success else '❌ Feil'}")
    else:
        run_bot()

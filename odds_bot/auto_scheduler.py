#!/usr/bin/env python3
"""
Auto Scheduler - Automatisk time-basert kjøring av odds bot.

Kjører:
- 09:00: Hent nye odds, plasser bets
- Hver time: Sjekk resultater, settle bets
- 22:00: Send daglig sammendrag

Bruk:
    python odds_bot/auto_scheduler.py start  # Start scheduler
    python odds_bot/auto_scheduler.py stop   # Stop scheduler
    python odds_bot/auto_scheduler.py status # Sjekk status
"""
import os
import sys
import time
import signal
import logging
import argparse
from datetime import datetime, timedelta
from threading import Thread

# Legg til prosjektrot i path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import schedule
from dotenv import load_dotenv

load_dotenv(os.path.join(_ROOT, '.env'))

# Logging
log_dir = os.path.join(_ROOT, 'data')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'scheduler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Globals
scheduler_thread = None
is_running = False
pid_file = os.path.join(_ROOT, 'data', 'scheduler.pid')


def get_pid() -> int:
    """Hent PID fra pid file hvis den finnes."""
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                return int(f.read().strip())
    except Exception as e:
        logger.warning(f"Kunne ikke lese PID file: {e}")
    return None


def save_pid(pid: int):
    """Lagre PID til file."""
    try:
        with open(pid_file, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        logger.warning(f"Kunne ikke lagre PID: {e}")


def remove_pid():
    """Fjern PID file."""
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception as e:
        logger.warning(f"Kunne ikke fjerne PID file: {e}")


def is_scheduler_running() -> bool:
    """Sjekk om scheduler allerede kjører."""
    pid = get_pid()
    if pid is None:
        return False
    
    # Sjekk om prosessen faktisk kjører
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        # Prosessen kjører ikke, fjern stale PID file
        remove_pid()
        return False


# ── Jobber ───────────────────────────────────────────────────────────────────
def job_fetch_and_place():
    """Hent odds og plasser bets."""
    logger.info("=" * 50)
    logger.info("🚀 Starter scheduled job: Fetch & Place")
    
    try:
        from odds_bot.main import run_pipeline
        count = run_pipeline()
        logger.info(f"✅ Job fullført: {count} bets plassert")
    except Exception as e:
        logger.error(f"❌ Feil i fetch & place job: {e}", exc_info=True)
    
    # Oppdater last_run i database
    try:
        from src.db import update_scheduler_last_run
        update_scheduler_last_run()
    except Exception as e:
        logger.warning(f"Kunne ikke oppdatere last_run: {e}")


def job_settle_bets():
    """Sjekk resultater og settle bets."""
    logger.info("=" * 50)
    logger.info("🔍 Starter scheduled job: Settle Bets")
    
    try:
        from odds_bot.main import settle_bets
        count = settle_bets()
        logger.info(f"✅ Job fullført: {count} bets settled")
    except Exception as e:
        logger.error(f"❌ Feil i settle job: {e}", exc_info=True)


def job_daily_summary():
    """Send daglig sammendrag."""
    logger.info("=" * 50)
    logger.info("📊 Starter scheduled job: Daily Summary")
    
    try:
        from odds_bot.main import notify_daily_summary
        notify_daily_summary()
        logger.info("✅ Daglig sammendrag sendt")
    except Exception as e:
        logger.error(f"❌ Feil i daily summary job: {e}", exc_info=True)


def job_hourly_check():
    """Time-basert sjekk - kombiner settle + eventuelt fetch."""
    hour = datetime.now().hour
    
    # Alltid settle bets
    job_settle_bets()
    
    # Fetch nye odds kun i "åpningstidene"
    if 9 <= hour <= 21:
        logger.info(f"⏰ Time {hour}: Sjekker for nye bets...")
        # Kun hvis det er mer enn 30 minutter siden siste run
        try:
            from src.db import get_scheduler_status
            status = get_scheduler_status()
            last_run = status.get('last_run')
            
            if last_run:
                last = datetime.fromisoformat(last_run)
                if datetime.now() - last < timedelta(minutes=30):
                    logger.info("Siste run var for nylig, hopper over fetch")
                    return
            
            job_fetch_and_place()
        except Exception as e:
            logger.warning(f"Kunne ikke sjekke siste run: {e}")


# ── Scheduler Konfigurasjon ──────────────────────────────────────────────────
def setup_schedule():
    """Sett opp alle scheduled jobs."""
    # Hver time: sjekk resultater
    schedule.every().hour.at(":00").do(job_settle_bets)
    
    # 09:00: Hent nye odds og plasser
    schedule.every().day.at("09:00").do(job_fetch_and_place)
    
    # 12:00: Ekstra fetch midt på dagen
    schedule.every().day.at("12:00").do(job_fetch_and_place)
    
    # 15:00: Ettermiddags fetch
    schedule.every().day.at("15:00").do(job_fetch_and_place)
    
    # 18:00: Kvelds fetch
    schedule.every().day.at("18:00").do(job_fetch_and_place)
    
    # 22:00: Daglig sammendrag
    schedule.every().day.at("22:00").do(job_daily_summary)
    
    logger.info("✅ Schedule konfigurert:")
    for job in schedule.jobs:
        logger.info(f"  - {job}")


def run_scheduler():
    """Hovedloop for scheduler."""
    global is_running
    
    logger.info("🚀 Scheduler starter...")
    setup_schedule()
    
    # Oppdater status i database
    try:
        from src.db import set_scheduler_status
        set_scheduler_status(is_running=True, pid=os.getpid())
    except Exception as e:
        logger.warning(f"Kunne ikke sette scheduler status: {e}")
    
    # Kjør en gang umiddelbart ved start
    logger.info("🔄 Kjører initial settle...")
    job_settle_bets()
    
    is_running = True
    while is_running:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stoppet av bruker (KeyboardInterrupt)")
            break
        except Exception as e:
            logger.error(f"Feil i scheduler loop: {e}", exc_info=True)
            time.sleep(5)  # Vent litt før retry
    
    # Rydd opp
    is_running = False
    try:
        from src.db import set_scheduler_status
        set_scheduler_status(is_running=False)
    except Exception as e:
        logger.warning(f"Kunne ikke oppdatere scheduler status ved stopp: {e}")
    
    remove_pid()
    logger.info("👋 Scheduler stoppet")


# ── Offentlig API ────────────────────────────────────────────────────────────
def start_scheduler() -> bool:
    """
    Start scheduler i bakgrunn.
    
    Returns:
        True hvis scheduler ble startet, False hvis den allerede kjører
    """
    global scheduler_thread
    
    if is_scheduler_running():
        logger.warning("Scheduler kjører allerede!")
        print("⚠️  Scheduler kjører allerede!")
        return False
    
    if scheduler_thread and scheduler_thread.is_alive():
        logger.warning("Scheduler thread kjører allerede!")
        return False
    
    save_pid(os.getpid())
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("✅ Scheduler startet i bakgrunn")
    print("✅ Scheduler startet i bakgrunn")
    print("   - Sjekker resultater hver time")
    print("   - Fetch & place: 09:00, 12:00, 15:00, 18:00")
    print("   - Daglig summary: 22:00")
    
    return True


def stop_scheduler() -> bool:
    """
    Stopp scheduler.
    
    Returns:
        True hvis scheduler ble stoppet, False hvis den ikke kjørte
    """
    global is_running, scheduler_thread
    
    pid = get_pid()
    if pid:
        try:
            # Send SIGTERM til scheduler prosessen
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sendt SIGTERM til scheduler (PID {pid})")
        except (OSError, ProcessLookupError):
            logger.warning(f"Kunne ikke sende signal til PID {pid}")
    
    is_running = False
    remove_pid()
    
    # Oppdater database
    try:
        from src.db import set_scheduler_status
        set_scheduler_status(is_running=False)
    except Exception as e:
        logger.warning(f"Kunne ikke oppdatere status ved stopp: {e}")
    
    logger.info("✅ Scheduler stoppet")
    print("✅ Scheduler stoppet")
    return True


def get_scheduler_status() -> dict:
    """
    Hent scheduler status.
    
    Returns:
        Dict med status informasjon
    """
    running = is_scheduler_running()
    pid = get_pid()
    
    status = {
        'is_running': running,
        'pid': pid,
        'next_runs': [],
    }
    
    if running:
        # Hent schedule info hvis tilgjengelig
        try:
            for job in schedule.jobs:
                next_run = job.next_run
                if next_run:
                    status['next_runs'].append({
                        'job': str(job.job_func.__name__),
                        'next_run': next_run.strftime('%Y-%m-%d %H:%M:%S'),
                    })
        except:
            pass
    
    # Hent fra database også
    try:
        from src.db import get_scheduler_status as get_db_status
        db_status = get_db_status()
        status['db_status'] = db_status
    except Exception as e:
        logger.warning(f"Kunne ikke hente DB status: {e}")
    
    return status


def print_status():
    """Print scheduler status til konsoll."""
    status = get_scheduler_status()
    
    print("\n📊 Scheduler Status")
    print("=" * 40)
    
    if status['is_running']:
        print("🟢 Status: KJØRER")
        if status['pid']:
            print(f"   PID: {status['pid']}")
    else:
        print("🔴 Status: STOPPET")
    
    if status.get('db_status'):
        db = status['db_status']
        if db.get('started_at'):
            print(f"   Startet: {db['started_at'][:19] if db['started_at'] else 'N/A'}")
        if db.get('last_run'):
            print(f"   Siste run: {db['last_run'][:19] if db['last_run'] else 'N/A'}")
    
    if status['next_runs']:
        print("\n⏰ Neste kjøringer:")
        for run in status['next_runs'][:5]:
            print(f"   {run['job']}: {run['next_run']}")
    
    print()


# ── Hoved-funksjon ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Auto Scheduler for Odds Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Eksempler:
  python odds_bot/auto_scheduler.py start    # Start scheduler
  python odds_bot/auto_scheduler.py stop     # Stopp scheduler
  python odds_bot/auto_scheduler.py status   # Sjekk status
  python odds_bot/auto_scheduler.py run      # Kjør én gang (ikke schedule)
        """
    )
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'status', 'run', 'fetch', 'settle'],
        help='Handling å utføre'
    )
    parser.add_argument(
        '--foreground', '-f',
        action='store_true',
        help='Kjør i forgrunn (ikke bakgrunn)'
    )
    
    args = parser.parse_args()
    
    if args.action == 'start':
        if args.foreground:
            print("🚀 Starter scheduler i forgrunn...")
            print("Trykk Ctrl+C for å stoppe\n")
            save_pid(os.getpid())
            run_scheduler()
        else:
            start_scheduler()
            # Hold main thread i live så daemon kan kjøre
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Avslutter...")
                stop_scheduler()
    
    elif args.action == 'stop':
        stop_scheduler()
    
    elif args.action == 'status':
        print_status()
    
    elif args.action == 'run':
        print("🔄 Kjører full pipeline én gang...")
        job_fetch_and_place()
        print("✅ Ferdig!")
    
    elif args.action == 'fetch':
        print("🔄 Henter odds og plasserer bets...")
        job_fetch_and_place()
        print("✅ Ferdig!")
    
    elif args.action == 'settle':
        print("🔍 Sjekker resultater...")
        job_settle_bets()
        print("✅ Ferdig!")


if __name__ == '__main__':
    main()

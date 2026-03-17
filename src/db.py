import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'mc.db')


def get_conn():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # ── Eksisterende tabeller ────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS bankroll (
            id      INTEGER PRIMARY KEY,
            balance REAL    NOT NULL DEFAULT 1000.0,
            updated_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            bot_type    TEXT    DEFAULT 'generic',
            status      TEXT    DEFAULT 'idle',
            description TEXT    DEFAULT '',
            created_at  TEXT,
            last_run    TEXT,
            run_count   INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id            INTEGER,
            match_id          TEXT,
            home_team         TEXT,
            away_team         TEXT,
            stake             REAL,
            odds              REAL,
            predicted_outcome TEXT,
            actual_outcome    TEXT,
            status            TEXT DEFAULT 'open',
            pnl               REAL DEFAULT 0.0,
            created_at        TEXT,
            settled_at        TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id       INTEGER,
            title        TEXT,
            description  TEXT DEFAULT '',
            status       TEXT DEFAULT 'pending',
            created_at   TEXT,
            completed_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS parlays (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id        INTEGER,
            name          TEXT,
            combined_odds REAL,
            stake         REAL,
            status        TEXT DEFAULT 'open',
            pnl           REAL DEFAULT 0.0,
            reasoning     TEXT DEFAULT '',
            created_at    TEXT,
            settled_at    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS parlay_legs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            parlay_id     INTEGER,
            match_id      TEXT,
            home_team     TEXT,
            away_team     TEXT,
            bet_type      TEXT,
            selection     TEXT,
            odds          REAL,
            result        TEXT DEFAULT 'pending',
            actual_result TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id     INTEGER,
            parlay_id  INTEGER,
            match_id   TEXT,
            home_team  TEXT,
            away_team  TEXT,
            bet_type   TEXT,
            selection  TEXT,
            odds       REAL,
            outcome    TEXT,
            reasoning  TEXT,
            learned_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date                TEXT,
            match               TEXT,
            league              TEXT,
            market              TEXT,
            selection           TEXT,
            odds                REAL,
            true_probability    REAL,
            implied_probability REAL,
            edge_pct            REAL,
            recommended_stake   REAL,
            bet_type            TEXT DEFAULT 'single',
            parlay_id           TEXT,
            status              TEXT DEFAULT 'open',
            actual_result       TEXT DEFAULT '',
            pnl                 REAL DEFAULT 0.0,
            created_at          TEXT,
            commence_time       TEXT
        )
    """)
    
    # ── NYE TABELLER ─────────────────────────────────────────────────────────
    
    # Betting log - detaljert logg over alle handlinger
    c.execute("""
        CREATE TABLE IF NOT EXISTS betting_log (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id   INTEGER,
            action              TEXT,  -- 'placed', 'placed_auto', 'settled', 'cancelled'
            timestamp           TEXT,
            details             TEXT
        )
    """)
    
    # Performance stats - aggregering per liga/market/dato
    c.execute("""
        CREATE TABLE IF NOT EXISTS performance_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT,
            league          TEXT,
            market          TEXT,
            bets_placed     INTEGER DEFAULT 0,
            bets_won        INTEGER DEFAULT 0,
            total_staked    REAL DEFAULT 0.0,
            total_pnl       REAL DEFAULT 0.0,
            roi_pct         REAL DEFAULT 0.0,
            updated_at      TEXT
        )
    """)
    
    # Scheduler status
    c.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_status (
            id          INTEGER PRIMARY KEY,
            is_running  INTEGER DEFAULT 0,
            started_at  TEXT,
            last_run    TEXT,
            pid         INTEGER
        )
    """)
    
    # Insert default bankroll hvis ikke finnes
    c.execute(
        "INSERT OR IGNORE INTO bankroll (id, balance, updated_at) VALUES (1, 1000.0, ?)",
        (datetime.utcnow().isoformat(),),
    )
    
    # Insert default scheduler status
    c.execute(
        "INSERT OR IGNORE INTO scheduler_status (id, is_running, started_at) VALUES (1, 0, ?)",
        (datetime.utcnow().isoformat(),),
    )
    
    conn.commit()
    conn.close()


# ── NYE FUNKSJONER FOR BETTING LOG ───────────────────────────────────────────
def log_betting_action(recommendation_id: int, action: str, details: str = ""):
    """Logg en betting-handling til betting_log tabellen."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO betting_log (recommendation_id, action, timestamp, details)
           VALUES (?, ?, ?, ?)""",
        (recommendation_id, action, datetime.utcnow().isoformat(), details),
    )
    conn.commit()
    conn.close()


def get_betting_log(recommendation_id: int = None, limit: int = 100) -> list:
    """Hent betting log, filtrert på recommendation_id hvis oppgitt."""
    conn = get_conn()
    if recommendation_id:
        rows = conn.execute(
            "SELECT * FROM betting_log WHERE recommendation_id=? ORDER BY timestamp DESC LIMIT ?",
            (recommendation_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM betting_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── NYE FUNKSJONER FOR PERFORMANCE STATS ─────────────────────────────────────
def update_performance_stats(league: str, market: str, won: bool, stake: float, pnl: float):
    """Oppdater performance stats for en liga/market kombinasjon."""
    conn = get_conn()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Sjekk om det finnes en rad for i dag
    row = conn.execute(
        "SELECT * FROM performance_stats WHERE date=? AND league=? AND market=?",
        (today, league, market),
    ).fetchone()
    
    if row:
        # Oppdater eksisterende rad
        new_bets_placed = row['bets_placed'] + 1
        new_bets_won = row['bets_won'] + (1 if won else 0)
        new_total_staked = row['total_staked'] + stake
        new_total_pnl = row['total_pnl'] + pnl
        new_roi_pct = (new_total_pnl / new_total_staked * 100) if new_total_staked > 0 else 0
        
        conn.execute(
            """UPDATE performance_stats 
               SET bets_placed=?, bets_won=?, total_staked=?, total_pnl=?, roi_pct=?, updated_at=?
               WHERE id=?""",
            (new_bets_placed, new_bets_won, new_total_staked, new_total_pnl, new_roi_pct,
             datetime.utcnow().isoformat(), row['id']),
        )
    else:
        # Opprett ny rad
        conn.execute(
            """INSERT INTO performance_stats 
               (date, league, market, bets_placed, bets_won, total_staked, total_pnl, roi_pct, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (today, league, market, 1, 1 if won else 0, stake, pnl,
             (pnl / stake * 100) if stake > 0 else 0, datetime.utcnow().isoformat()),
        )
    
    conn.commit()
    conn.close()


def get_performance_stats(date_from: str = None, date_to: str = None, 
                         league: str = None, market: str = None) -> list:
    """Hent performance stats med valgfrie filtre."""
    conn = get_conn()
    query = "SELECT * FROM performance_stats WHERE 1=1"
    params = []
    
    if date_from:
        query += " AND date>=?"
        params.append(date_from)
    if date_to:
        query += " AND date<=?"
        params.append(date_to)
    if league:
        query += " AND league=?"
        params.append(league)
    if market:
        query += " AND market=?"
        params.append(market)
    
    query += " ORDER BY date DESC, league, market"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_performance_summary() -> dict:
    """Hent aggregrert performance summary."""
    conn = get_conn()
    row = conn.execute(
        """SELECT 
            SUM(bets_placed) as total_bets,
            SUM(bets_won) as total_wins,
            SUM(total_staked) as total_staked,
            SUM(total_pnl) as total_pnl
        FROM performance_stats"""
    ).fetchone()
    conn.close()
    
    total_bets = row['total_bets'] or 0
    total_wins = row['total_wins'] or 0
    total_staked = row['total_staked'] or 0
    total_pnl = row['total_pnl'] or 0
    
    return {
        'total_bets': total_bets,
        'total_wins': total_wins,
        'total_losses': total_bets - total_wins,
        'win_rate': (total_wins / total_bets * 100) if total_bets > 0 else 0,
        'total_staked': total_staked,
        'total_pnl': total_pnl,
        'roi_pct': (total_pnl / total_staked * 100) if total_staked > 0 else 0,
    }


# ── NYE FUNKSJONER FOR SCHEDULER STATUS ──────────────────────────────────────
def set_scheduler_status(is_running: bool, pid: int = None):
    """Sett scheduler status i databasen."""
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    
    if is_running:
        conn.execute(
            """UPDATE scheduler_status 
               SET is_running=1, started_at=?, last_run=?, pid=?
               WHERE id=1""",
            (now, now, pid),
        )
    else:
        conn.execute(
            "UPDATE scheduler_status SET is_running=0, pid=NULL WHERE id=1",
        )
    
    conn.commit()
    conn.close()


def get_scheduler_status() -> dict:
    """Hent scheduler status."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM scheduler_status WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {'is_running': 0, 'started_at': None, 'last_run': None, 'pid': None}


def update_scheduler_last_run():
    """Oppdater last_run timestamp."""
    conn = get_conn()
    conn.execute(
        "UPDATE scheduler_status SET last_run=? WHERE id=1",
        (datetime.utcnow().isoformat(),),
    )
    conn.commit()
    conn.close()


# ── Bankroll ─────────────────────────────────────────────────────────────────
def get_balance() -> float:
    conn = get_conn()
    row = conn.execute("SELECT balance FROM bankroll WHERE id=1").fetchone()
    conn.close()
    return float(row["balance"]) if row else 1000.0


def set_balance(amount: float):
    conn = get_conn()
    conn.execute(
        "UPDATE bankroll SET balance=?, updated_at=? WHERE id=1",
        (amount, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


# ── Bots ─────────────────────────────────────────────────────────────────────
def add_bot(name: str, bot_type: str = "generic", description: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO bots (name, bot_type, status, description, created_at) VALUES (?,?,?,?,?)",
        (name, bot_type, "idle", description, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def list_bots():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bots ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_bot_status(bot_id: int, status: str):
    conn = get_conn()
    conn.execute(
        "UPDATE bots SET status=?, last_run=?, run_count=run_count+1 WHERE id=?",
        (status, datetime.utcnow().isoformat(), bot_id),
    )
    conn.commit()
    conn.close()


def delete_bot(bot_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM bots WHERE id=?", (bot_id,))
    conn.commit()
    conn.close()


# ── Bets ─────────────────────────────────────────────────────────────────────
def place_bet(bot_id, match_id, home_team, away_team, stake, odds, predicted_outcome):
    balance = get_balance()
    if stake > balance:
        raise ValueError(f"Insufficient balance: ${balance:.2f} available, ${stake:.2f} requested")
    conn = get_conn()
    conn.execute(
        """INSERT INTO bets
           (bot_id, match_id, home_team, away_team, stake, odds, predicted_outcome, status, created_at)
           VALUES (?,?,?,?,?,?,?,'open',?)""",
        (bot_id, match_id, home_team, away_team, stake, odds, predicted_outcome, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    set_balance(balance - stake)


def settle_bet(bet_id: int, actual_outcome: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM bets WHERE id=?", (bet_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Bet {bet_id} not found")
    bet = dict(row)
    won = bet["predicted_outcome"] == actual_outcome
    pnl = (bet["stake"] * (bet["odds"] - 1)) if won else -bet["stake"]
    payout = bet["stake"] * bet["odds"] if won else 0.0
    conn.execute(
        "UPDATE bets SET status=?, actual_outcome=?, pnl=?, settled_at=? WHERE id=?",
        ("won" if won else "lost", actual_outcome, pnl, datetime.utcnow().isoformat(), bet_id),
    )
    conn.commit()
    conn.close()
    if won:
        set_balance(get_balance() + payout)


def list_bets():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bets ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Jobs ─────────────────────────────────────────────────────────────────────
def add_job(bot_id: int, title: str, description: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO jobs (bot_id, title, description, status, created_at) VALUES (?,?,?,'pending',?)",
        (bot_id, title, description, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def complete_job(job_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE jobs SET status='done', completed_at=? WHERE id=?",
        (datetime.utcnow().isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def list_jobs():
    conn = get_conn()
    rows = conn.execute(
        """SELECT j.*, b.name as bot_name FROM jobs j
           LEFT JOIN bots b ON j.bot_id = b.id
           ORDER BY j.created_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Parlays ──────────────────────────────────────────────────────────────────
def add_parlay(bot_id: int, name: str, combined_odds: float, stake: float, reasoning: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO parlays (bot_id, name, combined_odds, stake, status, pnl, reasoning, created_at)
           VALUES (?,?,?,?,'open',0.0,?,?)""",
        (bot_id, name, combined_odds, stake, reasoning, datetime.utcnow().isoformat()),
    )
    parlay_id = cur.lastrowid
    conn.commit()
    conn.close()
    return parlay_id


def add_parlay_leg(parlay_id: int, match_id: str, home_team: str, away_team: str,
                   bet_type: str, selection: str, odds: float):
    conn = get_conn()
    conn.execute(
        """INSERT INTO parlay_legs (parlay_id, match_id, home_team, away_team, bet_type, selection, odds)
           VALUES (?,?,?,?,?,?,?)""",
        (parlay_id, match_id, home_team, away_team, bet_type, selection, odds),
    )
    conn.commit()
    conn.close()


def settle_parlay(parlay_id: int, outcome: str):
    """outcome: 'won' or 'lost'. Calculates pnl accordingly."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM parlays WHERE id=?", (parlay_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Parlay {parlay_id} not found")
    parlay = dict(row)
    if outcome == "won":
        pnl = parlay["stake"] * (parlay["combined_odds"] - 1)
    else:
        pnl = -parlay["stake"]
    conn.execute(
        "UPDATE parlays SET status=?, pnl=?, settled_at=? WHERE id=?",
        (outcome, pnl, datetime.utcnow().isoformat(), parlay_id),
    )
    conn.commit()
    conn.close()


def list_parlays(bot_id=None) -> list:
    conn = get_conn()
    if bot_id is not None:
        rows = conn.execute(
            "SELECT * FROM parlays WHERE bot_id=? ORDER BY created_at DESC", (bot_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM parlays ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_parlay_legs(parlay_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM parlay_legs WHERE parlay_id=? ORDER BY id", (parlay_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_parlay_leg_result(leg_id: int, result: str, actual_result: str = ""):
    conn = get_conn()
    conn.execute(
        "UPDATE parlay_legs SET result=?, actual_result=? WHERE id=?",
        (result, actual_result, leg_id),
    )
    conn.commit()
    conn.close()


# ── Learning Log ─────────────────────────────────────────────────────────────
def add_learning_log(bot_id: int, parlay_id: int, match_id: str, home_team: str,
                     away_team: str, bet_type: str, selection: str, odds: float,
                     outcome: str, reasoning: str = ""):
    conn = get_conn()
    conn.execute(
        """INSERT INTO learning_log
           (bot_id, parlay_id, match_id, home_team, away_team, bet_type, selection, odds, outcome, reasoning, learned_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (bot_id, parlay_id, match_id, home_team, away_team, bet_type, selection, odds,
         outcome, reasoning, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def list_learning_log(bot_id=None, limit: int = 50) -> list:
    conn = get_conn()
    if bot_id is not None:
        rows = conn.execute(
            "SELECT * FROM learning_log WHERE bot_id=? ORDER BY learned_at DESC LIMIT ?",
            (bot_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM learning_log ORDER BY learned_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Recommendations ──────────────────────────────────────────────────────────
def add_recommendation(date, match, league, market, selection, odds, true_probability,
                       implied_probability, edge_pct, recommended_stake,
                       bet_type='single', parlay_id=None, commence_time=None) -> int:
    """Insert a recommendation and return its id."""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO recommendations
           (date, match, league, market, selection, odds, true_probability,
            implied_probability, edge_pct, recommended_stake, bet_type, parlay_id,
            status, actual_result, pnl, created_at, commence_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'open','',0.0,?,?)""",
        (date, match, league, market, selection, odds, true_probability,
         implied_probability, edge_pct, recommended_stake, bet_type, parlay_id,
         datetime.utcnow().isoformat(), commence_time),
    )
    rec_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rec_id


def list_recommendations(status=None, date_from=None, date_to=None) -> list:
    """List recommendations with optional filters."""
    conn = get_conn()
    query = "SELECT * FROM recommendations WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if date_from:
        query += " AND date>=?"
        params.append(date_from)
    if date_to:
        query += " AND date<=?"
        params.append(date_to)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def settle_recommendation(rec_id: int, actual_result: str, won: bool):
    """Set status to won/lost and calculate pnl."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM recommendations WHERE id=?", (rec_id,)).fetchone()
    if not row:
        conn.close()
        return
    rec = dict(row)
    pnl = (rec['recommended_stake'] * (rec['odds'] - 1)) if won else -rec['recommended_stake']
    status = 'won' if won else 'lost'
    conn.execute(
        "UPDATE recommendations SET status=?, actual_result=?, pnl=? WHERE id=?",
        (status, actual_result, pnl, rec_id),
    )
    conn.commit()
    conn.close()


def get_recommendation_summary() -> dict:
    """Return {total_staked, total_pnl, win_count, loss_count, total_count, win_rate, roi_pct}"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT recommended_stake, pnl, status FROM recommendations WHERE status IN ('won','lost')"
    ).fetchall()
    conn.close()
    if not rows:
        return {
            'total_staked': 0.0,
            'total_pnl': 0.0,
            'win_count': 0,
            'loss_count': 0,
            'total_count': 0,
            'win_rate': 0.0,
            'roi_pct': 0.0,
        }
    total_staked = sum(r['recommended_stake'] for r in rows)
    total_pnl = sum(r['pnl'] for r in rows)
    win_count = sum(1 for r in rows if r['status'] == 'won')
    loss_count = sum(1 for r in rows if r['status'] == 'lost')
    total_count = len(rows)
    win_rate = (win_count / total_count * 100) if total_count > 0 else 0.0
    roi_pct = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0
    return {
        'total_staked': total_staked,
        'total_pnl': total_pnl,
        'win_count': win_count,
        'loss_count': loss_count,
        'total_count': total_count,
        'win_rate': win_rate,
        'roi_pct': roi_pct,
    }


# ── Hjelpefunksjoner for Dashboard ───────────────────────────────────────────
def get_daily_stats(date: str = None) -> dict:
    """Hent stats for en spesifikk dato (default: i dag)."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_conn()
    
    # Bets plassert i dag
    placed = conn.execute(
        "SELECT COUNT(*) as count FROM recommendations WHERE date=?",
        (date,)
    ).fetchone()
    
    # Bets vunnet/tapt i dag
    won = conn.execute(
        "SELECT COUNT(*) as count FROM recommendations WHERE date=? AND status='won'",
        (date,)
    ).fetchone()
    
    lost = conn.execute(
        "SELECT COUNT(*) as count FROM recommendations WHERE date=? AND status='lost'",
        (date,)
    ).fetchone()
    
    # PnL i dag
    pnl = conn.execute(
        "SELECT SUM(pnl) as total FROM recommendations WHERE date=? AND status IN ('won', 'lost')",
        (date,)
    ).fetchone()
    
    conn.close()
    
    return {
        'date': date,
        'bets_placed': placed['count'] if placed else 0,
        'bets_won': won['count'] if won else 0,
        'bets_lost': lost['count'] if lost else 0,
        'daily_pnl': pnl['total'] if pnl and pnl['total'] else 0,
    }


def get_bankroll_history(days: int = 30) -> list:
    """Hent bankroll historikk (forenklet - kun siste oppdatering per dag)."""
    conn = get_conn()
    
    # For nå, returnerer vi bare nåværende bankroll og dato
    # En full historikk ville krevd en egen bankroll_history tabell
    row = conn.execute(
        "SELECT balance, updated_at FROM bankroll WHERE id=1"
    ).fetchone()
    conn.close()
    
    if row:
        return [{'date': row['updated_at'][:10] if row['updated_at'] else datetime.now().strftime('%Y-%m-%d'), 
                 'balance': row['balance']}]
    return []


def get_recent_results(limit: int = 5) -> list:
    """Hent siste X resultater."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT match, league, selection, status, pnl, actual_result, date, odds, recommended_stake, edge_pct 
           FROM recommendations 
           WHERE status IN ('won', 'lost') 
           ORDER BY created_at DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

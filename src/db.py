import sqlite3
import os
from datetime import datetime

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_HERE, "data", "mc.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
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
    c.execute(
        "INSERT OR IGNORE INTO bankroll (id, balance, updated_at) VALUES (1, 1000.0, ?)",
        (datetime.utcnow().isoformat(),),
    )
    conn.commit()
    conn.close()


# ── Bankroll ──────────────────────────────────────────────────────────────────
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


# ── Bots ──────────────────────────────────────────────────────────────────────
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


# ── Bets ──────────────────────────────────────────────────────────────────────
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


# ── Jobs ──────────────────────────────────────────────────────────────────────
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

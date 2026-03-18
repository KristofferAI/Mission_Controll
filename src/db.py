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
    
    # Bankroll
    c.execute("""
        CREATE TABLE IF NOT EXISTS bankroll (
            id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 1000.0,
            updated_at TEXT
        )
    """)
    
    # Recommendations / Bets
    c.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            match TEXT,
            league TEXT,
            market TEXT,
            selection TEXT,
            odds REAL,
            true_probability REAL,
            implied_probability REAL,
            edge_pct REAL,
            recommended_stake REAL,
            status TEXT DEFAULT 'open',
            actual_result TEXT DEFAULT '',
            pnl REAL DEFAULT 0.0,
            created_at TEXT,
            commence_time TEXT
        )
    """)
    
    # Initialize bankroll
    c.execute("INSERT OR IGNORE INTO bankroll (id, balance) VALUES (1, 1000.0)")
    
    conn.commit()
    conn.close()


def get_balance() -> float:
    conn = get_conn()
    row = conn.execute("SELECT balance FROM bankroll WHERE id=1").fetchone()
    conn.close()
    return row['balance'] if row else 1000.0


def set_balance(amount: float):
    conn = get_conn()
    conn.execute(
        "UPDATE bankroll SET balance=?, updated_at=? WHERE id=1",
        (amount, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def add_recommendation(date, match, league, market, selection, odds, 
                       true_probability, implied_probability, edge_pct, 
                       recommended_stake, commence_time=None) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO recommendations 
           (date, match, league, market, selection, odds, true_probability,
            implied_probability, edge_pct, recommended_stake, status, created_at, commence_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (date, match, league, market, selection, odds, true_probability,
         implied_probability, edge_pct, recommended_stake, 'open', 
         datetime.utcnow().isoformat(), commence_time)
    )
    rec_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rec_id


def list_recommendations(status=None):
    conn = get_conn()
    query = "SELECT * FROM recommendations"
    params = []
    if status:
        query += " WHERE status=?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def settle_recommendation(rec_id: int, actual_result: str, won: bool):
    conn = get_conn()
    row = conn.execute(
        "SELECT recommended_stake, odds FROM recommendations WHERE id=?",
        (rec_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        return
    
    stake = row['recommended_stake']
    odds = row['odds']
    
    if won:
        pnl = stake * (odds - 1)
        status = 'won'
    else:
        pnl = -stake
        status = 'lost'
    
    conn.execute(
        "UPDATE recommendations SET status=?, actual_result=?, pnl=? WHERE id=?",
        (status, actual_result, pnl, rec_id)
    )
    conn.commit()
    conn.close()


def get_recommendation_summary():
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, pnl FROM recommendations WHERE status IN ('won','lost')"
    ).fetchall()
    conn.close()
    
    wins = sum(1 for r in rows if r['status'] == 'won')
    total = len(rows)
    pnl = sum(r['pnl'] for r in rows)
    
    return {
        'win_count': wins,
        'loss_count': total - wins,
        'total_count': total,
        'total_pnl': pnl,
        'win_rate': (wins / total * 100) if total > 0 else 0,
        'roi_pct': (pnl / 1000 * 100) if total > 0 else 0
    }

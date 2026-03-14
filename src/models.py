from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Bot:
    id: Optional[int] = None
    name: str = ""
    bot_type: str = "generic"
    status: str = "idle"
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_run: Optional[str] = None
    run_count: int = 0


@dataclass
class Bet:
    id: Optional[int] = None
    bot_id: Optional[int] = None
    match_id: str = ""
    home_team: str = ""
    away_team: str = ""
    stake: float = 0.0
    odds: float = 1.0
    predicted_outcome: str = "home"
    actual_outcome: Optional[str] = None
    status: str = "open"
    pnl: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    settled_at: Optional[str] = None


@dataclass
class Job:
    id: Optional[int] = None
    bot_id: Optional[int] = None
    title: str = ""
    description: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

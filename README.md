# 🎯 Mission Controll — Office MVP

Paper Betting Office built with **Python · Streamlit · SQLite**

Dark theme with `#1E90FF` accent. Generic multi-bot registry. Single flat repo.

---

## Quick Start

```bash
git clone https://github.com/KristofferAI/Mission_Controll.git
cd Mission_Controll
chmod +x bootstrap.sh
./bootstrap.sh
```

Then open **http://localhost:8501** in your browser.

---

## Features

| Tab | What it does |
|-----|-------------|
| 🎯 Overview | Live KPIs: bankroll, bots, PnL, win-rate. Cumulative PnL chart. |
| 🤖 Bots | Multi-bot registry — register, run, pause, delete any number of bots. |
| 💰 Bets | Paper betting ledger — place bets, settle outcomes, track PnL. |
| ⚙️ Jobs | Assign tasks to bots, track completion. |
| 🔧 Settings | Adjust bankroll, view DB stats, danger zone. |

---

## Project Structure

```
Mission_Controll/
├── src/
│   ├── db.py                        # SQLite wrapper (all CRUD)
│   ├── models.py                    # Bot, Bet, Job dataclasses
│   ├── services/
│   │   ├── bot_registry.py          # BotRegistry service
│   │   ├── betting.py               # BettingService
│   │   └── scheduler.py             # JobScheduler
│   └── dashboard/
│       ├── app.py                   # Streamlit entry point
│       └── pages/
│           ├── overview.py
│           ├── bots.py
│           ├── bets.py
│           ├── jobs.py
│           └── settings.py
├── data/                            # SQLite DB lives here (gitignored)
├── .streamlit/config.toml           # Dark theme + #1E90FF accent
├── requirements.txt
├── bootstrap.sh                     # One-click local setup
└── .env.template                    # Copy to .env for secrets
```

---

## Manual Setup (without bootstrap.sh)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

---

## Roadmap

- [ ] Live odds feed integration (Gamdom / free API)
- [ ] Soccer predictor model integration
- [ ] Bot auto-scheduler (cron-style)
- [ ] CSV export for bets / PnL
- [ ] GitHub Actions CI

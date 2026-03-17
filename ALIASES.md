# Mission Controll — Quick Commands
# Legg til i ~/.zshrc eller ~/.bash_profile for permanent alias

# Quick alias (kan legges til i shell config)
alias mc='cd ~/projects/Mission_Controll && source venv/bin/activate && streamlit run src/dashboard/app.py'
alias mc-bot='cd ~/projects/Mission_Controll && source venv/bin/activate && python3 odds_bot/main.py --run'
alias mc-full='cd ~/projects/Mission_Controll && source venv/bin/activate && python3 odds_bot/main.py --run && streamlit run src/dashboard/app.py'

# --- BRUK EN AV DISSE: ---

# Alternativ 1: Enkel én-linjer (kopier og lim inn i terminal)
cd ~/projects/Mission_Controll && source venv/bin/activate && streamlit run src/dashboard/app.py

# Alternativ 2: Bruk start.sh script
~/projects/Mission_Controll/start.sh dashboard

# Alternativ 3: Kjør bot + dashboard
~/projects/Mission_Controll/start.sh both

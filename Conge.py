import streamlit as st
import pandas as pd
import datetime
import calendar

# --- CONFIGURATION ET STYLE ---
st.set_page_config(layout="wide", page_title="Calendrier Interactif Congés")

st.markdown("""
<style>
    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }
    .day-box { border: 1px solid #ccc; padding: 10px; border-radius: 5px; min-height: 100px; }
    .code-TRA { background-color: #f0f2f6; }
    .code-CX { background-color: #ff4b4b; color: white; }
    .code-C4 { background-color: #ffa500; color: white; }
    .code-ZZ { background-color: #90ee90; }
    .code-CZ { background-color: #00ced1; color: white; }
    .code-FC { background-color: #ffff00; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS LOGIQUES ---
def get_french_holidays(year):
    # Liste simplifiée des jours fériés français
    return [
        datetime.date(year, 1, 1), datetime.date(year, 5, 1), datetime.date(year, 5, 8),
        datetime.date(year, 7, 14), datetime.date(year, 8, 15), datetime.date(year, 11, 1),
        datetime.date(year, 11, 11), datetime.date(year, 12, 25)
    ]

def determine_base_code(date, holidays):
    if date in holidays:
        return "FC"
    
    is_even = date.isocalendar()[1] % 2 == 0
    weekday = date.weekday() # 0=Lundi, 6=Dimanche
    
    # Logique Semaines Pairs/Impairs (Exemple: Impair = 3 jours ZZ, Pair = 2 jours ZZ)
    if is_even:
        return "ZZ" if weekday >= 5 else "TRA" # Samedi, Dimanche
    else:
        return "ZZ" if weekday >= 4 else "TRA" # Vendredi, Samedi, Dimanche

# --- INTERFACE UTILISATEUR ---
st.title("📅 Planificateur de Congés Interactif")

col1, col2 = st.columns([1, 3])

with col1:
    year = st.selectbox("Année", [2025, 2026], index=1)
    month = st.selectbox("Mois", range(1, 13), index=datetime.datetime.now().month - 1)
    
    st.info("""
    **Légende :**
    - **CX** : Congé | **CZ** : Congé Généré
    - **ZZ** : Repos | **TRA** : Travail
    - **C4** : Supplément | **FC** : Férié
    """)
    
    optimiser = st.button("🚀 Optimiser les jours d'absence")

# --- CALCUL DU CALENDRIER ---
num_days = calendar.monthrange(year, month)[1]
days = [datetime.date(year, month, d) for d in range(1, num_days + 1)]
holidays = get_french_holidays(year)

# Initialisation de l'état
if 'codes' not in st.session_state:
    st.session_state.codes = {d: determine_base_code(d, holidays) for d in days}

# --- LOGIQUE DE TRANSFORMATION (CZ & VACS) ---
# (Ici on applique les règles sur les ZZ entourés de CX)
current_codes = list(st.session_state.codes.values())
for i in range(1, len(current_codes) - 1):
    if current_codes[i] == "ZZ" or (current_codes[i] == "FC"):
        # Règle CZ : si entouré par des CX sur la période de vacances
        if "CX" in current_codes[:i] and "CX" in current_codes[i+1:]:
             # Simplification de la logique "étau"
             st.session_state.codes[days[i]] = "CZ"

# --- CALCUL DU COMPTEUR ---
# On compte tout ce qui n'est pas TRA
absence_count = sum(1 for c in st.session_state.codes.values() if c != "TRA")

with col1:
    st.metric("Total Jours Absence", absence_count)

# --- AFFICHAGE GRID TYPE OUTLOOK ---
st.write(f"### {calendar.month_name[month]} {year}")
cols = st.columns(7)
days_of_week = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

for i, dow in enumerate(days_of_week):
    cols[i].centered_text = f"**{dow}**"
    cols[i].write(dow)

grid_cols = st.columns(7)
# Ajustement pour le premier jour du mois
first_dow = days[0].weekday()

for i in range(first_dow):
    grid_cols[i].write("")

for date in days:
    idx = (date.day + first_dow - 1) % 7
    with grid_cols[idx]:
        current_code = st.session_state.codes[date]
        st.markdown(f"""
        <div class="day-box code-{current_code}">
            {date.day}<br><strong>{current_code}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Menu pour changer manuellement
        new_code = st.selectbox("", ["TRA", "CX", "C4", "ZZ", "FC"], 
                                index=["TRA", "CX", "C4", "ZZ", "FC"].index(current_code),
                                key=f"sel_{date}", label_visibility="collapsed")
        if new_code != current_code:
            st.session_state.codes[date] = new_code
            st.rerun()

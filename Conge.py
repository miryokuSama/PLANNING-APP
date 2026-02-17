import streamlit as st
import pandas as pd
import datetime
import calendar
import holidays

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Optimiseur de Congés")

st.markdown("""
<style>
    .day-container { border: 1px solid #ddd; padding: 5px; border-radius: 5px; min-height: 80px; font-size: 0.8em; }
    .code-TRA { background-color: #f0f2f6; color: #31333F; } 
    .code-CX { background-color: #ff4b4b; color: white; } 
    .code-C4 { background-color: #ffa500; color: white; } 
    .code-ZZ { background-color: #90ee90; color: #004d00; } 
    .code-CZ { background-color: #00ced1; color: white; } 
    .code-FC { background-color: #ffff00; color: black; font-weight: bold; border: 2px solid #e6e600; } 
    .day-number { font-weight: bold; }
    .code-label { display: block; text-align: center; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS LOGIQUES ---

def is_week_3_zz(date, parity_choice):
    week_num = date.isocalendar()[1]
    is_even = (week_num % 2 == 0)
    return is_even if parity_choice == "Semaines Paires" else not is_even

def get_base_code(date, parity_choice, fr_holidays):
    weekday = date.weekday()
    has_3_zz = is_week_3_zz(date, parity_choice)
    is_zz_day = (weekday >= 4) if has_3_zz else (weekday >= 5)
    
    if date in fr_holidays:
        return "FC", is_zz_day
    return ("ZZ" if is_zz_day else "TRA"), is_zz_day

def compute_calendar(dates, overrides, parity_choice, fr_holidays):
    # Étape 1 : Assigner les codes de base ou manuels
    current_codes = {}
    for d in dates:
        base_code, _ = get_base_code(d, parity_choice, fr_holidays)
        current_codes[d] = overrides.get(d, base_code)
    
    # Étape 2 : Appliquer la logique VACS / CZ
    final_codes = current_codes.copy()
    in_vacs = False
    
    for i, d in enumerate(dates):
        code = current_codes[d]
        _, is_zz_logic = get_base_code(d, parity_choice, fr_holidays)
        
        # Logique d'état VACS
        if code == "CX":
            in_vacs = True
        elif code == "C4":
            in_vacs = False # Le C4 termine la séquence actuelle
            if i + 1 < len(dates):
                next_code = current_codes[dates[i+1]]
                if next_code in ["CX", "C4"]:
                    # La VACS ne reprendra qu'au tour suivant (in_vacs reste False pour l'instant)
                    pass 
        elif code == "TRA":
            in_vacs = False

        # Transformation CZ (Seulement si en VACS et sur une semaine à 3 ZZ)
        if in_vacs and is_week_3_zz(d, parity_choice) and (code == "ZZ" or code == "FC"):
            if code != "FC": # On garde l'affichage FC mais logiquement c'est un CZ
                final_codes[d] = "CZ"
                
    return final_codes

# --- ALGORITHME D'OPTIMISATION ---
def optimize_vacations(dates, parity_choice, fr_holidays, max_cx, max_c4):
    best_overrides = {}
    max_absence = 0
    
    # Stratégie : On cherche à poser les CX/C4 sur les jours TRA qui touchent des semaines à 3 ZZ
    potential_days = [d for d in dates if get_base_code(d, parity_choice, fr_holidays)[0] == "TRA"]
    
    # Pour Streamlit, on va utiliser une approche glissante simple pour éviter de planter le navigateur
    # On essaie de poser les CX pour créer la plus longue chaîne
    for start_idx in range(len(potential_days)):
        temp_overrides = {}
        cx_left = max_cx
        c4_left = max_c4
        
        for d in potential_days[start_idx:]:
            if cx_left > 0:
                temp_overrides[d] = "CX"
                cx_left -= 1
            elif c4_left > 0:
                temp_overrides[d] = "C4"
                c4_left -= 1
        
        test_calendar = compute_calendar(dates, temp_overrides, parity_choice, fr_holidays)
        current_absence = sum(1 for c in test_calendar.values() if c != "TRA")
        
        if current_absence > max_absence:
            max_absence = current_absence
            best_overrides = temp_overrides
            
    return best_overrides

# --- INTERFACE ---
st.title("Calendrier de Congés Interactif & Optimisé")

with st.sidebar:
    st.header("1. Paramètres")
    year = st.number_input("Année", 2024, 2030, 2025)
    month = st.selectbox("Mois", range(1, 13), index=datetime.datetime.now().month - 1)
    parity = st.radio("Repos (3j) le Vendredi :", ["Semaines Paires", "Semaines Impaires"])
    
    st.header("2. Solde disponible")
    solde_cx = st.slider("Nombre de CX", 0, 30, 5)
    solde_c4 = st.slider("Nombre de C4", 0, 10, 2)
    
    if st.button("🚀 OPTIMISER MON MOIS"):
        dates = [datetime.date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)]
        fr_hols = holidays.France(years=year)
        best_plan = optimize_vacations(dates, parity, fr_hols, solde_cx, solde_c4)
        st.session_state.manual_overrides = best_plan
        st.success("Calendrier optimisé !")

# Données de base
dates = [datetime.date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)]
fr_hols = holidays.France(years=year)

if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}

# Calcul final
final_calendar = compute_calendar(dates, st.session_state.manual_overrides, parity, fr_hols)

# Métriques
abs_total = sum(1 for c in final_calendar.values() if c != "TRA")
st.metric("Total jours d'absence (Entreprise)", f"{abs_total} jours")

# Affichage Grille
cols = st.columns(7)
for i, name in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]):
    cols[i].write(f"**{name}**")

grid = st.columns(7)
for i in range(dates[0].weekday()):
    grid[i].write("")

for d in dates:
    code = final_calendar[d]
    with grid[d.weekday()]:
        st.markdown(f"""<div class="day-container code-{code}"><div class="day-number">{d.day}</div><div class="code-label">{code}</div></div>""", unsafe_allow_html=True)
        
        # Modification manuelle
        options = ["TRA", "CX", "C4", "ZZ", "FC"] if d in fr_hols else ["TRA", "CX", "C4", "ZZ"]
        current_idx = options.index(code) if code in options else options.index("ZZ")
        
        new_code = st.selectbox("", options, index=current_idx, key=f"s_{d}", label_visibility="collapsed")
        if new_code != (st.session_state.manual_overrides.get(d, get_base_code(d, parity, fr_hols)[0])):
            st.session_state.manual_overrides[d] = new_code
            st.rerun()

if st.button("Réinitialiser"):
    st.session_state.manual_overrides = {}
    st.rerun()

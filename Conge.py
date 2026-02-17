import streamlit as st
import pandas as pd
import datetime
import calendar
import holidays

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Gestionnaire de Congés Dynamique")

# (Styles CSS identiques au précédent pour la clarté)
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

# --- INITIALISATION SESSION STATE ---
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}  # Format: {datetime.date: "CODE"}

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

def compute_full_logic(dates, overrides, parity_choice, fr_holidays):
    """Calcule les codes finaux pour une liste de dates données"""
    current_codes = {d: overrides.get(d, get_base_code(d, parity_choice, fr_holidays)[0]) for d in dates}
    final_codes = current_codes.copy()
    in_vacs = False
    
    for i, d in enumerate(dates):
        code = current_codes[d]
        if code == "CX": in_vacs = True
        elif code == "C4":
            in_vacs = False
            if i + 1 < len(dates) and current_codes[dates[i+1]] in ["CX", "C4"]: pass 
        elif code == "TRA": in_vacs = False

        if in_vacs and is_week_3_zz(d, parity_choice) and (code == "ZZ" or code == "FC"):
            if code != "FC": final_codes[d] = "CZ"
                
    return final_codes

# --- BARRE LATÉRALE (SÉLECTEUR) ---
with st.sidebar:
    st.header("📅 Période & Paramètres")
    
    # Meilleur sélecteur : Date input configuré pour choisir un mois
    today = datetime.date.today()
    selected_date = st.date_input("Choisir un mois à afficher", value=today)
    view_year = selected_date.year
    view_month = selected_date.month

    parity = st.radio("Repos (3j) le Vendredi :", ["Semaines Paires", "Semaines Impaires"], index=1)
    
    st.divider()
    st.header("💰 Solde pour Optimisation")
    solde_cx = st.number_input("Nombre de CX", 0, 100, 5)
    solde_c4 = st.number_input("Nombre de C4", 0, 100, 2)

    if st.button("🚀 Optimiser ce mois"):
        # Logique d'optimisation (limitée au mois en cours pour la performance)
        all_month_days = [datetime.date(view_year, view_month, d) for d in range(1, calendar.monthrange(view_year, view_month)[1] + 1)]
        fr_hols = holidays.France(years=view_year)
        
        # Algorithme simplifié (glissant)
        best_o = {}
        max_a = 0
        potential_days = [d for d in all_month_days if get_base_code(d, parity, fr_hols)[0] == "TRA"]
        
        for start in range(len(potential_days)):
            temp = {}
            c_left, c4_left = solde_cx, solde_c4
            for d in potential_days[start:]:
                if c_left > 0: temp[d] = "CX"; c_left -= 1
                elif c4_left > 0: temp[d] = "C4"; c4_left -= 1
            
            res = compute_full_logic(all_month_days, {**st.session_state.manual_overrides, **temp}, parity, fr_hols)
            score = sum(1 for c in res.values() if c != "TRA")
            if score > max_a:
                max_a = score
                best_o = temp
        
        st.session_state.manual_overrides.update(best_o)
        st.rerun()

    if st.button("🗑️ Effacer tout le calendrier"):
        st.session_state.manual_overrides = {}
        st.rerun()

# --- CALCULS ---
days_in_month = [datetime.date(view_year, view_month, d) for d in range(1, calendar.monthrange(view_year, view_month)[1] + 1)]
fr_hols = holidays.France(years=view_year)
final_calendar = compute_full_logic(days_in_month, st.session_state.manual_overrides, parity, fr_hols)

# --- AFFICHAGE ---
st.title(f"Planification : {calendar.month_name[view_month]} {view_year}")

# Métriques globales (sur ce qui est en mémoire)
total_abs = sum(1 for d, c in final_calendar.items() if c != "TRA")
st.metric("Total jours d'absence (Ce mois)", f"{total_abs} jours")

# Grille de calendrier
cols = st.columns(7)
for i, name in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]):
    cols[i].markdown(f"**{name}**")

grid = st.columns(7)
first_day_weekday = days_in_month[0].weekday()
for i in range(first_day_weekday):
    grid[i].empty()

for d in days_in_month:
    code = final_calendar[d]
    with grid[d.weekday()]:
        st.markdown(f"""<div class="day-container code-{code}"><div class="day-number">{d.day}</div><div class="code-label">{code}</div></div>""", unsafe_allow_html=True)
        
        # Sélecteur compact
        opts = ["TRA", "CX", "C4", "ZZ", "FC"] if d in fr_hols else ["TRA", "CX", "C4", "ZZ"]
        # On s'assure que la valeur actuelle est dans les options pour éviter l'erreur
        current_val = code if code in opts else "ZZ" 
        
        new_c = st.selectbox("", opts, index=opts.index(current_val), key=f"d_{d}", label_visibility="collapsed")
        
        # Si l'utilisateur change manuellement
        if new_c != (st.session_state.manual_overrides.get(d, get_base_code(d, parity, fr_hols)[0])):
            st.session_state.manual_overrides[d] = new_c
            st.rerun()

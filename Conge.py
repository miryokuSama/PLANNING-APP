import streamlit as st
import pandas as pd
import datetime
import calendar
import holidays

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Planning Congés (Dim-Sam)")

st.markdown("""
<style>
    .day-container { border: 1px solid #ddd; padding: 5px; border-radius: 5px; min-height: 85px; font-size: 0.85em; }
    .code-TRA { background-color: #f8f9fa; color: #31333F; border-left: 5px solid #d1d3d4; } 
    .code-CX { background-color: #ff4b4b; color: white; } 
    .code-C4 { background-color: #ffa500; color: white; } 
    .code-ZZ { background-color: #90ee90; color: #004d00; } 
    .code-CZ { background-color: #00ced1; color: white; } 
    .code-FC { background-color: #ffff00; color: black; font-weight: bold; border: 2px solid #e6e600; } 
    .day-number { font-weight: bold; margin-bottom: 2px; }
    .code-label { display: block; text-align: center; font-weight: bold; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}

# --- FONCTIONS LOGIQUES ---

def get_sunday_start_weekday(date):
    """Retourne 0 pour Dimanche, 1 pour Lundi ... 6 pour Samedi"""
    return (date.weekday() + 1) % 7

def is_week_3_zz(date, parity_choice):
    # On garde le calcul ISO pour la parité de semaine standard
    week_num = date.isocalendar()[1]
    is_even = (week_num % 2 == 0)
    return is_even if parity_choice == "Semaines Paires" else not is_even

def get_base_code(date, parity_choice, fr_holidays):
    weekday_standard = date.weekday() # 4=Ven, 5=Sam, 6=Dim
    has_3_zz = is_week_3_zz(date, parity_choice)
    
    # Règle : Semaine à 3 ZZ = Ven/Sam/Dim. Semaine à 2 ZZ = Sam/Dim.
    is_zz_day = (weekday_standard >= 4) if has_3_zz else (weekday_standard >= 5)
    
    if date in fr_holidays:
        return "FC", is_zz_day
    return ("ZZ" if is_zz_day else "TRA"), is_zz_day

def compute_full_logic(dates, overrides, parity_choice, fr_holidays):
    current_codes = {d: overrides.get(d, get_base_code(d, parity_choice, fr_holidays)[0]) for d in dates}
    final_codes = current_codes.copy()
    in_vacs = False
    
    for i, d in enumerate(dates):
        code = current_codes[d]
        if code == "CX": in_vacs = True
        elif code == "C4":
            in_vacs = False
            # Reprise si suivi de CX ou C4
            if i + 1 < len(dates) and current_codes[dates[i+1]] in ["CX", "C4"]:
                pass # in_vacs reste false ici, il sera activé au tour suivant
        elif code == "TRA": in_vacs = False

        # Transformation CZ
        if in_vacs and is_week_3_zz(d, parity_choice) and (code == "ZZ" or code == "FC"):
            if code != "FC": final_codes[d] = "CZ"
                
    return final_codes

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Sélecteur Mois / Année
    col_y, col_m = st.columns(2)
    view_year = col_y.number_input("Année", 2024, 2030, 2025)
    view_month = col_m.selectbox("Mois", range(1, 13), index=datetime.date.today().month - 1)
    
    parity = st.radio("Cycle 3 jours (Ven-Dim) :", ["Semaines Paires", "Semaines Impaires"], index=1)
    
    st.divider()
    st.header("🎯 Optimisation")
    solde_cx = st.number_input("Quota CX", 0, 100, 5)
    solde_c4 = st.number_input("Quota C4", 0, 100, 2)
    
    if st.button("🚀 Lancer l'optimisation"):
        all_month_days = [datetime.date(view_year, view_month, d) for d in range(1, calendar.monthrange(view_year, view_month)[1] + 1)]
        fr_hols = holidays.France(years=view_year)
        
        # Algorithme de recherche glissante
        best_o = {}
        max_abs = 0
        tra_days = [d for d in all_month_days if get_base_code(d, parity, fr_hols)[0] == "TRA"]
        
        for start in range(len(tra_days)):
            temp = {}
            c_left, c4_left = solde_cx, solde_c4
            for d in tra_days[start:]:
                if c_left > 0: temp[d] = "CX"; c_left -= 1
                elif c4_left > 0: temp[d] = "C4"; c4_left -= 1
            
            res = compute_full_logic(all_month_days, {**st.session_state.manual_overrides, **temp}, parity, fr_hols)
            score = sum(1 for c in res.values() if c != "TRA")
            if score > max_abs:
                max_abs = score
                best_o = temp
        
        st.session_state.manual_overrides.update(best_o)
        st.rerun()

    if st.button("🔄 Reset mois en cours"):
        all_month_days = [datetime.date(view_year, view_month, d) for d in range(1, calendar.monthrange(view_year, view_month)[1] + 1)]
        for d in all_month_days:
            if d in st.session_state.manual_overrides:
                del st.session_state.manual_overrides[d]
        st.rerun()

# --- CALCULS ---
days_in_month = [datetime.date(view_year, view_month, d) for d in range(1, calendar.monthrange(view_year, view_month)[1] + 1)]
fr_hols = holidays.France(years=view_year)
final_calendar = compute_full_logic(days_in_month, st.session_state.manual_overrides, parity, fr_hols)

# --- AFFICHAGE ---
st.title(f"{calendar.month_name[view_month]} {view_year}")
abs_total = sum(1 for c in final_calendar.values() if c != "TRA")
st.subheader(f"📊 Absence totale : {abs_total} jours")

# En-têtes (Dimanche en premier)
days_headers = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]
header_cols = st.columns(7)
for i, day_name in enumerate(days_headers):
    header_cols[i].markdown(f"<div style='text-align:center; color:#666;'>{day_name}</div>", unsafe_allow_html=True)

# Grille
grid = st.columns(7)
# On calcule le premier jour : si c'est un Lundi (weekday 0), get_sunday_start_weekday retourne 1.
# On remplit donc 1 case vide (Dimanche).
first_day_offset = get_sunday_start_weekday(days_in_month[0])

for i in range(first_day_offset):
    grid[i].empty()

for d in days_in_month:
    col_idx = get_sunday_start_weekday(d)
    code = final_calendar[d]
    
    with grid[col_idx]:
        st.markdown(f"""
        <div class="day-container code-{code}">
            <div class="day-number">{d.day}</div>
            <div class="code-label">{code}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Sélecteur discret
        opts = ["TRA", "CX", "C4", "ZZ", "FC"] if d in fr_hols else ["TRA", "CX", "C4", "ZZ"]
        current_val = code if code in opts else "ZZ"
        
        new_c = st.selectbox("", opts, index=opts.index(current_val), key=f"d_{d}", label_visibility="collapsed")
        
        if new_c != (st.session_state.manual_overrides.get(d, get_base_code(d, parity, fr_hols)[0])):
            st.session_state.manual_overrides[d] = new_c
            st.rerun()

import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V15", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin-top: 30px; margin-bottom: 20px; text-align: center; font-size: 1.5rem; text-transform: uppercase; }
    .day-card { min-height: 110px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; }
    .date-num { font-weight: 800; font-size: 1.3rem; color: #2c3e50; }
    .day-name { font-size: 0.7rem; text-transform: uppercase; color: #95a5a6; font-weight: bold; margin-bottom: 5px; }
    .label-tag { font-size: 0.75rem; text-align: center; margin-top: 12px; border-radius: 4px; color: white; padding: 4px; font-weight: bold; }
    .bg-zz { background-color: #2ecc71; } 
    .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; border: 2px solid #2980b9; } 
    .bg-cz { background-color: #e74c3c; border: 2px solid #c0392b; color: white !important; }
    .bg-empty { background-color: transparent; border: none; }
    .tra-text { color: #bdc3c7; font-size: 0.7rem; margin-top: 15px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Planificateur Vincent (Logique Férié Sélective)")

# --- 1. CONFIGURATION ---
with st.expander("👤 1. CONFIGURATION DE VOTRE CYCLE DE REPOS", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"], key="imp")
    with c_opt2:
        off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"], key="pair")

# --- 2. RÉGLAGES ---
mode = st.radio("Objectif :", ["Pose simple", "Optimiser mes repos"], horizontal=True)

with st.expander("📅 2. RÉGLAGES DE LA PÉRIODE", expanded=True):
    col_d1, col_d2, col_q = st.columns([2, 2, 1])
    if mode == "Pose simple":
        with col_d1: d_debut = st.date_input("Du", datetime(2026, 5, 1))
        with col_d2: d_fin = st.date_input("Au", datetime(2026, 5, 31))
    else:
        with col_d1: d_debut = st.date_input("Début recherche", datetime(2026, 5, 1))
        with col_d2: d_fin = st.date_input("Fin recherche", datetime(2026, 8, 31))
    with col_q: quota = st.number_input("Quota CX", value=10)
    
    calculer = st.button("🚀 LANCER", use_container_width=True)

# --- LOGIQUE MÉTIER ---
def check_ferie(date):
    f = {(1, 1): "An", (1, 5): "1er Mai", (8, 5): "8 Mai", (14, 5): "Asc.", (25, 5): "Pent.", (14, 7): "F.Nat.", (15, 8): "Assompt.", (1, 11): "Touss.", (11, 11): "Arm.", (25, 12): "Noël"}
    return f.get((date.day, date.month))

def get_day_status(date, off_imp, off_pair):
    wn = date.isocalendar()[1]
    is_even = wn % 2 == 0
    jours_fr_map = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    day_name_fr = jours_fr_map[date.weekday()]
    
    current_off_list = off_pair if is_even else off_imp
    is_zz = day_name_fr in current_off_list
    label_ferie = check_ferie(date)
    
    if label_ferie: return "FC", label_ferie
    if is_zz: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

def run_simulation(start, end, max_cx, off_i, off_p):
    cx_s, cz_s, weeks_taxed = set(), set(), set()
    conso = 0
    curr = start
    while curr <= end:
        status, _ = get_day_status(curr, off_i, off_p)
        wn = curr.isocalendar()[1]
        
        if status == "TRA" and conso < max_cx:
            cx_s.add(curr)
            conso += 1
            
            # ANALYSE DE LA SEMAINE POUR CZ
            is_even = wn % 2 == 0
            current_off_list = off_p if is_even else off_i
            
            # La règle : 3 jours de repos théoriques dans le cycle (ZZ habituels)
            if len(current_off_list) >= 3 and wn not in weeks_taxed and conso < max_cx:
                # On cherche à taxer un CZ sur un jour qui est théoriquement un repos
                start_w = curr - timedelta(days=(curr.weekday() + 1) % 7) # Dimanche
                for i in range(7):
                    day_to_check = start_w + timedelta(days=i)
                    day_name_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][day_to_check.weekday()]
                    
                    # On taxe seulement si c'est un jour de repos habituel (ZZ théorique)
                    if day_name_fr in current_off_list:
                        cz_s.add(day_to_check)
                        conso += 1
                        weeks_taxed.add(wn)
                        break
        curr += timedelta(days=1)
    return cx_s, cz_s, conso

# --- AFFICHAGE ---
if calculer:
    cx_final, cz_final, total = run_simulation(d_debut, d_fin, quota, off_impair, off_pair)
    
    mes_mois = []
    curr_m = d_debut.replace(day=1)
    while curr_m <= d_fin.replace(day=1):
        mes_mois.append((curr_m.month, curr_m.year))
        if curr_m.month == 12: curr_m = curr_m.replace(year=curr_m.year+1, month=1)
        else: curr_m = curr_m.replace(month=curr_m.month+1)

    for m, y in mes_mois:
        st.markdown(f'<div class="month-title">{calendar.month_name[m]} {y}</div>', unsafe_allow_html=True)
        cal = calendar.Calendar(firstweekday=6)
        month_days = list(cal.itermonthdates(y, m))
        jours_fr = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
        for w in range(len(month_days)//7):
            cols = st.columns(7)
            for i in range(7):
                d = month_days[w*7+i]
                with cols[i]:
                    if d.month != m: st.markdown('<div class="day-card bg-empty"></div>', unsafe_allow_html=True)
                    else:
                        st_code, st_lbl = get_day_status(d, off_impair, off_pair)
                        is_cx = any(c.year==d.year and c.month==d.month and c.day==d.day for c in cx_final)
                        is_cz = any(c.year==d.year and c.month==d.month and c.day==d.day for c in cz_final)
                        
                        bg, tag = "", '<div class="tra-text">TRAVAILLÉ</div>'
                        if is_cx: bg="bg-cx"; tag='<div class="label-tag bg-cx">CONGÉ CX</div>'
                        elif is_cz: bg="bg-cz"; tag='<div class="label-tag bg-cz">CONGÉ CZ</div>'
                        elif st_code=="FC": bg="bg-fc"; tag=f'<div class="label-tag bg-fc">{st_lbl}</div>'
                        elif st_code=="ZZ": bg="bg-zz"; tag='<div class="label-tag bg-zz">REPOS ZZ</div>'
                        
                        st.markdown(f'<div class="day-card {bg}"><div class="day-name">{jours_fr[i]}</div><div class="date-num">{d.day}</div>{tag}</div>', unsafe_allow_html=True)
    st.info(f"📊 Total décompté : {total} jours.")

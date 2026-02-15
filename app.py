import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V13", layout="wide")

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

st.title("🛡️ Planificateur & Optimiseur de Repos")

# --- 1. CONFIGURATION DES REPOS ---
with st.expander("👤 1. CONFIGURATION DE VOTRE CYCLE DE REPOS", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"], key="imp")
    with c_opt2:
        off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"], key="pair")

# --- 2. CHOIX DU MODE ---
mode = st.radio("Choisissez votre objectif :", ["Pose simple (Date à Date)", "Optimiser mes repos (Max repos avec quota CX)"], horizontal=True)

with st.expander("📅 2. RÉGLAGES DE LA PÉRIODE", expanded=True):
    col_d1, col_d2, col_q = st.columns([2, 2, 1])
    if mode == "Pose simple (Date à Date)":
        with col_d1: d_debut = st.date_input("Du", datetime(2026, 5, 1))
        with col_d2: d_fin = st.date_input("Au", datetime(2026, 5, 15))
        with col_q: quota = st.number_input("Quota dispo", value=30)
    else:
        with col_d1: d_start_search = st.date_input("Rechercher à partir du", datetime(2026, 5, 1))
        with col_d2: d_end_search = st.date_input("Jusqu'au", datetime(2026, 8, 31))
        with col_q: quota = st.number_input("Nombre de CX à utiliser", value=5)
    
    calculer = st.button("🚀 LANCER", use_container_width=True)

# --- LOGIQUE ---
def get_day_status(date, off_imp, off_pair):
    wn = date.isocalendar()[1]
    is_even = wn % 2 == 0
    jours_fr_map = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    day_name_fr = jours_fr_map[date.weekday()]
    feries = {(1, 1): "An", (1, 5): "1er Mai", (8, 5): "8 Mai", (14, 5): "Asc.", (25, 5): "Pent.", (14, 7): "F.Nat.", (15, 8): "Assompt."}
    is_fc = (date.day, date.month) in feries
    current_off_list = off_pair if is_even else off_imp
    is_zz = day_name_fr in current_off_list
    if is_fc: return "FC", feries[(date.day, date.month)]
    if is_zz: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

def simulate_period(start, end, max_cx, off_i, off_p):
    cx_set, cz_set, weeks_taxed = set(), set(), set()
    conso = 0
    curr = start
    while curr <= end:
        status, _ = get_day_status(curr, off_i, off_p)
        wn = curr.isocalendar()[1]
        if status == "TRA" and conso < max_cx:
            cx_set.add(curr)
            conso += 1
            is_even = wn % 2 == 0
            current_off_list = off_p if is_even else off_i
            if len(current_off_list) >= 3 and wn not in weeks_taxed and conso < max_cx:
                start_week = curr - timedelta(days=(curr.weekday() + 1) % 7)
                for i in range(7):
                    check_day = start_week + timedelta(days=i)
                    st_c, _ = get_day_status(check_day, off_i, off_p)
                    if st_c == "ZZ":
                        cz_set.add(check_day); conso += 1; weeks_taxed.add(wn); break
        curr += timedelta(days=1)
    return cx_set, cz_set, conso

cx_final, cz_final = set(), set()

if calculer:
    if mode == "Pose simple (Date à Date)":
        cx_final, cz_final, total = simulate_period(d_debut, d_fin, quota, off_impair, off_pair)
        date_debut_view, date_fin_view = d_debut, d_fin
    else:
        # OPTIMISEUR : On cherche la fenêtre qui donne le plus de jours OFF (ZZ+FC+CX+CZ) pour un quota de CX donné
        best_off_count = 0
        best_dates = (d_start_search, d_start_search + timedelta(days=7))
        
        # On fait glisser une fenêtre sur 4 mois max pour trouver le meilleur spot
        for i in range((d_end_search - d_start_search).days - 7):
            temp_start = d_start_search + timedelta(days=i)
            # On cherche combien de jours on peut couvrir avec le quota en partant de cette date
            temp_cx, temp_cz, temp_conso = set(), set(), 0
            curr_test = temp_start
            off_in_window = 0
            while temp_conso < quota and curr_test <= d_end_search:
                s, _ = get_day_status(curr_test, off_impair, off_pair)
                if s == "TRA":
                    temp_conso += 1
                    # Taxe CZ simplifiée pour le calcul de l'optimiseur
                    wn = curr_test.isocalendar()[1]
                    is_even = wn % 2 == 0
                    current_off_list = off_pair if is_even else off_impair
                    if len(current_off_list) >= 3: temp_conso += 0.25 # On simule le coût CZ
                off_in_window += 1
                curr_test += timedelta(days=1)
            
            if off_in_window > best_off_count:
                best_off_count = off_in_window
                best_dates = (temp_start, curr_test - timedelta(days=1))
        
        cx_final, cz_final, total = simulate_period(best_dates[0], best_dates[1], quota, off_impair, off_pair)
        date_debut_view, date_fin_view = best_dates[0], best_dates[1]
        st.success(f"💡 Meilleure option trouvée : du {date_debut_view.strftime('%d/%m')} au {date_fin_view.strftime('%d/%m')} ({best_off_count} jours de repos consécutifs !)")

    # --- AFFICHAGE ---
    mes_mois = []
    curr = date_debut_view.replace(day=1)
    while curr <= date_fin_view.replace(day=1):
        mes_mois.append((curr.month, curr.year))
        if curr.month == 12: curr = curr.replace(year=curr.year+1, month=1)
        else: curr = curr.replace(month=curr.month+1)

    for m, y in mes_mois:
        st.markdown(f'<div class="month-title">{calendar.month_name[m]} {y}</div>', unsafe_allow_html=True)
        cal = calendar.Calendar(firstweekday=6)
        month_days = list(cal.itermonthdates(y, m))
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
                        st.markdown(f'<div class="day-card {bg}"><div class="day-name">{["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"][i]}</div><div class="date-num">{d.day}</div>{tag}</div>', unsafe_allow_html=True)
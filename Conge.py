import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V16", layout="wide")

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

st.title("🛡️ Planificateur Vincent (Version Finale)")

# --- 1. CONFIGURATION ---
with st.expander("👤 1. CONFIGURATION DU CYCLE", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c1, c2 = st.columns(2)
    with c1: off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    with c2: off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

# --- 2. RÉGLAGES ---
mode = st.radio("Objectif :", ["Pose simple", "Optimiser mes repos"], horizontal=True)

with st.expander("📅 2. PÉRIODE ET QUOTA", expanded=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a: d_debut_in = st.date_input("Du / Début recherche", datetime(2026, 5, 1))
    with col_b: d_fin_in = st.date_input("Au / Fin recherche", datetime(2026, 6, 30))
    with col_c: quota_val = st.number_input("Quota CX", value=10)
    calculer = st.button("🚀 LANCER", use_container_width=True)

# --- FONCTIONS ---
def get_day_status(date, off_i, off_p):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    wn = date.isocalendar()[1]
    day_name = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"][date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    if f.get((date.day, date.month)): return "FC", f.get((date.day, date.month))
    if day_name in off_list: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

def run_sim(start, end, max_cx, off_i, off_p):
    cx_s, cz_s, weeks_t = set(), set(), set()
    conso = 0
    curr = start
    while curr <= end:
        s, _ = get_day_status(curr, off_i, off_p)
        wn = curr.isocalendar()[1]
        if s == "TRA" and conso < max_cx:
            cx_s.add(curr); conso += 1
            off_list = off_p if wn % 2 == 0 else off_i
            if len(off_list) >= 3 and wn not in weeks_t and conso < max_cx:
                sw = curr - timedelta(days=(curr.weekday() + 1) % 7)
                for i in range(7):
                    d_check = sw + timedelta(days=i)
                    d_name = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"][d_check.weekday()]
                    if d_name in off_list:
                        cz_s.add(d_check); conso += 1; weeks_t.add(wn); break
        curr += timedelta(days=1)
    return cx_s, cz_s, conso

# --- CALCUL ET AFFICHAGE ---
if calculer:
    if mode == "Pose simple":
        cx_final, cz_final, total = run_sim(d_debut_in, d_fin_in, quota_val, off_impair, off_pair)
        d_view_start, d_view_end = d_debut_in, d_fin_in
        st.info(f"📊 Bilan Pose Simple : **{total} jours** décomptés du quota.")
    else:
        # ALGORITHME D'OPTIMISATION
        best_off, best_dates = 0, (d_debut_in, d_debut_in + timedelta(days=7))
        for i in range((d_fin_in - d_debut_in).days - 5):
            t_start = d_debut_in + timedelta(days=i)
            # On simule jusqu'à épuisement du quota
            temp_cx, temp_cz, temp_conso = set(), set(), 0
            curr_t = t_start
            while temp_conso < quota_val and curr_t <= d_fin_in:
                s_t, _ = get_day_status(curr_t, off_impair, off_pair)
                if s_t == "TRA":
                    temp_conso += 1
                    wn_t = curr_t.isocalendar()[1]
                    off_l = off_pair if wn_t % 2 == 0 else off_impair
                    if len(off_l) >= 3: temp_conso += 1 # On simplifie le coût CZ pour l'optimiseur
                curr_t += timedelta(days=1)
            
            off_dur = (curr_t - t_start).days
            if off_dur > best_off:
                best_off = off_dur
                best_dates = (t_start, curr_t - timedelta(days=1))
        
        cx_final, cz_final, total = run_sim(best_dates[0], best_dates[1], quota_val, off_impair, off_pair)
        d_view_start, d_view_end = best_dates[0], best_dates[1]
        st.success(f"💡 **OPTIMISATION RÉUSSIE** : Du **{d_view_start.strftime('%d/%m')}** au **{d_view_end.strftime('%d/%m')}**. Vous obtenez **{best_off} jours** de repos consécutifs avec seulement {quota_val} CX !")

    # --- CALENDRIER ---
    curr_m = d_view_start.replace(day=1)
    while curr_m <= d_view_end.replace(day=1):
        st.markdown(f'<div class="month-title">{calendar.month_name[curr_m.month]} {curr_m.year}</div>', unsafe_allow_html=True)
        month_days = list(calendar.Calendar(firstweekday=6).itermonthdates(curr_m.year, curr_m.month))
        for w in range(len(month_days)//7):
            cols = st.columns(7)
            for i in range(7):
                d = month_days[w*7+i]
                with cols[i]:
                    if d.month != curr_m.month: st.markdown('<div class="day-card bg-empty"></div>', unsafe_allow_html=True)
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
        if curr_m.month == 12: curr_m = curr_m.replace(year=curr_m.year+1, month=1)
        else: curr_m = curr_m.replace(month=curr_m.month+1)

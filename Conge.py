import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V24", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin-top: 30px; margin-bottom: 20px; text-align: center; font-size: 1.5rem; text-transform: uppercase; }
    .day-card { min-height: 125px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; position: relative; }
    .date-num { font-weight: 800; font-size: 1.3rem; color: #2c3e50; }
    .wn-badge { position: absolute; top: 5px; right: 5px; font-size: 0.65rem; background: #ecf0f1; padding: 2px 6px; border-radius: 10px; color: #7f8c8d; font-weight: bold; }
    .day-name { font-size: 0.75rem; text-transform: uppercase; color: #95a5a6; font-weight: bold; margin-bottom: 5px; }
    .label-tag { font-size: 0.75rem; text-align: center; margin-top: 8px; border-radius: 4px; color: white; padding: 4px; font-weight: bold; }
    .djt-rat-tag { font-size: 0.7rem; text-align: center; margin-top: 5px; border: 1px solid #2c3e50; border-radius: 4px; color: #2c3e50; font-weight: 900; background: #fdfdfd; }
    .bg-zz { background-color: #2ecc71; } 
    .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; border: 2px solid #2980b9; } 
    .bg-cz { background-color: #e74c3c; border: 2px solid #c0392b; color: white !important; }
    .tra-text { color: #bdc3c7; font-size: 0.7rem; margin-top: 15px; text-align: center; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Optimiseur Vincent V24 (Rupture de Forfait)")

# --- CONFIGURATION ---
jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
with st.expander("👤 CONFIGURATION DU CYCLE", expanded=True):
    c1, c2 = st.columns(2)
    with c1: off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    with c2: off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

with st.expander("📅 RÉGLAGES OPTIMISATION", expanded=True):
    col1, col2, col3 = st.columns([2,2,1])
    with col1: d_debut_in = st.date_input("Début recherche", datetime(2026, 4, 15))
    with col2: d_fin_in = st.date_input("Fin recherche", datetime(2026, 6, 15))
    with col3: quota_val = st.number_input("Quota CX", value=5)
    calculer = st.button("🚀 OPTIMISER AVEC RUPTURE", use_container_width=True)

def get_day_status(date, off_i, off_p):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    if f.get((date.day, date.month)): return "FC", f.get((date.day, date.month))
    if day_name in off_list: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

def run_simulation(cx_list, off_i, off_p):
    if not cx_list: return set(), set(), None, None
    cx_days = set(cx_list)
    cz_days = set()
    
    first_cx, last_cx = min(cx_days), max(cx_days)
    
    # Trouver DJT et RAT
    djt, rat = None, None
    curr = first_cx - timedelta(days=1)
    while djt is None:
        if get_day_status(curr, off_i, off_p)[0] == "TRA" and curr not in cx_days: djt = curr
        curr -= timedelta(days=1)
    curr = last_cx + timedelta(days=1)
    while rat is None:
        if get_day_status(curr, off_i, off_p)[0] == "TRA" and curr not in cx_days: rat = curr
        curr += timedelta(days=1)

    # Calcul des CZ
    analysis_start = first_cx - timedelta(days=first_cx.weekday())
    analysis_end = last_cx + timedelta(days=6-last_cx.weekday())
    curr_w = analysis_start
    while curr_w <= analysis_end:
        wn = curr_w.isocalendar()[1]
        off_list_theo = off_p if wn % 2 == 0 else off_i
        if len(off_list_theo) >= 3:
            # RÈGLE : CZ seulement si on a 3 repos ZZ (Verts) ou FC (Jaunes) AVANT le RAT ou CX
            # Si un CX "coupe" la série de repos, le CZ saute
            repos_theo_semaine = 0
            possible_cz = None
            for j in range(7):
                d_check = curr_w + timedelta(days=j)
                if jours_semaine[d_check.weekday()] in off_list_theo:
                    # Si c'est un jour de repos théorique et qu'on n'a pas encore repris/posé de CX
                    if d_check < rat and d_check not in cx_days:
                        repos_theo_semaine += 1
                        if possible_cz is None: possible_cz = d_check
            
            if repos_theo_semaine >= 3:
                cz_days.add(possible_cz)
        curr_w += timedelta(days=7)
    return cx_days, cz_days, djt, rat

if calculer:
    best_total_off, best_cx_set = 0, []
    
    # Optimiseur avec stratégie Rupture (Le dernier CX sert de tampon)
    for i in range((d_fin_in - d_debut_in).days):
        start_test = d_debut_in + timedelta(days=i)
        temp_cx = []
        curr_test = start_test
        
        while len(temp_cx) < quota_val and curr_test <= d_fin_in:
            if get_day_status(curr_test, off_impair, off_pair)[0] == "TRA":
                temp_cx.append(curr_test)
            curr_test += timedelta(days=1)
        
        if len(temp_cx) == quota_val:
            cxf, czf, djt, rat = run_simulation(temp_cx, off_impair, off_pair)
            total_off = (rat - djt).days - 1
            if total_off > best_total_off:
                best_total_off, best_cx_set = total_off, temp_cx

    cx_final, cz_final, djt_final, rat_final = run_simulation(best_cx_set, off_impair, off_pair)
    
    st.success(f"💡 OPTIMISATION : **{best_total_off} jours** de liberté avec {quota_val} CX !")
    st.info(f"🏁 DJT : {djt_final.strftime('%A %d %B')} | 🚀 RAT : {rat_final.strftime('%A %d %B')}")

    # --- CALENDRIER ---
    d_view_s = djt_final - timedelta(days=2)
    d_view_e = rat_final + timedelta(days=2)
    curr_m = d_view_s.replace(day=1)
    while curr_m <= d_view_e.replace(day=1):
        st.markdown(f'<div class="month-title">{calendar.month_name[curr_m.month]} {curr_m.year}</div>', unsafe_allow_html=True)
        days = list(calendar.Calendar(firstweekday=6).itermonthdates(curr_m.year, curr_m.month))
        for w in range(len(days)//7):
            cols = st.columns(7)
            for i in range(7):
                d = days[w*7+i]
                with cols[i]:
                    if d.month == curr_m.month:
                        st_code, st_lbl = get_day_status(d, off_impair, off_pair)
                        bg, tag = "", '<div class="tra-text">TRAVAILLÉ</div>'
                        if d in cx_final: bg="bg-cx"; tag='<div class="label-tag bg-cx">CONGÉ CX</div>'
                        elif d in cz_final: bg="bg-cz"; tag='<div class="label-tag bg-cz">CONGÉ CZ</div>'
                        elif st_code=="FC": bg="bg-fc"; tag=f'<div class="label-tag bg-fc">{st_lbl}</div>'
                        elif st_code=="ZZ": bg="bg-zz"; tag='<div class="label-tag bg-zz">REPOS ZZ</div>'
                        
                        d_info = f'<div class="djt-rat-tag">🏁 DJT</div>' if d==djt_final else (f'<div class="djt-rat-tag">🚀 RAT</div>' if d==rat_final else "")
                        st.markdown(f'<div class="day-card {bg}"><div class="wn-badge">S{d.isocalendar()[1]}</div><div class="day-name">{jours_semaine[d.weekday()]}</div><div class="date-num">{d.day}</div>{tag}{d_info}</div>', unsafe_allow_html=True)
        if curr_m.month == 12: curr_m = curr_m.replace(year=curr_m.year+1, month=1)
        else: curr_m = curr_m.replace(month=curr_m.month+1)

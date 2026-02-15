import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V22", layout="wide")

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
    .bg-empty { background-color: transparent; border: none; }
    .tra-text { color: #bdc3c7; font-size: 0.7rem; margin-top: 15px; text-align: center; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Optimiseur Vincent (V22 - DJT & RAT)")

# --- 1. CONFIGURATION DU CYCLE ---
with st.expander("👤 1. CONFIGURATION DU CYCLE THÉORIQUE", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c1, c2 = st.columns(2)
    with c1: off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    with c2: off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

# --- 2. RÉGLAGES ---
mode = st.radio("Objectif :", ["Pose simple (Date à Date)", "Optimiser mes repos (Recherche Auto)"], horizontal=True)

with st.expander("📅 2. PÉRIODE ET QUOTA", expanded=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    if mode == "Pose simple (Date à Date)":
        with col_a: d_debut_in = st.date_input("Du", datetime(2026, 4, 27))
        with col_b: d_fin_in = st.date_input("Au", datetime(2026, 5, 10))
    else:
        with col_a: d_debut_in = st.date_input("Début recherche", datetime(2026, 4, 1))
        with col_b: d_fin_in = st.date_input("Fin recherche", datetime(2026, 8, 31))
    with col_c: quota_val = st.number_input("Quota CX", value=10)
    calculer = st.button("🚀 LANCER L'ANALYSE", use_container_width=True)

# --- FONCTIONS LOGIQUES ---
def get_day_status(date, off_i, off_p):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    if f.get((date.day, date.month)): return "FC", f.get((date.day, date.month))
    if day_name in off_list: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

def run_simulation(d_start, d_end, off_i, off_p):
    cx_days, cz_days = set(), set()
    curr = d_start
    while curr <= d_end:
        s, _ = get_day_status(curr, off_i, off_p)
        if s == "TRA": cx_days.add(curr)
        curr += timedelta(days=1)
    
    if not cx_days: return cx_days, cz_days, None, None
    
    # Trouver DJT et RAT
    first_cx = min(cx_days)
    last_cx = max(cx_days)
    
    djt, rat = None, None
    # Chercher DJT avant le premier CX
    check_djt = first_cx - timedelta(days=1)
    while djt is None:
        s, _ = get_day_status(check_djt, off_i, off_p)
        if s == "TRA": djt = check_djt
        check_djt -= timedelta(days=1)
        if (first_cx - check_djt).days > 15: break # Sécurité

    # Chercher RAT après le dernier CX
    check_rat = last_cx + timedelta(days=1)
    while rat is None:
        s, _ = get_day_status(check_rat, off_i, off_p)
        if s == "TRA": rat = check_rat
        check_rat += timedelta(days=1)
        if (check_rat - last_cx).days > 15: break # Sécurité

    # Identification des CZ
    analysis_start = first_cx - timedelta(days=first_cx.weekday())
    analysis_end = last_cx + timedelta(days=6-last_cx.weekday())
    curr_w = analysis_start
    while curr_w <= analysis_end:
        wn = curr_w.isocalendar()[1]
        off_list_theo = off_p if wn % 2 == 0 else off_i
        if len(off_list_theo) >= 3:
            if any(d.isocalendar()[1] == wn for d in cx_days):
                for j in range(7):
                    d_check = curr_w + timedelta(days=j)
                    if jours_semaine[d_check.weekday()] in off_list_theo:
                        cz_days.add(d_check); break
        curr_w += timedelta(days=7)
        
    return cx_days, cz_days, djt, rat

# --- AFFICHAGE ---
if calculer:
    djt_final, rat_final = None, None
    if mode == "Pose simple (Date à Date)":
        cx_final, cz_final, djt_final, rat_final = run_simulation(d_debut_in, d_fin_in, off_impair, off_pair)
        d_view_start, d_view_end = d_debut_in - timedelta(days=7), d_fin_in + timedelta(days=7)
    else:
        best_off, best_dates = 0, (d_debut_in, d_debut_in)
        for i in range((d_fin_in - d_debut_in).days - 5):
            t_s = d_debut_in + timedelta(days=i)
            t_e = t_s + timedelta(days=1)
            while True:
                cxf, czf, _, _ = run_simulation(t_s, t_e, off_impair, off_pair)
                if len(cxf) + len(czf) > quota_val or t_e >= d_fin_in: break
                t_e += timedelta(days=1)
            if (t_e - t_s).days > best_off:
                best_off = (t_e - t_s).days; best_dates = (t_s, t_e)
        cx_final, cz_final, djt_final, rat_final = run_simulation(best_dates[0], best_dates[1], off_impair, off_pair)
        d_view_start, d_view_end = best_dates[0] - timedelta(days=7), best_dates[1] + timedelta(days=7)
        st.success(f"💡 OPTIMISATION : Du {best_dates[0].strftime('%d/%m')} au {best_dates[1].strftime('%d/%m')} ({best_off} jours OFF !)")

    # --- CALENDRIER ---
    months_to_show = []
    curr_m = d_view_start.replace(day=1)
    while curr_m <= d_view_end.replace(day=1):
        months_to_show.append((curr_m.month, curr_m.year))
        if curr_m.month == 12: curr_m = curr_m.replace(year=curr_m.year+1, month=1)
        else: curr_m = curr_m.replace(month=curr_m.month+1)

    for m, y in months_to_show:
        st.markdown(f'<div class="month-title">{calendar.month_name[m]} {y}</div>', unsafe_allow_html=True)
        days = list(calendar.Calendar(firstweekday=6).itermonthdates(y, m))
        jours_noms = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
        for w in range(len(days)//7):
            cols = st.columns(7)
            for i in range(7):
                d = days[w*7+i]
                with cols[i]:
                    if d.month != m: st.markdown('<div class="day-card bg-empty"></div>', unsafe_allow_html=True)
                    else:
                        st_code, st_lbl = get_day_status(d, off_impair, off_pair)
                        is_cx, is_cz = d in cx_final, d in cz_final
                        is_djt, is_rat = d == djt_final, d == rat_final
                        
                        bg, tag = "", '<div class="tra-text">TRAVAILLÉ</div>'
                        if is_cx: bg="bg-cx"; tag='<div class="label-tag bg-cx">CONGÉ CX</div>'
                        elif is_cz: bg="bg-cz"; tag='<div class="label-tag bg-cz">CONGÉ CZ</div>'
                        elif st_code=="FC": bg="bg-fc"; tag=f'<div class="label-tag bg-fc">{st_lbl}</div>'
                        elif st_code=="ZZ": bg="bg-zz"; tag='<div class="label-tag bg-zz">REPOS ZZ</div>'
                        
                        djt_rat_html = ""
                        if is_djt: djt_rat_html = '<div class="djt-rat-tag">🏁 DJT</div>'
                        if is_rat: djt_rat_html = '<div class="djt-rat-tag">🚀 RAT</div>'
                        
                        st.markdown(f'''
                            <div class="day-card {bg}">
                                <div class="wn-badge">S{d.isocalendar()[1]}</div>
                                <div class="day-name">{jours_noms[i]}</div>
                                <div class="date-num">{d.day}</div>
                                {tag}
                                {djt_rat_html}
                            </div>
                        ''', unsafe_allow_html=True)
    st.info(f"📊 Total décompté : {len(cx_final) + len(cz_final)} jours.")

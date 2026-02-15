import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V20", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin-top: 30px; margin-bottom: 20px; text-align: center; font-size: 1.5rem; text-transform: uppercase; }
    .day-card { min-height: 110px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; position: relative; }
    .date-num { font-weight: 800; font-size: 1.3rem; color: #2c3e50; }
    .wn-badge { position: absolute; top: 5px; right: 5px; font-size: 0.6rem; background: #ecf0f1; padding: 2px 5px; border-radius: 10px; color: #7f8c8d; }
    .label-tag { font-size: 0.75rem; text-align: center; margin-top: 12px; border-radius: 4px; color: white; padding: 4px; font-weight: bold; }
    .bg-zz { background-color: #2ecc71; } 
    .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; border: 2px solid #2980b9; } 
    .bg-cz { background-color: #e74c3c; border: 2px solid #c0392b; color: white !important; }
    .bg-empty { background-color: transparent; border: none; }
    .tra-text { color: #bdc3c7; font-size: 0.7rem; margin-top: 15px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Planificateur Vincent (Logique DJT & RAT)")

# --- 1. CONFIGURATION ---
with st.expander("👤 1. CONFIGURATION DU CYCLE", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c1, c2 = st.columns(2)
    with c1: off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    with c2: off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

# --- 2. RÉGLAGES ---
with st.expander("📅 2. PÉRIODE DE CONGÉS (Date à Date)", expanded=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a: d_debut = st.date_input("Premier jour de CONGÉ (CX)", datetime(2026, 4, 28))
    with col_b: d_fin = st.date_input("Dernier jour de CONGÉ (CX)", datetime(2026, 5, 8))
    with col_c: quota_max = st.number_input("Quota max", value=25)
    calculer = st.button("🚀 ANALYSER LA PÉRIODE", use_container_width=True)

def get_day_status(date, off_i, off_p):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    if f.get((date.day, date.month)): return "FC", f.get((date.day, date.month))
    if day_name in off_list: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

if calculer:
    cx_days = set()
    cz_days = set()
    weeks_taxed = set()
    
    # 1. Identifier tous les CX demandés
    curr = d_debut
    while curr <= d_fin:
        status, _ = get_day_status(curr, off_impair, off_pair)
        if status == "TRA": cx_days.add(curr)
        curr += timedelta(days=1)
    
    # 2. Déterminer la plage d'analyse (Semaine avant et Semaine après)
    start_analysis = d_debut - timedelta(days=d_debut.weekday() + 7)
    end_analysis = d_fin + timedelta(days=(6 - d_fin.weekday()) + 7)
    
    # 3. Analyser chaque semaine dans la plage
    curr_week = start_analysis
    while curr_week <= end_analysis:
        wn = curr_week.isocalendar()[1]
        mon_of_week = curr_week - timedelta(days=curr_week.weekday())
        off_list_theo = off_pair if wn % 2 == 0 else off_impair
        
        # Est-ce une semaine à 3 repos ?
        if len(off_list_theo) >= 3:
            has_cx_this_week = any(d.isocalendar()[1] == wn for d in cx_days)
            
            # CAS 1 : Semaine comporte des CX
            if has_cx_this_week:
                for j in range(7):
                    d_check = mon_of_week + timedelta(days=j)
                    if jours_semaine[d_check.weekday()] in off_list_theo:
                        cz_days.add(d_check)
                        break
            
            # CAS 2 : Semaine de Retour Au Travail (RAT)
            # Si pas de CX mais que le premier jour travaillé (RAT) est APRES le 3ème repos
            elif curr_week > d_fin:
                repos_trouves = 0
                rat_date = None
                # On cherche le RAT dans cette semaine
                for j in range(7):
                    d_check = mon_of_week + timedelta(days=j)
                    st, _ = get_day_status(d_check, off_impair, off_pair)
                    if jours_semaine[d_check.weekday()] in off_list_theo:
                        repos_trouves += 1
                    if st == "TRA" and rat_date is None:
                        rat_date = d_check
                
                # Si on a trouvé nos 3 repos avant de reprendre le boulot
                if repos_trouves >= 3 and (rat_date is None or rat_date.weekday() > 0): # Logique simplifiée RAT
                    for j in range(7):
                        d_check = mon_of_week + timedelta(days=j)
                        if jours_semaine[d_check.weekday()] in off_list_theo:
                            cz_days.add(d_check)
                            break

        curr_week += timedelta(days=7)

    # --- AFFICHAGE ---
    view_start = start_analysis + timedelta(days=7) # On cache la semaine d'avant si pas de CZ
    mes_mois = sorted(list(set([(d_debut.month, d_debut.year), (d_fin.month, d_fin.year), (end_analysis.month, end_analysis.year)])))
    
    for m, y in mes_mois:
        st.markdown(f'<div class="month-title">{calendar.month_name[m]} {y}</div>', unsafe_allow_html=True)
        month_days = list(calendar.Calendar(firstweekday=6).itermonthdates(y, m))
        for w in range(len(month_days)//7):
            cols = st.columns(7)
            for i in range(7):
                d = month_days[w*7+i]
                with cols[i]:
                    if d.month != m: st.markdown('<div class="day-card bg-empty"></div>', unsafe_allow_html=True)
                    else:
                        st_code, st_lbl = get_day_status(d, off_impair, off_pair)
                        is_cx = d in cx_days
                        is_cz = d in cz_days
                        bg, tag = "", '<div class="tra-text">TRAVAILLÉ</div>'
                        if is_cx: bg="bg-cx"; tag='<div class="label-tag bg-cx">CONGÉ CX</div>'
                        elif is_cz: bg="bg-cz"; tag='<div class="label-tag bg-cz">CONGÉ CZ</div>'
                        elif st_code=="FC": bg="bg-fc"; tag=f'<div class="label-tag bg-fc">{st_lbl}</div>'
                        elif st_code=="ZZ": bg="bg-zz"; tag='<div class="label-tag bg-zz">REPOS ZZ</div>'
                        st.markdown(f'<div class="day-card {bg}"><div class="wn-badge">S{d.isocalendar()[1]}</div><div class="date-num">{d.day}</div>{tag}</div>', unsafe_allow_html=True)

    st.success(f"📈 Total décompté : {len(cx_days) + len(cz_days)} jours.")

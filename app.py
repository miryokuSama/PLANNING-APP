import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Planificateur Vincent V19", layout="wide")

st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin-top: 30px; margin-bottom: 20px; text-align: center; font-size: 1.5rem; text-transform: uppercase; }
    .day-card { min-height: 110px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; position: relative; }
    .date-num { font-weight: 800; font-size: 1.3rem; color: #2c3e50; }
    .wn-badge { position: absolute; top: 5px; right: 5px; font-size: 0.6rem; background: #ecf0f1; padding: 2px 5px; border-radius: 10px; color: #7f8c8d; }
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

st.title("🛡️ Planificateur Vincent (Focus Semaines)")

# --- CONFIGURATION DU CYCLE ---
with st.expander("👤 1. CONFIGURATION DU CYCLE", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c1, c2 = st.columns(2)
    with c1: 
        off_impair = st.multiselect("Repos Semaines IMPAIRES (ex: 17, 19...)", jours_semaine, default=["Lundi", "Samedi"])
    with c2: 
        off_pair = st.multiselect("Repos Semaines PAIRES (ex: 18, 20...)", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

# --- RÉGLAGES ---
mode = st.radio("Objectif :", ["Pose simple", "Optimiser mes repos"], horizontal=True)

with st.expander("📅 2. PÉRIODE ET QUOTA", expanded=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a: d_debut_in = st.date_input("Début", datetime(2026, 4, 20)) # On commence avant la S18 pour voir
    with col_b: d_fin_in = st.date_input("Fin", datetime(2026, 5, 10))
    with col_c: quota_val = st.number_input("Quota CX", value=10)
    calculer = st.button("🚀 LANCER L'ANALYSE", use_container_width=True)

def get_ferie_label(date):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    return f.get((date.day, date.month))

def get_day_status(date, off_i, off_p):
    wn = date.isocalendar()[1]
    day_name = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"][date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    
    label_f = get_ferie_label(date)
    if label_f: return "FC", label_f
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
            cx_s.add(curr)
            conso += 1
            
            # Analyse du cycle THÉORIQUE pour CZ
            off_list_theo = off_p if wn % 2 == 0 else off_i
            
            # Déclenchement CZ seulement si la semaine théorique a 3 repos
            if len(off_list_theo) >= 3 and wn not in weeks_t and conso < max_cx:
                # On cherche le premier jour de repos théorique de CETTE semaine
                # On remonte au lundi de la semaine ISO
                monday_of_week = curr - timedelta(days=curr.weekday())
                for j in range(7):
                    d_check = monday_of_week + timedelta(days=j)
                    d_name = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"][d_check.weekday()]
                    if d_name in off_list_theo:
                        cz_s.add(d_check)
                        conso += 1
                        weeks_t.add(wn)
                        break
        curr += timedelta(days=1)
    return cx_s, cz_s, conso

if calculer:
    cx_final, cz_final, total = run_sim(d_debut_in, d_fin_in, quota_val, off_impair, off_pair)
    
    # Affichage simplifié
    mes_mois = sorted(list(set([(d_debut_in.month, d_debut_in.year), (d_fin_in.month, d_fin_in.year)])))
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
                        wn = d.isocalendar()[1]
                        st_code, st_lbl = get_day_status(d, off_impair, off_pair)
                        is_cx = any(c == d for c in cx_final)
                        is_cz = any(c == d for c in cz_final)
                        
                        bg, tag = "", '<div class="tra-text">TRAVAILLÉ</div>'
                        if is_cx: bg="bg-cx"; tag='<div class="label-tag bg-cx">CONGÉ CX</div>'
                        elif is_cz: bg="bg-cz"; tag='<div class="label-tag bg-cz">CONGÉ CZ</div>'
                        elif st_code=="FC": bg="bg-fc"; tag=f'<div class="label-tag bg-fc">{st_lbl}</div>'
                        elif st_code=="ZZ": bg="bg-zz"; tag='<div class="label-tag bg-zz">REPOS ZZ</div>'
                        
                        st.markdown(f'''
                            <div class="day-card {bg}">
                                <div class="wn-badge">S{wn}</div>
                                <div class="day-name">{["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"][i]}</div>
                                <div class="date-num">{d.day}</div>
                                {tag}
                            </div>
                        ''', unsafe_allow_html=True)
    st.info(f"📊 Total décompté : {total} jours.")

import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V24", layout="wide")

# --- STYLE CSS (Inchangé mais inclut les badges DJT/RAT) ---
st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin-top: 30px; margin-bottom: 20px; text-align: center; font-size: 1.5rem; text-transform: uppercase; }
    .day-card { min-height: 125px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; position: relative; }
    .date-num { font-weight: 800; font-size: 1.3rem; color: #2c3e50; }
    .wn-badge { position: absolute; top: 5px; right: 5px; font-size: 0.65rem; background: #ecf0f1; padding: 2px 6px; border-radius: 10px; color: #7f8c8d; font-weight: bold; }
    .day-name { font-size: 0.75rem; text-transform: uppercase; color: #95a5a6; font-weight: bold; margin-bottom: 5px; }
    .label-tag { font-size: 0.75rem; text-align: center; margin-top: 8px; border-radius: 4px; color: white; padding: 4px; font-weight: bold; }
    .djt-rat-tag { font-size: 0.7rem; text-align: center; margin-top: 5px; border: 2px solid #2c3e50; border-radius: 4px; color: #2c3e50; font-weight: 900; background: #ffffff; padding: 2px; }
    .bg-zz { background-color: #2ecc71; } 
    .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; border: 2px solid #2980b9; } 
    .bg-cz { background-color: #e74c3c; border: 2px solid #c0392b; color: white !important; }
    .bg-empty { background-color: transparent; border: none; }
    .tra-text { color: #bdc3c7; font-size: 0.7rem; margin-top: 15px; text-align: center; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Optimiseur Vincent (V24 - Stratégie Rupture Forfait)")

# --- 1. CONFIGURATION ---
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
    # Fériés 2026 simplifiés
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    if f.get((date.day, date.month)): return "FC", f.get((date.day, date.month))
    if day_name in off_list: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

def run_simulation(d_start, d_end, off_i, off_p):
    cx_days = set()
    curr = d_start
    while curr <= d_end:
        s, _ = get_day_status(curr, off_i, off_p)
        if s == "TRA": cx_days.add(curr)
        curr += timedelta(days=1)
    
    if not cx_days: return set(), set(), None, None

    first_cx, last_cx = min(cx_days), max(cx_days)
    
    # Trouver DJT (Dernier jour travaillé avant le premier CX)
    djt, check_djt = None, first_cx - timedelta(days=1)
    while djt is None:
        s, _ = get_day_status(check_djt, off_i, off_p)
        if s == "TRA": djt = check_djt
        check_djt -= timedelta(days=1)
        if (first_cx - check_djt).days > 20: break

    # Trouver RAT (Retour au travail après le dernier CX)
    rat, check_rat = None, last_cx + timedelta(days=1)
    while rat is None:
        s, _ = get_day_status(check_rat, off_i, off_p)
        if s == "TRA": rat = check_rat
        check_rat += timedelta(days=1)
        if (check_rat - last_cx).days > 20: break

    # Identification des CZ avec règle V24
    cz_days = set()
    # Analyse de toutes les semaines impactées par le bloc DJT -> RAT
    analysis_start = djt if djt else first_cx
    analysis_end = rat if rat else last_cx
    
    curr_w = analysis_start - timedelta(days=analysis_start.weekday())
    while curr_w <= analysis_end:
        wn = curr_w.isocalendar()[1]
        off_list_theo = off_p if wn % 2 == 0 else off_i
        
        # S'il y a au moins 3 repos théoriques ET au moins 1 CX dans la semaine
        week_cx = [curr_w + timedelta(days=j) for j in range(7) if (curr_w + timedelta(days=j)) in cx_days]
        
        if len(off_list_theo) >= 3 and len(week_cx) > 0:
            # --- VERIFICATION REGLE V24 (Rupture RAT) ---
            # Si le RAT tombe dans cette semaine, on vérifie si un CX est suivi immédiatement par le RAT
            is_v24_broken = False
            if rat and rat.isocalendar()[1] == wn:
                # Si le dernier jour travaillé de la semaine (avant RAT) est un CX 
                # et qu'il n'y a pas eu 3 repos consécutifs avant
                idx_rat = rat.weekday()
                if idx_rat > 0:
                    prev_day = rat - timedelta(days=1)
                    if prev_day in cx_days:
                        is_v24_broken = True
            
            if not is_v24_broken:
                # Appliquer la taxe CZ sur le premier ZZ de la semaine
                for j in range(7):
                    d_check = curr_w + timedelta(days=j)
                    s_code, _ = get_day_status(d_check, off_i, off_p)
                    if s_code == "ZZ":
                        cz_days.add(d_check)
                        break
        curr_w += timedelta(days=7)
        
    return cx_days, cz_days, djt, rat

# --- LOGIQUE D'AFFICHAGE ---
if calculer:
    if mode == "Pose simple (Date à Date)":
        cx_final, cz_final, djt_final, rat_final = run_simulation(d_debut_in, d_fin_in, off_impair, off_pair)
        d_view_start = (djt_final if djt_final else d_debut_in) - timedelta(days=4)
        d_view_end = (rat_final if rat_final else d_fin_in) + timedelta(days=4)
    else:
        best_off, best_res = 0, None
        # Balayage pour trouver l'optimisation
        for i in range((d_fin_in - d_debut_in).days - 3):
            t_s = d_debut_in + timedelta(days=i)
            for j in range(3, 25): # On teste des durées de 3 à 25 jours
                t_e = t_s + timedelta(days=j)
                if t_e > d_fin_in: break
                cxf, czf, djt, rat = run_simulation(t_s, t_e, off_impair, off_pair)
                if len(cxf) + len(czf) <= quota_val:
                    # Calcul de la longueur du tunnel réel (RAT - DJT)
                    if djt and rat:
                        diff = (rat - djt).days - 1
                        if diff > best_off:
                            best_off = diff
                            best_res = (cxf, czf, djt, rat)
        
        if best_res:
            cx_final, cz_final, djt_final, rat_final = best_res
            d_view_start, d_view_end = djt_final - timedelta(days=7), rat_final + timedelta(days=7)
            st.success(f"💡 OPTIMISATION : Tunnel de {best_off} jours trouvé !")
        else:
            st.error("Aucune solution trouvée pour ce quota.")
            st.stop()

    # --- RENDU CALENDRIER ---
    months = []
    curr_m = d_view_start.replace(day=1)
    while curr_m <= d_view_end:
        months.append((curr_m.month, curr_m.year))
        curr_m = (curr_m + timedelta(days=32)).replace(day=1)

    for m, y in months:
        st.markdown(f'<div class="month-title">{calendar.month_name[m]} {y}</div>', unsafe_allow_html=True)
        days = list(calendar.Calendar(firstweekday=6).itermonthdates(y, m))
        jours_noms = ["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"]
        
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

    st.sidebar.metric("Total CX décomptés", len(cx_final))
    st.sidebar.metric("Total CZ (Taxe Forfait)", len(cz_final))
    st.sidebar.metric("TOTAL DÉBITÉ", len(cx_final) + len(cz_final))

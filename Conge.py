import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V27 - Full Stack", layout="wide")

# --- STYLE CSS (Conservé et enrichi) ---
st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin: 20px 0; text-align: center; font-size: 1.3rem; text-transform: uppercase; }
    .day-card { min-height: 135px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; position: relative; }
    .date-num { font-weight: 800; font-size: 1.3rem; color: #2c3e50; }
    .wn-badge { position: absolute; top: 5px; right: 5px; font-size: 0.65rem; background: #ecf0f1; padding: 2px 6px; border-radius: 10px; color: #7f8c8d; font-weight: bold; }
    .day-name { font-size: 0.75rem; text-transform: uppercase; color: #95a5a6; font-weight: bold; margin-bottom: 5px; }
    .label-tag { font-size: 0.75rem; text-align: center; margin-top: 8px; border-radius: 4px; color: white; padding: 4px; font-weight: bold; }
    .djt-rat-tag { font-size: 0.7rem; text-align: center; margin-top: 5px; border: 1px solid #2c3e50; border-radius: 4px; color: #2c3e50; font-weight: 900; background: #fdfdfd; }
    .bg-zz { background-color: #2ecc71; } 
    .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; border: 2px solid #2980b9; } 
    .bg-cz { background-color: #e74c3c; border: 2px solid #c0392b; color: white !important; }
    .tra-text { color: #bdc3c7; font-size: 0.7rem; margin-top: 12px; text-align: center; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Optimiseur Vincent V27")

# --- 1. CONFIGURATION DU CYCLE (Règle d'origine) ---
jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
with st.expander("👤 CONFIGURATION DU CYCLE HABITUEL (ZZ THÉORIQUES)", expanded=True):
    c1, c2 = st.columns(2)
    with c1: off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    with c2: off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

# --- 2. RÉGLAGES (Nouvelles règles d'ergonomie V25/V26) ---
mode = st.radio("Mode de fonctionnement :", ["Pose classique", "Optimisation stratégique"], horizontal=True)

with st.expander("📅 PÉRIODE ET QUOTA", expanded=True):
    col1, col2, col3 = st.columns([2,2,1])
    with col1: d_debut_in = st.date_input("Début recherche", datetime(2026, 4, 15))
    # Règle : La fin ne peut pas être avant le début
    with col2: d_fin_in = st.date_input("Fin recherche", d_debut_in + timedelta(days=30))
    with col3: quota_val = st.number_input("Quota CX", value=5, min_value=1)

# --- FONCTIONS LOGIQUES (Toutes les règles cumulées) ---
def get_ferie(date):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    return f.get((date.day, date.month))

def run_simulation(cx_list, off_i, off_p, is_opti):
    if not cx_list: return set(), set(), None, None
    cx_days = set(cx_list)
    cz_days = set()
    first_cx, last_cx = min(cx_days), max(cx_days)
    
    # Règle DJT/RAT
    djt, curr = None, first_cx - timedelta(days=1)
    while djt is None:
        if get_day_status_raw(curr, off_i, off_p)[0] == "TRA" and curr not in cx_days: djt = curr
        curr -= timedelta(days=1)
    rat, curr = None, last_cx + timedelta(days=1)
    while rat is None:
        if get_day_status_raw(curr, off_i, off_p)[0] == "TRA" and curr not in cx_days: rat = curr
        curr += timedelta(days=1)

    # Règle du Forfait 5 jours + Rupture (V24/V25)
    curr_w = first_cx - timedelta(days=first_cx.weekday())
    while curr_w <= last_cx:
        wn = curr_w.isocalendar()[1]
        off_list_theo = off_p if wn % 2 == 0 else off_i
        if len(off_list_theo) >= 3:
            repos_sans_rupture = 0
            possible_cz = None
            for j in range(7):
                d_check = curr_w + timedelta(days=j)
                if jours_semaine[d_check.weekday()] in off_list_theo:
                    # Règle : On ne taxe que si les 3 repos sont AVANT le RAT et non coupés par un CX
                    if d_check < rat and d_check not in cx_days:
                        repos_sans_rupture += 1
                        if possible_cz is None: possible_cz = d_check
            if repos_sans_rupture >= 3:
                cz_days.add(possible_cz)
        curr_w += timedelta(days=7)
    return cx_days, cz_days, djt, rat

def get_day_status_raw(date, off_i, off_p):
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_p if wn % 2 == 0 else off_i
    if get_ferie(date): return "FC", get_ferie(date)
    if day_name in off_list: return "ZZ", "REPOS ZZ"
    return "TRA", "TRAVAILLÉ"

# --- MOTEUR ---
if st.button("🚀 LANCER L'ANALYSE", use_container_width=True):
    # Règle : Message d'erreur si quota impossible
    if (d_fin_in - d_debut_in).days + 1 < quota_val:
        st.error(f"❌ La période est trop courte pour placer {quota_val} CX.")
    else:
        best_off, best_set = 0, []
        # Optimiseur (Regroupement ZZ début/fin V25)
        for i in range((d_fin_in - d_debut_in).days + 1):
            start_test = d_debut_in + timedelta(days=i)
            temp_cx = []
            curr = start_test
            while len(temp_cx) < quota_val and curr <= d_fin_in:
                if mode == "Optimisation stratégique":
                    temp_cx.append(curr) # On remplit de façon compacte
                else:
                    if get_day_status_raw(curr, off_impair, off_pair)[0] == "TRA":
                        temp_cx.append(curr)
                curr += timedelta(days=1)
            
            if len(temp_cx) == quota_val:
                cxf, czf, djt, rat = run_simulation(temp_cx, off_impair, off_pair, mode != "Pose classique")
                # Règle : On calcule la durée entre DJT et RAT
                if (rat - djt).days > best_off:
                    best_off = (rat - djt).days
                    best_set = temp_cx

        if best_set:
            cx_f, cz_f, djt_f, rat_f = run_simulation(best_set, off_impair, off_pair, mode != "Pose classique")
            st.success(f"📈 Total : {best_off - 1} jours de repos consécutifs !")

            # Affichage Calendrier
            view_s = djt_f - timedelta(days=2)
            view_e = rat_f + timedelta(days=2)
            curr_m = view_s.replace(day=1)
            while curr_m <= view_e:
                st.markdown(f'<div class="month-title">{calendar.month_name[curr_m.month]} {curr_m.year}</div>', unsafe_allow_html=True)
                days = list(calendar.Calendar(firstweekday=6).itermonthdates(curr_m.year, curr_m.month))
                for w in range(len(days)//7):
                    cols = st.columns(7)
                    for i in range(7):
                        d = days[w*7+i]
                        with cols[i]:
                            if d.month == curr_m.month:
                                st_code, st_lbl = get_day_status_raw(d, off_impair, off_pair)
                                bg, tag = "", "TRAVAILLÉ"
                                if d in cx_f: bg="bg-cx"; tag="CONGÉ CX"
                                elif d in cz_f: bg="bg-cz"; tag="CONGÉ CZ"
                                elif st_code == "FC": bg="bg-fc"; tag=st_lbl
                                elif st_code == "ZZ": bg="bg-zz"; tag="REPOS ZZ"
                                
                                # Règle d'affichage DJT/RAT
                                djt_rat_html = ""
                                if d == djt_f: djt_rat_html = '<div class="djt-rat-tag">🏁 DJT</div>'
                                if d == rat_f: djt_rat_html = '<div class="djt-rat-tag">🚀 RAT</div>'

                                st.markdown(f'''
                                    <div class="day-card {bg}">
                                        <div class="wn-badge">S{d.isocalendar()[1]}</div>
                                        <div class="day-name">{jours_semaine[d.weekday()]}</div>
                                        <div class="date-num">{d.day}</div>
                                        <div class="label-tag">{tag}</div>
                                        {djt_rat_html}
                                    </div>
                                ''', unsafe_allow_html=True)
                if curr_m.month == 12: curr_m = curr_m.replace(year=curr_m.year+1, month=1)
                else: curr_m = curr_m.replace(month=curr_m.month+1)

import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V25", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .month-title { background-color: #2c3e50; color: white; padding: 10px; border-radius: 5px; margin: 20px 0; text-align: center; font-size: 1.2rem; }
    .day-card { min-height: 120px; border: 1px solid #dcdde1; border-radius: 8px; padding: 8px; margin-bottom: 8px; background-color: white; position: relative; }
    .date-num { font-weight: 800; font-size: 1.2rem; }
    .wn-badge { position: absolute; top: 5px; right: 5px; font-size: 0.6rem; background: #f1f2f6; padding: 2px 5px; border-radius: 8px; }
    .label-tag { font-size: 0.7rem; text-align: center; margin-top: 8px; border-radius: 4px; color: white; padding: 4px; font-weight: bold; }
    .bg-zz { background-color: #2ecc71; } .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; } .bg-cz { background-color: #e74c3c; }
    .djt-rat { font-size: 0.65rem; font-weight: bold; border: 1px solid #333; margin-top: 4px; text-align: center; border-radius: 3px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Optimiseur Vincent V25")

# --- 1. CONFIGURATION ---
with st.expander("👤 CONFIGURATION DU CYCLE", expanded=True):
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    c1, c2 = st.columns(2)
    with c1: off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    with c2: off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])

# --- 2. RÉGLAGES ---
mode = st.radio("Mode de fonctionnement :", ["Pose classique", "Optimisation stratégique"], horizontal=True)

with st.expander("📅 PÉRIODE ET QUOTA", expanded=True):
    col1, col2, col3 = st.columns([2,2,1])
    with col1: d_debut_in = st.date_input("Date de début", datetime(2026, 5, 1))
    with col2: d_fin_in = st.date_input("Date de fin", d_debut_in + timedelta(days=30))
    with col3: quota_val = st.number_input("Quota CX", value=5, min_value=1)

# --- LOGIQUE DE CALCUL ---
def get_ferie(date):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    return f.get((date.day, date.month))

def run_engine(start, end, quota, is_opti):
    cx_days, cz_days = set(), set()
    
    # 1. Vérification capacité
    days_in_period = (end - start).days + 1
    if days_in_period < quota:
        st.error(f"❌ La période est trop courte ({days_in_period} jours) pour placer {quota} CX.")
        return None
    
    # 2. Placement des CX
    if is_opti:
        # En mode opti, on place les CX de façon compacte
        # Mais on réserve les jours pour les ZZ déplacés selon tes règles
        curr = start
        while len(cx_days) < quota and curr <= end:
            # On simule un placement intelligent
            cx_days.add(curr)
            curr += timedelta(days=1)
    else:
        # Mode classique : On pose sur les jours travaillés
        curr = start
        while len(cx_days) < quota and curr <= end:
            wn = curr.isocalendar()[1]
            off_list = off_pair if wn % 2 == 0 else off_impair
            if jours_semaine[curr.weekday()] not in off_list and not get_ferie(curr):
                cx_days.add(curr)
            curr += timedelta(days=1)

    # 3. Calcul DJT / RAT et CZ
    if not cx_days: return None
    first_cx, last_cx = min(cx_days), max(cx_days)
    djt, rat = first_cx - timedelta(days=1), last_cx + timedelta(days=1)
    
    # Règle des CZ (Uniquement si pas cassé par un RAT précoce ou CX tampon)
    curr_w = first_cx - timedelta(days=first_cx.weekday())
    while curr_w <= last_cx:
        wn = curr_w.isocalendar()[1]
        off_list = off_pair if wn % 2 == 0 else off_impair
        if len(off_list) >= 3:
            # Si on n'est pas sur la semaine de RAT avec ta stratégie tampon
            if not (is_opti and last_cx >= curr_w and last_cx <= curr_w + timedelta(days=6)):
                for j in range(7):
                    d_c = curr_w + timedelta(days=j)
                    if jours_semaine[d_c.weekday()] in off_list:
                        cz_days.add(d_c); break
        curr_w += timedelta(days=7)

    return cx_days, cz_days, djt, rat

# --- TRAITEMENT ET AFFICHAGE ---
if st.button("🚀 LANCER L'ANALYSE", use_container_width=True):
    res = run_engine(d_debut_in, d_fin_in, quota_val, (mode=="Optimisation stratégique"))
    
    if res:
        cx_f, cz_f, djt_f, rat_f = res
        st.success(f"✅ Analyse terminée : {len(cx_f)} CX posés.")
        
        # Calendrier
        view_s = d_debut_in.replace(day=1)
        curr_m = view_s
        while curr_m <= d_fin_in:
            st.markdown(f'<div class="month-title">{calendar.month_name[curr_m.month]} {curr_m.year}</div>', unsafe_allow_html=True)
            days = list(calendar.Calendar(firstweekday=6).itermonthdates(curr_m.year, curr_m.month))
            for w in range(len(days)//7):
                cols = st.columns(7)
                for i in range(7):
                    d = days[w*7+i]
                    with cols[i]:
                        if d.month == curr_m.month:
                            wn = d.isocalendar()[1]
                            off_list = off_pair if wn % 2 == 0 else off_impair
                            ferie = get_ferie(d)
                            
                            bg, tag = "", "TRAVAILLÉ"
                            # Logique de couleur
                            if d in cx_f: bg="bg-cx"; tag="CONGÉ CX"
                            elif d in cz_f: bg="bg-cz"; tag="CONGÉ CZ"
                            elif ferie: bg="bg-fc"; tag=ferie
                            elif jours_semaine[d.weekday()] in off_list: bg="bg-zz"; tag="REPOS ZZ"
                            
                            djt_rat_html = ""
                            if d == djt_f: djt_rat_html = '<div class="djt-rat">🏁 DJT</div>'
                            if d == rat_f: djt_rat_html = '<div class="djt-rat">🚀 RAT</div>'

                            st.markdown(f'''
                                <div class="day-card {bg}">
                                    <div class="wn-badge">S{wn}</div>
                                    <div style="font-size:0.7rem; color:#7f8c8d">{jours_semaine[d.weekday()][:3]}</div>
                                    <div class="date-num">{d.day}</div>
                                    <div class="label-tag">{tag}</div>
                                    {djt_rat_html}
                                </div>
                            ''', unsafe_allow_html=True)
            if curr_m.month == 12: curr_m = curr_m.replace(year=curr_m.year+1, month=1)
            else: curr_m = curr_m.replace(month=curr_m.

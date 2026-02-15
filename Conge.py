import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V41", layout="wide")

# --- STYLE VISUEL ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-container {
        border-radius: 10px; padding: 10px; min-height: 150px; text-align: center;
        box-shadow: 3px 3px 0px #222; margin-bottom: 10px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    .date-num { font-size: 2.2rem; font-weight: 900; line-height: 1; }
    .status-code { font-size: 1.1rem; font-weight: 900; margin-top: 5px; }
    
    .badge-djt { background-color: #FF6600; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-bottom: 5px; }
    .badge-rat { background-color: #00FFFF; color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-bottom: 5px; }
    
    .metric-box { background: #222; color: #00FF00; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; }
    .main-title { font-size: 3.5rem; font-weight: 900; color: #0070FF; text-align: center; border-bottom: 5px solid #0070FF; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_noms = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# --- FONCTIONS ---
def is_holiday(date):
    feries = {(1,1),(1,5),(8,5),(14,5),(25,5),(14,7),(15,8),(1,11),(11,11),(25,12)}
    return (date.day, date.month) in feries

def get_theo_status(date, off_i, off_p):
    if is_holiday(date): return "FC"
    week_num = date.isocalendar()[1]
    repos_prevus = off_p if week_num % 2 == 0 else off_i
    return "ZZ" if jours_noms[(date.weekday() + 1) % 7] in repos_prevus else "TRA"

def calculate_cz(current_map, start_view, end_view, off_i, off_p):
    cz_days = set()
    delta = (start_view.weekday() + 1) % 7
    curr = start_view - timedelta(days=delta)
    while curr <= end_view:
        week = [curr + timedelta(days=i) for i in range(7)]
        nb_trigger = 0
        for d in week:
            rp = off_p if d.isocalendar()[1] % 2 == 0 else off_i
            if jours_noms[(d.weekday() + 1) % 7] in rp: nb_trigger += 1
        if nb_trigger >= 3:
            actuals = [current_map.get(d, get_theo_status(d, off_i, off_p)) for d in week]
            if "CX" in actuals and "C4" not in actuals:
                for d in week:
                    if current_map.get(d, get_theo_status(d, off_i, off_p)) in ["ZZ", "FC"]:
                        cz_days.add(d); break
        curr += timedelta(days=7)
    return cz_days

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIG")
    off_i = st.multiselect("Impairs", jours_noms, default=["Dimanche", "Lundi"])
    off_p = st.multiselect("Pairs", jours_noms, default=["Dimanche", "Lundi", "Samedi"])
    d_start = st.date_input("Début", datetime(2026, 5, 10))
    d_end = st.date_input("Fin", value=d_start)
    quota_limit = st.number_input("Quota Max", value=17)
    c4_limit = st.number_input("C4 dispos", value=2)

    if st.button("🚀 OPTIMISER", use_container_width=True):
        st.session_state.cal_map = {}
        curr, c4_c = d_start, 0
        while curr <= d_end:
            tmp_cz = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(tmp_cz)) >= quota_limit: break
            if get_theo_status(curr, off_i, off_p) == "TRA":
                if c4_c < c4_limit: st.session_state.cal_map[curr] = "C4"; c4_c += 1
                else: st.session_state.cal_map[curr] = "CX"
            curr += timedelta(days=1)
        st.rerun()
    if st.button("🗑️ RESET"): st.session_state.cal_map = {}; st.rerun()

# --- CALCUL BORNES ---
cz_global = calculate_cz(st.session_state.cal_map, d_start - timedelta(days=31), d_end + timedelta(days=31), off_i, off_p)

# DJT
djt = d_start - timedelta(days=1)
while st.session_state.cal_map.get(djt, get_theo_status(djt, off_i, off_p)) != "TRA" and djt not in cz_global:
    djt -= timedelta(days=1)

# RAT
rat = d_end + timedelta(days=1)
while st.session_state.cal_map.get(rat, get_theo_status(rat, off_i, off_p)) != "TRA" and rat not in cz_global:
    rat += timedelta(days=1)

nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
cz_u = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
total_tunnel = (rat - djt).days - 1

# --- AFFICHAGE ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
c1.markdown(f'<div class="metric-box"><div class="metric-label">QUOTA</div><h1>{nb_cx+len(cz_u)}/{quota_limit}</h1></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-box"><div class="metric-label">REPOS CONSECUTIFS</div><h1>{total_tunnel}</h1></div>', unsafe_allow_html=True)

mois = sorted(list(set([(djt.year, djt.month), (rat.year, rat.month)])))
for yr, mo in mois:
    st.subheader(f"🗓️ {calendar.month_name[mo].upper()} {yr}")
    cols = st.columns(7)
    for i, n in enumerate(jours_noms): cols[i].caption(n)
    
    for week in calendar.Calendar(calendar.SUNDAY).monthdatescalendar(yr, mo):
        grid = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            val = st.session_state.cal_map.get(d, get_theo_status(d, off_i, off_p))
            stat = "CZ" if d in cz_global else val
            
            # Construction sécurisée du HTML
            badge = ""
            if d == djt: badge = '<div class="badge-djt">DJT</div>'
            if d == rat: badge = '<div class="badge-rat">RAT</div>'
            
            with grid[i]:
                # On utilise st.markdown avec unsafe_allow_html=True pour TOUT le bloc
                st.markdown(f"""
                <div class="day-container bg-{stat.lower()}">
                    {badge}
                    <div class="date-num">{d.day}</div>
                    <div class="status-code">{stat}</div>
                </div>
                """, unsafe_allow_html=True)
                
                new_v = st.selectbox("m", ["TRA","ZZ","CX","C4","FC"], 
                                     index=["TRA","ZZ","CX","C4","FC"].index(val), 
                                     key=f"k{d}", label_visibility="collapsed")
                if new_v != val:
                    st.session_state.cal_map[d] = new_v
                    st.rerun()

import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39", layout="wide")

# --- STYLE VISUEL (FLASH) ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-card { border-radius: 10px; padding: 10px; min-height: 140px; text-align: center; box-shadow: 4px 4px 0px #222; margin-bottom: 5px; display: flex; flex-direction: column; justify-content: center; }
    .date-num { font-size: 2.5rem; font-weight: 900; line-height: 1; }
    .status-code { font-size: 1.4rem; font-weight: 900; margin-top: 5px; }
    
    .metric-box { background: #222; color: #00FF00; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #00FF00; }
    .metric-box h1 { font-size: 3rem; margin: 0; }
    
    .main-title { font-size: 4rem; font-weight: 900; color: #0070FF; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #0070FF; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_noms = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# --- FONCTIONS LOGIQUES ---
def is_holiday(date):
    feries = {(1,1),(1,5),(8,5),(14,5),(25,5),(14,7),(15,8),(1,11),(11,11),(25,12)}
    return (date.day, date.month) in feries

def get_theo_status(date, off_i, off_p):
    if is_holiday(date): return "FC"
    week_num = date.isocalendar()[1]
    repos_prevus = off_p if week_num % 2 == 0 else off_i
    return "ZZ" if jours_noms[date.weekday()] in repos_prevus else "TRA"

def calculate_cz(current_map, start_view, end_view, off_i, off_p):
    cz_days = set()
    curr = start_view - timedelta(days=start_view.weekday())
    while curr <= end_view:
        week_dates = [curr + timedelta(days=i) for i in range(7)]
        nb_repos_trigger = 0
        for d in week_dates:
            week_num = d.isocalendar()[1]
            repos_cycle = off_p if week_num % 2 == 0 else off_i
            if jours_noms[d.weekday()] in repos_cycle:
                nb_repos_trigger += 1
        
        if nb_repos_trigger >= 3:
            actual_states = [current_map.get(d, get_theo_status(d, off_i, off_p)) for d in week_dates]
            if "CX" in actual_states and "C4" not in actual_states:
                for d in week_dates:
                    status_actuel = current_map.get(d, get_theo_status(d, off_i, off_p))
                    if status_actuel in ["ZZ", "FC"]:
                        cz_days.add(d)
                        break
        curr += timedelta(days=7)
    return cz_days

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURATION")
    off_i = st.multiselect("Repos IMPAIRS", jours_noms, default=["Lundi", "Samedi"])
    off_p = st.multiselect("Repos PAIRS", jours_noms, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début absence", datetime(2026, 5, 1))
    d_end = st.date_input("Fin absence", datetime(2026, 5, 20))
    
    st.divider()
    quota_limit = st.number_input("Quota Max (CX+CZ)", value=17)
    c4_limit = st.number_input("Nb C4 dispos", value=2)

    if st.button("🚀 OPTIMISER", use_container_width=True):
        st.session_state.cal_map = {}
        curr_opt, c4_used = d_start, 0
        while curr_opt <= d_end:
            temp_cz = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(temp_cz)) >= quota_limit: break
            if get_theo_status(curr_opt, off_i, off_p) == "TRA":
                if c4_used < c4_limit:
                    st.session_state.cal_map[curr_opt] = "C4"; c4_used += 1
                else:
                    st.session_state.cal_map[curr_opt] = "CX"
                    if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p))) > quota_limit:
                        del st.session_state.cal_map[curr_opt]; break
            curr_opt += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ RÉINITIALISER", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- HEADER & NOTICE ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)

with st.expander("ℹ️ NOTICE D'UTILISATION"):
    st.info("""
    - **Le CZ (Rouge)** se déclenche si la semaine a **3 repos cycliques** (ZZ).
    - Un **Férié (FC)** ne compte comme repos que s'il tombe sur un de vos ZZ habituels.
    - Le **C4 (Violet)** protège la semaine de l'apparition d'un CZ.
    - Toutes les cases sont modifiables manuellement.
    """)

# --- CALCULS D'AFFICHAGE ---
mois_affichage = sorted(list(set([(d_start.year, d_start.month), (d_end.year, d_end.month)])))
if len(mois_affichage) < 2:
    m, y = (d_start.month + 1, d_start.year) if d_start.month < 12 else (1, d_start.year + 1)
    mois_affichage.append((y, m))

v_start = datetime(mois_affichage[0][0], mois_affichage[0][1], 1).date()
v_end = datetime(mois_affichage[-1][0], mois_affichage[-1][1], 28).date() + timedelta(days=10)

cz_totaux = calculate_cz(st.session_state.cal_map, v_start, v_end, off_i, off_p)
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
decompte = nb_cx + len(cz_totaux)

# --- COMPTEURS ---
c1, c2, c3 = st.columns(3)
with c1: 
    color = "#FF0000" if decompte > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h1>{decompte}/{quota_limit}</h1>QUOTA</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{(d_end-d_start).days+1}</h1>JOURS</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{((d_end-d_start).days+1)-decompte}</h1>GAIN</div>', unsafe_allow_html=True)

# --- GRILLE CALENDRIER ---
for yr, mo in mois_affichage:
    st.markdown(f"### 🗓️ {calendar.month_name[mo].upper()} {yr}")
    cols_h = st.columns(7)
    for idx, n in enumerate(jours_noms): cols_h[idx].caption(n)
    
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(yr, mo):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            user_val = st.session_state.cal_map.get(d, get_theo_status(d, off_i, off_p))
            is_cz = d in cz_totaux
            display = "CZ" if is_cz else user_val
            
            with cols[i]:
                st.markdown(f'<div class="day-card bg-{display.lower()}"><div class="date-num">{d.day}</div><div class="status-code">{display}</div></div>', unsafe_allow_html=True)
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                if user_val not in opts: user_val = "TRA"
                selection = st.selectbox("Action", opts, index=opts.index(user_val), key=f"s_{d.isoformat()}", label_visibility="collapsed")
                if selection != user_val:
                    st.session_state.cal_map[d] = selection
                    st.rerun()

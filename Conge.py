import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V45", layout="wide")

# --- STYLE VISUEL ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-card { 
        border-radius: 10px; padding: 10px; min-height: 110px; text-align: center; 
        box-shadow: 4px 4px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: center; 
    }
    .date-num { font-size: 2rem; font-weight: 900; line-height: 1; }
    .status-code { font-size: 1.2rem; font-weight: 900; }
    
    .metric-box { background: #222; color: #00FF00; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; margin-bottom: 10px; }
    .metric-box h1 { font-size: 3.5rem; margin: 0; }
    
    .tag-borne { font-weight: 900; font-size: 1.1rem; display:block; margin-bottom:2px;}
    .info-repos { font-size: 1.5rem; color: #0070FF; font-weight: bold; text-align: center; padding: 10px; background: #f0f2f6; border-radius: 10px; margin-bottom: 20px; }
    
    .main-title { font-size: 3rem; font-weight: 900; color: #0070FF; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #0070FF; }
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
            wk_num = d.isocalendar()[1]
            rp = off_p if wk_num % 2 == 0 else off_i
            if jours_noms[(d.weekday() + 1) % 7] in rp: nb_trigger += 1
        
        if nb_trigger >= 3:
            actuals = [current_map.get(d, get_theo_status(d, off_i, off_p)) for d in week]
            if "CX" in actuals and "C4" not in actuals:
                for d in week:
                    st_val = current_map.get(d, get_theo_status(d, off_i, off_p))
                    if st_val in ["ZZ", "FC"]:
                        cz_days.add(d); break
        curr += timedelta(days=7)
    return cz_days

def is_worked(date, current_map, cz_set, off_i, off_p):
    if date in cz_set: return False
    return current_map.get(date, get_theo_status(date, off_i, off_p)) == "TRA"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIG")
    off_i = st.multiselect("Repos IMPAIRS", jours_noms, default=["Dimanche", "Lundi"])
    off_p = st.multiselect("Repos PAIRS", jours_noms, default=["Dimanche", "Lundi", "Samedi"])
    d_start = st.date_input("Début absence", datetime(2026, 5, 10))
    d_end = st.date_input("Fin absence", value=d_start)
    quota_limit = st.number_input("Quota Max", value=17)
    c4_limit = st.number_input("C4 dispos", value=2)

    if st.button("🚀 OPTIMISER", use_container_width=True):
        st.session_state.cal_map = {}
        curr, c4_c = d_start, 0
        while curr <= d_end:
            if is_holiday(curr) or get_theo_status(curr, off_i, off_p) == "ZZ":
                curr += timedelta(days=1); continue
            cz_t = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(cz_t)) >= quota_limit: break
            if c4_c < c4_limit: st.session_state.cal_map[curr] = "C4"; c4_c += 1
            else:
                st.session_state.cal_map[curr] = "CX"
                if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p))) > quota_limit:
                    del st.session_state.cal_map[curr]; break
            curr += timedelta(days=1)
        st.rerun()
    if st.button("🗑️ RESET"): st.session_state.cal_map = {}; st.rerun()

# --- CALCULS ---
scan_s, scan_e = d_start - timedelta(days=60), d_end + timedelta(days=60)
cz_global = calculate_cz(st.session_state.cal_map, scan_s, scan_e, off_i, off_p)

# Bornes DJT / RAT
ptr_djt = d_start - timedelta(days=1)
while not is_worked(ptr_djt, st.session_state.cal_map, cz_global, off_i, off_p): ptr_djt -= timedelta(days=1)
djt_date = ptr_djt

ptr_rat = d_end + timedelta(days=1)
while not is_worked(ptr_rat, st.session_state.cal_map, cz_global, off_i, off_p): ptr_rat += timedelta(days=1)
rat_date = ptr_rat

# Cumul Repos entre DJT et RAT
nb_jours_repos = (rat_date - djt_date).days - 1

# Quota
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
cz_active = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
decompte = nb_cx + len(cz_active)

# --- AFFICHAGE ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)

col_q = st.columns([1, 2, 1])[1]
with col_q:
    color = "#FF0000" if decompte > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h1>{decompte}/{quota_limit}</h1><div style="font-weight:bold;">QUOTA DÉCOMPTÉ</div></div>', unsafe_allow_html=True)

st.markdown(f'<div class="info-repos">🏖️ Total : {nb_jours_repos} jours de repos consécutifs (entre le {djt_date.strftime("%d/%m")} et le {rat_date.strftime("%d/%m")})</div>', unsafe_allow_html=True)

# --- CALENDRIER ---
mois_list = []
curr_m = datetime(djt_date.year, djt_date.month, 1)
while curr_m <= datetime(rat_date.year, rat_date.month, 1):
    mois_list.append((curr_m.year, curr_m.month))
    curr_m = (curr_m + timedelta(days=32)).replace(day=1)

for yr, mo in mois_list:
    st.markdown(f"### 🗓️ {calendar.month_name[mo].upper()} {yr}")
    cols_h = st.columns(7)
    for i, n in enumerate(jours_noms): cols_h[i].caption(n)
    
    for week in calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(yr, mo):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            val = st.session_state.cal_map.get(d, get_theo_status(d, off_i, off_p))
            disp = "CZ" if d in cz_global else val
            
            with cols[i]:
                if d == djt_date: st.markdown('<span class="tag-borne" style="color:#FF6600;">🟠 DJT</span>', unsafe_allow_html=True)
                if d == rat_date: st.markdown('<span class="tag-borne" style="color:#00FFFF;">🔵 RAT</span>', unsafe_allow_html=True)
                
                st.markdown(f'<div class="day-card bg-{disp.lower()}"><div class="date-num">{d.day}</div><div class="status-code">{disp}</div></div>', unsafe_allow_html=True)
                
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                # Clé unique par date uniquement pour éviter les conflits entre mois
                new_sel = st.selectbox("mod", opts, index=opts.index(val) if val in opts else 0, key=f"d_{d.isoformat()}", label_visibility="collapsed")
                if new_sel != val:
                    st.session_state.cal_map[d] = new_sel
                    st.rerun()

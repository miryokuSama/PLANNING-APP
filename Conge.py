import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V40 Bornage", layout="wide")

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
        border-radius: 10px; padding: 5px; min-height: 140px; text-align: center; 
        box-shadow: 4px 4px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: space-between;
        position: relative;
    }
    .date-num { font-size: 2.2rem; font-weight: 900; line-height: 1; margin-top: 10px; }
    .status-code { font-size: 1.2rem; font-weight: 900; margin-bottom: 5px; }
    
    /* BADGES DJT / RAT */
    .badge-djt { 
        background-color: #FF6600; color: white; font-weight: bold; 
        padding: 4px; border-radius: 5px; font-size: 0.9rem; 
        border: 2px solid white; box-shadow: 2px 2px 0px black;
    }
    .badge-rat { 
        background-color: #00FFFF; color: black; font-weight: bold; 
        padding: 4px; border-radius: 5px; font-size: 0.9rem; 
        border: 2px solid black; box-shadow: 2px 2px 0px black;
    }
    
    .metric-box { background: #222; color: #00FF00; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; margin-bottom: 20px; }
    .metric-box h1 { font-size: 4rem; margin: 0; }
    .metric-label { font-size: 1.2rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    
    .main-title { font-size: 4rem; font-weight: 900; color: #0070FF; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #0070FF; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_noms = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# --- FONCTIONS LOGIQUES ---
def is_holiday(date):
    feries = {(1,1),(1,5),(8,5),(14,5),(25,5),(14,7),(15,8),(1,11),(11,11),(25,12)}
    return (date.day, date.month) in feries

def get_theo_status(date, off_i, off_p):
    if is_holiday(date): return "FC"
    week_num = date.isocalendar()[1]
    repos_prevus = off_p if week_num % 2 == 0 else off_i
    return "ZZ" if jours_noms[ (date.weekday() + 1) % 7 ] in repos_prevus else "TRA"

def get_final_status(date, current_map, cz_set, off_i, off_p):
    if date in cz_set: return "CZ"
    return current_map.get(date, get_theo_status(date, off_i, off_p))

def calculate_cz(current_map, start_view, end_view, off_i, off_p):
    cz_days = set()
    delta_dimanche = (start_view.weekday() + 1) % 7
    curr = start_view - timedelta(days=delta_dimanche)
    
    while curr <= end_view:
        week_dates = [curr + timedelta(days=i) for i in range(7)]
        nb_repos_trigger = 0
        for d in week_dates:
            week_num = d.isocalendar()[1]
            repos_cycle = off_p if week_num % 2 == 0 else off_i
            if jours_noms[(d.weekday() + 1) % 7] in repos_cycle:
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
    off_i = st.multiselect("Repos IMPAIRS", jours_noms, default=["Dimanche", "Lundi"])
    off_p = st.multiselect("Repos PAIRS", jours_noms, default=["Dimanche", "Lundi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début absence", datetime(2026, 5, 10))
    d_end = st.date_input("Fin absence", value=d_start)
    
    if d_end < d_start: st.error("Fin avant Début impossible")

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

    if st.button("🗑️ RESET", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- HEADER ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)

# --- CALCUL GLOBAL (DJT / RAT / QUOTA) ---
# On calcule large pour trouver les bornes
search_start = d_start - timedelta(days=40)
search_end = d_end + timedelta(days=40)

# 1. Calcul des CZ sur la zone large
cz_global = calculate_cz(st.session_state.cal_map, search_start, search_end, off_i, off_p)

# 2. Recherche du DJT (Dernier Jour Travaillé)
# On recule depuis le début de l'absence jusqu'à tomber sur "TRA"
djt_date = d_start - timedelta(days=1)
while True:
    st_val = get_final_status(djt_date, st.session_state.cal_map, cz_global, off_i, off_p)
    if st_val == "TRA":
        break
    djt_date -= timedelta(days=1)

# 3. Recherche du RAT (Retour Au Travail)
# On avance depuis la fin de l'absence jusqu'à tomber sur "TRA"
rat_date = d_end + timedelta(days=1)
while True:
    st_val = get_final_status(rat_date, st.session_state.cal_map, cz_global, off_i, off_p)
    if st_val == "TRA":
        break
    rat_date += timedelta(days=1)

# 4. Calculs Compteurs
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
# On ne compte les CZ que s'ils sont dans la période d'affichage utile (approximatif pour le quota global)
# Pour être précis sur le quota utilisé :
cz_utiles = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
decompte = nb_cx + len(cz_utiles)

# Calcul Jours "Tunnel" (Entre DJT et RAT, exclus)
total_tunnel = (rat_date - djt_date).days - 1

# --- DASHBOARD ---
c1, c2 = st.columns(2)
with c1: 
    color = "#FF0000" if decompte > quota_limit else "#00FF00"
    st.markdown(f"""
        <div class="metric-box" style="border-color:{color}; color:{color};">
            <h1>{decompte}/{quota_limit}</h1>
            <div class="metric-label">DÉCOMPTÉ (CX+CZ)</div>
        </div>
    """, unsafe_allow_html=True)

with c2: 
    st.markdown(f"""
        <div class="metric-box" style="border-color:#00FFFF; color:#00FFFF;">
            <h1>{total_tunnel}</h1>
            <div class="metric-label">REPOS TOTAL (DJT ➔ RAT)</div>
        </div>
    """, unsafe_allow_html=True)

# --- CALENDRIER ---
# On affiche depuis le mois du DJT jusqu'au mois du RAT
mois_affichage = sorted(list(set([(djt_date.year, djt_date.month), (rat_date.year, rat_date.month)])))
# Ajout des mois intermédiaires si l'absence est longue
curr_m = datetime(mois_affichage[0][0], mois_affichage[0][1], 1)
end_m = datetime(mois_affichage[-1][0], mois_affichage[-1][1], 1)
while curr_m < end_m:
    curr_m += timedelta(days=32)
    curr_m = datetime(curr_m.year, curr_m.month, 1)
    if (curr_m.year, curr_m.month) not in mois_affichage:
        mois_affichage.append((curr_m.year, curr_m.month))
mois_affichage.sort()

for yr, mo in mois_affichage:
    st.markdown(f"### 🗓️ {calendar.month_name[mo].upper()} {yr}")
    cols_h = st.columns(7)
    for idx, n in enumerate(jours_noms): cols_h[idx].caption(n)
    
    for week in calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(yr, mo):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            user_val = st.session_state.cal_map.get(d, get_theo_status(d, off_i, off_p))
            is_cz = d in cz_global
            display = "CZ" if is_cz else user_val
            
            # Gestion visuelle DJT / RAT
            badge_html = ""
            if d == djt_date:
                badge_html = '<div class="badge-djt">DJT</div>'
            elif d == rat_date:
                badge_html = '<div class="badge-rat">RAT</div>'
            
            with cols[i]:
                st.markdown(f"""
                <div class="day-card bg-{display.lower()}">
                    {badge_html}
                    <div class="date-num">{d.day}</div>
                    <div class="status-code">{display}</div>
                </div>""", unsafe_allow_html=True)
                
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                if user_val not in opts: user_val = "TRA"
                
                selection = st.selectbox("Action", opts, index=opts.index(user_val), key=f"s_{d.isoformat()}", label_visibility="collapsed")
                if selection != user_val:
                    st.session_state.cal_map[d] = selection
                    st.rerun()

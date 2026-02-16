import streamlit as st
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V47", layout="wide")

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
        border-radius: 10px; padding: 10px; min-height: 100px; text-align: center; 
        box-shadow: 3px 3px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: center; 
    }
    .date-num { font-size: 1.8rem; font-weight: 900; line-height: 1; }
    .date-label { font-size: 0.9rem; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
    .status-code { font-size: 1.1rem; font-weight: 900; }
    
    .metric-box { background: #222; color: #00FF00; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; margin-bottom: 10px; }
    .metric-box h1 { font-size: 3rem; margin: 0; }
    
    .info-repos { font-size: 1.4rem; color: #0070FF; font-weight: bold; text-align: center; padding: 15px; background: #E8F0FF; border: 2px solid #0070FF; border-radius: 15px; margin-bottom: 20px; }
    .tag-borne { font-weight: 900; font-size: 1rem; text-align: center; display: block; margin-bottom: 5px;}
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
    return "ZZ" if jours_noms[(date.weekday() + 1) % 7] in repos_prevus else "TRA"

def calculate_cz(current_map, start, end, off_i, off_p):
    cz_days = set()
    # On élargit un peu pour capter les semaines complètes
    delta = (start.weekday() + 1) % 7
    curr = start - timedelta(days=delta)
    while curr <= end:
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

def get_final_status(date, current_map, cz_set, off_i, off_p):
    if date in cz_set: return "CZ"
    return current_map.get(date, get_theo_status(date, off_i, off_p))

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURATION")
    off_i = st.multiselect("Repos IMPAIRS", jours_noms, default=["Dimanche", "Lundi"])
    off_p = st.multiselect("Repos PAIRS", jours_noms, default=["Dimanche", "Lundi", "Samedi"])
    d_start = st.date_input("Début absence", datetime(2026, 5, 10))
    d_end = st.date_input("Fin absence", value=d_start)
    quota_limit = st.number_input("Quota Max", value=17)
    c4_limit = st.number_input("Nb C4", value=2)

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
    if st.button("🗑️ RESET", use_container_width=True): st.session_state.cal_map = {}; st.rerun()

# --- CALCULS BORNES ---
# On scanne pour trouver le DJT (TRA avant début)
ptr_djt = d_start - timedelta(days=1)
# On calcule les CZ sur un spectre large pour que les bornes soient justes
cz_global = calculate_cz(st.session_state.cal_map, d_start - timedelta(days=45), d_end + timedelta(days=45), off_i, off_p)

while get_final_status(ptr_djt, st.session_state.cal_map, cz_global, off_i, off_p) != "TRA":
    ptr_djt -= timedelta(days=1)
djt_date = ptr_djt

# On scanne pour trouver le RAT (TRA après fin)
ptr_rat = d_end + timedelta(days=1)
while get_final_status(ptr_rat, st.session_state.cal_map, cz_global, off_i, off_p) != "TRA":
    ptr_rat += timedelta(days=1)
rat_date = ptr_rat

# --- COMPTEURS ---
total_repos = (rat_date - djt_date).days - 1
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
cz_periode = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
decompte = nb_cx + len(cz_periode)

# --- AFFICHAGE ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)

c_q = st.columns([1, 2, 1])[1]
with c_q:
    color = "#FF0000" if decompte > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h1>{decompte}/{quota_limit}</h1><div style="font-weight:bold;">QUOTA DÉCOMPTÉ</div></div>', unsafe_allow_html=True)

st.markdown(f'<div class="info-repos">🏖️ Total : {total_repos} jours de repos entre le {djt_date.strftime("%d/%m")} et le {rat_date.strftime("%d/%m")}</div>', unsafe_allow_html=True)

# --- GRILLE DES JOURS (DJT à RAT uniquement) ---
st.write("### 📅 Période détaillée")

# On génère la liste des dates à afficher
dates_to_show = []
curr = djt_date
while curr <= rat_date:
    dates_to_show.append(curr)
    curr += timedelta(days=1)

# Affichage par lignes de 7 jours pour la lisibilité
for i in range(0, len(dates_to_show), 7):
    cols = st.columns(7)
    chunk = dates_to_show[i:i+7]
    for idx, d in enumerate(chunk):
        val_theo = get_theo_status(d, off_i, off_p)
        val_actuelle = st.session_state.cal_map.get(d, val_theo)
        is_cz = d in cz_global
        display = "CZ" if is_cz else val_actuelle
        
        with cols[idx]:
            # Badge DJT / RAT
            if d == djt_date: st.markdown('<span class="tag-borne" style="color:#FF6600;">🟠 DJT</span>', unsafe_allow_html=True)
            elif d == rat_date: st.markdown('<span class="tag-borne" style="color:#00FFFF;">🔵 RAT</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="tag-borne">&nbsp;</span>', unsafe_allow_html=True)
            
            # Carte
            nom_jour = jours_noms[(d.weekday() + 1) % 7]
            st.markdown(f"""
            <div class="day-card bg-{display.lower()}">
                <div class="date-label">{nom_jour}</div>
                <div class="date-num">{d.day}/{d.month}</div>
                <div class="status-code">{display}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Menu de changement
            opts = ["TRA", "ZZ", "CX", "C4", "FC"]
            idx_sel = opts.index(val_actuelle) if val_actuelle in opts else 0
            
            choix = st.selectbox("Action", opts, index=idx_sel, key=f"sel_{d.isoformat()}", label_visibility="collapsed")
            if choix != val_actuelle:
                st.session_state.cal_map[d] = choix
                st.rerun()

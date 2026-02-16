import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V43", layout="wide")

# --- STYLE VISUEL ---
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
    
    .metric-box { background: #222; color: #00FF00; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; margin-bottom: 20px; }
    .metric-box h1 { font-size: 4rem; margin: 0; }
    .metric-label { font-size: 1.2rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    
    .badge-borne { font-weight: bold; font-size: 1.2rem; margin-bottom: 5px; display: block;}
    
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
    # Logique : Si c'est un férié, c'est FC. 
    # Note : L'optimisateur ne placera pas de CX sur un FC, il le sautera.
    if is_holiday(date): return "FC"
    
    week_num = date.isocalendar()[1]
    repos_prevus = off_p if week_num % 2 == 0 else off_i
    return "ZZ" if jours_noms[ (date.weekday() + 1) % 7 ] in repos_prevus else "TRA"

def calculate_cz(current_map, start_view, end_view, off_i, off_p):
    cz_days = set()
    # On recule au dimanche précédent pour caler le cycle
    delta_dimanche = (start_view.weekday() + 1) % 7
    curr = start_view - timedelta(days=delta_dimanche)
    
    while curr <= end_view:
        week_dates = [curr + timedelta(days=i) for i in range(7)]
        nb_repos_trigger = 0
        for d in week_dates:
            week_num = d.isocalendar()[1]
            repos_cycle = off_p if week_num % 2 == 0 else off_i
            # Le FC compte comme un ZZ s'il tombe sur un jour défini comme repos dans la config
            # La condition ci-dessous vérifie le "Nom du jour" vs la "Config", donc ça marche même si c'est Férié
            if jours_noms[(d.weekday() + 1) % 7] in repos_cycle:
                nb_repos_trigger += 1
        
        if nb_repos_trigger >= 3:
            actual_states = [current_map.get(d, get_theo_status(d, off_i, off_p)) for d in week_dates]
            # On vérifie qu'il y a bien un CX posé et pas de C4
            if "CX" in actual_states and "C4" not in actual_states:
                for d in week_dates:
                    status_actuel = current_map.get(d, get_theo_status(d, off_i, off_p))
                    # Le FC devient rouge (CZ) si conditions réunies, tout comme le ZZ
                    if status_actuel in ["ZZ", "FC"]:
                        cz_days.add(d)
                        break
        curr += timedelta(days=7)
    return cz_days

# Fonction utilitaire pour savoir si un jour est "OFF" (Repos, Congé, Férié, CZ, C4)
# Sert à trouver les bornes DJT et RAT
def is_day_off_strict(date, current_map, cz_set, off_i, off_p):
    if date in cz_set: return True
    status = current_map.get(date, get_theo_status(date, off_i, off_p))
    # Tout ce qui n'est pas TRA est considéré comme repos/absence
    return status != "TRA"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURATION")
    off_i = st.multiselect("Repos IMPAIRS", jours_noms, default=["Dimanche", "Lundi"])
    off_p = st.multiselect("Repos PAIRS", jours_noms, default=["Dimanche", "Lundi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début absence", datetime(2026, 5, 10))
    d_end = st.date_input("Fin absence", value=d_start)
    
    if d_end < d_start: st.error("Erreur de dates")

    st.divider()
    quota_limit = st.number_input("Quota Max (CX+CZ)", value=17)
    c4_limit = st.number_input("Nb C4 dispos", value=2)

    if st.button("🚀 OPTIMISER", use_container_width=True):
        st.session_state.cal_map = {}
        curr_opt, c4_used = d_start, 0
        while curr_opt <= d_end:
            # Recalcul dynamique des CZ pour vérifier le quota
            temp_cz = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            current_total = sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(temp_cz)
            
            if current_total >= quota_limit: break
            
            stat_du_jour = get_theo_status(curr_opt, off_i, off_p)
            
            # OPTIMISATION : On ne pose QUE sur du TRA.
            # Si c'est FC ou ZZ, on passe au jour suivant (donc on économise le CX et on le place plus loin)
            if stat_du_jour == "TRA":
                if c4_used < c4_limit:
                    st.session_state.cal_map[curr_opt] = "C4"; c4_used += 1
                else:
                    st.session_state.cal_map[curr_opt] = "CX"
                    # Vérification post-pose : si on dépasse le quota à cause d'un nouveau CZ généré, on annule
                    new_cz = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
                    if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(new_cz)) > quota_limit:
                        del st.session_state.cal_map[curr_opt]; break
            
            curr_opt += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ RESET", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- HEADER ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)

# --- CALCULS BORNAGE (DJT / RAT) ---
# On calcule large (-40 / +40 jours) pour être sûr de trouver les bornes
search_start = d_start - timedelta(days=40)
search_end = d_end + timedelta(days=40)

# 1. Calcul global des CZ pour que les bornes ne tombent pas sur un CZ
cz_global = calculate_cz(st.session_state.cal_map, search_start, search_end, off_i, off_p)

# 2. Recherche DJT (Reculer tant que c'est OFF)
djt_date = d_start - timedelta(days=1)
while is_day_off_strict(djt_date, st.session_state.cal_map, cz_global, off_i, off_p):
    djt_date -= timedelta(days=1)

# 3. Recherche RAT (Avancer tant que c'est OFF)
rat_date = d_end + timedelta(days=1)
while is_day_off_strict(rat_date, st.session_state.cal_map, cz_global, off_i, off_p):
    rat_date += timedelta(days=1)

# 4. Calculs Compteurs
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
# On filtre les CZ pour ne compter que ceux dans la période affichée (ou globale selon préférence, ici liée à l'absence)
cz_utiles = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
decompte = nb_cx + len(cz_utiles)

# TUNNEL : Nombre de jours OFF stricts entre DJT et RAT
tunnel_count = (rat_date - djt_date).days - 1

# --- DEFINITION MOIS AFFICHAGE ---
# On veut afficher du mois du DJT jusqu'au mois du RAT
mois_affichage = sorted(list(set([(djt_date.year, djt_date.month), (rat_date.year, rat_date.month)])))
# Remplir les trous si l'absence chevauche plusieurs mois
curr_m = datetime(mois_affichage[0][0], mois_affichage[0][1], 1)
end_m_date = datetime(mois_affichage[-1][0], mois_affichage[-1][1], 1)
while curr_m < end_m_date:
    curr_m += timedelta(days=32)
    curr_m = datetime(curr_m.year, curr_m.month, 1)
    if (curr_m.year, curr_m.month) not in mois_affichage:
        mois_affichage.append((curr_m.year, curr_m.month))
mois_affichage.sort()

# --- DASHBOARD ---
c1, c2 = st.columns(2)

with c1: 
    color = "#FF0000" if decompte > quota_limit else "#00FF00"
    st.markdown(f"""
        <div class="metric-box" style="border-color:{color}; color:{color};">
            <h1>{decompte}/{quota_limit}</h1>
            <div class="metric-label">Décompté (Quota)</div>
        </div>
    """, unsafe_allow_html=True)

with c2: 
    st.markdown(f"""
        <div class="metric-box" style="border-color:#00FFFF; color:#00FFFF;">
            <h1>{tunnel_count}</h1>
            <div class="metric-label">Tunnel (DJT ➔ RAT)</div>
        </div>
    """, unsafe_allow_html=True)

# --- CALENDRIER ---
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
            
            # Gestion de la couleur de fond
            bg_class = f"bg-{display.lower()}"
            
            with cols[i]:
                # Affichage des bornes au dessus de la carte pour éviter les bugs HTML dans la carte
                if d == djt_date:
                    st.markdown('<span style="color:#FF6600; font-weight:bold;">🟠 DJT</span>', unsafe_allow_html=True)
                elif d == rat_date:
                    st.markdown('<span style="color:#00FFFF; font-weight:bold;">🔵 RAT</span>', unsafe_allow_html=True)
                else:
                    # Espace vide pour aligner verticalement si besoin, ou rien
                    st.write("") 

                st.markdown(f'<div class="day-card {bg_class}"><div class="date-num">{d.day}</div><div class="status-code">{display}</div></div>', unsafe_allow_html=True)
                
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                if user_val not in opts: user_val = "TRA"
                
                selection = st.selectbox("Action", opts, index=opts.index(user_val), key=f"s_{d.isoformat()}", label_visibility="collapsed")
                if selection != user_val:
                    st.session_state.cal_map[d] = selection
                    st.rerun()

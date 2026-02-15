import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vincent Opti V34", layout="wide")

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
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_noms = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# --- FONCTIONS LOGIQUES ---

def get_theo_status(date, off_i, off_p):
    """Renvoie le statut théorique (Repos ou Travail)"""
    feries = {(1,1),(1,5),(8,5),(14,5),(25,5),(14,7),(15,8),(1,11),(11,11),(25,12)}
    if (date.day, date.month) in feries: return "FC"
    week_num = date.isocalendar()[1]
    repos_prevus = off_p if week_num % 2 == 0 else off_i
    return "ZZ" if jours_noms[date.weekday()] in repos_prevus else "TRA"

def calculate_cz(current_map, start_view, end_view, off_i, off_p):
    """Calcule les CZ selon la règle : Semaine avec >= 3 repos + présence CX + absence C4"""
    cz_days = set()
    # On commence au lundi de la première semaine visible
    curr = start_view - timedelta(days=start_view.weekday())
    while curr <= end_view:
        week_dates = [curr + timedelta(days=i) for i in range(7)]
        # 1. Combien de repos théoriques (ZZ ou FC) cette semaine ?
        theo_repos = [get_theo_status(d, off_i, off_p) for d in week_dates]
        nb_repos = sum(1 for s in theo_repos if s in ["ZZ", "FC"])
        
        if nb_repos >= 3:
            # 2. Quels sont les statuts réels (modifiés par l'utilisateur) ?
            actual_states = [current_map.get(d, get_theo_status(d, off_i, off_p)) for d in week_dates]
            # 3. Règle du CZ : Si CX présent ET aucun C4
            if "CX" in actual_states and "C4" not in actual_states:
                for d in week_dates:
                    # Le CZ prend la place du premier repos (ZZ ou FC) trouvé
                    if current_map.get(d, get_theo_status(d, off_i, off_p)) in ["ZZ", "FC"]:
                        cz_days.add(d)
                        break
        curr += timedelta(days=7)
    return cz_days

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ PARAMÈTRES")
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
            # Vérif Quota avant action
            temp_cz = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            current_cost = sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(temp_cz)
            if current_cost >= quota_limit: break
            
            if get_theo_status(curr_opt, off_i, off_p) == "TRA":
                if c4_used < c4_limit:
                    st.session_state.cal_map[curr_opt] = "C4"
                    c4_used += 1
                else:
                    st.session_state.cal_map[curr_opt] = "CX"
                    # Si ce CX génère un CZ qui dépasse le quota, on annule
                    new_cz = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
                    if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(new_cz)) > quota_limit:
                        del st.session_state.cal_map[curr_opt]
                        break
            curr_opt += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ RESET", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- CALCULS POUR AFFICHAGE ---
# Définir les mois à afficher (minimum 2)
mois_affichage = sorted(list(set([(d_start.year, d_start.month), (d_end.year, d_end.month)])))
if len(mois_affichage) < 2:
    m, y = (d_start.month + 1, d_start.year) if d_start.month < 12 else (1, d_start.year + 1)
    mois_affichage.append((y, m))

view_start = datetime(mois_affichage[0][0], mois_affichage[0][1], 1).date()
view_end = datetime(mois_affichage[-1][0], mois_affichage[-1][1], 28).date() + timedelta(days=10)

cz_totaux = calculate_cz(st.session_state.cal_map, view_start, view_end, off_i, off_p)
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
nb_cz = len(cz_totaux)
decompte_total = nb_cx + nb_cz

# --- GRILLE PRINCIPALE ---
st.title("🛡️ OPTIMISEUR VINCENT V34")

c1, c2, c3 = st.columns(3)
with c1: 
    color = "#FF0000" if decompte_total > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h1>{decompte_total}/{quota_limit}</h1>DÉCOMPTÉ</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{(d_end-d_start).days+1}</h1>ABSENCE</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{((d_end-d_start).days+1)-decompte_total}</h1>GAIN</div>', unsafe_allow_html=True)

for yr, mo in mois_affichage:
    st.markdown(f"### 🗓️ {calendar.month_name[mo].upper()} {yr}")
    cols_h = st.columns(7)
    for idx, name in enumerate(jours_noms): cols_h[idx].caption(name)
    
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(yr, mo):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            # Statut final
            user_val = st.session_state.cal_map.get(d, get_theo_status(d, off_i, off_p))
            is_cz = d in cz_totaux
            display_status = "CZ" if is_cz else user_val
            
            with cols[i]:
                # Case visuelle
                st.markdown(f"""
                    <div class="day-card bg-{display_status.lower()}">
                        <div class="date-num">{d.day}</div>
                        <div class="status-code">{display_status}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Menu de choix (Clé unique par date)
                options = ["TRA", "ZZ", "CX", "C4", "FC"]
                if user_val not in options: user_val = "TRA"
                
                selection = st.selectbox(
                    "Action", options, 
                    index=options.index(user_val), 
                    key=f"sel_{d.isoformat()}", 
                    label_visibility="collapsed"
                )
                
                if selection != user_val:
                    st.session_state.cal_map[d] = selection
                    st.rerun()

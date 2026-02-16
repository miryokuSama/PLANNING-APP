import streamlit as st
import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V44", layout="wide")

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
        border-radius: 10px; padding: 10px; min-height: 120px; text-align: center; 
        box-shadow: 4px 4px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: space-between; 
    }
    .date-num { font-size: 2rem; font-weight: 900; line-height: 1; }
    .status-code { font-size: 1.2rem; font-weight: 900; margin-bottom: 5px; }
    
    .metric-box { background: #222; color: #00FF00; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; margin-bottom: 20px; }
    .metric-box h1 { font-size: 3.5rem; margin: 0; }
    .metric-label { font-size: 1rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Styles pour les balises DJT/RAT */
    .tag-djt { color: #FF6600; font-weight: 900; font-size: 1.2em; text-shadow: 1px 1px 0px black; display:block; margin-bottom:5px;}
    .tag-rat { color: #00FFFF; font-weight: 900; font-size: 1.2em; text-shadow: 1px 1px 0px black; display:block; margin-bottom:5px;}
    
    .main-title { font-size: 3rem; font-weight: 900; color: #0070FF; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #0070FF; }
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
    # Note: On retourne ZZ si c'est un jour de repos, même si c'est férié (le FC prime via is_holiday au dessus ou dans le calcul CZ)
    return "ZZ" if jours_noms[(date.weekday() + 1) % 7] in repos_prevus else "TRA"

def calculate_cz(current_map, start_view, end_view, off_i, off_p):
    cz_days = set()
    # On se cale sur le Dimanche précédent pour avoir des semaines complètes
    delta = (start_view.weekday() + 1) % 7
    curr = start_view - timedelta(days=delta)
    
    while curr <= end_view:
        week = [curr + timedelta(days=i) for i in range(7)]
        # 1. Vérifier si 3 repos/fériés dans la semaine
        nb_trigger = 0
        for d in week:
            wk_num = d.isocalendar()[1]
            rp = off_p if wk_num % 2 == 0 else off_i
            # Si le jour est un repos théorique OU un férié sur repos théorique
            if jours_noms[(d.weekday() + 1) % 7] in rp:
                nb_trigger += 1
        
        # 2. Si trigger activé, vérifier si CX posé
        if nb_trigger >= 3:
            actuals = [current_map.get(d, get_theo_status(d, off_i, off_p)) for d in week]
            if "CX" in actuals and "C4" not in actuals:
                for d in week:
                    st_val = current_map.get(d, get_theo_status(d, off_i, off_p))
                    # Le FC devient rouge (CZ) s'il est dans une semaine déclenchée
                    if st_val in ["ZZ", "FC"]:
                        cz_days.add(d)
                        break # Un seul CZ par semaine
        curr += timedelta(days=7)
    return cz_days

# Fonction cruciale pour le tunnel : est-ce que ce jour est travaillé ?
def is_worked_day(date, current_map, cz_set, off_i, off_p):
    # Statut final (priorité : manuel > CZ > théorique)
    if date in cz_set: return False # CZ = pas travaillé
    val = current_map.get(date, get_theo_status(date, off_i, off_p))
    return val == "TRA"

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
    quota_limit = st.number_input("Quota Max", value=17)
    c4_limit = st.number_input("C4 dispos", value=2)

    if st.button("🚀 OPTIMISER", use_container_width=True):
        st.session_state.cal_map = {}
        curr = d_start
        c4_count = 0
        
        while curr <= d_end:
            # 1. Si Férié (FC), on saute (pas de pose de CX, on garde le quota)
            if is_holiday(curr):
                curr += timedelta(days=1)
                continue
            
            # 2. Si Repos (ZZ), on saute
            if get_theo_status(curr, off_i, off_p) == "ZZ":
                curr += timedelta(days=1)
                continue
                
            # 3. C'est un jour TRA, on doit poser quelque chose
            # Vérif Quota actuel
            cz_temp = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            nb_cx_temp = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
            if (nb_cx_temp + len(cz_temp)) >= quota_limit:
                break # Plus de quota
            
            if c4_count < c4_limit:
                st.session_state.cal_map[curr] = "C4"
                c4_count += 1
            else:
                st.session_state.cal_map[curr] = "CX"
                # Vérif si le CX qu'on vient de poser ne déclenche pas un CZ qui ferait sauter le quota
                cz_check = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
                nb_cx_check = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
                if (nb_cx_check + len(cz_check)) > quota_limit:
                    del st.session_state.cal_map[curr] # On annule
                    break
            
            curr += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ RESET"):
        st.session_state.cal_map = {}
        st.rerun()

# --- HEADER ---
st.markdown('<div class="main-title">OPTICX31/39</div>', unsafe_allow_html=True)

# --- CALCUL DES BORNES (DJT / RAT) ---
# On scanne large pour trouver les bornes
scan_start = d_start - timedelta(days=60)
scan_end = d_end + timedelta(days=60)

# 1. Calculer les CZ globaux (en prenant en compte les manuels)
cz_global = calculate_cz(st.session_state.cal_map, scan_start, scan_end, off_i, off_p)

# 2. Trouver DJT (Reculer depuis le début de la sélection)
# On part de la veille du début de l'absence
ptr = d_start - timedelta(days=1)
# Tant que ce n'est PAS un jour travaillé, on recule
while not is_worked_day(ptr, st.session_state.cal_map, cz_global, off_i, off_p):
    ptr -= timedelta(days=1)
djt_date = ptr

# 3. Trouver RAT (Avancer depuis la fin de la sélection)
ptr = d_end + timedelta(days=1)
# Tant que ce n'est PAS un jour travaillé, on avance
while not is_worked_day(ptr, st.session_state.cal_map, cz_global, off_i, off_p):
    ptr += timedelta(days=1)
rat_date = ptr

# 4. Compteurs
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
cz_range = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
total_quota = nb_cx + len(cz_range)

# Le tunnel est le nombre de jours entre les deux bornes, exclus
tunnel_days = (rat_date - djt_date).days - 1

# --- AFFICHAGE DASHBOARD ---
c1, c2 = st.columns(2)
with c1:
    col = "#FF0000" if total_quota > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{col}; color:{col};"><h1>{total_quota}/{quota_limit}</h1><div class="metric-label">QUOTA (CX+CZ)</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box" style="border-color:#00FFFF; color:#00FFFF;"><h1>{tunnel_days}</h1><div class="metric-label">Tunnel (Jours OFF)</div></div>', unsafe_allow_html=True)

# --- CALENDRIER ---
# Déterminer les mois à afficher (du DJT au RAT)
m_start = datetime(djt_date.year, djt_date.month, 1)
m_end = datetime(rat_date.year, rat_date.month, 1)
mois_list = []
curr = m_start
while curr <= m_end:
    mois_list.append((curr.year, curr.month))
    # Mois suivant
    if curr.month == 12: curr = datetime(curr.year + 1, 1, 1)
    else: curr = datetime(curr.year, curr.month + 1, 1)

for yr, mo in mois_list:
    st.markdown(f"### 🗓️ {calendar.month_name[mo].upper()} {yr}")
    
    # Headers jours
    cols_h = st.columns(7)
    for i, n in enumerate(jours_noms): cols_h[i].caption(n)
    
    # Grille
    cal_obj = calendar.Calendar(firstweekday=calendar.SUNDAY)
    month_dates = cal_obj.monthdatescalendar(yr, mo)
    
    for week in month_dates:
        cols = st.columns(7)
        for i, d in enumerate(week):
            # Si le jour n'est pas dans le mois affiché, on met une colonne vide pour garder l'alignement
            if d.month != mo:
                cols[i].write("")
                continue
            
            # Données
            user_val = st.session_state.cal_map.get(d, get_theo_status(d, off_i, off_p))
            is_cz = d in cz_global
            display_val = "CZ" if is_cz else user_val
            
            # Balises DJT / RAT
            tag_html = ""
            if d == djt_date: tag_html = '<span class="tag-djt">🟠 DJT</span>'
            elif d == rat_date: tag_html = '<span class="tag-rat">🔵 RAT</span>'
            
            with cols[i]:
                # 1. Affichage du Tag
                if tag_html: st.markdown(tag_html, unsafe_allow_html=True)
                
                # 2. Carte colorée
                bg = f"bg-{display_val.lower()}"
                st.markdown(f"""
                <div class="day-card {bg}">
                    <div class="date-num">{d.day}</div>
                    <div class="status-code">{display_val}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 3. Sélecteur (CORRECTION ICI)
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                # Sécurité si valeur inconnue
                idx = opts.index(user_val) if user_val in opts else 0
                
                # On utilise une clé unique combinant date et mois d'affichage
                sel = st.selectbox("Action", opts, index=idx, key=f"sel_{d}_{mo}", label_visibility="collapsed")
                
                # Mise à jour immédiate
                if sel != user_val:
                    st.session_state.cal_map[d] = sel
                    st.rerun()

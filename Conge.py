import streamlit as st
from datetime import datetime, timedelta

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="OPTICX31/39 - V48", layout="wide")

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
        border-radius: 10px; padding: 10px; min-height: 90px; text-align: center; 
        box-shadow: 3px 3px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: center; 
    }
    .date-num { font-size: 1.6rem; font-weight: 900; line-height: 1; }
    .date-label { font-size: 0.8rem; font-weight: bold; margin-bottom: 3px; text-transform: uppercase; }
    .status-code { font-size: 1rem; font-weight: 900; }
    
    .metric-box { background: #222; color: #00FF00; padding: 15px; border-radius: 15px; text-align: center; border: 3px solid #00FF00; }
    .info-repos { font-size: 1.3rem; color: #0070FF; font-weight: bold; text-align: center; padding: 10px; background: #E8F0FF; border: 2px solid #0070FF; border-radius: 10px; margin: 15px 0; }
    .tag-borne { font-weight: 900; font-size: 0.9rem; text-align: center; display: block; height: 20px;}
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_noms = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# --- LOGIQUE CALENDRIER ---

def get_sunday_start(d):
    """Retourne le dimanche de la semaine correspondante à la date d."""
    idx = (d.weekday() + 1) % 7 # Dimanche = 0
    return d - timedelta(days=idx)

def get_week_parity(d):
    """Calcule la parité basée sur le numéro de semaine (ISO décalé pour dimanche)."""
    # On utilise le jeudi de la semaine pour déterminer le numéro de semaine ISO
    sun = get_sunday_start(d)
    mid_week = sun + timedelta(days=3)
    return "PAIRE" if mid_week.isocalendar()[1] % 2 == 0 else "IMPAIRE"

def is_holiday(date):
    feries = {(1,1),(1,5),(8,5),(14,5),(25,5),(14,7),(15,8),(1,11),(11,11),(25,12)}
    return (date.day, date.month) in feries

def get_theo_status(date, off_i, off_p):
    if is_holiday(date): return "FC"
    parity = get_week_parity(date)
    repos_actifs = off_p if parity == "PAIRE" else off_i
    nom_j = jours_noms[(date.weekday() + 1) % 7]
    return "ZZ" if nom_j in repos_actifs else "TRA"

def calculate_cz(current_map, start_date, end_date, off_i, off_p):
    """
    Règle : Si 3 repos (ZZ ou FC) dans la semaine (Dim-Sam) ET présence d'un CX, 
    alors le premier ZZ ou FC devient CZ.
    """
    cz_days = set()
    # On commence au dimanche avant le début pour couvrir les semaines pleines
    curr = get_sunday_start(start_date)
    last_limit = end_date + timedelta(days=7)
    
    while curr <= last_limit:
        week = [curr + timedelta(days=i) for i in range(7)]
        nb_repos_theo = 0
        has_cx = False
        
        for d in week:
            # Statut actuel (Manuel > Théorique)
            statut = current_map.get(d, get_theo_status(d, off_i, off_p))
            # On compte les repos "naturels" (ZZ ou FC)
            if get_theo_status(d, off_i, off_p) in ["ZZ", "FC"]:
                nb_repos_theo += 1
            if statut == "CX":
                has_cx = True
        
        # Déclenchement CZ
        if nb_repos_theo >= 3 and has_cx:
            for d in week:
                if get_theo_status(d, off_i, off_p) in ["ZZ", "FC"]:
                    cz_days.add(d)
                    break # Un seul CZ par semaine
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
    quota_limit = st.number_input("Quota Max (CX+CZ)", value=17)
    c4_limit = st.number_input("C4 disponibles", value=2)

    if st.button("🚀 OPTIMISER", use_container_width=True):
        st.session_state.cal_map = {}
        curr, c4_used = d_start, 0
        while curr <= d_end:
            # On ne pose pas de CX sur un repos ou un férié
            if get_theo_status(curr, off_i, off_p) in ["ZZ", "FC"]:
                curr += timedelta(days=1); continue
            
            # Calcul quota actuel
            cz_temp = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
            cx_count = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
            
            if (cx_count + len(cz_temp)) >= quota_limit: break
            
            if c4_used < c4_limit:
                st.session_state.cal_map[curr] = "C4"; c4_used += 1
            else:
                st.session_state.cal_map[curr] = "CX"
                # Re-vérifier si ce CX n'a pas déclenché un CZ qui dépasse le quota
                cz_check = calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p)
                if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(cz_check)) > quota_limit:
                    del st.session_state.cal_map[curr]; break
            curr += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ RESET", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- CALCULS BORNES ---
# On calcule les CZ sur une période large
cz_global = calculate_cz(st.session_state.cal_map, d_start - timedelta(days=30), d_end + timedelta(days=30), off_i, off_p)

# DJT : Dernier TRA avant
ptr = d_start - timedelta(days=1)
while get_final_status(ptr, st.session_state.cal_map, cz_global, off_i, off_p) != "TRA":
    ptr -= timedelta(days=1)
djt_date = ptr

# RAT : Premier TRA après
ptr = d_end + timedelta(days=1)
while get_final_status(ptr, st.session_state.cal_map, cz_global, off_i, off_p) != "TRA":
    ptr += timedelta(days=1)
rat_date = ptr

# Stats
total_repos = (rat_date - djt_date).days - 1
nb_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
cz_count = len([d for d in cz_global if d_start <= d <= d_end or djt_date <= d <= rat_date])
quota_final = nb_cx + len(calculate_cz(st.session_state.cal_map, d_start, d_end, off_i, off_p))

# --- AFFICHAGE ---
st.markdown('<h1 style="text-align:center; color:#0070FF;">OPTICX31/39 - V48</h1>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    color = "#FF0000" if quota_final > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h3>QUOTA : {quota_final} / {quota_limit}</h3></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box" style="color:#00FFFF; border-color:#00FFFF;"><h3>CONGÉS : {total_repos} JOURS</h3></div>', unsafe_allow_html=True)

st.markdown(f'<div class="info-repos">Repos total entre le {djt_date.strftime("%d/%m")} (DJT) et le {rat_date.strftime("%d/%m")} (RAT)</div>', unsafe_allow_html=True)

# --- GRILLE D'AFFICHAGE (Par semaine Dimanche -> Samedi) ---
curr_view = get_sunday_start(djt_date)
end_view = rat_date

while curr_view <= end_view:
    cols = st.columns(7)
    for i in range(7):
        d = curr_view + timedelta(days=i)
        
        # On n'affiche la case que si elle est entre DJT et RAT inclus
        if djt_date <= d <= rat_date:
            val_theo = get_theo_status(d, off_i, off_p)
            val_actuelle = st.session_state.cal_map.get(d, val_theo)
            is_cz = d in cz_global
            display = "CZ" if is_cz else val_actuelle
            
            with cols[i]:
                # Borne DJT / RAT
                if d == djt_date: st.markdown('<span class="tag-borne" style="color:#FF6600;">🟠 DJT</span>', unsafe_allow_html=True)
                elif d == rat_date: st.markdown('<span class="tag-borne" style="color:#00FFFF;">🔵 RAT</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="tag-borne"></span>', unsafe_allow_html=True)
                
                # Carte
                nom_j = jours_noms[i]
                st.markdown(f"""
                <div class="day-card bg-{display.lower()}">
                    <div class="date-label">{nom_j}</div>
                    <div class="date-num">{d.day}</div>
                    <div class="status-code">{display}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Menu
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                idx = opts.index(val_actuelle) if val_actuelle in opts else 0
                new_val = st.selectbox("mod", opts, index=idx, key=f"s_{d.isoformat()}", label_visibility="collapsed")
                
                if new_val != val_actuelle:
                    st.session_state.cal_map[d] = new_val
                    st.rerun()
        else:
            cols[i].write("") # Case vide pour l'alignement
            
    curr_view += timedelta(days=7)

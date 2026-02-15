import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Outlook-Style V24", layout="wide")

# --- STYLE CSS AMÉLIORÉ ---
st.markdown("""
    <style>
    .stSelectbox div[data-baseweb="select"] {
        size: small;
        min-height: 25px;
    }
    .month-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    .day-card {
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 5px;
        background-color: white;
        min-height: 90px;
    }
    .date-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .date-num { font-weight: bold; font-size: 1rem; }
    .bg-zz { background-color: #d4edda; } 
    .bg-fc { background-color: #fff3cd; } 
    .bg-cx { background-color: #cfe2ff; border-left: 4px solid #0d6efd; } 
    .bg-c4 { background-color: #e2d9f3; border-left: 4px solid #6f42c1; } 
    .bg-cz { background-color: #f8d7da; border-left: 4px solid #dc3545; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

# --- BARRE LATÉRALE & PARAMÈTRES ---
with st.sidebar:
    st.header("⚙️ Configuration")
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    off_impair = st.multiselect("Repos Sem. IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos Sem. PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début de période", datetime(2026, 5, 1))
    d_end = st.date_input("Fin de période", datetime(2026, 6, 30))

# --- FONCTIONS LOGIQUES ---
def get_theoretical_status(date):
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_pair if wn % 2 == 0 else off_impair
    return "ZZ" if day_name in off_list else "TRA"

# --- CALCUL DES CZ (AUTOMATIQUE) ---
def compute_cz():
    cz_days = set()
    # On analyse du début à la fin de la période sélectionnée, semaine par semaine
    curr_w = d_start - timedelta(days=d_start.weekday())
    while curr_w <= d_end:
        wn = curr_w.isocalendar()[1]
        off_list_theo = off_pair if wn % 2 == 0 else off_impair
        
        if len(off_list_theo) >= 3:
            week_dates = [curr_w + timedelta(days=i) for i in range(7)]
            # On vérifie l'état actuel (manuel ou théo)
            states = [st.session_state.cal_map.get(dt, get_theoretical_status(dt)) for dt in week_dates]
            
            if "CX" in states and "C4" not in states:
                # Appliquer CZ sur le premier ZZ ou FC de la semaine
                for dt in week_dates:
                    if st.session_state.cal_map.get(dt, get_theoretical_status(dt)) in ["ZZ", "FC"]:
                        cz_days.add(dt)
                        break
        curr_w += timedelta(days=7)
    return cz_days

cz_active_days = compute_cz()

# --- AFFICHAGE DU CALENDRIER ---
st.title("📅 Planning Interactif Vincent")

# Générer la liste des mois à afficher
months = []
curr = d_start.replace(day=1)
while curr <= d_end:
    months.append((curr.year, curr.month))
    if curr.month == 12: curr = curr.replace(year=curr.year+1, month=1)
    else: curr = curr.replace(month=curr.month+1)

for year, month in months:
    with st.container():
        st.markdown(f'### {calendar.month_name[month]} {year}')
        
        # En-tête des jours
        hcols = st.columns(7)
        for i, jn in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]):
            hcols[i].markdown(f"**{jn}**")

        cal = calendar.Calendar(firstweekday=0)
        for week in cal.monthdatescalendar(year, month):
            cols = st.columns(7)
            for i, d in enumerate(week):
                if d.month != month:
                    cols[i].write("")
                    continue
                
                # Déterminer le statut
                is_cz = d in cz_active_days
                current_status = st.session_state.cal_map.get(d, get_theoretical_status(d))
                
                # Couleur de fond
                bg = {"ZZ": "bg-zz", "FC": "bg-fc", "CX": "bg-cx", "C4": "bg-c4", "TRA": ""}.get(current_status, "")
                if is_cz: bg = "bg-cz"

                with cols[i]:
                    st.markdown(f'<div class="day-card {bg}">', unsafe_allow_html=True)
                    st.markdown(f'<div class="date-num">{d.day}</div>', unsafe_allow_html=True)
                    
                    # Sélecteur Outlook-style
                    options = ["TRA", "ZZ", "CX", "C4", "FC"]
                    # On évite de proposer CZ car il est automatique
                    try:
                        idx = options.index(current_status)
                    except:
                        idx = 0
                        
                    new_status = st.selectbox("", options, index=idx, key=f"sel-{d}", label_visibility="collapsed")
                    
                    if new_status != current_status:
                        st.session_state.cal_map[d] = new_status
                        st.rerun()
                    
                    if is_cz:
                        st.markdown('<div style="color:#dc3545; font-size:0.7rem; font-weight:bold;">⚠️ AUTO-CZ</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

# --- RÉCAPITULATIF FIXE EN BAS ---
st.divider()
cx_total = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX" and d_start <= d <= d_end)
c4_total = sum(1 for d, v in st.session_state.cal_map.items() if v == "C4" and d_start <= d <= d_end)
cz_total = sum(1 for d in cz_active_days if d_start <= d <= d_end)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Congés CX", cx_total)
c2.metric("Congés C4 (Protections)", c4_total)
c3.metric("Jours CZ (Perdus)", cz_total)
c4.metric("Total décompté (CX+CZ)", cx_total + cz_total)

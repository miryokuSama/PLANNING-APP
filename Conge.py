import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V23 - Manuel", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .month-title { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; margin-top: 20px; text-align: center; font-size: 1.2rem; }
    .day-card { min-height: 110px; border: 1px solid #dcdde1; border-radius: 8px; padding: 5px; background-color: white; transition: 0.3s; }
    .date-num { font-weight: 800; font-size: 1.1rem; color: #2c3e50; }
    .label-tag { font-size: 0.7rem; text-align: center; margin-top: 5px; border-radius: 4px; color: white; padding: 2px; font-weight: bold; }
    .bg-zz { background-color: #2ecc71; } 
    .bg-fc { background-color: #f1c40f; color: black !important; } 
    .bg-cx { background-color: #3498db; border: 2px solid #2980b9; } 
    .bg-c4 { background-color: #9b59b6; border: 2px solid #8e44ad; } 
    .bg-cz { background-color: #e74c3c; border: 2px solid #c0392b; }
    .stButton>button { border: none; background: transparent; padding: 0; width: 100%; height: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION DE L'ÉTAT ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}  # Stockage des modifs manuelles {date: type}

# --- CONFIGURATION ---
st.title("🛡️ Optimiseur Manuel V23")

with st.sidebar:
    st.header("⚙️ Paramètres Cycle")
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    off_impair = st.multiselect("Repos Semaines IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos Semaines PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])
    
    if st.button("🔄 Réinitialiser tout"):
        st.session_state.cal_map = {}
        st.rerun()

# --- FONCTIONS LOGIQUES ---
def get_theoretical_status(date):
    f = {(1,1):"An",(1,5):"1er Mai",(8,5):"8 Mai",(14,5):"Asc.",(25,5):"Pent.",(14,7):"F.Nat.",(15,8):"Assompt.",(1,11):"Touss.",(11,11):"Arm.",(25,12):"Noël"}
    wn = date.isocalendar()[1]
    day_name = jours_semaine[date.weekday()]
    off_list = off_pair if wn % 2 == 0 else off_impair
    if f.get((date.day, date.month)): return "FC"
    if day_name in off_list: return "ZZ"
    return "TRA"

def toggle_day(d):
    # Déterminer l'état actuel pour savoir vers quoi basculer
    current = st.session_state.cal_map.get(d, get_theoretical_status(d))
    order = ["TRA", "CX", "C4", "ZZ", "FC"]
    next_status = order[(order.index(current) + 1) % len(order)]
    st.session_state.cal_map[d] = next_status

# --- CALCUL DES RÈGLES (CZ AUTO) ---
# On calcule les CZ dynamiquement en fonction de ce qui est dans cal_map
cz_days = set()
all_dates = list(st.session_state.cal_map.keys())
if all_dates:
    start_sim = min(all_dates) - timedelta(days=7)
    end_sim = max(all_dates) + timedelta(days=7)
    
    curr_w = start_sim - timedelta(days=start_sim.weekday())
    while curr_w <= end_sim:
        wn = curr_w.isocalendar()[1]
        # On regarde le cycle théorique pour savoir si c'est une semaine à 3 repos
        off_list_theo = off_pair if wn % 2 == 0 else off_impair
        
        if len(off_list_theo) >= 3:
            week_dates = [curr_w + timedelta(days=i) for i in range(7)]
            has_cx = any(st.session_state.cal_map.get(dt, get_theoretical_status(dt)) == "CX" for dt in week_dates)
            has_c4 = any(st.session_state.cal_map.get(dt, get_theoretical_status(dt)) == "C4" for dt in week_dates)
            
            if has_cx and not has_c4:
                # On marque le premier ZZ (théorique ou manuel) comme CZ
                for dt in week_dates:
                    if st.session_state.cal_map.get(dt, get_theoretical_status(dt)) in ["ZZ", "FC"]:
                        cz_days.add(dt)
                        break
        curr_w += timedelta(days=7)

# --- AFFICHAGE DU CALENDRIER (MAI 2026 par défaut pour l'exemple) ---
col_m1, col_m2 = st.columns(2)

def draw_month(container, year, month):
    container.markdown(f'<div class="month-title">{calendar.month_name[month]} {year}</div>', unsafe_allow_html=True)
    cal = calendar.Calendar(firstweekday=0) # Semaine commence lundi
    days = list(cal.itermonthdates(year, month))
    
    cols = container.columns(7)
    for idx, name in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]):
        cols[idx].caption(name)

    for i in range(len(days)//7):
        cols = container.columns(7)
        for j in range(7):
            d = days[i*7+j]
            if d.month != month:
                cols[j].write("")
                continue
            
            status = st.session_state.cal_map.get(d, get_theoretical_status(d))
            if d in cz_days: status = "CZ" # Priorité visuelle au CZ auto
            
            bg = {"ZZ": "bg-zz", "FC": "bg-fc", "CX": "bg-cx", "C4": "bg-c4", "CZ": "bg-cz", "TRA": ""}.get(status, "")
            
            with cols[j]:
                st.markdown(f'<div class="day-card {bg}">', unsafe_allow_html=True)
                if st.button(f"{d.day}", key=f"btn-{d}"):
                    toggle_day(d)
                    st.rerun()
                st.markdown(f'<div class="label-tag">{status}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

with col_m1: draw_month(st, 2026, 4)
with col_m2: draw_month(st, 2026, 5)

# --- RÉCAPITULATIF ---
st.divider()
cx_count = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
c4_count = sum(1 for v in st.session_state.cal_map.values() if v == "C4")
cz_count = len(cz_days)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Compteur CX", cx_count)
c2.metric("Compteur C4", c4_count)
c3.metric("Compteur CZ (Auto)", cz_count)
c4.metric("Total Décompté", cx_count + cz_count)

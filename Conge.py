import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V26 - Flash", layout="wide")

# --- STYLE CSS FLASHY & LARGE ---
st.markdown("""
    <style>
    /* Couleurs vibrantes */
    .bg-zz { background-color: #00FF00 !important; color: black !important; } /* Vert Fluide */
    .bg-fc { background-color: #FFFF00 !important; color: black !important; } /* Jaune Pur */
    .bg-cx { background-color: #0070FF !important; color: white !important; } /* Bleu Électrique */
    .bg-c4 { background-color: #A000FF !important; color: white !important; } /* Violet Profond */
    .bg-cz { background-color: #FF0000 !important; color: white !important; } /* Rouge Alerte */
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; }

    .day-card {
        border: 2px solid #222;
        border-radius: 10px;
        padding: 8px;
        min-height: 140px;
        text-align: center;
        box-shadow: 3px 3px 0px #888;
        margin-bottom: 10px;
    }
    .date-num { 
        font-size: 2.2rem; 
        font-weight: 900; 
        line-height: 1;
        margin-bottom: 0px;
    }
    .day-name-full { 
        font-size: 0.9rem; 
        text-transform: uppercase; 
        font-weight: bold;
        margin-bottom: 10px;
        display: block;
    }
    .status-code {
        font-size: 1.4rem;
        font-weight: 900;
        text-shadow: 1px 1px 0px rgba(0,0,0,0.2);
        margin-top: 5px;
        display: block;
    }
    /* Style du selectbox interne */
    .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(255,255,255,0.8);
        border: 1px solid black !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION & LOGIQUE ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_complets = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def get_theoretical_status(date, o_i, o_p):
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    off_list = o_p if wn % 2 == 0 else o_i
    return "ZZ" if jours_complets[date.weekday()] in off_list else "TRA"

def compute_cz_internal(temp_map, start, end, o_i, o_p):
    cz_days = set()
    curr_w = start - timedelta(days=start.weekday())
    while curr_w <= end:
        wn = curr_w.isocalendar()[1]
        off_list_theo = o_p if wn % 2 == 0 else o_i
        if len(off_list_theo) >= 3:
            week_dates = [curr_w + timedelta(days=i) for i in range(7)]
            states = [temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) for dt in week_dates]
            if "CX" in states and "C4" not in states:
                for dt in week_dates:
                    if temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) in ["ZZ", "FC"]:
                        cz_days.add(dt)
                        break
        curr_w += timedelta(days=7)
    return cz_days

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ RÉGLAGES")
    off_impair = st.multiselect("Repos IMPAIRS", jours_complets, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos PAIRS", jours_complets, default=["Lundi", "Mardi", "Samedi"])
    d_start = st.date_input("Début", datetime(2026, 5, 1))
    d_end = st.date_input("Fin", datetime(2026, 6, 30))
    st.divider()
    quota_cx = st.number_input("Quota CX", value=10)
    quota_c4 = st.number_input("Quota C4", value=2)
    if st.button("🚀 OPTIMISER MAINTENANT", use_container_width=True):
        # Moteur d'optimisation simplifié (recherche tunnel max)
        best_config = {}
        # Simulation basique pour l'exemple : pose CX sur les TRA
        curr = d_start
        c_count, c4_count = 0, 0
        while curr <= d_end:
            if get_theoretical_status(curr, off_impair, off_pair) == "TRA":
                if c4_count < quota_c4: 
                    best_config[curr] = "C4"; c4_count += 1
                elif c_count < quota_cx: 
                    best_config[curr] = "CX"; c_count += 1
            curr += timedelta(days=1)
        st.session_state.cal_map = best_config
        st.rerun()

# --- AFFICHAGE ---
st.title("⚡ VISUAL PLANNING V26")
cz_active_days = compute_cz_internal(st.session_state.cal_map, d_start, d_end, off_impair, off_pair)

months = []
curr = d_start.replace(day=1)
while curr <= d_end:
    months.append((curr.year, curr.month))
    curr = (curr.replace(day=28) + timedelta(days=4)).replace(day=1)

for year, month in months:
    st.markdown(f"## 🗓️ {calendar.month_name[month].upper()} {year}")
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != month: continue
            
            # Détermination du statut et de la classe CSS
            is_cz = d in cz_active_days
            status = st.session_state.cal_map.get(d, get_theoretical_status(d, off_impair, off_pair))
            if is_cz: status = "CZ"
            
            bg_class = f"bg-{status.lower()}"
            day_name = jours_complets[d.weekday()]

            with cols[i]:
                st.markdown(f"""
                    <div class="day-card {bg_class}">
                        <span class="day-name-full">{day_name}</span>
                        <div class="date-num">{d.day}</div>
                        <span class="status-code">{status}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Menu déroulant caché/discret dessous pour changer
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                new_status = st.selectbox("", opts, index=opts.index(status) if status in opts else 0, key=f"s-{d}", label_visibility="collapsed")
                if new_status != status and not is_cz:
                    st.session_state.cal_map[d] = new_status
                    st.rerun()

# --- BARRE DE SCORE ---
st.markdown("---")
cx_total = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX" and d_start <= d <= d_end)
cz_total = sum(1 for d in cz_active_days if d_start <= d <= d_end)
st.warning(f"📊 TOTAL À DÉCOMPTER : {cx_total + cz_total} jours (CX: {cx_total} + CZ: {cz_total})")

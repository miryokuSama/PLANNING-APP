import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V27 - Expert", layout="wide")

# --- STYLE CSS FLASHY (Contraste Maximum) ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-card { 
        border-radius: 10px; 
        padding: 8px; 
        min-height: 150px; 
        text-align: center; 
        box-shadow: 4px 4px 0px #222; 
        margin-bottom: 10px; 
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .date-num { font-size: 2.8rem; font-weight: 900; line-height: 1; }
    .day-name-full { font-size: 0.8rem; text-transform: uppercase; font-weight: bold; margin-bottom: 5px; }
    .status-code { font-size: 1.6rem; font-weight: 900; display: block; margin-top: 5px; }
    
    .metric-box { 
        background: #222; 
        color: #00FF00; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        border: 2px solid #00FF00; 
    }
    .metric-box h1 { font-size: 3.5rem; margin: 0; padding: 0; color: inherit; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION DE LA MÉMOIRE ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_complets = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# --- LOGIQUE MÉTIER ---
def get_theoretical_status(date, o_i, o_p):
    # Liste simplifiée des jours fériés
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    off_list = o_p if wn % 2 == 0 else o_i
    return "ZZ" if jours_complets[date.weekday()] in off_list else "TRA"

def compute_cz_internal(temp_map, start, end, o_i, o_p):
    cz_days = set()
    # On analyse par semaine complète autour de la période
    curr_w = start - timedelta(days=start.weekday())
    while curr_w <= end + timedelta(days=7):
        wn = curr_w.isocalendar()[1]
        off_list_theo = o_p if wn % 2 == 0 else o_i
        if len(off_list_theo) >= 3:
            week_dates = [curr_w + timedelta(days=i) for i in range(7)]
            # On vérifie les états réels dans la semaine
            states = [temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) for dt in week_dates]
            # RÈGLE : Si CX présent ET pas de C4 protecteur
            if "CX" in states and "C4" not in states:
                for dt in week_dates:
                    if temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) in ["ZZ", "FC"]:
                        cz_days.add(dt)
                        break
        curr_w += timedelta(days=7)
    return cz_days

# --- BARRE LATÉRALE (CONTRÔLES) ---
with st.sidebar:
    st.title("⚙️ CONFIGURATION")
    off_impair = st.multiselect("Repos IMPAIRS", jours_complets, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos PAIRS", jours_complets, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début période", datetime(2026, 5, 1))
    d_end = st.date_input("Fin période", datetime(2026, 5, 31))
    
    st.divider()
    st.subheader("🛠️ ACTIONS")
    quota_cx = st.number_input("Quota CX disponible", value=10, min_value=0)
    quota_c4 = st.number_input("Quota C4 disponible", value=2, min_value=0)
    
    if st.button("🚀 OPTIMISATION INTELLIGENTE", use_container_width=True):
        new_map = {}
        curr, c_count, c4_count = d_start, 0, 0
        while curr <= d_end:
            if get_theoretical_status(curr, off_impair, off_pair) == "TRA":
                if c4_count < quota_c4: 
                    new_map[curr] = "C4"
                    c4_count += 1
                elif c_count < quota_cx: 
                    new_map[curr] = "CX"
                    c_count += 1
            curr += timedelta(days=1)
        st.session_state.cal_map = new_map
        st.rerun()

    if st.button("📅 POSE CLASSIQUE (BLOC)", use_container_width=True):
        new_map = {}
        curr = d_start
        while curr <= d_end:
            # En bloc, on pose sur tous les jours (TRA et ZZ)
            new_map[curr] = "CX"
            curr += timedelta(days=1)
        st.session_state.cal_map = new_map
        st.rerun()

    if st.button("🗑️ RÉINITIALISER", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- CALCUL DES COMPTEURS ---
cz_active_days = compute_cz_internal(st.session_state.cal_map, d_start, d_end, off_impair, off_pair)
cx_posés = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX" and d_start <= d <= d_end)
cz_générés = len([d for d in cz_active_days if d_start <= d <= d_end])
total_décompté = cx_posés + cz_générés

# Calcul gain
absence_totale = (d_end - d_start).days + 1
gain = absence_totale - total_décompté

# --- AFFICHAGE PRINCIPAL ---
st.title("⚡ VISUAL PLANNING V27")

c1, c2, c3 = st.columns(3)
with c1: 
    st.markdown(f'<div class="metric-box"><h1>{total_décompté}</h1>DÉCOMPTÉ (CX+CZ)</div>', unsafe_allow_html=True)
with c2: 
    # Correction de l'apostrophe avec l'antislash \'
    st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{absence_totale}</h1>JOURS D\'ABSENCE</div>', unsafe_allow_html=True)
with c3: 
    st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{gain}</h1>JOURS GAGNÉS</div>', unsafe_allow_html=True)

st.divider()

# Identification des mois à afficher
dates_periode = [d_start + timedelta(days=i) for i in range((d_end - d_start).days + 1)]
mois_a_afficher = sorted(list(set([(d.year, d.month) for d in dates_periode])))

for year, month in mois_a_afficher:
    st.markdown(f"## 🗓️ {calendar.month_name[month].upper()} {year}")
    
    # En-tête des jours
    cols_h = st.columns(7)
    for idx, j_nom in enumerate(jours_complets):
        cols_h[idx].markdown(f"**{j_nom}**")
    
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != month:
                continue
            
            # Statut final
            is_cz = d in cz_active_days
            status = st.session_state.cal_map.get(d, get_theoretical_status(d, off_impair, off_pair))
            if is_cz: status = "CZ"
            
            bg_class = f"bg-{status.lower()}"
            
            with cols[i]:
                st.markdown(f"""
                    <div class="day-card {bg_class}">
                        <div class="day-name-full">{jours_complets[d.weekday()]}</div>
                        <div class="date-num">{d.day}</div>
                        <div class="status-code">{status}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Menu de modification (Selectbox)
                # On ne permet pas de modifier manuellement un CZ car il est auto-généré par la règle
                if not is_cz:
                    opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                    idx_opt = opts.index(status) if status in opts else 0
                    new_val = st.selectbox("", opts, index=idx_opt, key=f"sel-{d}", label_visibility="collapsed")
                    if new_val != status:
                        st.session_state.cal_map[d] = new_val
                        st.rerun()
                else:
                    st.write("") # Espace pour garder l'alignement

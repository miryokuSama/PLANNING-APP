import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V33 - Réparé", layout="wide")

# --- 1. STYLE CSS (FLASHY & PROPRE) ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-card { 
        border-radius: 10px; padding: 10px; min-height: 140px; text-align: center; 
        box-shadow: 4px 4px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: center;
    }
    .date-num { font-size: 2.5rem; font-weight: 900; line-height: 1; }
    .status-code { font-size: 1.4rem; font-weight: 900; margin-top: 5px; }
    .metric-box { background: #222; color: #00FF00; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #00FF00; }
    .metric-box h1 { font-size: 3rem; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE DE BASE ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_complets = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def get_theo(date, o_i, o_p):
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    return "ZZ" if jours_complets[date.weekday()] in (o_p if wn % 2 == 0 else o_i) else "TRA"

def get_cz_days(current_map, start_view, end_view, o_i, o_p):
    """Calcule quels jours deviennent des CZ en fonction des CX posés"""
    cz_list = set()
    curr = start_view - timedelta(days=start_view.weekday()) # Début de semaine
    while curr <= end_view:
        week = [curr + timedelta(days=i) for i in range(7)]
        # On récupère le statut de chaque jour de la semaine
        week_states = [current_map.get(d, get_theo(d, o_i, o_p)) for d in week]
        
        # RÈGLE : Si CX présent et pas de C4
        if "CX" in week_states and "C4" not in week_states:
            # On cherche le premier repos (ZZ ou FC) pour poser le CZ
            for d in week:
                if current_map.get(d, get_theo(d, o_i, o_p)) in ["ZZ", "FC"]:
                    cz_list.add(d)
                    break
        curr += timedelta(days=7)
    return cz_list

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ RÉGLAGES")
    o_i = st.multiselect("Repos IMPAIRS", jours_complets, default=["Lundi", "Samedi"])
    o_p = st.multiselect("Repos PAIRS", jours_complets, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début période", datetime(2026, 5, 1))
    d_end = st.date_input("Fin période", datetime(2026, 5, 31))
    
    st.divider()
    quota_limit = st.number_input("Quota Max (CX+CZ)", value=17)
    c4_limit = st.number_input("Nb de C4", value=2)

    if st.button("🚀 OPTIMISER SOUS QUOTA", use_container_width=True):
        st.session_state.cal_map = {}
        curr_opt, used_c4 = d_start, 0
        while curr_opt <= d_end:
            # Calcul du coût actuel
            temp_cz = get_cz_days(st.session_state.cal_map, d_start, d_end, o_i, o_p)
            current_cost = sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(temp_cz)
            
            if current_cost >= quota_limit: break # STOP si quota atteint
            
            if get_theo(curr_opt, o_i, o_p) == "TRA":
                if used_c4 < c4_limit:
                    st.session_state.cal_map[curr_opt] = "C4"
                    used_c4 += 1
                else:
                    st.session_state.cal_map[curr_opt] = "CX"
                    # Vérification immédiate si le CZ généré ne nous fait pas dépasser
                    new_cz = get_cz_days(st.session_state.cal_map, d_start, d_end, o_i, o_p)
                    if (sum(1 for v in st.session_state.cal_map.values() if v == "CX") + len(new_cz)) > quota_limit:
                        del st.session_state.cal_map[curr_opt]
                        break
            curr_opt += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ RESET", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- 4. CALCULS FINAUX ---
# Définition de la vue (2 mois minimum)
mois_list = sorted(list(set([(d_start.year, d_start.month), (d_end.year, d_end.month)])))
if len(mois_list) < 2:
    m, y = (d_start.month + 1, d_start.year) if d_start.month < 12 else (1, d_start.year + 1)
    mois_list.append((y, m))

view_start = datetime(mois_list[0][0], mois_list[0][1], 1).date()
view_end = datetime(mois_list[-1][0], mois_list[-1][1], 28).date() + timedelta(days=10)

cz_actives = get_cz_days(st.session_state.cal_map, view_start, view_end, o_i, o_p)
total_cx = sum(1 for v in st.session_state.cal_map.values() if v == "CX")
total_decompté = total_cx + len(cz_actives)

# --- 5. AFFICHAGE ---
st.title("🛡️ VINCENT OPTI - V33")

c1, c2, c3 = st.columns(3)
with c1: 
    color = "#FF0000" if total_decompté > quota_limit else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h1>{total_decompté}/{quota_limit}</h1>DÉCOMPTÉ (CX+CZ)</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{(d_end-d_start).days+1}</h1>DURÉE ABSENCE</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{((d_end-d_start).days+1)-total_decompté}</h1>GAIN RÉEL</div>', unsafe_allow_html=True)

for yr, mo in mois_list:
    st.markdown(f"## 🗓️ {calendar.month_name[mo].upper()} {yr}")
    col_h = st.columns(7)
    for idx, n in enumerate(jours_complets): col_h[idx].caption(n)
    
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(yr, mo):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            # État actuel
            stored_val = st.session_state.cal_map.get(d, get_theo(d, o_i, o_p))
            is_cz = d in cz_actives
            current_status = "CZ" if is_cz else stored_val
            
            with cols[i]:
                # Affichage de la case
                st.markdown(f"""
                    <div class="day-card bg-{current_status.lower()}">
                        <div class="date-num">{d.day}</div>
                        <div class="status-code">{current_status}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # SÉLECTEUR AVEC CLÉ UNIQUE (Date ISO)
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                # On s'assure que stored_val est dans opts
                if stored_val not in opts: stored_val = "TRA"
                
                new_choice = st.selectbox(
                    "Changer", 
                    opts, 
                    index=opts.index(stored_val), 
                    key=f"btn_{d.isoformat()}", 
                    label_visibility="collapsed"
                )
                
                if new_choice != stored_val:
                    st.session_state.cal_map[d] = new_choice
                    st.rerun()

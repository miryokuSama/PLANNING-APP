import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V31 - Contrôle Total", layout="wide")

# --- 1. STYLE CSS (FLASH & INTERACTIF) ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-card { 
        border-radius: 10px; padding: 10px; min-height: 160px; text-align: center; 
        box-shadow: 4px 4px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .date-num { font-size: 2.8rem; font-weight: 900; line-height: 1; }
    .day-name-full { font-size: 0.85rem; text-transform: uppercase; font-weight: bold; }
    .status-code { font-size: 1.6rem; font-weight: 900; }
    
    .metric-box { 
        background: #222; color: #00FF00; padding: 15px; border-radius: 10px; 
        text-align: center; border: 2px solid #00FF00; 
    }
    .metric-box h1 { font-size: 3.5rem; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_complets = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def get_theoretical_status(date, o_i, o_p):
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    off_list = o_p if wn % 2 == 0 else o_i
    return "ZZ" if jours_complets[date.weekday()] in off_list else "TRA"

def compute_cz_internal(temp_map, start_date, end_date, o_i, o_p):
    """Calcule les CZ sur une plage de dates donnée"""
    cz_days = set()
    curr_w = start_date - timedelta(days=start_date.weekday())
    while curr_w <= end_date:
        wn = curr_w.isocalendar()[1]
        off_list_theo = o_p if wn % 2 == 0 else o_i
        if len(off_list_theo) >= 3:
            week_dates = [curr_w + timedelta(days=i) for i in range(7)]
            states = [temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) for dt in week_dates]
            # Si un CX est présent et AUCUN C4 ne protège la semaine
            if "CX" in states and "C4" not in states:
                for dt in week_dates:
                    # Le CZ se place sur le premier repos (ZZ ou FC) trouvé
                    if temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) in ["ZZ", "FC"]:
                        cz_days.add(dt)
                        break
        curr_w += timedelta(days=7)
    return cz_days

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ CONFIGURATION")
    off_impair = st.multiselect("Repos IMPAIRS", jours_complets, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos PAIRS", jours_complets, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début de période", datetime(2026, 5, 1))
    d_end = st.date_input("Fin de période", datetime(2026, 5, 15))
    
    st.divider()
    quota_max = st.number_input("Quota Total (CX + CZ)", value=17)
    quota_c4 = st.number_input("Quota C4", value=2)
    
    if st.button("🚀 OPTIMISATION", use_container_width=True):
        new_map = {}
        curr, c4_c = d_start, 0
        while curr <= d_end:
            # Simulation quota
            cz_sim = compute_cz_internal(new_map, d_start, d_end, off_impair, off_pair)
            if (sum(1 for v in new_map.values() if v=="CX") + len(cz_sim)) >= quota_max: break
            
            if get_theoretical_status(curr, off_impair, off_pair) == "TRA":
                if c4_c < quota_c4: new_map[curr] = "C4"; c4_c += 1
                else:
                    new_map[curr] = "CX"
                    if (sum(1 for v in new_map.values() if v=="CX") + len(compute_cz_internal(new_map, d_start, d_end, off_impair, off_pair))) > quota_max:
                        del new_map[curr]; break
            curr += timedelta(days=1)
        st.session_state.cal_map = new_map
        st.rerun()

    if st.button("🗑️ VIDER TOUT", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- 4. DETERMINATION DES MOIS A AFFICHER (MINIMUM 2) ---
mois_selectionnes = set([(d_start.year, d_start.month), (d_end.year, d_end.month)])
if len(mois_selectionnes) < 2:
    m = d_start.month + 1 if d_start.month < 12 else 1
    y = d_start.year if d_start.month < 12 else d_start.year + 1
    mois_selectionnes.add((y, m))

mois_a_afficher = sorted(list(mois_selectionnes))

# --- 5. CALCUL DES CZ SUR TOUTE LA ZONE VISIBLE ---
# On définit les bornes d'affichage pour que les CZ soient calculés partout
first_day_view = datetime(mois_a_afficher[0][0], mois_a_afficher[0][1], 1).date()
last_day_view = datetime(mois_a_afficher[-1][0], mois_a_afficher[-1][1], 28).date() + timedelta(days=7)

cz_active_days = compute_cz_internal(st.session_state.cal_map, first_day_view, last_day_view, off_impair, off_pair)

# --- 6. CALCUL DES COMPTEURS ---
cx_posés = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX")
cz_count = len([d for d in cz_active_days if d in st.session_state.cal_map or get_theoretical_status(d, off_impair, off_pair) != "TRA"])
# Note: On ne compte les CZ que s'ils sont dans la plage globale ou impactés par une pose
total_deb = cx_posés + len(cz_active_days)

# --- 7. AFFICHAGE ---
st.title("🛡️ VINCENT OPTI - V31")

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="metric-box"><h1>{total_deb}/{quota_max}</h1>DÉCOMPTÉ</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{(d_end-d_start).days+1}</h1>ABSENCE PRÉVUE</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{((d_end-d_start).days+1) - total_deb}</h1>GAIN</div>', unsafe_allow_html=True)

for year, month in mois_a_afficher:
    st.markdown(f"## 🗓️ {calendar.month_name[month].upper()} {year}")
    cols_header = st.columns(7)
    for idx, name in enumerate(jours_complets): cols_header[idx].caption(name)
    
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != month: continue
            
            # Statuts
            mapped_status = st.session_state.cal_map.get(d, get_theoretical_status(d, off_impair, off_pair))
            is_cz = d in cz_active_days
            display_status = "CZ" if is_cz else mapped_status
            
            with cols[i]:
                # La carte affiche la couleur du CZ si nécessaire
                st.markdown(f"""
                    <div class="day-card bg-{display_status.lower()}">
                        <div class="day-name-full">{jours_complets[d.weekday()]}</div>
                        <div class="date-num">{d.day}</div>
                        <div class="status-code">{display_status}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Le selectbox montre TOUJOURS la valeur réelle (modifiable)
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                # On s'assure que l'index est correct
                current_idx = opts.index(mapped_status) if mapped_status in opts else 0
                
                new_val = st.selectbox("", opts, index=current_idx, key=f"sel-{d}", label_visibility="collapsed")
                
                if new_val != mapped_status:
                    st.session_state.cal_map[d] = new_val
                    st.rerun()

import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V29.2 - Multi-Mois", layout="wide")

# --- 1. STYLE CSS COMPLET (FLASH & CONTRASTE) ---
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
    .quota-alert { background: #FF0000; color: white; padding: 15px; border-radius: 10px; font-weight: bold; text-align: center; font-size: 1.5rem; margin: 10px 0; border: 3px solid black; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALISATION ET LOGIQUE ---
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
    # On balaie un peu plus large pour ne rien rater
    while curr_w <= end + timedelta(days=7):
        wn = curr_w.isocalendar()[1]
        off_list_theo = o_p if wn % 2 == 0 else o_i
        if len(off_list_theo) >= 3:
            week_dates = [curr_w + timedelta(days=i) for i in range(7)]
            states = [temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) for dt in week_dates]
            if "CX" in states and "C4" not in states:
                for dt in week_dates:
                    if temp_map.get(dt, get_theoretical_status(dt, o_i, o_p)) in ["ZZ", "FC"]:
                        cz_days.add(dt); break
        curr_w += timedelta(days=7)
    return cz_days

# --- 3. BARRE LATÉRALE ---
with st.sidebar:
    st.title("⚙️ CONFIGURATION")
    off_impair = st.multiselect("Repos IMPAIRS", jours_complets, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos PAIRS", jours_complets, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début de période", datetime(2026, 5, 1))
    d_end = st.date_input("Fin de période", datetime(2026, 5, 15)) # Exemple courte durée
    
    st.divider()
    st.subheader("📊 QUOTAS")
    quota_max = st.number_input("Quota Total (CX + CZ)", value=17, min_value=1)
    quota_c4 = st.number_input("Quota C4 disponible", value=2, min_value=0)
    
    st.divider()
    if st.button("🚀 OPTIMISATION INTELLIGENTE", use_container_width=True):
        new_map = {}
        curr, c4_count = d_start, 0
        while curr <= d_end:
            temp_cz = compute_cz_internal(new_map, d_start, d_end, off_impair, off_pair)
            cx_actuels = sum(1 for v in new_map.values() if v == "CX")
            if (cx_actuels + len(temp_cz)) >= quota_max: break
            
            if get_theoretical_status(curr, off_impair, off_pair) == "TRA":
                if c4_count < quota_c4: 
                    new_map[curr] = "C4"; c4_count += 1
                else:
                    new_map[curr] = "CX"
                    cz_after = compute_cz_internal(new_map, d_start, d_end, off_impair, off_pair)
                    if (sum(1 for v in new_map.values() if v == "CX") + len(cz_after)) > quota_max:
                        del new_map[curr]
                        break
            curr += timedelta(days=1)
        st.session_state.cal_map = new_map
        st.rerun()

    if st.button("📅 POSE CLASSIQUE (BLOC)", use_container_width=True):
        new_map = {}
        curr = d_start
        while curr <= d_end:
            new_map[curr] = "CX"
            cz_check = compute_cz_internal(new_map, d_start, d_end, off_impair, off_pair)
            if (sum(1 for v in new_map.values() if v == "CX") + len(cz_check)) > quota_max:
                del new_map[curr]
                break
            curr += timedelta(days=1)
        st.session_state.cal_map = new_map
        st.rerun()

    if st.button("🗑️ RÉINITIALISER", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- 4. CALCULS ET COMPTEURS ---
cz_active_days = compute_cz_internal(st.session_state.cal_map, d_start, d_end, off_impair, off_pair)
cx_posés = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX" and d_start <= d <= d_end)
cz_count = len([d for d in cz_active_days if d_start <= d <= d_end])
conges_consommes = cx_posés + cz_count
absence_totale = (d_end - d_start).days + 1
gain = absence_totale - conges_consommes

# --- 5. AFFICHAGE DES MÉTRIQUES ---
st.title("🛡️ OPTIMISEUR VINCENT V29.2")

c1, c2, c3 = st.columns(3)
with c1: 
    color = "#FF0000" if conges_consommes > quota_max else "#00FF00"
    st.markdown(f'<div class="metric-box" style="border-color:{color}; color:{color};"><h1>{conges_consommes}/{quota_max}</h1>DÉCOMPTÉ (CX+CZ)</div>', unsafe_allow_html=True)
with c2: 
    st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{absence_totale}</h1>JOURS D\'ABSENCE</div>', unsafe_allow_html=True)
with c3: 
    st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{gain}</h1>JOURS GAGNÉS</div>', unsafe_allow_html=True)

if conges_consommes > quota_max:
    st.markdown(f'<div class="quota-alert">⚠️ QUOTA DÉPASSÉ !</div>', unsafe_allow_html=True)

st.divider()

# --- 6. LOGIQUE D'AFFICHAGE MULTI-MOIS (MINIMUM 2) ---
# On calcule les mois de la période
mois_selectionnes = set([(d_start.year, d_start.month)])
dates_p = [d_start + timedelta(days=i) for i in range((d_end - d_start).days + 1)]
for d in dates_p:
    mois_selectionnes.add((d.year, d.month))

# On force l'ajout du mois suivant le dernier mois sélectionné s'il n'y en a qu'un
if len(mois_selectionnes) < 2:
    dernier_mois = max(mois_selectionnes)
    # Calcul du mois suivant
    if dernier_mois[1] == 12:
        mois_selectionnes.add((dernier_mois[0] + 1, 1))
    else:
        mois_selectionnes.add((dernier_mois[0], dernier_mois[1] + 1))

mois_a_afficher = sorted(list(mois_selectionnes))

# --- 7. GRILLE CALENDRIER ---
for year, month in mois_a_afficher:
    st.markdown(f"## 🗓️ {calendar.month_name[month].upper()} {year}")
    cols_h = st.columns(7)
    for idx, j_nom in enumerate(jours_complets):
        cols_h[idx].caption(j_nom)
    
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != month: continue
            
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
                
                if not is_cz:
                    opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                    idx_opt = opts.index(status) if status in opts else 0
                    new_val = st.selectbox("", opts, index=idx_opt, key=f"sel-{d}", label_visibility="collapsed")
                    if new_val != status:
                        st.session_state.cal_map[d] = new_val
                        st.rerun()
                else:
                    st.write("")

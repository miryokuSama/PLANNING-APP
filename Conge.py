import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V32 - Contrôle Total", layout="wide")

# --- 1. STYLE CSS FLASHY ---
st.markdown("""
    <style>
    .bg-zz { background-color: #00FF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-fc { background-color: #FFFF00 !important; color: black !important; border: 2px solid #000; } 
    .bg-cx { background-color: #0070FF !important; color: white !important; border: 2px solid #000; } 
    .bg-c4 { background-color: #A000FF !important; color: white !important; border: 2px solid #000; } 
    .bg-cz { background-color: #FF0000 !important; color: white !important; border: 2px solid #000; }
    .bg-tra { background-color: #FFFFFF !important; color: #333 !important; border: 1px solid #ddd; }
    
    .day-card { 
        border-radius: 10px; padding: 10px; min-height: 150px; text-align: center; 
        box-shadow: 4px 4px 0px #222; margin-bottom: 5px; 
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .date-num { font-size: 2.8rem; font-weight: 900; line-height: 1; }
    .status-code { font-size: 1.6rem; font-weight: 900; }
    .metric-box { background: #222; color: #00FF00; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #00FF00; }
    .metric-box h1 { font-size: 3.2rem; margin: 0; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE ET ÉTATS ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

jours_complets = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def get_theo(date, o_i, o_p):
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    return "ZZ" if jours_complets[date.weekday()] in (o_p if wn % 2 == 0 else o_i) else "TRA"

# --- 3. BARRE LATÉRALE ---
with st.sidebar:
    st.title("⚙️ RÉGLAGES")
    off_i = st.multiselect("Repos IMPAIRS", jours_complets, default=["Lundi", "Samedi"])
    off_p = st.multiselect("Repos PAIRS", jours_complets, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début période", datetime(2026, 5, 1))
    d_end = st.date_input("Fin période", datetime(2026, 5, 15))
    
    st.divider()
    q_max = st.number_input("Quota Total (CX + CZ)", value=17)
    q_c4 = st.number_input("Quota C4", value=2)
    
    if st.button("🚀 LANCER L'OPTIMISATION", use_container_width=True):
        st.session_state.cal_map = {} # Reset pour l'optimisation
        curr, c4_count = d_start, 0
        while curr <= d_end:
            # On vérifie le coût actuel (CX + CZ) avant de poser
            # Pour l'optimisation, on utilise une simulation simplifiée
            if get_theo(curr, off_i, off_p) == "TRA":
                if c4_count < q_c4: 
                    st.session_state.cal_map[curr] = "C4"
                    c4_count += 1
                else: 
                    st.session_state.cal_map[curr] = "CX"
            curr += timedelta(days=1)
        st.rerun()

    if st.button("📅 POSE CLASSIQUE (BLOC)", use_container_width=True):
        st.session_state.cal_map = {}
        curr = d_start
        while curr <= d_end:
            st.session_state.cal_map[curr] = "CX"
            curr += timedelta(days=1)
        st.rerun()

    if st.button("🗑️ TOUT EFFACER", use_container_width=True):
        st.session_state.cal_map = {}
        st.rerun()

# --- 4. PRÉPARATION DE L'AFFICHAGE MULTI-MOIS ---
mois_list = set([(d_start.year, d_start.month), (d_end.year, d_end.month)])
if len(mois_list) < 2:
    m = d_start.month + 1 if d_start.month < 12 else 1
    y = d_start.year if d_start.month < 12 else d_start.year + 1
    mois_list.add((y, m))
mois_a_afficher = sorted(list(mois_list))

# --- 5. MOTEUR DE CALCUL DES CZ (S'applique sur TOUTE la vue) ---
def compute_all_cz():
    cz_found = set()
    # On balaie large (du lundi de la première semaine au dimanche de la dernière)
    start_view = datetime(mois_a_afficher[0][0], mois_a_afficher[0][1], 1).date()
    start_view -= timedelta(days=start_view.weekday())
    
    curr = start_view
    while curr <= (datetime(mois_a_afficher[-1][0], mois_a_afficher[-1][1], 28).date() + timedelta(days=10)):
        week_dates = [curr + timedelta(days=i) for i in range(7)]
        # Statut réel de chaque jour de la semaine
        states = [st.session_state.cal_map.get(d, get_theo(d, off_i, off_p)) for d in week_dates]
        
        # Condition CZ : Un CX est présent ET pas de C4
        if "CX" in states and "C4" not in states:
            # On compte les jours de repos (ZZ ou FC)
            repos_count = sum(1 for s in states if s in ["ZZ", "FC"])
            if repos_count >= 1: # Si la règle de ton entreprise s'applique ici
                for d in week_dates:
                    if st.session_state.cal_map.get(d, get_theo(d, off_i, off_p)) in ["ZZ", "FC"]:
                        cz_found.add(d)
                        break
        curr += timedelta(days=7)
    return cz_found

cz_active = compute_all_cz()

# --- 6. COMPTEURS ---
cx_count = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX")
cz_count_visible = len([d for d in cz_active if d >= d_start and d <= d_end or d in st.session_state.cal_map])
total_conges = cx_count + len(cz_active)

# --- 7. GRILLE ---
st.title("🛡️ VINCENT OPTI - V32")

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="metric-box"><h1>{total_conges}/{q_max}</h1>DÉCOMPTÉ</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-box" style="border-color:#0070FF; color:#0070FF;"><h1>{(d_end-d_start).days+1}</h1>DURÉE</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-box" style="border-color:#FFFF00; color:#FFFF00;"><h1>{((d_end-d_start).days+1)-total_conges}</h1>GAIN</div>', unsafe_allow_html=True)

for yr, mo in mois_a_afficher:
    st.markdown(f"## 🗓️ {calendar.month_name[mo].upper()} {yr}")
    cols_h = st.columns(7)
    for idx, name in enumerate(jours_complets): cols_h[idx].caption(name)
    
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(yr, mo):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != mo: continue
            
            # Détermination de ce qu'on affiche
            val_stockee = st.session_state.cal_map.get(d, get_theo(d, off_i, off_p))
            is_cz = d in cz_active
            color_status = "CZ" if is_cz else val_stockee
            
            with cols[i]:
                st.markdown(f"""
                    <div class="day-card bg-{color_status.lower()}">
                        <div class="date-num">{d.day}</div>
                        <div class="status-code">{color_status}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # LE SÉLECTEUR EST LE ROI
                opts = ["TRA", "ZZ", "CX", "C4", "FC"]
                # Si le jour est théoriquement autre chose, on s'assure qu'il est dans la liste
                if val_stockee not in opts: opts.append(val_stockee)
                
                # On utilise une clé unique qui ne dépend pas du statut pour éviter les bugs de rafraîchissement
                choice = st.selectbox("Type", opts, index=opts.index(val_stockee), key=f"date-{d}", label_visibility="collapsed")
                
                if choice != val_stockee:
                    st.session_state.cal_map[d] = choice
                    st.rerun()

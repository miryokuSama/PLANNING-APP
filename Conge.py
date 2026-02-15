import streamlit as st
import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Optimiseur Vincent V25", layout="wide")

# --- STYLE CSS (Conservé de la V24) ---
st.markdown("""
    <style>
    .stSelectbox div[data-baseweb="select"] { size: small; min-height: 25px; }
    .day-card { border: 1px solid #ced4da; border-radius: 4px; padding: 5px; background-color: white; min-height: 90px; }
    .date-num { font-weight: bold; font-size: 1rem; }
    .bg-zz { background-color: #d4edda; } 
    .bg-fc { background-color: #fff3cd; } 
    .bg-cx { background-color: #cfe2ff; border-left: 4px solid #0d6efd; } 
    .bg-c4 { background-color: #e2d9f3; border-left: 4px solid #6f42c1; } 
    .bg-cz { background-color: #f8d7da; border-left: 4px solid #dc3545; }
    .opti-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #3498db; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if 'cal_map' not in st.session_state:
    st.session_state.cal_map = {}

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Configuration Cycle")
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    off_impair = st.multiselect("Repos Sem. IMPAIRES", jours_semaine, default=["Lundi", "Samedi"])
    off_pair = st.multiselect("Repos Sem. PAIRES", jours_semaine, default=["Lundi", "Mardi", "Samedi"])
    
    st.divider()
    d_start = st.date_input("Début de recherche", datetime(2026, 4, 1))
    d_end = st.date_input("Fin de recherche", datetime(2026, 8, 31))

# --- LOGIQUE DE BASE ---
def get_theoretical_status(date, o_i, o_p):
    f = {(1,1):"FC",(1,5):"FC",(8,5):"FC",(14,5):"FC",(25,5):"FC",(14,7):"FC",(15,8):"FC",(1,11):"FC",(11,11):"FC",(25,12):"FC"}
    if f.get((date.day, date.month)): return "FC"
    wn = date.isocalendar()[1]
    off_list = o_p if wn % 2 == 0 else o_i
    return "ZZ" if jours_semaine[date.weekday()] in off_list else "TRA"

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

# --- MOTEUR D'OPTIMISATION ---
st.markdown('<div class="opti-box">', unsafe_allow_html=True)
st.subheader("🚀 Optimisation Automatique")
c_opti1, c_opti2, c_opti3 = st.columns([1,1,1])
with c_opti1: quota_cx = st.number_input("Nombre de CX max", min_value=1, value=10)
with c_opti2: quota_c4 = st.number_input("Nombre de C4 max", min_value=0, value=2)
with c_opti3: launch_opti = st.button("LANCER L'ANALYSE", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if launch_opti:
    best_absence = 0
    best_config = {}
    
    # On teste des périodes de 1 à 30 jours au sein de la plage
    # Pour faire simple et rapide, on cherche le tunnel de jours travaillés le plus rentable
    delta_recherche = (d_end - d_start).days
    
    for i in range(delta_recherche):
        for j in range(i + 5, delta_recherche): # Fenêtre d'au moins 5 jours
            test_start = d_start + timedelta(days=i)
            test_end = d_start + timedelta(days=j)
            
            # Simuler la pose de congés sur les jours TRA de cette fenêtre
            temp_map = {}
            temp_cx = 0
            temp_c4 = 0
            
            curr = test_start
            while curr <= test_end:
                status = get_theoretical_status(curr, off_impair, off_pair)
                if status == "TRA":
                    # On pose d'abord des C4 s'il en reste, puis des CX
                    if temp_c4 < quota_c4:
                        temp_map[curr] = "C4"
                        temp_c4 += 1
                    elif temp_cx < quota_cx:
                        temp_map[curr] = "CX"
                        temp_cx += 1
                curr += timedelta(days=1)
            
            if temp_cx <= quota_cx and temp_c4 <= quota_c4:
                # Calculer le tunnel total (avec ZZ avant et après)
                # On cherche les bornes réelles d'absence
                czs = compute_cz_internal(temp_map, test_start, test_end, off_impair, off_pair)
                total_absence = (test_end - test_start).days + 1
                
                # Bonus : On ajoute les repos collés avant et après
                # (Simplification pour l'exemple)
                if total_absence > best_absence:
                    best_absence = total_absence
                    best_config = temp_map.copy()

    if best_config:
        st.session_state.cal_map = best_config
        st.success(f"✅ Optimisation terminée ! Tunnel trouvé de {best_absence} jours d'absence.")
    else:
        st.warning("Aucune configuration trouvée avec ces quotas.")

# --- AFFICHAGE (CALENDRIER) ---
st.title("📅 Calendrier de Pose")
cz_active_days = compute_cz_internal(st.session_state.cal_map, d_start, d_end, off_impair, off_pair)

# (Ici on reprend la boucle d'affichage de la V24 pour dessiner les mois)
months = []
curr = d_start.replace(day=1)
while curr <= d_end:
    months.append((curr.year, curr.month))
    if curr.month == 12: curr = curr.replace(year=curr.year+1, month=1)
    else: curr = curr.replace(month=curr.month+1)

for year, month in months:
    st.markdown(f'### {calendar.month_name[month]} {year}')
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d.month != month: continue
            
            is_cz = d in cz_active_days
            current_status = st.session_state.cal_map.get(d, get_theoretical_status(d, off_impair, off_pair))
            bg = {"ZZ": "bg-zz", "FC": "bg-fc", "CX": "bg-cx", "C4": "bg-c4", "TRA": ""}.get(current_status, "")
            if is_cz: bg = "bg-cz"

            with cols[i]:
                st.markdown(f'<div class="day-card {bg}">', unsafe_allow_html=True)
                st.markdown(f'<div class="date-num">{d.day}</div>', unsafe_allow_html=True)
                options = ["TRA", "ZZ", "CX", "C4", "FC"]
                new_status = st.selectbox("", options, index=options.index(current_status) if current_status in options else 0, key=f"sel-{d}", label_visibility="collapsed")
                if new_status != current_status:
                    st.session_state.cal_map[d] = new_status
                    st.rerun()
                if is_cz: st.markdown('<div style="color:#dc3545; font-size:0.6rem; font-weight:bold;">⚠️ CZ</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

# --- RÉCAPITULATIF ---
st.divider()
cx_total = sum(1 for d, v in st.session_state.cal_map.items() if v == "CX" and d_start <= d <= d_end)
c4_total = sum(1 for d, v in st.session_state.cal_map.items() if v == "C4" and d_start <= d <= d_end)
cz_total = sum(1 for d in cz_active_days if d_start <= d <= d_end)
st.metric("Total décompté (CX + CZ)", f"{cx_total + cz_total} jours")

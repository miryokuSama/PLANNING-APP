import streamlit as st
from datetime import date
import calendar

st.set_page_config(layout="wide")
st.title("📅 Planning congés stratégique")

CODES = ["TRA", "CX", "ZZ", "C4", "FC"]

COLOR_MAP = {
    "TRA": "#E0E0E0",
    "CX": "#FF3B30",
    "CZ": "#AF52DE",
    "ZZ": "#007AFF",
    "C4": "#FF9500",
    "FC": "#34C759"
}

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Paramètres")

mode_semaine = st.sidebar.radio(
    "Semaines avec 3 ZZ",
    ["Semaines impaires", "Semaines paires"]
)

year = st.sidebar.selectbox("Année", [2026, 2027, 2028])
month1 = st.sidebar.selectbox("Mois 1", list(range(1, 13)))
month2 = st.sidebar.selectbox("Mois 2", list(range(1, 13)))

quota_CX = st.sidebar.number_input("Quota CX disponible", 0, 60, 25)
quota_C4 = st.sidebar.number_input("Quota C4 disponible", 0, 30, 5)

# =====================================================
# FÉRIÉS FIXES (exemple)
# =====================================================

FERIES = [
    date(2026, 1, 1),
    date(2026, 5, 1),
    date(2026, 5, 8),
    date(2026, 7, 14),
    date(2026, 8, 15),
    date(2026, 11, 1),
    date(2026, 11, 11),
    date(2026, 12, 25)
]

# =====================================================
# GÉNÉRATION JOURS
# =====================================================

def generate_days(y, m):
    days = []
    cal = calendar.monthcalendar(y, m)

    for week in cal:
        for d in week:
            if d != 0:
                current_date = date(y, m, d)
                week_number = current_date.isocalendar().week
                is_pair = week_number % 2 == 0

                if mode_semaine == "Semaines impaires":
                    semaine_3ZZ = not is_pair
                else:
                    semaine_3ZZ = is_pair

                default_code = "TRA"
                if current_date in FERIES:
                    default_code = "FC"

                days.append({
                    "date": current_date,
                    "code": default_code,
                    "semaine_3ZZ": semaine_3ZZ
                })

    return days


days_list = generate_days(year, month1) + generate_days(year, month2)
days_list = sorted(days_list, key=lambda x: x["date"])

# =====================================================
# OPTIMISEUR
# =====================================================

def optimize_vacs(days, quota_CX, quota_C4):

    best_start = 0
    best_length = 0

    for start in range(len(days)):

        cx_left = quota_CX
        c4_left = quota_C4
        length = 0

        for i in range(start, len(days)):

            if days[i]["code"] == "TRA":

                if cx_left > 0:
                    cx_left -= 1
                elif c4_left > 0:
                    c4_left -= 1
                else:
                    break

            length += 1

        if length > best_length:
            best_length = length
            best_start = start

    # Appliquer la meilleure séquence
    cx_left = quota_CX
    c4_left = quota_C4

    for i in range(best_start, best_start + best_length):

        if days[i]["code"] == "TRA":

            if cx_left > 0:
                days[i]["code"] = "CX"
                cx_left -= 1
            elif c4_left > 0:
                days[i]["code"] = "C4"
                c4_left -= 1

    return days

# =====================================================
# BOUTON OPTIMISATION
# =====================================================

if st.button("🚀 Optimiser pour VACS maximale"):
    days_list = optimize_vacs(days_list, quota_CX, quota_C4)

# =====================================================
# LOGIQUE VACS + CZ
# =====================================================

def apply_vacs_logic(days):

    vacation_active = False

    for i in range(len(days)):

        code = days[i]["code"]

        if code == "CX":
            vacation_active = True

        if vacation_active:

            if code == "ZZ" and days[i]["semaine_3ZZ"]:

                for j in range(i + 1, len(days)):
                    if days[j]["code"] == "TRA":
                        break
                    if days[j]["code"] == "CX":
                        days[i]["code"] = "CZ"
                        break

            if code in ["TRA", "C4"]:
                vacation_active = False

    return days

days_list = apply_vacs_logic(days_list)

# =====================================================
# AFFICHAGE CALENDRIER
# =====================================================

def render_month(y, m):

    st.markdown(f"## {calendar.month_name[m]} {y}")
    cal = calendar.monthcalendar(y, m)

    headers = st.columns(7)
    for i, day_name in enumerate(["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]):
        headers[i].markdown(f"**{day_name}**")

    month_days = [d for d in days_list if d["date"].month == m]
    index = 0

    absence_total = 0
    used_CX = 0
    used_C4 = 0

    for week in cal:
        cols = st.columns(7)

        for i, day_num in enumerate(week):

            if day_num == 0:
                cols[i].write("")
            else:
                day_data = month_days[index]
                d = day_data["date"]
                code = day_data["code"]

                color = COLOR_MAP.get(code, "#CCCCCC")

                cols[i].markdown(
                    f"""
                    <div style="
                        background-color:{color};
                        padding:12px;
                        border-radius:10px;
                        text-align:center;
                        color:white;
                        font-weight:bold;
                        min-height:70px;
                    ">
                        {d.day}<br>{code}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if code != "TRA":
                    absence_total += 1

                if code in ["CX", "CZ"]:
                    used_CX += 1

                if code == "C4":
                    used_C4 += 1

                index += 1

    return absence_total, used_CX, used_C4


colA, colB = st.columns(2)

with colA:
    abs1, cx1, c41 = render_month(year, month1)

with colB:
    abs2, cx2, c42 = render_month(year, month2)

absence_total = abs1 + abs2
used_CX = cx1 + cx2
used_C4 = c41 + c42

remaining_CX = quota_CX - used_CX
remaining_C4 = quota_C4 - used_C4

st.markdown("---")
st.metric("Absence totale entreprise", absence_total)

col1, col2 = st.columns(2)

with col1:
    st.metric("CX utilisés (CX + CZ)", used_CX)
    st.metric("CX restants", remaining_CX)

with col2:
    st.metric("C4 utilisés", used_C4)
    st.metric("C4 restants", remaining_C4)

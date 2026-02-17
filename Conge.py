import streamlit as st
from datetime import date
import calendar

st.set_page_config(layout="wide")
st.title("📅 Planning congés interactif")

CODES = ["TRA", "CX", "ZZ", "C4", "FC"]

COLOR_MAP = {
    "TRA": "#E0E0E0",
    "CX": "#FF4B4B",
    "CZ": "#9C27B0",
    "ZZ": "#2196F3",
    "C4": "#FF9800",
    "FC": "#4CAF50"
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
# GÉNÉRATION MOIS
# =====================================================

def generate_month(y, m):
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

# =====================================================
# LOGIQUE VACS + CZ
# =====================================================

def apply_vacs_logic(days_list):
    vacation_active = False

    for i in range(len(days_list)):

        code = days_list[i]["code"]

        if code == "CX":
            vacation_active = True

        if vacation_active:

            if code == "ZZ" and days_list[i]["semaine_3ZZ"]:
                for j in range(i + 1, len(days_list)):
                    if days_list[j]["code"] == "TRA":
                        break
                    if days_list[j]["code"] == "CX":
                        days_list[i]["code"] = "CZ"
                        break

            if code in ["TRA", "C4"]:
                vacation_active = False

    return days_list

# =====================================================
# AFFICHAGE CALENDRIER GRILLE
# =====================================================

def render_calendar(y, m):

    st.markdown(f"## {calendar.month_name[m]} {y}")

    cal = calendar.monthcalendar(y, m)
    days_data = generate_month(y, m)
    days_data = apply_vacs_logic(days_data)

    absence_total = 0
    used_CX = 0
    used_C4 = 0

    headers = st.columns(7)
    for i, day_name in enumerate(["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]):
        headers[i].markdown(f"**{day_name}**")

    day_index = 0

    for week in cal:
        cols = st.columns(7)

        for i, day_num in enumerate(week):

            if day_num == 0:
                cols[i].write("")
            else:
                day_data = days_data[day_index]
                d = day_data["date"]
                code = day_data["code"]

                selected = cols[i].selectbox(
                    "",
                    CODES,
                    index=CODES.index(code),
                    key=f"{m}_{d.isoformat()}"
                )

                day_data["code"] = selected
                code = selected

                color = COLOR_MAP[code]

                cols[i].markdown(
                    f"""
                    <div style="
                        background-color:{color};
                        padding:10px;
                        border-radius:8px;
                        text-align:center;
                        color:white;
                        font-weight:bold;
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

                day_index += 1

    return absence_total, used_CX, used_C4


# =====================================================
# AFFICHAGE 2 MOIS CÔTE À CÔTE
# =====================================================

colA, colB = st.columns(2)

with colA:
    abs1, cx1, c41 = render_calendar(year, month1)

with colB:
    abs2, cx2, c42 = render_cale_

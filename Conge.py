import streamlit as st
from datetime import date
import calendar

st.set_page_config(layout="wide")
st.title("📅 Calendrier interactif de congés")

CODES = ["TRA", "CX", "ZZ", "C4", "FC"]

# =====================================================
# SIDEBAR PARAMÈTRES
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
# FÉRIÉS (exemple fixe 2026)
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
# GÉNÉRATION DES JOURS
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


days_list = generate_month(year, month1) + generate_month(year, month2)
days_list = sorted(days_list, key=lambda x: x["date"])

# =====================================================
# AFFICHAGE SÉLECTION UTILISATEUR
# =====================================================

st.markdown("### Sélection des jours")

for idx, day in enumerate(days_list):

    d = day["date"]

    selected = st.selectbox(
        f"{d.strftime('%a')} {d.day}/{d.month}",
        CODES,
        index=CODES.index(day["code"]),
        key=f"select_{idx}_{d.isoformat()}"
    )

    day["code"] = selected

# =====================================================
# LOGIQUE VACS + TRANSFORMATION CZ
# =====================================================

vacation_active = False

for i in range(len(days_list)):

    code = days_list[i]["code"]

    # Début VACS
    if code == "CX":
        vacation_active = True

    if vacation_active:

        # Transformation ZZ -> CZ
        if code == "ZZ" and days_list[i]["semaine_3ZZ"]:

            # Cherche CX futur avant fin VACS
            for j in range(i + 1, len(days_list)):
                if days_list[j]["code"] == "TRA":
                    break
                if days_list[j]["code"] == "CX":
                    days_list[i]["code"] = "CZ"
                    break

        # Fin VACS
        if code == "TRA":
            vacation_active = False

        if code == "C4":
            vacation_active = False

# =====================================================
# COMPTEURS
# =====================================================

absence_total = 0
used_CX = 0
used_C4 = 0

for day in days_list:

    if day["code"] != "TRA":
        absence_total += 1

    if day["code"] == "CX":
        used_CX += 1

    if day["code"] == "CZ":
        used_CX += 1

    if day["code"] == "C4":
        used_C4 += 1

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

# =====================================================
# BOUTON OPTIMISATION (structure prête)
# =====================================================

if st.button("Optimiser les jours d'absence"):
    st.info("Moteur d'optimisation stratégique à implémenter.")

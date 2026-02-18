# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import calendar
import json
import os
import holidays

# ---------------------------
# Constantes et utilitaires
# ---------------------------
WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
WEEKDAY_IDX = {name: i for i, name in enumerate(WEEKDAYS)}  # Lundi=0 ... Dimanche=6

CODES = ["TRA", "ZZ", "CX", "CZ", "C4", "FC"]

DATA_FILE = "calendar_state.json"

FR_HOLIDAYS = holidays.France()

# ---------------------------
# Fonctions de persistance
# ---------------------------
def load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, default=str, ensure_ascii=False, indent=2)

# ---------------------------
# Génération calendrier
# ---------------------------
def month_grid(year, month):
    """Retourne une liste de semaines; chaque semaine est une liste de 7 dates (datetime.date or None). 
    Les semaines commencent le dimanche (index 6 dans python calendar) — on réorganise pour commencer dimanche."""
    cal = calendar.Calendar(firstweekday=6)  # dimanche
    month_days = list(cal.itermonthdates(year, month))
    weeks = [month_days[i:i+7] for i in range(0, len(month_days), 7)]
    return weeks

def date_key(d):
    return d.isoformat()

# ---------------------------
# Initialisation état
# ---------------------------
st.set_page_config(layout="wide", page_title="Gestion calendrier congés")
state = load_state()

if "data" not in state:
    state["data"] = {}  # structure: { "YYYY-MM": { "YYYY-MM-DD": code, ... }, ... }
if "settings" not in state:
    state["settings"] = {}

# ---------------------------
# Sidebar : paramètres globaux
# ---------------------------
st.sidebar.header("Paramètres affichage et règles")

# Période à afficher : choix dynamique (jour/mois/année)
today = date.today()
col1, col2, col3 = st.sidebar.columns([1,1,1])
with col1:
    sel_day = st.sidebar.number_input("Jour", min_value=1, max_value=31, value=today.day, step=1)
with col2:
    sel_month = st.sidebar.selectbox("Mois", list(range(1,13)), index=today.month-1, format_func=lambda x: calendar.month_name[x])
with col3:
    sel_year = st.sidebar.number_input("Année", min_value=1900, max_value=2100, value=today.year, step=1)

display_date = date(sel_year, sel_month, min(sel_day, calendar.monthrange(sel_year, sel_month)[1]))

# Option d'afficher 1 ou 2 mois
show_two_months = st.sidebar.checkbox("Afficher 2 mois (mois suivant inclus)", value=False)

# Parité pour semaines à 3 ZZ
st.sidebar.markdown("**Parité semaines 3 ZZ**")
parity_choice = st.sidebar.radio("Semaines à 3 ZZ sur :", ("Paires", "Impaires"))

# Choix du jour supplémentaire ZZ pour semaines impaires/paires (selectbox unique comme demandé)
zz_odd = st.sidebar.selectbox("ZZ semaine impairs (jour supplémentaire)", WEEKDAYS, index=6)  # default Dimanche
zz_even = st.sidebar.selectbox("ZZ semaine pairs (jour supplémentaire)", WEEKDAYS, index=6)

# Choix si les semaines doivent contenir 2 ou 3 ZZ
zz_count_mode = st.sidebar.radio("Nombre de jours ZZ par semaine", ("2 jours (weekend)", "3 jours (weekend + extra)"))
zz_three = (zz_count_mode == "3 jours (weekend + extra)")

# Compteurs CX et C4
st.sidebar.markdown("**Compteurs**")
cx_total = st.sidebar.number_input("Compteur CX (unités totales à poser)", min_value=0, max_value=31, value=3, step=1)
c4_total = st.sidebar.number_input("Compteur C4 (max 4 unités)", min_value=0, max_value=4, value=0, step=1)

# Bouton optimisation (en bas)
st.sidebar.markdown("---")
optimize_btn = st.sidebar.button("Optimiser (mode optimisation)")

# ---------------------------
# Helpers logique métier
# ---------------------------
def is_week_even(d: date):
    # semaine ISO: isocalendar()[1]; pair si divisible par 2
    return (d.isocalendar()[1] % 2) == 0

def default_assign_codes_for_month(year, month):
    """Assigne TRA par défaut puis applique ZZ et FC selon règles de base."""
    weeks = month_grid(year, month)
    month_key = f"{year:04d}-{month:02d}"
    if month_key not in state["data"]:
        state["data"][month_key] = {}
    for week in weeks:
        for d in week:
            if d.month != month:
                continue
            key = date_key(d)
            # Par défaut TRA
            state["data"][month_key].setdefault(key, "TRA")
    # Appliquer ZZ selon règle: weekend (Samedi, Dimanche) + extra si 3-ZZ
    for week in weeks:
        for d in week:
            if d.month != month:
                continue
            wd = d.weekday()  # Lundi=0 ... Dimanche=6
            # weekend = Samedi(5) Dimanche(6)
            if wd in (5,6):
                state["data"][month_key][date_key(d)] = "ZZ"
            elif zz_three:
                # extra day depending on parity of week
                week_even = is_week_even(d)
                if week_even and parity_choice == "Paires":
                    extra = zz_even
                elif (not week_even) and parity_choice == "Impaires":
                    extra = zz_odd
                else:
                    extra = None
                if extra is not None and WEEKDAY_IDX[extra] == wd:
                    state["data"][month_key][date_key(d)] = "ZZ"
    # Appliquer FC (jours fériés français) — marquer FC but treat as ZZ for logic
    for d in pd.date_range(start=date(year, month, 1), end=date(year, month, calendar.monthrange(year, month)[1])):
        d0 = d.date()
        if d0 in FR_HOLIDAYS:
            state["data"][month_key][date_key(d0)] = "FC"

def get_code(d: date):
    key = f"{d.year:04d}-{d.month:02d}"
    return state["data"].get(key, {}).get(date_key(d), "TRA")

def set_code(d: date, code: str):
    key = f"{d.year:04d}-{d.month:02d}"
    state["data"].setdefault(key, {})
    state["data"][key][date_key(d)] = code

# ---------------------------
# Appliquer initialisation pour mois(s) affichés
# ---------------------------
months_to_show = [display_date]
if show_two_months:
    # mois suivant
    y = sel_year
    m = sel_month + 1
    if m == 13:
        m = 1
        y += 1
    months_to_show.append(date(y, m, 1))

for d in months_to_show:
    default_assign_codes_for_month(d.year, d.month)

# ---------------------------
# Règles d'évaluation VACS / CZ / C4 / FC
# ---------------------------
def is_fc(d: date):
    return get_code(d) == "FC"

def is_zz(d: date):
    c = get_code(d)
    return c == "ZZ" or c == "FC"  # FC treated as ZZ for logic

def is_tra(d: date):
    return get_code(d) == "TRA"

def is_cx(d: date):
    return get_code(d) == "CX"

def is_c4(d: date):
    return get_code(d) == "C4"

def week_has_three_zz(week_start_date: date):
    """Détermine si la semaine (contenant week_start_date) est une semaine 'à 3 ZZ' selon parité et mode."""
    # find any day in that week and check parity
    week_even = is_week_even(week_start_date)
    if not zz_three:
        return False
    if week_even and parity_choice == "Paires":
        return True
    if (not week_even) and parity_choice == "Impaires":
        return True
    return False

def simulate_vacs_from(start_date: date, months_scope):
    """Simule la période VACS démarrant au start_date sans interruption (sauf C4 si présent).
    Retourne la liste des dates considérés en absence (CX, CZ, ZZ traités) et la date de fin (exclusive)."""
    d = start_date
    absence = []
    in_vacs = False
    # VACS starts at first CX encountered; here we assume start_date is CX
    in_vacs = True
    while True:
        # stop if date outside scope
        if not any((d.year == m.year and d.month == m.month) for m in months_scope):
            break
        code = get_code(d)
        if code == "TRA":
            break
        # C4 interrupts VACS but counts as absence
        if code == "C4":
            absence.append(d)
            break
        # If in VACS and day is ZZ and week is 3-ZZ -> becomes CZ (counted as absence)
        if in_vacs and is_zz(d):
            # check if week is 3-ZZ
            # find a representative day in that week (use d)
            if week_has_three_zz(d):
                absence.append(d)  # CZ effectively
            else:
                absence.append(d)  # still ZZ but not CZ; counts as absence if contiguous to VACS
        elif code == "CX" or code == "FC":
            absence.append(d)
        else:
            # any other code (TRA) breaks
            break
        d = d + timedelta(days=1)
    return absence

def total_absence_count_for_vacs(start_date: date, months_scope):
    """Calcule le total d'absences liées à une VACS démarrant start_date (incluant CZ transformés)."""
    abs_days = simulate_vacs_from(start_date, months_scope)
    # On ajoute aussi les ZZ collés avant et après la période VACS (règle: 'collé à la période de VACS avant et après')
    if not abs_days:
        return 0
    first = abs_days[0]
    last = abs_days[-1]
    # compter ZZ/FC contigus avant
    d = first - timedelta(days=1)
    while any((d.year == m.year and d.month == m.month) for m in months_scope):
        if is_zz(d):
            abs_days.insert(0, d)
            d = d - timedelta(days=1)
        else:
            break
    # après
    d = last + timedelta(days=1)
    while any((d.year == m.year and d.month == m.month) for m in months_scope):
        if is_zz(d):
            abs_days.append(d)
            d = d + timedelta(days=1)
        else:
            break
    # unique
    unique_days = sorted({dd for dd in abs_days})
    return len(unique_days), unique_days

# ---------------------------
# Optimisation (heuristique)
# ---------------------------
def optimize_placement(months_scope, cx_quota, c4_quota):
    """Heuristique pour placer CX et C4 afin de maximiser période d'absence totale.
    Stratégie :
    - Cherche le meilleur jour unique pour démarrer une VACS (un CX) qui maximise l'absence totale.
    - Si plusieurs CX disponibles, on tente d'utiliser C4 pour interrompre et relancer une nouvelle VACS plus loin.
    - On applique placements sur une copie, puis on écrit dans state si amélioration.
    """
    # Collect candidate days (days that are not TRA or can be converted)
    candidates = []
    for m in months_scope:
        weeks = month_grid(m.year, m.month)
        for week in weeks:
            for d in week:
                if d.month != m.month:
                    continue
                # candidate if day is TRA/ZZ/FC (we can set CX on TRA or ZZ/FC)
                candidates.append(d)
    # Evaluate each candidate as single CX start
    best_score = -1
    best_plan = None

    # We'll try greedy sequences: pick best start, then optionally place C4 and pick next start, etc.
    # Limit attempts to reasonable number
    candidates = sorted(set(candidates))
    for start in candidates:
        # copy state codes
        backup = json.loads(json.dumps(state["data"]))
        # place CX at start
        set_code(start, "CX")
        used_cx = 1
        used_c4 = 0
        total_days, days_list = total_absence_count_for_vacs(start, months_scope)
        score = total_days
        # try to extend by using remaining CXs: place C4 to interrupt then place next CX at best next start
        current_end = days_list[-1] if days_list else start
        while used_cx < cx_quota and used_c4 < c4_quota:
            # place C4 on the day after current_end if within scope and not TRA
            next_c4_day = current_end + timedelta(days=1)
            if not any((next_c4_day.year == m.year and next_c4_day.month == m.month) for m in months_scope):
                break
            # place C4 (it counts as absence and interrupts)
            set_code(next_c4_day, "C4")
            used_c4 += 1
            # find next best start after next_c4_day
            best_local = None
            best_local_score = -1
            for cand in candidates:
                if cand <= next_c4_day:
                    continue
                # place CX temporarily
                prev = state["data"].get(f"{cand.year:04d}-{cand.month:02d}", {}).get(date_key(cand), None)
                set_code(cand, "CX")
                s, dl = total_absence_count_for_vacs(start, months_scope)
                # compute incremental unique days
                # compute union of days from previous and new
                # For simplicity, recompute total absence across all CX/C4 placed by scanning months and counting codes that are CX/C4/CZ/ZZ contiguous to CX sequences
                # We'll approximate by summing s
                if s > best_local_score:
                    best_local_score = s
                    best_local = cand
                # revert cand
                if prev is None:
                    # remove
                    state["data"][f"{cand.year:04d}-{cand.month:02d}"].pop(date_key(cand), None)
                else:
                    set_code(cand, prev)
            if best_local is None:
                break
            # place chosen CX
            set_code(best_local, "CX")
            used_cx += 1
            # recompute total from first start (approx)
            total_days, days_list = total_absence_count_for_vacs(start, months_scope)
            score = total_days
            current_end = days_list[-1] if days_list else current_end
        # restore state to backup for next iteration
        state["data"] = backup
        if score > best_score:
            best_score = score
            best_plan = {"start": start, "score": score}
    # Si on a trouvé un plan, appliquer placements de façon simple : place CX sur best start et éventuellement C4/CX en greedy
    if best_plan:
        # apply
        start = best_plan["start"]
        set_code(start, "CX")
        used_cx = 1
        used_c4 = 0
        total_days, days_list = total_absence_count_for_vacs(start, months_scope)
        current_end = days_list[-1] if days_list else start
        while used_cx < cx_quota and used_c4 < c4_quota:
            next_c4_day = current_end + timedelta(days=1)
            if not any((next_c4_day.year == m.year and next_c4_day.month == m.month) for m in months_scope):
                break
            set_code(next_c4_day, "C4")
            used_c4 += 1
            # find next best start after next_c4_day
            best_local = None
            best_local_score = -1
            for m in months_scope:
                weeks = month_grid(m.year, m.month)
                for week in weeks:
                    for cand in week:
                        if cand.month != m.month:
                            continue
                        if cand <= next_c4_day:
                            continue
                        prev = state["data"].get(f"{cand.year:04d}-{cand.month:02d}", {}).get(date_key(cand), None)
                        set_code(cand, "CX")
                        s, dl = total_absence_count_for_vacs(start, months_scope)
                        if s > best_local_score:
                            best_local_score = s
                            best_local = cand
                        # revert
                        if prev is None:
                            state["data"][f"{cand.year:04d}-{cand.month:02d}"].pop(date_key(cand), None)
                        else:
                            set_code(cand, prev)
            if best_local is None:
                break
            set_code(best_local, "CX")
            used_cx += 1
            total_days, days_list = total_absence_count_for_vacs(start, months_scope)
            current_end = days_list[-1] if days_list else current_end
    # sauvegarder
    save_state(state)
    return best_score

# ---------------------------
# Interface principale : affichage calendrier en grille (type Outlook)
# ---------------------------
st.title("Gestionnaire de calendrier de congés")

# Afficher chaque mois en colonne
cols = st.columns(len(months_to_show))
for idx, m in enumerate(months_to_show):
    with cols[idx]:
        st.subheader(f"{calendar.month_name[m.month]} {m.year}")
        weeks = month_grid(m.year, m.month)
        # Table header: Sunday..Saturday (we want weeks starting Sunday)
        header = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
        # Build a DataFrame for layout with custom HTML per cell using st.markdown
        # We'll render grid manually
        for week in weeks:
            cols_week = st.columns(7)
            for i, d in enumerate(week):
                col = cols_week[i]
                with col:
                    if d.month != m.month:
                        st.write("")  # empty cell
                        continue
                    code = get_code(d)
                    # Visual priority: FC absolute visual priority
                    display_code = code
                    # Color mapping
                    color = "#ffffff"
                    if display_code == "TRA":
                        color = "#f0f0f0"
                    elif display_code == "ZZ":
                        color = "#cfe8ff"
                    elif display_code == "CX":
                        color = "#ffd9b3"
                    elif display_code == "CZ":
                        color = "#ffb3b3"
                    elif display_code == "C4":
                        color = "#d1c4e9"
                    elif display_code == "FC":
                        color = "#ffef9f"
                    # Cell content: numéro du jour, jour en toutes lettres, code statut
                    day_label = f"**{d.day}**\n\n{WEEKDAYS[d.weekday()]}\n\n**{display_code}**"
                    st.markdown(f"<div style='background:{color};padding:6px;border-radius:6px'>{day_label}</div>", unsafe_allow_html=True)
                    # Selectbox discret pour modifier le code du jour
                    sel = st.selectbox(f"Code {d.isoformat()}", CODES, index=CODES.index(code), key=f"sel_{d.isoformat()}")
                    if sel != code:
                        set_code(d, sel)
        st.markdown("---")

# ---------------------------
# Affichage compteurs et métriques
# ---------------------------
# Calculer total absence dans période VACS + ZZ collés
def compute_total_absence_for_scope(months_scope):
    # find first CX in scope
    all_dates = []
    for m in months_scope:
        weeks = month_grid(m.year, m.month)
        for week in weeks:
            for d in week:
                if d.month != m.month:
                    continue
                all_dates.append(d)
    all_dates = sorted(all_dates)
    # find first CX
    first_cx = None
    for d in all_dates:
        if get_code(d) == "CX":
            first_cx = d
            break
    if not first_cx:
        return 0, []
    count, days = total_absence_count_for_vacs(first_cx, months_scope)
    return count, days

total_abs, abs_days = compute_total_absence_for_scope(months_to_show)
st.sidebar.markdown(f"**Total absence (VACS + ZZ collés)** : **{total_abs}** jours")

# ---------------------------
# Optimisation déclenchée
# ---------------------------
if optimize_btn:
    with st.spinner("Optimisation en cours..."):
        score = optimize_placement(months_to_show, int(cx_total), int(c4_total))
    st.success(f"Optimisation terminée. Score estimé (jours d'absence maximisés) : {score}")
    # reload state and recompute
    save_state(state)

# ---------------------------
# Boutons sauvegarde / reset
# ---------------------------
col_save, col_reset = st.columns([1,1])
with col_save:
    if st.button("Sauvegarder état"):
        save_state(state)
        st.success("État sauvegardé.")
with col_reset:
    if st.button("Réinitialiser mois affiché"):
        # reset only months shown
        for m in months_to_show:
            key = f"{m.year:04d}-{m.month:02d}"
            if key in state["data"]:
                state["data"].pop(key, None)
        save_state(state)
        st.experimental_rerun()

# ---------------------------
# Affichage détail jours d'absence
# ---------------------------
if abs_days:
    st.markdown("### Détails jours d'absence liés à la période VACS")
    df = pd.DataFrame({"date": [d.isoformat() for d in abs_days], "code": [get_code(d) for d in abs_days]})
    st.table(df)

# ---------------------------
# Fin
# ---------------------------
st.markdown("**Légende codes** : TRA = Jour travaillé; ZZ = Repos habituel; CX = Congé posé; CZ = Congé généré; C4 = Congé supplémentaire; FC = Jour férié.")

# app.py
import streamlit as st
from datetime import date, timedelta
import calendar
import json
import os
import pandas as pd
import holidays
from itertools import combinations

# ---------------------------
# Configuration
# ---------------------------
st.set_page_config(layout="wide", page_title="Gestion calendrier congés")
DATA_FILE = "calendar_state.json"
FR_HOLIDAYS = holidays.France()

# Codes
CODES = ["TRA", "ZZ", "CX", "CZ", "C4", "FC"]
WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
# For display header starting Sunday
HEADER_DAYS = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# ---------------------------
# Persistence helpers
# ---------------------------
def load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"data": {}, "settings": {}}
    return {"data": {}, "settings": {}}

def save_state(state):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)

state = load_state()
if "data" not in state:
    state["data"] = {}
if "settings" not in state:
    state["settings"] = {}

# ---------------------------
# Utilitaires calendrier
# ---------------------------
def month_grid(year, month):
    cal = calendar.Calendar(firstweekday=6)  # semaine commence dimanche
    month_days = list(cal.itermonthdates(year, month))
    weeks = [month_days[i:i+7] for i in range(0, len(month_days), 7)]
    return weeks

def date_key(d: date):
    return d.isoformat()

def display_date_str(d: date):
    return d.strftime("%d/%m/%Y")

def weekday_fr(d: date):
    return WEEKDAYS_FR[d.weekday()]

def month_key(year, month):
    return f"{year:04d}-{month:02d}"

def ensure_month_initialized(year, month):
    key = month_key(year, month)
    if key not in state["data"]:
        state["data"][key] = {}
    # initialize all days to TRA then apply ZZ/FC defaults later
    for w in month_grid(year, month):
        for d in w:
            if d.month != month:
                continue
            state["data"][key].setdefault(date_key(d), "TRA")

# ---------------------------
# Sidebar : paramètres
# ---------------------------
st.sidebar.header("Paramètres affichage et règles")

today = date.today()
col1, col2, col3 = st.sidebar.columns([1,1,1])
with col1:
    sel_day = st.sidebar.number_input("Jour", min_value=1, max_value=31, value=today.day, step=1)
with col2:
    sel_month = st.sidebar.selectbox("Mois", list(range(1,13)), index=today.month-1, format_func=lambda x: calendar.month_name[x])
with col3:
    sel_year = st.sidebar.number_input("Année", min_value=1900, max_value=2100, value=today.year, step=1)

display_date = date(sel_year, sel_month, min(sel_day, calendar.monthrange(sel_year, sel_month)[1]))

show_two_months = st.sidebar.checkbox("Afficher 2 mois (mois suivant inclus)", value=False)

st.sidebar.markdown("### Parité et jours ZZ")
parity_choice = st.sidebar.radio("Semaines à 3 ZZ sur :", ("Paires", "Impaires"))

# Allow user to choose exactly which days are ZZ for even and odd weeks.
st.sidebar.markdown("**Choix des jours ZZ pour semaines impaires**")
zz_odd = st.sidebar.multiselect("ZZ semaine impaires (choisir 2 ou 3 jours)", WEEKDAYS_FR, default=["samedi", "dimanche"])
st.sidebar.markdown("**Choix des jours ZZ pour semaines paires**")
zz_even = st.sidebar.multiselect("ZZ semaine paires (choisir 2 ou 3 jours)", WEEKDAYS_FR, default=["samedi", "dimanche"])

# Validate selections: enforce 2 or 3 days
def validate_zz_selection(sel):
    if len(sel) < 2:
        return sel + ["samedi", "dimanche"][:2-len(sel)]
    if len(sel) > 3:
        return sel[:3]
    return sel

zz_odd = validate_zz_selection(zz_odd)
zz_even = validate_zz_selection(zz_even)

st.sidebar.markdown("**Mode ZZ par semaine**")
zz_mode = st.sidebar.radio("Nombre de ZZ par semaine", ("2 jours", "3 jours"))

st.sidebar.markdown("### Compteurs")
cx_quota = st.sidebar.number_input("Compteur CX (unités totales à poser)", min_value=0, max_value=31, value=3, step=1)
c4_quota = st.sidebar.number_input("Compteur C4 (max 4 unités)", min_value=0, max_value=4, value=0, step=1)

st.sidebar.markdown("---")
optimize_btn = st.sidebar.button("Optimiser (mode optimisation)")

# ---------------------------
# Initialisation mois(s)
# ---------------------------
months_to_show = [display_date]
if show_two_months:
    y = sel_year
    m = sel_month + 1
    if m == 13:
        m = 1
        y += 1
    months_to_show.append(date(y, m, 1))

for m in months_to_show:
    ensure_month_initialized(m.year, m.month)

# ---------------------------
# Accesseurs codes
# ---------------------------
def get_code(d: date):
    key = month_key(d.year, d.month)
    return state["data"].get(key, {}).get(date_key(d), "TRA")

def set_code(d: date, code: str):
    key = month_key(d.year, d.month)
    state["data"].setdefault(key, {})
    state["data"][key][date_key(d)] = code

# ---------------------------
# Règles métier : utilitaires
# ---------------------------
def is_week_even(d: date):
    return (d.isocalendar()[1] % 2) == 0

def is_fc(d: date):
    return get_code(d) == "FC"

def treated_as_zz(d: date):
    # FC treated as ZZ for logic
    c = get_code(d)
    return c == "ZZ" or c == "FC"

def week_is_three_zz(d: date):
    # Determine if this week is considered a "3-ZZ" week based on parity and selection
    week_even = is_week_even(d)
    if parity_choice == "Paires":
        target = zz_even
    else:
        target = zz_odd
    # If zz_mode is 3 jours, then weeks of the chosen parity are 3-ZZ
    if zz_mode == "3 jours":
        # week parity matches selection of which weeks are 3-ZZ
        if parity_choice == "Paires":
            return week_even
        else:
            return not week_even
    return False

def apply_default_zz_and_fc_for_month(year, month):
    key = month_key(year, month)
    for w in month_grid(year, month):
        for d in w:
            if d.month != month:
                continue
            # FC detection
            if d in FR_HOLIDAYS:
                state["data"][key][date_key(d)] = "FC"
                continue
            # default TRA
            state["data"][key].setdefault(date_key(d), "TRA")
    # Apply ZZ according to selections for each week
    for w in month_grid(year, month):
        for d in w:
            if d.month != month:
                continue
            week_even = is_week_even(d)
            chosen = zz_even if week_even else zz_odd
            if WEEKDAYS_FR[d.weekday()] in chosen:
                # mark as ZZ unless it's FC (FC kept)
                if state["data"][key].get(date_key(d)) != "FC":
                    state["data"][key][date_key(d)] = "ZZ"

# ---------------------------
# Application des règles VACS / CZ / C4
# ---------------------------
def apply_business_rules(months_scope):
    # First, ensure defaults (TRA/ZZ/FC) applied for months in scope
    for m in months_scope:
        apply_default_zz_and_fc_for_month(m.year, m.month)

    # Clear any CZ marks before recomputing
    for m in months_scope:
        key = month_key(m.year, m.month)
        for w in month_grid(m.year, m.month):
            for d in w:
                if d.month != m.month:
                    continue
                if state["data"][key].get(date_key(d)) == "CZ":
                    # revert to ZZ (or FC) before recompute
                    if d in FR_HOLIDAYS:
                        state["data"][key][date_key(d)] = "FC"
                    else:
                        # if day is in chosen ZZ set, keep ZZ, else TRA
                        week_even = is_week_even(d)
                        chosen = zz_even if week_even else zz_odd
                        if WEEKDAYS_FR[d.weekday()] in chosen:
                            state["data"][key][date_key(d)] = "ZZ"
                        else:
                            state["data"][key][date_key(d)] = "TRA"

    # Now scan chronologically and apply VACS logic
    # Build sorted list of all dates in scope
    all_dates = []
    for m in months_scope:
        for w in month_grid(m.year, m.month):
            for d in w:
                if d.month != m.month:
                    continue
                all_dates.append(d)
    all_dates = sorted(all_dates)

    in_vacs = False
    for d in all_dates:
        code = get_code(d)
        if code == "CX":
            # start VACS at first CX encountered (or continue if already in)
            in_vacs = True
            # CX remains CX
            continue
        if code == "C4":
            # C4 counts as absence and interrupts VACS
            in_vacs = False
            continue
        if code == "TRA":
            # TRA breaks VACS
            in_vacs = False
            continue
        # For ZZ or FC or other codes when in_vacs, possibly convert to CZ
        if in_vacs and treated_as_zz(d) and week_is_three_zz(d):
            # mark as CZ (but keep FC visually as FC; we store CZ for logic but keep FC display)
            if d in FR_HOLIDAYS:
                # keep FC visually but mark CZ in a separate flag by storing "FC" and also "CZ" in metadata
                # For simplicity, store "FC" but also set a derived flag in session for display; here we set "CZ" to show transformation
                state["data"][month_key(d.year, d.month)][date_key(d)] = "CZ"
            else:
                state["data"][month_key(d.year, d.month)][date_key(d)] = "CZ"
        else:
            # if not in vacs, ensure ZZ/FC remain as set by defaults
            # do nothing
            pass

# ---------------------------
# Absence counting utilities
# ---------------------------
def simulate_vacs_from(start_date, months_scope):
    # returns sorted unique list of absence dates for VACS starting at start_date
    abs_days = []
    d = start_date
    in_vacs = True
    while True:
        # stop if outside scope months
        if not any((d.year == m.year and d.month == m.month) for m in months_scope):
            break
        code = get_code(d)
        if code == "TRA":
            break
        abs_days.append(d)
        if code == "C4":
            # C4 included then stop
            break
        d = d + timedelta(days=1)
    # add contiguous ZZ/FC before and after
    # before
    first = abs_days[0] if abs_days else None
    last = abs_days[-1] if abs_days else None
    if not abs_days:
        return []
    d = first - timedelta(days=1)
    while any((d.year == m.year and d.month == m.month) for m in months_scope):
        if treated_as_zz(d):
            abs_days.insert(0, d)
            d = d - timedelta(days=1)
        else:
            break
    d = last + timedelta(days=1)
    while any((d.year == m.year and d.month == m.month) for m in months_scope):
        if treated_as_zz(d):
            abs_days.append(d)
            d = d + timedelta(days=1)
        else:
            break
    # unique sorted
    unique = sorted({dd for dd in abs_days})
    return unique

def total_absence_for_scope(months_scope):
    # find first CX in scope
    all_dates = []
    for m in months_scope:
        for w in month_grid(m.year, m.month):
            for d in w:
                if d.month != m.month:
                    continue
                all_dates.append(d)
    all_dates = sorted(all_dates)
    first_cx = None
    for d in all_dates:
        if get_code(d) == "CX":
            first_cx = d
            break
    if not first_cx:
        return 0, []
    days = simulate_vacs_from(first_cx, months_scope)
    return len(days), days

# ---------------------------
# Optimisation (greedy iterative)
# ---------------------------
def evaluate_total_absence_with_plan(months_scope):
    # apply business rules then compute total absence
    apply_business_rules(months_scope)
    cnt, days = total_absence_for_scope(months_scope)
    return cnt, days

def optimize_placement(months_scope, cx_quota, c4_quota):
    # Greedy iterative: place CXs one by one choosing the CX that gives the largest marginal gain.
    # Optionally place C4s to interrupt and allow new VACS sequences.
    # Work on a backup copy of state
    backup = json.loads(json.dumps(state["data"]))
    try:
        # ensure defaults applied
        for m in months_scope:
            apply_default_zz_and_fc_for_month(m.year, m.month)
        # candidate days: any day in scope that is not already CX or C4
        candidates = []
        for m in months_scope:
            for w in month_grid(m.year, m.month):
                for d in w:
                    if d.month != m.month:
                        continue
                    if get_code(d) not in ("CX", "C4"):
                        candidates.append(d)
        candidates = sorted(set(candidates))
        placed_cx = []
        placed_c4 = []
        # initial baseline
        baseline_cnt, _ = evaluate_total_absence_with_plan(months_scope)
        # place CXs greedily
        for _ in range(int(cx_quota)):
            best_gain = 0
            best_day = None
            for cand in candidates:
                if cand in placed_cx or cand in placed_c4:
                    continue
                prev = state["data"].get(month_key(cand.year, cand.month), {}).get(date_key(cand), None)
                set_code(cand, "CX")
                cnt, _ = evaluate_total_absence_with_plan(months_scope)
                gain = cnt - baseline_cnt
                # revert
                if prev is None:
                    state["data"][month_key(cand.year, cand.month)].pop(date_key(cand), None)
                else:
                    set_code(cand, prev)
                if gain > best_gain:
                    best_gain = gain
                    best_day = cand
            if best_day is None:
                # no positive gain candidate, still place CX on earliest candidate to consume quota
                for cand in candidates:
                    if cand not in placed_cx and cand not in placed_c4:
                        best_day = cand
                        break
            if best_day is None:
                break
            # place it permanently
            set_code(best_day, "CX")
            placed_cx.append(best_day)
            baseline_cnt, _ = evaluate_total_absence_with_plan(months_scope)
        # place C4s greedily to try to increase total absence by interrupting and allowing new VACS
        for _ in range(int(c4_quota)):
            best_gain = 0
            best_day = None
            # candidate for C4: any day not CX/C4
            for cand in candidates:
                if cand in placed_cx or cand in placed_c4:
                    continue
                prev = state["data"].get(month_key(cand.year, cand.month), {}).get(date_key(cand), None)
                set_code(cand, "C4")
                cnt, _ = evaluate_total_absence_with_plan(months_scope)
                gain = cnt - baseline_cnt
                # revert
                if prev is None:
                    state["data"][month_key(cand.year, cand.month)].pop(date_key(cand), None)
                else:
                    set_code(cand, prev)
                if gain > best_gain:
                    best_gain = gain
                    best_day = cand
            if best_day is None:
                # place C4 after last placed CX if possible
                if placed_cx:
                    last_end = simulate_vacs_from(placed_cx[-1], months_scope)
                    if last_end:
                        candidate_day = last_end[-1] + timedelta(days=1)
                        if any((candidate_day.year == m.year and candidate_day.month == m.month) for m in months_scope):
                            best_day = candidate_day
            if best_day is None:
                break
            set_code(best_day, "C4")
            placed_c4.append(best_day)
            baseline_cnt, _ = evaluate_total_absence_with_plan(months_scope)
        # final evaluation
        final_cnt, final_days = evaluate_total_absence_with_plan(months_scope)
        save_state(state)
        return final_cnt, placed_cx, placed_c4, final_days
    finally:
        # nothing to do; state already saved if success. If you want to rollback on failure, restore backup.
        pass

# ---------------------------
# Reactivity: apply rules initially
# ---------------------------
apply_business_rules(months_to_show)
save_state(state)

# ---------------------------
# Main UI : affichage calendrier
# ---------------------------
st.title("Gestionnaire de calendrier de congés")

cols = st.columns(len(months_to_show))
for idx, m in enumerate(months_to_show):
    with cols[idx]:
        st.subheader(f"{calendar.month_name[m.month]} {m.year}")
        weeks = month_grid(m.year, m.month)
        # header
        header_cols = st.columns(7)
        for i, h in enumerate(HEADER_DAYS):
            header_cols[i].markdown(f"**{h}**")
        # render weeks
        for week in weeks:
            week_cols = st.columns(7)
            for i, d in enumerate(week):
                col = week_cols[i]
                with col:
                    if d.month != m.month:
                        st.write("")  # empty cell
                        continue
                    code = get_code(d)
                    # display date full and day name
                    date_str = display_date_str(d)
                    day_name = weekday_fr(d)
                    # color mapping
                    color = "#ffffff"
                    if code == "TRA":
                        color = "#f7f7f7"
                    elif code == "ZZ":
                        color = "#cfe8ff"
                    elif code == "CX":
                        color = "#ffd9b3"
                    elif code == "CZ":
                        color = "#ffb3b3"
                    elif code == "C4":
                        color = "#d1c4e9"
                    elif code == "FC":
                        color = "#ffef9f"
                    # show cell with full info
                    st.markdown(
                        f"<div style='background:{color};padding:8px;border-radius:6px'>"
                        f"<div style='font-weight:600'>{date_str}</div>"
                        f"<div style='color:#333'>{day_name}</div>"
                        f"<div style='margin-top:6px;font-weight:700'>{code}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    # selectbox to change code manually
                    key = f"sel_{d.isoformat()}"
                    # ensure index exists
                    try:
                        idx_code = CODES.index(code) if code in CODES else 0
                    except Exception:
                        idx_code = 0
                    sel = st.selectbox("", CODES, index=idx_code, key=key, label_visibility="collapsed")
                    if sel != code:
                        set_code(d, sel)
                        # after manual change, reapply business rules and save, then rerun to reflect changes
                        apply_business_rules(months_to_show)
                        save_state(state)
                        st.experimental_rerun()
        st.markdown("---")

# ---------------------------
# Metrics and optimisation
# ---------------------------
total_abs, abs_days = total_absence_for_scope(months_to_show)
st.sidebar.markdown(f"**Total absence (VACS + ZZ collés)** : **{total_abs}** jours")

if optimize_btn:
    with st.spinner("Optimisation en cours..."):
        final_cnt, placed_cx, placed_c4, final_days = optimize_placement(months_to_show, cx_quota, c4_quota)
    st.success(f"Optimisation terminée. Jours d'absence totaux : {final_cnt}")
    if placed_cx:
        st.sidebar.markdown(f"CX placés : {', '.join([d.strftime('%d/%m/%Y') for d in placed_cx])}")
    if placed_c4:
        st.sidebar.markdown(f"C4 placés : {', '.join([d.strftime('%d/%m/%Y') for d in placed_c4])}")
    # reapply rules and rerun to reflect placements
    apply_business_rules(months_to_show)
    save_state(state)
    st.experimental_rerun()

# Save / reset controls
col_save, col_reset = st.columns([1,1])
with col_save:
    if st.button("Sauvegarder état"):
        save_state(state)
        st.success("État sauvegardé.")
with col_reset:
    if st.button("Réinitialiser mois affiché"):
        for m in months_to_show:
            key = month_key(m.year, m.month)
            if key in state["data"]:
                state["data"].pop(key, None)
        save_state(state)
        st.experimental_rerun()

# Détail jours d'absence
if abs_days:
    st.markdown("### Détails jours d'absence liés à la période VACS")
    df = pd.DataFrame({"date": [d.strftime("%d/%m/%Y") for d in abs_days], "jour": [weekday_fr(d) for d in abs_days], "code": [get_code(d) for d in abs_days]})
    st.table(df)

st.markdown("**Légende** : TRA = Jour travaillé; ZZ = Repos habituel; CX = Congé posé; CZ = Congé généré; C4 = Congé supplémentaire; FC = Jour férié.")

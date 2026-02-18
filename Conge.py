# app.py
import streamlit as st
from datetime import date, timedelta
import calendar
import json
import os
import pandas as pd
import holidays

# ---------------------------
# Configuration
# ---------------------------
st.set_page_config(layout="wide", page_title="Gestion calendrier congés")
DATA_FILE = "calendar_state.json"
FR_HOLIDAYS = holidays.France()

CODES = ["TRA", "ZZ", "CX", "CZ", "C4", "FC"]
WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
HEADER_DAYS = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# ---------------------------
# Helpers safe rerun
# ---------------------------
def safe_rerun():
    """Appelle st.experimental_rerun() de façon sûre (protège contre AttributeError)."""
    rerun = getattr(st, "experimental_rerun", None)
    if callable(rerun):
        try:
            rerun()
        except Exception:
            # si rerun échoue, on stoppe proprement la session pour éviter l'AttributeError
            st.stop()

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

def save_state(state_obj):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state_obj, f, ensure_ascii=False, indent=2, default=str)

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

st.sidebar.markdown("**Choix des jours ZZ pour semaines impaires**")
zz_odd = st.sidebar.multiselect("ZZ semaine impaires (2 ou 3 jours)", WEEKDAYS_FR, default=["samedi", "dimanche"])
st.sidebar.markdown("**Choix des jours ZZ pour semaines paires**")
zz_even = st.sidebar.multiselect("ZZ semaine paires (2 ou 3 jours)", WEEKDAYS_FR, default=["samedi", "dimanche"])

def validate_zz_selection(sel):
    if len(sel) < 2:
        base = ["samedi", "dimanche"]
        for s in base:
            if s not in sel:
                sel.append(s)
            if len(sel) >= 2:
                break
    if len(sel) > 3:
        sel = sel[:3]
    return sel

zz_odd = validate_zz_selection(zz_odd)
zz_even = validate_zz_selection(zz_even)

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

def treated_as_zz(d: date):
    """Retourne True si le jour est traité comme ZZ pour la logique (ZZ ou FC)."""
    c = get_code(d)
    return c == "ZZ" or c == "FC"

def week_is_three_zz(d: date):
    """Une semaine est '3-ZZ' si la sélection pour sa parité contient 3 jours et la parité correspond."""
    week_even = is_week_even(d)
    chosen = zz_even if week_even else zz_odd
    if len(chosen) == 3:
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
            if d in FR_HOLIDAYS:
                state["data"][key][date_key(d)] = "FC"
                continue
            state["data"][key].setdefault(date_key(d), "TRA")
    # Appliquer ZZ selon sélection (sans écraser FC)
    for w in month_grid(year, month):
        for d in w:
            if d.month != month:
                continue
            week_even = is_week_even(d)
            chosen = zz_even if week_even else zz_odd
            if WEEKDAYS_FR[d.weekday()] in chosen:
                if state["data"][key].get(date_key(d)) != "FC":
                    state["data"][key][date_key(d)] = "ZZ"

# ---------------------------
# Application des règles VACS / CZ / C4
# ---------------------------
def apply_business_rules(months_scope):
    """
    Applique :
    - defaults (TRA/ZZ/FC),
    - calcule les périodes VACS (déclenchées par CX),
    - transforme ZZ -> CZ uniquement si en VACS et semaine à 3 ZZ,
    - FC reste FC visuellement mais est traité comme ZZ pour la logique.
    """
    # 1) Defaults
    for m in months_scope:
        apply_default_zz_and_fc_for_month(m.year, m.month)

    # 2) Revenir sur CZ précédents (ne pas écraser FC)
    for m in months_scope:
        key = month_key(m.year, m.month)
        for w in month_grid(m.year, m.month):
            for d in w:
                if d.month != m.month:
                    continue
                if state["data"][key].get(date_key(d)) == "CZ":
                    # si jour férié, garder FC; sinon remettre ZZ si sélection le prévoit, sinon TRA
                    if d in FR_HOLIDAYS:
                        state["data"][key][date_key(d)] = "FC"
                    else:
                        week_even = is_week_even(d)
                        chosen = zz_even if week_even else zz_odd
                        if WEEKDAYS_FR[d.weekday()] in chosen:
                            state["data"][key][date_key(d)] = "ZZ"
                        else:
                            state["data"][key][date_key(d)] = "TRA"

    # 3) Parcours chronologique pour appliquer VACS et CZ
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
            in_vacs = True
            continue
        if code == "C4":
            # C4 compte comme absence mais interrompt la VACS
            in_vacs = False
            continue
        if code == "TRA":
            in_vacs = False
            continue
        # Si on est en VACS et le jour est traité comme ZZ et la semaine est 3-ZZ :
        # - si le jour est ZZ (non-FC) -> on le marque CZ
        # - si le jour est FC -> on le laisse FC (visuel) mais il sera compté comme CZ dans les calculs via is_effective_cz()
        if in_vacs and treated_as_zz(d) and week_is_three_zz(d):
            if get_code(d) == "ZZ":
                state["data"][month_key(d.year, d.month)][date_key(d)] = "CZ"
            # si FC, on ne change pas la valeur stockée (reste "FC"), mais la logique d'absence le traitera comme CZ

# ---------------------------
# Fonctions d'évaluation CZ effectif et d'absence
# ---------------------------
def is_effective_cz(d: date, months_scope):
    """
    Retourne True si le jour doit être considéré comme CZ pour le calcul d'absence :
    - stocké "CZ" OU
    - stocké "FC" et en période VACS et semaine à 3-ZZ
    """
    code = get_code(d)
    if code == "CZ":
        return True
    if code == "FC":
        # pour savoir si FC est 'effectivement CZ', il faut vérifier s'il est dans une VACS
        # On détecte la présence d'une VACS qui englobe ce jour en recherchant un CX antérieur non interrompu par TRA/C4
        # Parcourir en arrière jusqu'à trouver un CX ou une interruption
        dd = d
        # chercher le début de la séquence en remontant
        while True:
            prev = dd - timedelta(days=1)
            # si prev hors scope, on arrête
            if not any((prev.year == m.year and prev.month == m.month) for m in months_scope):
                break
            prev_code = get_code(prev)
            if prev_code == "CX":
                # il y a un CX avant sans interruption -> d est dans VACS
                # vérifier que la semaine est 3-ZZ
                return week_is_three_zz(d)
            if prev_code in ("TRA", "C4"):
                break
            dd = prev
        # aussi vérifier si d lui-même est après un CX (parcours avant n'a trouvé CX mais peut y avoir CX sur d ou après)
        # on vérifie s'il existe un CX avant d dans la période sans interruption
        dd = d
        while True:
            prev = dd - timedelta(days=1)
            if not any((prev.year == m.year and prev.month == m.month) for m in months_scope):
                break
            prev_code = get_code(prev)
            if prev_code == "CX":
                return week_is_three_zz(d)
            if prev_code in ("TRA", "C4"):
                break
            dd = prev
    return False

def simulate_vacs_from(start_date, months_scope):
    """
    Retourne la liste unique et triée des jours d'absence pour une VACS démarrant à start_date.
    Les jours comptés : CX, C4, CZ (stocké) et ZZ/FC qui sont traités comme CZ via is_effective_cz.
    On arrête la VACS au premier TRA ou après un C4.
    """
    abs_days = []
    d = start_date
    while True:
        if not any((d.year == m.year and d.month == m.month) for m in months_scope):
            break
        code = get_code(d)
        if code == "TRA":
            break
        # CX, C4, CZ sont comptés ; FC peut être compté via is_effective_cz
        if code in ("CX", "C4", "CZ"):
            abs_days.append(d)
        elif code == "ZZ":
            # si ZZ stocké mais en semaine 3-ZZ et en VACS -> CZ effectif (mais ici on ne sait pas si on est en VACS)
            # pour la simulation, on considère la VACS démarrant à start_date, donc on est en VACS
            if week_is_three_zz(d):
                abs_days.append(d)  # compte comme CZ
        elif code == "FC":
            # FC treated as ZZ for logic; if week_is_three_zz -> count as CZ
            if week_is_three_zz(d):
                abs_days.append(d)
            else:
                # FC not in 3-ZZ week: still counts as absence if contiguous to VACS (we'll include contiguous ZZ/FC later)
                abs_days.append(d)
        d = d + timedelta(days=1)
    if not abs_days:
        return []
    # ajouter ZZ/FC contigus avant et après
    first = abs_days[0]
    last = abs_days[-1]
    # avant
    d = first - timedelta(days=1)
    while any((d.year == m.year and d.month == m.month) for m in months_scope):
        if treated_as_zz(d):
            abs_days.insert(0, d)
            d = d - timedelta(days=1)
        else:
            break
    # après
    d = last + timedelta(days=1)
    while any((d.year == m.year and d.month == m.month) for m in months_scope):
        if treated_as_zz(d):
            abs_days.append(d)
            d = d + timedelta(days=1)
        else:
            break
    unique = sorted({dd for dd in abs_days})
    return unique

def total_absence_for_scope(months_scope):
    # trouver le premier CX dans la période
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
# Optimisation (greedy amélioré)
# ---------------------------
def evaluate_total_absence_with_plan(months_scope):
    apply_business_rules(months_scope)
    cnt, days = total_absence_for_scope(months_scope)
    return cnt, days

def optimize_placement(months_scope, cx_quota, c4_quota):
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
    baseline_cnt, _ = evaluate_total_absence_with_plan(months_scope)

    # placer CX par gain marginal (fallback earliest pour consommer quota)
    for _ in range(int(cx_quota)):
        best_gain = -1
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
            for cand in candidates:
                if cand not in placed_cx and cand not in placed_c4:
                    best_day = cand
                    break
        if best_day is None:
            break
        set_code(best_day, "CX")
        placed_cx.append(best_day)
        baseline_cnt, _ = evaluate_total_absence_with_plan(months_scope)

    # placer C4 par gain marginal (fallback heuristique)
    for _ in range(int(c4_quota)):
        best_gain = -1
        best_day = None
        for cand in candidates:
            if cand in placed_cx or cand in placed_c4:
                continue
            prev = state["data"].get(month_key(cand.year, cand.month), {}).get(date_key(cand), None)
            set_code(cand, "C4")
            cnt, _ = evaluate_total_absence_with_plan(months_scope)
            gain = cnt - baseline_cnt
            if prev is None:
                state["data"][month_key(cand.year, cand.month)].pop(date_key(cand), None)
            else:
                set_code(cand, prev)
            if gain > best_gain:
                best_gain = gain
                best_day = cand
        if best_day is None:
            if placed_cx:
                last_vacs = simulate_vacs_from(placed_cx[-1], months_scope)
                if last_vacs:
                    candidate_day = last_vacs[-1] + timedelta(days=1)
                    if any((candidate_day.year == m.year and candidate_day.month == m.month) for m in months_scope):
                        best_day = candidate_day
        if best_day is None:
            break
        set_code(best_day, "C4")
        placed_c4.append(best_day)
        baseline_cnt, _ = evaluate_total_absence_with_plan(months_scope)

    final_cnt, final_days = evaluate_total_absence_with_plan(months_scope)
    save_state(state)
    return final_cnt, placed_cx, placed_c4, final_days

# ---------------------------
# Reactivity control (callbacks)
# ---------------------------
if "needs_rerun" not in st.session_state:
    st.session_state["needs_rerun"] = False

def on_selectbox_change(date_iso):
    """
    Callback when a day's selectbox changes.
    Update state and mark for rerun.
    """
    key = f"sel_{date_iso}"
    new_value = st.session_state.get(key)
    d = date.fromisoformat(date_iso)
    set_code(d, new_value)
    # save immediately
    save_state(state)
    # mark for rerun after rendering
    st.session_state["needs_rerun"] = True

# ---------------------------
# Initial application of rules
# ---------------------------
apply_business_rules(months_to_show)
save_state(state)

# ---------------------------
# Main UI : affichage calendrier (selectbox with on_change)
# ---------------------------
st.title("Gestionnaire de calendrier de congés")

cols = st.columns(len(months_to_show))

for idx, m in enumerate(months_to_show):
    with cols[idx]:
        st.subheader(f"{calendar.month_name[m.month]} {m.year}")
        weeks = month_grid(m.year, m.month)
        header_cols = st.columns(7)
        for i, h in enumerate(HEADER_DAYS):
            header_cols[i].markdown(f"**{h}**")
        for week in weeks:
            week_cols = st.columns(7)
            for i, d in enumerate(week):
                col = week_cols[i]
                with col:
                    if d.month != m.month:
                        st.write("")
                        continue
                    code = get_code(d)
                    date_str = display_date_str(d)
                    day_name = weekday_fr(d)
                    # determine display code: if FC but is_effective_cz -> show "FC" visually but will be counted as CZ
                    display_code = code
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
                    st.markdown(
                        f"<div style='background:{color};padding:8px;border-radius:6px'>"
                        f"<div style='font-weight:600'>{date_str}</div>"
                        f"<div style='color:#333'>{day_name}</div>"
                        f"<div style='margin-top:6px;font-weight:700'>{display_code}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    # selectbox with callback
                    key = f"sel_{d.isoformat()}"
                    if key not in st.session_state:
                        st.session_state[key] = code
                    st.selectbox("", CODES, key=key, on_change=on_selectbox_change, args=(d.isoformat(),), label_visibility="collapsed")

st.markdown("---")

# After rendering, if any change occurred, reapply rules, save and rerun once (safe)
if st.session_state.get("needs_rerun", False):
    apply_business_rules(months_to_show)
    save_state(state)
    st.session_state["needs_rerun"] = False
    safe_rerun()

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
    apply_business_rules(months_to_show)
    save_state(state)
    safe_rerun()

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
        safe_rerun()

# Détail jours d'absence
if abs_days:
    st.markdown("### Détails jours d'absence liés à la période VACS")
    df = pd.DataFrame({"date": [d.strftime("%d/%m/%Y") for d in abs_days], "jour": [weekday_fr(d) for d in abs_days], "code": [get_code(d) for d in abs_days]})
    st.table(df)

st.markdown("**Légende** : TRA = Jour travaillé; ZZ = Repos habituel; CX = Congé posé; CZ = Congé généré; C4 = Congé supplémentaire; FC = Jour férié.")

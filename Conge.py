# app.py
import streamlit as st
import pandas as pd
import numpy as np
import calendar
import json
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path

# -------------------------
# Constants and utilities
# -------------------------
DATA_DIR = Path("calendar_data")
DATA_DIR.mkdir(exist_ok=True)

CODES = ["TRA", "ZZ", "CX", "CZ", "C4", "FC"]
DEFAULT_CODE = "TRA"

def month_key(year: int, month: int):
    return f"{year:04d}-{month:02d}"

def save_month_data(key: str, df: pd.DataFrame):
    path = DATA_DIR / f"{key}.json"
    df_to_save = df.to_dict(orient="records")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(df_to_save, f, default=str, ensure_ascii=False)

def load_month_data(key: str):
    path = DATA_DIR / f"{key}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def week_is_even(dt: date):
    # ISO week number parity: use isocalendar().week
    return (dt.isocalendar()[1] % 2) == 0

def sunday_start_calendar(year: int, month: int):
    # returns list of weeks, each week is list of date or None, weeks start Sunday
    first = date(year, month, 1)
    last = (first + relativedelta(months=1)) - timedelta(days=1)
    # find first Sunday on or before first
    start = first
    while start.weekday() != 6:  # Sunday = 6
        start -= timedelta(days=1)
    end = last
    while end.weekday() != 5:  # Saturday = 5
        end += timedelta(days=1)
    days = list(daterange(start, end))
    weeks = [days[i:i+7] for i in range(0, len(days), 7)]
    return weeks

# -------------------------
# Business logic functions
# -------------------------
def init_month_df(year: int, month: int):
    first = date(year, month, 1)
    last = (first + relativedelta(months=1)) - timedelta(days=1)
    rows = []
    for d in daterange(first, last):
        rows.append({
            "date": d,
            "day": d.day,
            "weekday": calendar.day_name[d.weekday()],
            "code": DEFAULT_CODE,
            "is_fc": False  # user can mark FC
        })
    return pd.DataFrame(rows)

def apply_zz_pattern(df: pd.DataFrame, zz_even_weeks: int, zz_odd_weeks: int, parity_three_days_is_even: bool):
    # zz_even_weeks and zz_odd_weeks are counts of ZZ per week (2 or 3)
    # parity_three_days_is_even True => weeks with 3 ZZ are even weeks
    df = df.copy()
    df['weeknum'] = df['date'].apply(lambda d: d.isocalendar()[1])
    def week_zz_count(d):
        is_even = (d.isocalendar()[1] % 2) == 0
        three_is_even = parity_three_days_is_even
        if is_even:
            return zz_even_weeks if three_is_even else zz_odd_weeks
        else:
            return zz_odd_weeks if three_is_even else zz_even_weeks
    df['zz_count_week'] = df['date'].apply(week_zz_count)
    # For each week, mark the first N days of week (starting Sunday) as ZZ by default
    df['is_zz_candidate'] = False
    for weeknum, group in df.groupby('weeknum'):
        week_dates = sorted(group['date'].tolist(), key=lambda d: d.weekday())  # Monday..Sunday ordering
        # We need Sunday-first ordering for selection
        # Build Sunday-first list:
        sunday_first = sorted(group['date'].tolist(), key=lambda d: ((d.weekday()+1) % 7))
        n = group['zz_count_week'].iloc[0]
        # choose n days in the week to be ZZ: prefer contiguous at week start (Sunday, Monday...)
        chosen = set(sunday_first[:n])
        df.loc[df['date'].isin(chosen), 'is_zz_candidate'] = True
    # Apply FC: FC remains FC but treated as ZZ for logic
    df.loc[df['is_fc'] == True, 'is_zz_candidate'] = True
    # Set code to ZZ if candidate and currently TRA (do not override CX/C4/FC)
    df.loc[(df['is_zz_candidate']) & (df['code'] == DEFAULT_CODE), 'code'] = "ZZ"
    return df

def compute_vacs_and_transformations(df: pd.DataFrame):
    """
    Apply rules:
    - VACS starts at first CX and continues until a TRA or a C4 is encountered.
    - During VACS, if a day is ZZ and the week is a 3-ZZ week, ZZ -> CZ.
    - FC stays FC but is treated as ZZ for CZ transformation.
    - C4 ends VACS immediately and counts as absence.
    """
    df = df.copy().sort_values('date').reset_index(drop=True)
    df['in_vacs'] = False
    in_vacs = False
    for idx, row in df.iterrows():
        code = row['code']
        if code == "CX":
            in_vacs = True
            df.at[idx, 'in_vacs'] = True
            continue
        if code == "C4":
            # C4 ends VACS but itself is considered absence
            df.at[idx, 'in_vacs'] = False
            in_vacs = False
            continue
        if code == "TRA":
            # TRA ends VACS
            df.at[idx, 'in_vacs'] = False
            in_vacs = False
            continue
        # For other codes, if currently in_vacs, mark
        if in_vacs:
            df.at[idx, 'in_vacs'] = True
        else:
            df.at[idx, 'in_vacs'] = False

    # Transform ZZ -> CZ if in_vacs and week has 3 ZZ (we need to detect week type)
    # Determine week zz_count from existing ZZ candidates per week
    df['weeknum'] = df['date'].apply(lambda d: d.isocalendar()[1])
    # For each week, count how many ZZ-like days (ZZ or FC treated as ZZ)
    week_zz_counts = {}
    for weeknum, group in df.groupby('weeknum'):
        # count days that are ZZ or FC
        count = ((group['code'] == "ZZ") | (group['is_fc'] == True)).sum()
        week_zz_counts[weeknum] = int(count)
    df['week_zz_count'] = df['weeknum'].map(week_zz_counts)

    # Apply CZ transformation
    df['effective_code'] = df['code']
    for idx, row in df.iterrows():
        if row['in_vacs'] and (row['code'] == "ZZ" or row['is_fc'] == True):
            if row['week_zz_count'] >= 3:
                # ZZ becomes CZ; FC remains FC visually but for counting treat as CZ
                if row['is_fc']:
                    # keep FC visually but mark effective_code as CZ for counting
                    df.at[idx, 'effective_code'] = "CZ"
                else:
                    df.at[idx, 'effective_code'] = "CZ"
        # C4 remains C4, CX remains CX, TRA remains TRA, FC remains FC visually
    return df

def count_absences(df: pd.DataFrame):
    # Absence days are CX, CZ, C4, and FC when treated as CZ (effective_code)
    df = df.copy()
    abs_mask = df['effective_code'].isin(["CX", "CZ", "C4"])
    total = int(abs_mask.sum())
    return total

# -------------------------
# Optimization heuristic
# -------------------------
def optimize_placement(original_df: pd.DataFrame, cx_quota: int, c4_quota: int, parity_three_days_is_even: bool, zz_even_weeks: int, zz_odd_weeks: int):
    """
    Greedy heuristic:
    - Start from a copy of df with ZZ pattern applied.
    - Place CX days one by one: at each step, evaluate placing a CX on each TRA or ZZ day (not FC, not already CX/C4)
      and compute the delta in total absences after recomputing VACS/CZ. Choose the day with max delta.
    - After placing all CX, optionally place up to c4_quota C4 days where they increase total absences (rare).
    - This heuristic tries to maximize total absences given fixed CX quota.
    """
    df_base = original_df.copy()
    # ensure codes are normalized
    df_base.loc[df_base['code'].isnull(), 'code'] = DEFAULT_CODE
    # apply initial ZZ pattern
    df = apply_zz_pattern(df_base, zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)
    df = compute_vacs_and_transformations(df)
    df['effective_code'] = df['effective_code'].fillna(df['code'])
    best_df = df.copy()
    placed_cx = []
    placed_c4 = []

    # Helper to simulate placing a code and computing absences
    def simulate_with_placement(df_current, placements):
        df_sim = df_current.copy()
        for pdate, pcode in placements.items():
            df_sim.loc[df_sim['date'] == pdate, 'code'] = pcode
            if pcode == "FC":
                df_sim.loc[df_sim['date'] == pdate, 'is_fc'] = True
        df_sim = apply_zz_pattern(df_sim, zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)
        df_sim = compute_vacs_and_transformations(df_sim)
        df_sim['effective_code'] = df_sim['effective_code'].fillna(df_sim['code'])
        return df_sim, count_absences(df_sim)

    # initial absence count
    _, current_abs = simulate_with_placement(df_base, {})
    # Place CX greedily
    placements = {}
    for i in range(cx_quota):
        best_gain = -1
        best_date = None
        best_candidate_df = None
        # candidate days: those not already CX or C4 or FC (we can place CX on FC? business says FC has priority visual but considered ZZ; we avoid overriding FC)
        candidates = df_base.loc[~df_base['code'].isin(["CX", "C4"]) & (df_base['is_fc'] == False), 'date'].tolist()
        for cand in candidates:
            if cand in placements:
                continue
            trial_placements = placements.copy()
            trial_placements[cand] = "CX"
            df_trial, trial_abs = simulate_with_placement(df_base, trial_placements)
            gain = trial_abs - current_abs
            if gain > best_gain:
                best_gain = gain
                best_date = cand
                best_candidate_df = df_trial
        if best_date is None:
            break
        # commit
        placements[best_date] = "CX"
        df_base = df_base.copy()
        df_base.loc[df_base['date'] == best_date, 'code'] = "CX"
        current_abs = count_absences(compute_vacs_and_transformations(apply_zz_pattern(df_base, zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)))
        placed_cx.append(best_date)

    # Place C4 greedily (C4 ends VACS; sometimes useful to end a VACS early to allow another CX to start later; but here we only place C4 if it increases absences)
    for j in range(min(c4_quota, 4)):
        best_gain = -1
        best_date = None
        for cand in df_base.loc[~df_base['code'].isin(["C4"]) & (df_base['is_fc'] == False), 'date'].tolist():
            trial_df = df_base.copy()
            trial_df.loc[trial_df['date'] == cand, 'code'] = "C4"
            trial_df = apply_zz_pattern(trial_df, zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)
            trial_df = compute_vacs_and_transformations(trial_df)
            gain = count_absences(trial_df) - current_abs
            if gain > best_gain:
                best_gain = gain
                best_date = cand
        if best_date is None or best_gain <= 0:
            break
        df_base.loc[df_base['date'] == best_date, 'code'] = "C4"
        placed_c4.append(best_date)
        current_abs = count_absences(compute_vacs_and_transformations(apply_zz_pattern(df_base, zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)))

    # Final recompute
    df_final = apply_zz_pattern(df_base, zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)
    df_final = compute_vacs_and_transformations(df_final)
    df_final['effective_code'] = df_final['effective_code'].fillna(df_final['code'])
    return df_final, placed_cx, placed_c4

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Gestionnaire de calendrier de congés", layout="wide")

st.title("Gestionnaire de calendrier de congés")

# Sidebar: period selector and options
st.sidebar.header("Période et paramètres")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_month = st.date_input("Date de début (jour=1 pour sélectionner un mois)", value=date.today().replace(day=1))
with col2:
    show_two_months = st.sidebar.checkbox("Afficher 2 mois", value=False)

# ZZ selectors
st.sidebar.markdown("**Sélecteurs ZZ**")
parity_choice = st.sidebar.radio("Semaines à 3 jours ZZ sur :", ("Paires", "Impaire"))
parity_three_days_is_even = (parity_choice == "Paires")
# For flexibility allow user to set counts (2 or 3)
zz_even_weeks = st.sidebar.selectbox("ZZ jours semaine paire", options=[2,3], index=0 if parity_three_days_is_even else 1)
zz_odd_weeks = st.sidebar.selectbox("ZZ jours semaine impaire", options=[2,3], index=1 if parity_three_days_is_even else 0)

st.sidebar.markdown("**Compteurs**")
cx_quota = st.sidebar.number_input("Quota total CX à poser", min_value=0, max_value=31, value=3, step=1)
c4_quota = st.sidebar.number_input("Quota C4 (max 4 unités)", min_value=0, max_value=4, value=0, step=1)

# Load or init month(s)
months_to_show = 2 if show_two_months else 1
base_year = start_month.year
base_month = start_month.month

dfs = []
for m in range(months_to_show):
    dt = (start_month + relativedelta(months=m))
    key = month_key(dt.year, dt.month)
    loaded = load_month_data(key)
    if loaded is None:
        dfm = init_month_df(dt.year, dt.month)
    else:
        dfm = loaded
        # ensure columns exist
        if 'is_fc' not in dfm.columns:
            dfm['is_fc'] = False
    dfs.append((key, dfm))

# Provide a global control to reset month data
if st.sidebar.button("Réinitialiser mois affiché"):
    for key, _ in dfs:
        path = DATA_DIR / f"{key}.json"
        if path.exists():
            path.unlink()
    st.experimental_rerun()

# Main area: render months
for key, df in dfs:
    st.subheader(f"Mois : {key}")
    # allow marking FC days quickly: multiselect of dates
    fc_dates = st.multiselect(f"Marquer jours fériés (FC) pour {key}", options=[d.strftime("%Y-%m-%d") for d in df['date']], default=[d.strftime("%Y-%m-%d") for d in df.loc[df['is_fc']==True,'date']])
    df['is_fc'] = df['date'].apply(lambda d: d.strftime("%Y-%m-%d") in fc_dates)

    # Apply ZZ pattern and compute derived fields for display
    df_display = apply_zz_pattern(df.copy(), zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)
    df_display = compute_vacs_and_transformations(df_display)
    df_display['effective_code'] = df_display['effective_code'].fillna(df_display['code'])

    # Render calendar grid (weeks start Sunday)
    weeks = sunday_start_calendar(int(key.split("-")[0]), int(key.split("-")[1]))
    for week in weeks:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day.month != int(key.split("-")[1]):
                    st.write("")  # empty cell for other months
                    continue
                row = df_display.loc[df_display['date'] == day].iloc[0]
                # Visual priority: FC displayed prominently
                display_code = row['code']
                effective = row['effective_code']
                day_label = f"**{row['day']} - {row['weekday']}**"
                st.markdown(day_label)
                # Show current code and effective code
                st.write(f"**Code:** {display_code}  ")
                st.write(f"**Effectif:** {effective}  ")
                # selectbox to change code manually
                new_code = st.selectbox(f"Modifier {day}", options=CODES, index=CODES.index(display_code), key=f"{key}_{day}")
                # checkbox to mark FC
                is_fc = st.checkbox("FC", value=row['is_fc'], key=f"fc_{key}_{day}")
                # update df
                df.loc[df['date'] == day, 'code'] = new_code
                df.loc[df['date'] == day, 'is_fc'] = is_fc

    # Save month data after edits
    save_month_data(key, df)

    # Show summary counters for this month
    df_after = apply_zz_pattern(df.copy(), zz_even_weeks, zz_odd_weeks, parity_three_days_is_even)
    df_after = compute_vacs_and_transformations(df_after)
    df_after['effective_code'] = df_after['effective_code'].fillna(df_after['code'])
    total_abs = count_absences(df_after)
    st.info(f"**Total jours d'absence (sur la période affichée)** : {total_abs}")

# Global optimization controls
st.markdown("---")
st.header("Optimisation automatique")
st.write("Le mode optimisation place les CX et C4 (dans la limite des quotas) pour maximiser le total d'absences pendant les périodes VACS.")

if st.button("Lancer optimisation"):
    # Combine all months into one df for optimization and persistence
    combined = pd.concat([d for _, d in dfs], ignore_index=True)
    combined = combined.sort_values('date').reset_index(drop=True)
    # Run optimizer
    optimized_df, placed_cx, placed_c4 = optimize_placement(combined.copy(), int(cx_quota), int(c4_quota), parity_three_days_is_even, zz_even_weeks, zz_odd_weeks)
    # Persist results back to per-month files
    for key, _ in dfs:
        year, month = map(int, key.split("-"))
        mask = optimized_df['date'].apply(lambda d: d.year == year and d.month == month)
        df_month = optimized_df.loc[mask, ['date','day','weekday','code','is_fc','effective_code']].copy()
        # ensure 'code' column exists: optimized_df may have effective_code; prefer code if present
        if 'code' not in df_month.columns:
            df_month['code'] = df_month['effective_code']
        # Save: keep only date, code, is_fc
        df_to_save = df_month[['date','day','weekday','code','is_fc']].copy()
        save_month_data(key, df_to_save)
    st.success(f"Optimisation terminée. CX placés: {len(placed_cx)}; C4 placés: {len(placed_c4)}")
    if placed_cx:
        st.write("Dates CX placés :", ", ".join([d.strftime("%Y-%m-%d") for d in placed_cx]))
    if placed_c4:
        st.write("Dates C4 placés :", ", ".join([d.strftime("%Y-%m-%d") for d in placed_c4]))
    st.experimental_rerun()

st.markdown("---")
st.caption("Notes :\n- Les jours fériés (FC) sont marqués manuellement et restent visibles comme FC mais sont traités comme ZZ pour la logique CZ.\n- La persistance est locale dans le dossier calendar_data. Afficher 2 mois applique les mêmes règles sur la continuité entre mois.")

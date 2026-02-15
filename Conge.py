import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Tentative d'import de holidays avec gestion d'erreur gracieuse
try:
    import holidays
except ImportError:
    st.error("L'application est en cours de configuration. Veuillez patienter 30 secondes et rafraîchir la page (Fichier requirements.txt en cours d'installation).")
    st.stop()

# --- INITIALISATION ---
if 'selected_cx' not in st.session_state:
    st.session_state.selected_cx = []

st.set_page_config(layout="wide", page_title="OptiCongés V24")

# --- LOGIQUE MÉTIER ---

def get_fr_holidays(year):
    return holidays.France(years=year)

def apply_v24_logic(df, repos_p, repos_i):
    df['Type'] = "TRAVAIL"
    df['Label'] = "Travail"
    df['Color'] = "#ffffff"
    
    fr_holidays = get_fr_holidays(df['Date'].dt.year.unique().tolist())

    for i, row in df.iterrows():
        d = row['Date']
        # 1. Gestion des Fériés (Priorité Absolue)
        if d in fr_holidays:
            df.at[i, 'Type'] = "FC"
            df.at[i, 'Label'] = f"Férié ({fr_holidays.get(d)})"
            df.at[i, 'Color'] = "#f1c40f" # Jaune
            continue

        # 2. Gestion des Repos Théoriques (ZZ)
        is_even = d.isocalendar()[1] % 2 == 0
        day_name = d.strftime('%A')
        current_repos = repos_p if is_even else repos_i
        
        if day_name in current_repos:
            df.at[i, 'Type'] = "ZZ"
            df.at[i, 'Label'] = "Repos (ZZ)"
            df.at[i, 'Color'] = "#2ecc71" # Vert

    # 3. Injection des Congés (CX)
    for d_cx in st.session_state.selected_cx:
        idx = df[df['Date'].dt.date == d_cx].index
        if not idx.empty:
            df.at[idx[0], 'Type'] = "CX"
            df.at[idx[0], 'Label'] = "Congé Payé (CX)"
            df.at[idx[0], 'Color'] = "#3498db" # Bleu

    # 4. Règle du Forfait 5 Jours & V24
    df['Week'] = df['Date'].dt.isocalendar().week
    for (year, week), week_data in df.groupby([df['Date'].dt.year, 'Week']):
        # Un jour férié tombant sur un repos compte dans le quota des 3 jours
        # Mais on ne taxe que les ZZ (verts)
        repos_theoriques = week_data[week_data['Type'].isin(['ZZ', 'FC'])]
        has_cx = (week_data['Type'] == "CX").any()
        
        if len(repos_theoriques) >= 3 and has_cx:
            # Vérification Rupture V24 (si la semaine finit par CX -> TRAVAIL)
            types = week_data['Type'].tolist()
            is_v24_broken = (types[-1] == "TRAVAIL" and types[-2] == "CX")
            
            if not is_v24_broken:
                zz_only = week_data[week_data['Type'] == "ZZ"].index
                if not zz_only.empty:
                    df.at[zz_only[0], 'Type'] = "CZ"
                    df.at[zz_only[0], 'Label'] = "Forfait (CZ)"
                    df.at[zz_only[0], 'Color'] = "#e74c3c" # Rouge
    return df

# --- INTERFACE ---
st.title("📅 Gestionnaire de Cycle V24")

with st.sidebar:
    st.header("⚙️ Configuration")
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    rp = st.multiselect("Repos Semaine PAIRE", days, default=['Saturday', 'Sunday'])
    ri = st.multiselect("Repos Semaine IMPAIRE", days, default=['Monday', 'Saturday'])
    
    st.markdown("---")
    dates = st.date_input("Période", [datetime.now(), datetime.now() + timedelta(days=30)])

col_l, col_r = st.columns([1, 2])

with col_l:
    st.subheader("Action")
    new_cx = st.date_input("Ajouter un congé (CX)")
    if st.button("Valider le congé"):
        if new_cx not in st.session_state.selected_cx:
            st.session_state.selected_cx.append(new_cx)
            st.rerun()
    if st.button("Réinitialiser"):
        st.session_state.selected_cx = []
        st.rerun()

if len(dates) == 2:
    df_calc = pd.DataFrame({'Date': pd.date_range(dates[0], dates[1])})
    df_res = apply_v24_logic(df_calc, rp, ri)
    
    with col_r:
        st.subheader("Planning")
        def style_df(row):
            return [f'background-color: {row.Color}; color: black'] * len(row)
        
        display_df = df_res[['Date', 'Label']].copy()
        display_df['Date'] = display_df['Date'].dt.strftime('%d/%m (%a)')
        st.table(display_df.style.apply(style_df, axis=1))

    # Stats
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("CX Posés", len(st.session_state.selected_cx))
    c2.metric("Taxes CZ", len(df_res[df_res['Type'] == "CZ"]))
    c3.metric("Total Débité", len(st.session_state.selected_cx) + len(df_res[df_res['Type'] == "CZ"]))

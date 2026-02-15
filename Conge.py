import streamlit as st
import pandas as pd
import holidays
from datetime import datetime, timedelta

# --- 1. INITIALISATION DES ÉTATS (Sécurité Streamlit Cloud) ---
if 'repos_pair' not in st.session_state:
    st.session_state.repos_pair = ['Saturday', 'Sunday']
if 'repos_impair' not in st.session_state:
    st.session_state.repos_impair = ['Saturday', 'Sunday']
if 'selected_cx' not in st.session_state:
    st.session_state.selected_cx = []

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="OptiCongés V24", page_icon="📅")

# --- 3. LOGIQUE MÉTIER ---

def get_holiday_name(date):
    """Récupère le nom du jour férié français s'il existe."""
    fr_holidays = holidays.France(years=date.year)
    return fr_holidays.get(date)

def get_is_even(date):
    """Vérifie si la semaine ISO est paire."""
    return date.isocalendar()[1] % 2 == 0

def apply_v24_logic(df):
    """
    Applique la cascade de priorités :
    1. Férié (FC) - Jaune
    2. Repos (ZZ) - Vert
    3. Congé (CX) - Bleu
    4. Forfait (CZ) - Rouge (Si >= 3 repos + 1 CX, sauf si V24 brise la règle)
    """
    df['Type'] = "TRAVAIL"
    df['Label'] = "Travail"
    df['Color'] = "#ffffff"
    
    # Étape A : Marquage des bases (Fériés et Repos selon Profil)
    for i, row in df.iterrows():
        d = row['Date']
        is_even = get_is_even(d)
        day_name = d.strftime('%A')
        holiday = get_holiday_name(d)
        
        repos_config = st.session_state.repos_pair if is_even else st.session_state.repos_impair
        
        if holiday:
            df.at[i, 'Type'] = "FC"
            df.at[i, 'Label'] = f"Férié ({holiday})"
            df.at[i, 'Color'] = "#f1c40f" # Jaune
        elif day_name in repos_config:
            df.at[i, 'Type'] = "ZZ"
            df.at[i, 'Label'] = "Repos (ZZ)"
            df.at[i, 'Color'] = "#2ecc71" # Vert
            
    # Étape B : Injection des Congés (CX) manuels
    for d_cx in st.session_state.selected_cx:
        # On convertit en datetime pour la comparaison
        d_cx_dt = pd.to_datetime(d_cx)
        idx = df[df['Date'] == d_cx_dt].index
        if not idx.empty:
            df.at[idx[0], 'Type'] = "CX"
            df.at[idx[0], 'Label'] = "Congé Payé (CX)"
            df.at[idx[0], 'Color'] = "#3498db" # Bleu

    # Étape C : La Règle du Forfait (Transformation ZZ -> CZ)
    # Analyse par bloc de semaine ISO
    df['Week'] = df['Date'].dt.isocalendar().week
    df['Year'] = df['Date'].dt.isocalendar().year
    
    for (y, w), week_data in df.groupby(['Year', 'Week']):
        indices = week_data.index
        # On compte les jours de "repos" au sens large (ZZ + FC)
        repos_count = len(week_data[week_data['Type'].isin(['ZZ', 'FC'])])
        has_cx = (week_data['Type'] == 'CX').any()
        
        # Condition Forfait : 3 repos minimum et au moins 1 jour de congé posé
        if repos_count >= 3 and has_cx:
            # --- Règle V24 (Rupture du forfait) ---
            # Si la semaine finit par CX puis Travail (RAT), on peut potentiellement casser le forfait
            is_v24_broken = False
            types_list = week_data['Type'].tolist()
            if len(types_list) >= 2:
                if types_list[-1] == "TRAVAIL" and types_list[-2] == "CX":
                    is_v24_broken = True
            
            if not is_v24_broken:
                # Transformer le PREMIER ZZ disponible en CZ (Taxe)
                zz_indices = week_data[week_data['Type'] == 'ZZ'].index
                if not zz_indices.empty:
                    target_idx = zz_indices[0]
                    df.at[target_idx, 'Type'] = "CZ"
                    df.at[target_idx, 'Label'] = "Forfait (CZ)"
                    df.at[target_idx, 'Color'] = "#e74c3c" # Rouge

    return df

# --- 4. INTERFACE UTILISATEUR ---

st.title("🚀 Optimiseur de Cycle - Règle V24")
st.info("Priorités : Férié (Jaune) > Forfait (Rouge) > Congé (Bleu) > Repos (Vert)")

with st.sidebar:
    st.header("⚙️ Profil de Repos")
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    st.session_state.repos_pair = st.multiselect("Repos (Semaine Paire)", days_list, default=['Saturday', 'Sunday'])
    st.session_state.repos_impair = st.multiselect("Repos (Semaine Impaire)", days_list, default=['Monday', 'Saturday'])
    
    st.markdown("---")
    st.header("📅 Période")
    today = datetime.now()
    d_range = st.date_input("Choisir les dates", [today, today + timedelta(days=60)])

# Zone de saisie des congés
col_input, col_stats = st.columns([2, 1])

with col_input:
    st.subheader("➕ Poser un jour de congé (CX)")
    cx_date = st.date_input("Date du congé", key="picker")
    c1, c2 = st.columns(2)
    if c1.button("Ajouter le Congé"):
        if cx_date not in st.session_state.selected_cx:
            st.session_state.selected_cx.append(cx_date)
            st.rerun()
    if c2.button("🗑️ Vider tout"):
        st.session_state.selected_cx = []
        st.rerun()

# Calcul du DataFrame
if len(d_range) == 2:
    dates = pd.date_range(d_range[0], d_range[1])
    df_base = pd.DataFrame({'Date': dates})
    df_result = apply_v24_logic(df_base)

    # Affichage des statistiques
    with col_stats:
        st.subheader("📊 Bilan")
        total_cx = len(st.session_state.selected_cx)
        total_cz = len(df_result[df_result['Type'] == "CZ"])
        st.metric("Congés posés (CX)", total_cx)
        st.metric("Taxe prélevée (CZ)", total_cz, delta="-1 jour", delta_color="inverse")
        st.write(f"**Total débité : {total_cx + total_cz} jours**")

    # Affichage du tableau final
    st.markdown("---")
    
    # Formatage pour l'affichage
    df_display = df_result.copy()
    df_display['Jour'] = df_display['Date'].dt.strftime('%d/%m/%Y (%a)')
    df_display = df_display[['Jour', 'Label']]

    def color_row(row):
        # On récupère la couleur depuis le dataframe d'origine
        color = df_result.loc[row.name, 'Color']
        return [f'background-color: {color}; color: black'] * len(row)

    st.table(df_display.style.apply(color_row, axis=1))

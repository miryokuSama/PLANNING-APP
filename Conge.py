import streamlit as st
import pandas as pd
import holidays
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="OptiCongés V24", page_icon="📅")

# --- LOGIQUE MÉTIER ---

def get_holiday_name(date):
    fr_holidays = holidays.France(years=date.year)
    return fr_holidays.get(date)

def get_is_even(date):
    return date.isocalendar()[1] % 2 == 0

def apply_v24_logic(df):
    """
    Applique la transformation ZZ -> CZ (Forfait 5 jours)
    et gère la rupture du RAT (V24).
    """
    df['Type'] = "TRAVAIL"
    df['Color'] = "#ffffff" # Blanc par défaut
    
    # 1. Marquage initial (Fériés et Repos Théoriques)
    for i, row in df.iterrows():
        d = row['Date']
        is_even = get_is_even(d)
        day_name = d.strftime('%A')
        holiday = get_holiday_name(d)
        
        # Repos théorique selon profil
        repos_config = st.session_state.repos_pair if is_even else st.session_state.repos_impair
        
        if holiday:
            df.at[i, 'Type'] = "FC"
            df.at[i, 'Label'] = f"Férié ({holiday})"
            df.at[i, 'Color'] = "#f1c40f" # Jaune
        elif day_name in repos_config:
            df.at[i, 'Type'] = "ZZ"
            df.at[i, 'Label'] = "Repos"
            df.at[i, 'Color'] = "#2ecc71" # Vert
            
    # 2. Injection des Congés (CX) posés par l'utilisateur
    for d_cx in st.session_state.selected_cx:
        idx = df[df['Date'] == d_cx].index
        if not idx.empty:
            df.at[idx[0], 'Type'] = "CX"
            df.at[idx[0], 'Label'] = "Congé Payé"
            df.at[idx[0], 'Color'] = "#3498db" # Bleu

    # 3. Règle du Forfait & V24 (Analyse par semaine ISO)
    for (year, week), week_data in df.groupby([df['Date'].dt.year, df['Date'].dt.isocalendar().week]):
        indices = week_data.index
        # Compter les repos (ZZ ou FC tombant sur un repos théorique)
        # Note : Un FC est prioritaire à l'affichage mais compte comme un repos pour le calcul du quota
        repos_count = len(week_data[week_data['Type'].isin(['ZZ', 'FC'])])
        has_cx = (week_data['Type'] == 'CX').any()
        
        # Condition Forfait : >= 3 repos ET au moins 1 CX
        if repos_count >= 3 and has_cx:
            # Recherche de la rupture V24 : 
            # Si la semaine se termine par ZZ -> ZZ -> CX -> RAT(Travail)
            # On vérifie si les derniers jours empêchent la taxe
            is_v24_broken = False
            last_days = week_data['Type'].tolist()
            # Simple simulation de la règle de rupture V24
            if len(last_days) >= 3 and last_days[-1] == "TRAVAIL" and last_days[-2] == "CX":
                 is_v24_broken = True
            
            if not is_v24_broken:
                # Transformer le PREMIER ZZ de la semaine en CZ (Rouge)
                zz_indices = week_data[week_data['Type'] == 'ZZ'].index
                if not zz_indices.empty:
                    df.at[zz_indices[0], 'Type'] = "CZ"
                    df.at[zz_indices[0], 'Label'] = "Taxe Forfait (CZ)"
                    df.at[zz_indices[0], 'Color'] = "#e74c3c" # Rouge

    return df

# --- INTERFACE STREAMLIT ---

st.title("📅 Optimiseur de Congés - Système V24")
st.markdown("---")

# Sidebar : Configuration des profils
with st.sidebar:
    st.header("⚙️ Configuration")
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    st.subheader("Semaine PAIRE")
    st.session_state.repos_pair = st.multiselect("Repos fixes (P)", days_list, default=['Saturday', 'Sunday'], key="p_repos")
    
    st.subheader("Semaine IMPAIRE")
    st.session_state.repos_impair = st.multiselect("Repos fixes (I)", days_list, default=['Saturday', 'Sunday'], key="i_repos")
    
    st.markdown("---")
    date_range = st.date_input("Période d'analyse", [datetime.now(), datetime.now() + timedelta(days=30)])
    
    if 'selected_cx' not in st.session_state:
        st.session_state.selected_cx = []

# Main Layout
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("🛠️ Poser des congés")
    new_cx = st.date_input("Choisir une date de CX", key="cx_picker")
    if st.button("Ajouter le CX"):
        if new_cx not in st.session_state.selected_cx:
            st.session_state.selected_cx.append(new_cx)
    
    if st.button("Réinitialiser"):
        st.session_state.selected_cx = []
        st.rerun()

    st.write("**Congés posés :**", len(st.session_state.selected_cx))

with col2:
    if len(date_range) == 2:
        start_date, end_date = date_range
        dates = pd.date_range(start_date, end_date)
        df_cal = pd.DataFrame({'Date': dates})
        
        # Application du moteur de règles
        df_final = apply_v24_logic(df_cal)
        
        # Affichage visuel (Tableau stylisé)
        st.subheader("🗓️ Visualisation du Cycle")
        
        def color_cells(row):
            return [f'background-color: {row.Color}; color: black' for _ in row]

        # Ajout des badges DJT / RAT (Simulation simple sur le bloc)
        # On marque le début et la fin de la période de repos
        
        styled_df = df_final[['Date', 'Type', 'Label']].copy()
        styled_df['Date'] = styled_df['Date'].dt.strftime('%d/%m/%Y (%a)')
        
        st.table(df_final.style.apply(color_cells, axis=1))

# --- RÉSUMÉ DES COMPTEURS ---
st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total Congés (CX)", len(st.session_state.selected_cx))
with c2:
    count_cz = len(df_final[df_final['Type'] == "CZ"])
    st.metric("Taxe Forfait (CZ)", count_cz, delta_color="inverse")
with c3:
    total_off = len(df_final[df_final['Type'].isin(['ZZ', 'CX', 'CZ', 'FC'])])
    st.metric("Jours de Repos Réels", total_off)

st.info("💡 **Rappel V24** : Si vous reprenez le travail (RAT) juste après un bloc de repos incluant un CX, vérifiez que la séquence casse bien le forfait 5 jours.")

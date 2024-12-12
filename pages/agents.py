import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Agents",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# URL de base pour l'API
API_URL = "http://localhost:8000/"

# Fonction pour récupérer les données générales des agents
def fetch_agents_data(api_url, month):
    """
    Récupère les données des agents pour un mois donné.
    """
    try:
        response = requests.get(f"{api_url}/agents/{month}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la récupération des données des agents : {e}")
        return None

# Fonction pour récupérer les données du meilleur agent
def fetch_top_agent(api_url, month):
    """
    Récupère les données du meilleur agent pour un mois donné.
    """
    try:
        response = requests.get(f"{api_url}/top-agent/sales/{month}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la récupération du meilleur agent : {e}")
        return None

# Fonction pour normaliser les données imbriquées
def normalize_data(data):
    """
    Transforme les données imbriquées en un format plat.
    """
    normalized_data = []
    for item in data:
        flat_item = {
            "agent_name": item.get("agent", {}).get("agent_name", "Inconnu"),
            "won_deals": item.get("metrics", {}).get("won_deals", 0),
            "lost_deals": item.get("metrics", {}).get("lost_deals", 0),
            "total_sales": item.get("metrics", {}).get("total_sales", 0),
        }
        normalized_data.append(flat_item)
    return normalized_data

# Fonction pour transformer les données en DataFrame
def create_agents_dataframe(data):
    """
    Transforme les données des agents en un DataFrame pandas.
    """
    if not data:
        st.error("Aucune donnée disponible.")
        return pd.DataFrame()

    # Debug: Affichez les données brutes pour analyse
    st.write("Données brutes :", data)

    # Normaliser les données si elles sont imbriquées
    if isinstance(data, list) and isinstance(data[0], dict) and "agent" in data[0]:
        data = normalize_data(data)
        st.write("Données normalisées :", data)

    df = pd.DataFrame(data)

    # Vérification des colonnes nécessaires
    required_columns = {'agent_name', 'won_deals', 'lost_deals', 'success_rate', 'total_sales'}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        st.warning(f"Colonnes manquantes : {', '.join(missing_columns)}. Elles seront initialisées avec des valeurs par défaut.")
        for col in missing_columns:
            df[col] = 0  # Initialiser les colonnes manquantes

    # Calcul du taux de succès si nécessaire
    if 'success_rate' not in df.columns:
        df['success_rate'] = (df['won_deals'] / (df['won_deals'] + df['lost_deals'])).fillna(0) * 100

    return df

# Fonction principale du tableau de bord
def main():
    st.title("📊 Dashboard de Performance des Agents")

    # Sélecteur de mois
    month = st.selectbox(
        "Sélectionnez un mois",
        options=range(1, 11),
        format_func=lambda x: [
            'Mars', 'Avril', 'Mai', 'Juin','Juillet', 
            'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ][x - 1]
    )

    # Récupération des données des agents
    agents_data = fetch_agents_data(API_URL, month)
    df_agents = create_agents_dataframe(agents_data)

    # Vérification des données
    if df_agents.empty:
        st.error("Aucune donnée d'agent disponible.")
        return

    # Récupération du meilleur agent
    top_agent_data = fetch_top_agent(API_URL, month)

    # Metrics principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nombre d'Agents", len(df_agents))
    with col2:
        st.metric("Taux de Conversion Moyen", f"{df_agents['success_rate'].mean():.2f}%")
    with col3:
        st.metric("Ventes Totales", f"{df_agents['total_sales'].sum():,}")
    with col4:
        if top_agent_data:
            st.metric("Meilleur Agent", f"{top_agent_data['top_agent']['agent_name']} : {top_agent_data['top_agent']['total_sales']:,}")

    # Visualisation des ventes par région
    st.subheader(f"Performances pour le mois de {['Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][month-1]}")
    if 'region' in df_agents.columns:
        region_sales = df_agents.groupby('region')['total_sales'].sum()
        fig_region = px.pie(
            values=region_sales.values,
            names=region_sales.index,
            title="Répartition des Ventes par Région"
        )
        st.plotly_chart(fig_region)

    # Leaderboard des agents
    st.subheader("Leaderboard des Agents")
    top_agents = df_agents.nlargest(10, 'total_sales')
    fig_top_agents = px.bar(
        top_agents,
        x='agent_name',
        y='total_sales',
        title="Top 10 Agents par Ventes",
        labels={'total_sales': 'Ventes', 'agent_name': 'Agent'}
    )
    st.plotly_chart(fig_top_agents)

    # Tableau des détails des agents
    st.subheader("Détails des Agents")
    columns_to_show = ['agent_name', 'region', 'won_deals', 'success_rate', 'total_sales']
    df_display = df_agents[columns_to_show].copy() if all(col in df_agents for col in columns_to_show) else df_agents

    # Formatage conditionnel
    if 'success_rate' in df_display.columns:
        df_display['success_rate'] = df_display['success_rate'].apply(lambda x: f"{x:.2f}%")
    if 'total_sales' in df_display.columns:
        df_display['total_sales'] = df_display['total_sales'].apply(lambda x: f"{x:,}")

    st.dataframe(df_display, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
import streamlit as st
import requests

# Configurer la page
st.set_page_config(
    page_title="Tableau de Bord des Agents",
    page_icon="👨‍💼​",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ajout du style CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f0f0;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stMetric > div {
        color: black !important;
    }
</style>
""", unsafe_allow_html=True)

# Mapper les noms de mois à leurs numéros (commençant à partir de mars)
MOIS_NOMS = {
    "Mars": "03",
    "Avril": "04",
    "Mai": "05",
    "Juin": "06",
    "Juillet": "07",
    "Août": "08",
    "Septembre": "09",
    "Octobre": "10",
    "Novembre": "11",
    "Décembre": "12",
    "Janvier": "01",
    "Février": "02"
}

def get_top_agent_data(month):
    """Appelle l'API pour obtenir les données du meilleur agent."""
    url = f"http://localhost:8000/top-agent/sales/{month}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()  # Retourne les données sous forme de dict
    else:
        st.error("Erreur lors de la récupération des données du meilleur agent.")
        return None

def get_conversion_rate_data(month):
    """Appelle l'API pour obtenir le taux de conversion mensuel."""
    url = f"http://localhost:8000/sales/conversion_rate/{month}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()  # Retourne les données sous forme de dict
    else:
        st.error("Erreur lors de la récupération du taux de conversion.")
        return None

def agents_dashboard():
    st.title("Tableau de Bord des Agents")
    
    # Sélecteur de mois avec noms
    mois_selectionne = st.selectbox(
        "Sélectionnez un mois :",
        options=list(MOIS_NOMS.keys())  # Affiche les noms des mois
    )
    
    # Récupérer le numéro de mois sélectionné
    mois = MOIS_NOMS[mois_selectionne]
    
    # Récupérer les données via l'API
    meilleur_agent = get_top_agent_data(mois)
    conversion_rate_data = get_conversion_rate_data(mois)
    
    # Afficher les données récupérées
    col1, col2, col3 = st.columns(3)
    
    if meilleur_agent:
        with col1:
            st.subheader("Meilleur Agent")
            st.metric(label="Nom", value=meilleur_agent['name'])
            st.metric(label=f"Taux de Conversion de {meilleur_agent['name']}", 
                      value=f"{meilleur_agent['conversion_rate']}%")
    
    if conversion_rate_data:
        with col2:
            st.subheader("Taux de Conversion")
            taux_conversion = conversion_rate_data.get('conversion_rate', 0)
            st.metric(label="Conversion Moyenne", value=f"{taux_conversion:.2f}%")
    
    with col3:
        st.subheader("Temps Moyen de Vente")
        # Placeholder pour d'autres données si disponibles via l'API
        st.metric(label="Durée Moyenne", value="N/A")
    
    # Tableau des agents (à implémenter si l'API fournit ces données)
    st.subheader("Leaderboard des Agents")
    st.info("Le tableau des agents sera ajouté lorsque l'API fournira ces données.")

def main():
    agents_dashboard()

if __name__ == "__main__":
    main()

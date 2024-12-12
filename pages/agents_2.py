import streamlit as st
import pandas as pd
import random

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

def generate_agent_data(num_agents=10):
    """Génère des données fictives pour les agents"""
    agents = [
        "Alice Dupont", "Bernard Martin", "Claire Leroy", 
        "David Rousseau", "Emma Dubois", "François Petit", 
        "Géraldine Cohen", "Henri Moreau", "Isabelle Laurent", 
        "Jean Durand"
    ]
    
    data = []
    for agent in agents:
        deals_total = random.randint(50, 200)
        deals_won = random.randint(30, deals_total)
        deals_loose = deals_total - deals_won
        revenue = random.randint(10000, 50000)
        
        data.append({
            "Nom": agent,
            "Deals Total": deals_total,
            "Deals Won": deals_won,
            "Deals Loose": deals_loose,
            "Taux de Conversion": round(deals_won / deals_total * 100, 2),
            "Temps Moyen de Vente (jours)": round(random.uniform(1, 30), 2),
            "Revenue (€)": revenue
        })
    
    return pd.DataFrame(data)

def agents_dashboard():
    st.title("Tableau de Bord des Agents")
    
    # Générer des données fictives
    df_agents = generate_agent_data()
    
    # Meilleur agent
    meilleur_agent = df_agents.loc[df_agents['Taux de Conversion'].idxmax()]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Meilleur Agent")
        st.metric(label="Nom", value=meilleur_agent['Nom'])
        st.metric(label=f"Taux de Conversion de {meilleur_agent['Nom']}", 
                  value=f"{meilleur_agent['Taux de Conversion']}%")
    
    with col2:
        st.subheader("Taux de Conversion")
        taux_conversion_moyen = df_agents['Taux de Conversion'].mean()
        st.metric(label="Conversion Moyenne", 
                  value=f"{taux_conversion_moyen:.2f}%")
    
    with col3:
        st.subheader("Temps Moyen de Vente")
        temps_moyen_vente = df_agents['Temps Moyen de Vente (jours)'].mean()
        st.metric(label="Durée Moyenne", 
                  value=f"{temps_moyen_vente:.2f} jours")
    
    # Leaderboard des agents
    st.subheader("Leaderboard des Agents")
    
    # Appliquer un style à la DataFrame pour aligner les chiffres correctement
    styled_df = df_agents[['Nom', 'Deals Total', 'Deals Won', 'Deals Loose', 'Taux de Conversion', 'Revenue (€)']].style.format(
        {"Revenue (€)": "{:,.0f}€", "Taux de Conversion": "{:.2f}%"}
    ).set_properties(
        **{'text-align': 'left'}, subset=['Nom']
    )
    
    st.dataframe(styled_df, use_container_width=True)

def main():
    agents_dashboard()

if __name__ == "__main__":
    main()
import streamlit as st

# Titre principal de l'application
st.title("Tableau de Bord")

# Accueil
st.write("Bienvenue dans le tableau de bord. Utilisez la barre latérale pour naviguer entre les pages.")

# Détection automatique des pages dans le dossier `pages`
st.sidebar.title("Navigation")
st.sidebar.info("Utilisez la barre latérale pour accéder aux différentes pages.")
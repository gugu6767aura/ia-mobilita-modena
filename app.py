import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd

# 1. CONFIGURAZIONE DELLA PAGINA
st.set_page_config(layout="wide", page_title="Assistente IA Mobilità - Modena", page_icon="🚌")

st.title("🚌 Assistente IA Mobilità - Modena")
st.markdown("---")

# 2. STRUTTURA A COLONNE SUPERIORI (Assistente IA & Tabellone Live)
col_top1, col_top2 = st.columns([1, 1])

with col_top1:
    st.subheader("🤖 Assistente IA")
    user_query = st.text_input("Domanda sulle linee 1-13:", placeholder="Es: Quale bus prendo per andare in stazione?")
    if st.button("Chiedi"):
        if user_query:
            st.info("L'assistente IA sta elaborando la risposta per la tua rotta...")
        else:
            st.warning("Inserisci una domanda prima di inviare.")

with col_top2:
    st.subheader("📊 Tabellone Live")
    # Simulazione dati tabellone come da tuo screenshot
    data_tabellone = {
        "Linea": ["1B", "2A"],
        "Direzione": ["Ariete", "San Damaso"],
        "Stato": ["In Orario 🔵", "+4 min 🔴"],
        "Prossima Fermata": ["Autostazione", "Via Campi"]
    }
    df_tabellone = pd.DataFrame(data_tabellone)
    st.dataframe(df_tabellone, use_container_width=True, hide_index=True)

st.markdown("---")

# 3. STRUTTURA A COLONNE INFERIORI (Percorso, Mappa Live, Gestione Fermate)
col_bot1, col_bot2, col_bot3 = st.columns([1, 1.2, 1])

with col_bot1:
    st.subheader("🗺️ Percorso")
    partenza = st.text_input("📍 Partenza:", value="Viale Muratori")
    arrivo = st.text_input("📍 Arrivo:", value="Via Giardini")
    
    if st.button("Calcola Percorso"):
        st.success("🗺️ **Trovato!** Cammina a Piazzale Risorgimento, prendi il bus **1B** fino a **Giardini Donatello**.")
        st.link_button("🌐 Apri e Naviga su Google Maps", "https://google.com")

with col_bot2:
    st.subheader("🗺️ Mappa Live")
    # Centro di Modena coordinata approssimativa
    mappa_modena = folium.Map(location=[44.643, 10.925], zoom_start=14, tiles="OpenStreetMap")
    
    # Esempi di marker simulati sulla mappa
    folium.Marker([44.645, 10.922], popup="Autostazione", icon=folium.Icon(color="blue", icon="bus", prefix="fa")).add_to(mappa_modena)
    folium.Marker([44.647, 10.932], popup="Stazione FS", icon=folium.Icon(color="blue", icon="bus", prefix="fa")).add_to(mappa_modena)
    folium.Marker([44.634, 10.916], popup="Via Giardini", icon=folium.Icon(color="green", icon="info-sign")).add_to(mappa_modena)
    
    # Rendering della mappa dentro Streamlit
    st_folium(mappa_modena, width=500, height=350, returned_objects=[])

with col_bot3:
    st.subheader("⚙️ Gestione Fermate")
    nome_fermata = st.text_input("Nome Fermata:", placeholder="Inserisci nome...")
    latitudine = st.number_input("Latitudine:", value=44.64000, format="%.5f")
    longitudine = st.number_input("Longitudine:", value=10.91610, format="%.5f")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ Aggiungi"):
            st.toast(f"Fermata '{nome_fermata}' salvata!")
    with col_btn2:
        if st.button("🔄 Ripristina Predefinite"):
            st.toast("Database fermate ripristinato.")

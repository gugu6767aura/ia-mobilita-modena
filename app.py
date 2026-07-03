import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

# 1. CONFIGURAZIONE INTERFACCIA (Stile Mockup Wide)
st.set_page_config(layout="wide", page_title="Assistente IA Mobilità - Modena", page_icon="🚌")

st.title("🚌 Assistente IA Mobilità - Modena")
st.markdown("---")

# Tentativo di importare il super database che hai creato
try:
    from dati_linee import DATABASE_LINEE, COLORI_LINEE
except ImportError:
    st.error("⚠️ Errore: Assicurati che il file 'dati_linee.py' sia nella stessa cartella di 'app.py'")
    st.stop()

# 2. GRIGLIA SUPERIORE (Assistente IA & Tabellone Live come da tuo mockup)
col_top1, col_top2 = st.columns(2)

with col_top1:
    st.subheader("🤖 Assistente IA")
    user_query = st.text_input("Domanda sulle linee urbane:", placeholder="Es: Quale bus prendo per andare in ospedale?")
    if st.button("Chiedi"):
        if user_query:
            st.info("L'assistente IA sta elaborando la rotta ottimale...")
        else:
            st.warning("Inserisci una domanda prima di inviare.")

with col_top2:
    st.subheader("📊 Tabellone Live")
    data_tabellone = {
        "Linea": ["1", "7", "13"],
        "Direzione": ["Marinuzzi", "Gramsci", "Baggiovara"],
        "Stato": ["+2 min 🔴", "In Orario 🔵", "-1 min 🟢"],
        "Prossima Fermata": ["Autostazione", "Stazione FS", "Direzionale 70"]
    }
    st.dataframe(pd.DataFrame(data_tabellone), use_container_width=True, hide_index=True)

st.markdown("---")

# 3. GRIGLIA INFERIORE (Percorso, Mappa Live, Gestione Fermate)
col_bot1, col_bot2, col_bot3 = st.columns([1, 1.2, 1])

# --- COLONNA 3: GESTIONE FERMATE (Menu a Cascata Interattivi) ---
with col_bot3:
    st.subheader("⚙️ Gestione Fermate")
    
    # Menu 1: Selezione della Linea attiva (Estrae le chiavi dal tuo database)
    lista_linee = list(DATABASE_LINEE.keys())
    linea_selezionata = st.selectbox("1. Seleziona Linea:", options=lista_linee)
    
    # Menu 2: Selezione Direzione (Mappata su "andata" o "ritorno" in minuscolo)
    direzione_interfaccia = st.radio("2. Direzione della Corsa:", options=["Andata", "Ritorno"], horizontal=True)
    chiave_direzione = direzione_interfaccia.lower()
    
    # Estrazione dinamica delle fermate in base alla linea e direzione scelta
    lista_fermate = DATABASE_LINEE[linea_selezionata][chiave_direzione]
    nomi_fermate = [f["nome"] for f in lista_fermate]
    
    # Menu 3: Selezione della singola fermata reale di Modena
    fermata_scelta = st.selectbox(f"3. Fermata Attiva ({direzione_interfaccia}):", options=nomi_fermate)
    
    # Recupero coordinate della fermata attiva per riempire i campi di testo
    dati_fermata = next(f for f in lista_fermate if f["nome"] == fermata_scelta)
    lat_attiva = dati_fermata["lat"]
    lon_attiva = dati_fermata["lon"]
    
    # Output campi bloccati (compilati in automatico come nel tuo mockup)
    st.text_input("Nome Fermata Selezionata:", value=fermata_scelta, disabled=True)
    st.number_input("Latitudine Geografica:", value=lat_attiva, format="%.5f", disabled=True)
    st.number_input("Longitudine Geografica:", value=lon_attiva, format="%.5f", disabled=True)

# --- COLONNA 1: MODULO PERCORSO ---
with col_bot1:
    st.subheader("🗺️ Percorso")
    partenza = st.text_input("📍 Punto A (Partenza):", value="Viale Muratori")
    arrivo = st.text_input("📍 Punto B (Destinazione):", value="Via Giardini")
    
    if st.button("Calcola Percorso Ottimale"):
        st.success("🗺️ **Rotta Trovata!** Cammina fino a Muratori, prendi la **Linea 6** o **11** verso Via Giardini.")
        st.link_button("🌐 Apri Navigatore Google Maps", f"https://google.com{lat_attiva},{lon_attiva}")

# --- COLONNA 2: MAPPA LIVE (Reattiva ai Menu della Colonna 3) ---
with col_bot2:
    st.subheader("🗺️ Mappa Live")
    
    # La mappa si centra e si sposta da sola sulla fermata cliccata nel menu
    mappa_modena = folium.Map(location=[lat_attiva, lon_attiva], zoom_start=14, tiles="CartoDB positron")
    
    # Disegna la linea stradale continua (PolyLine) unendo tutte le fermate della corsa
    coordinate_tracciato = [[f["lat"], f["lon"]] for f in lista_fermate]
    colore_linea = COLORI_LINEE.get(linea_selezionata, "#3498db")
    
    folium.PolyLine(
        locations=coordinate_tracciato,
        color=colore_linea,
        weight=4,
        opacity=0.85
    ).add_to(mappa_modena)
    
    # Posiziona i Marker: Stella Rossa per la fermata scelta nel menu, Bus Blu per le altre
    for fermata in lista_fermate:
        is_selected = (fermata["nome"] == fermata_scelta)
        
        folium.Marker(
            location=[fermata["lat"], fermata["lon"]],
            popup=f"<b>🚌 {fermata['nome']}</b><br><small>{linea_selezionata}</small>",
            tooltip=fermata["nome"],
            icon=folium.Icon(
                color="red" if is_selected else "blue", 
                icon="star" if is_selected else "bus", 
                prefix="fa"
            )
        ).add_to(mappa_modena)
        
    # Rendering finale della mappa nello spazio centrale
    st_folium(mappa_modena, width=500, height=380, key=f"map_{linea_selezionata}_{chiave_direzione}", returned_objects=[])

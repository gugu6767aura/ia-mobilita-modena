import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

# 1. CONFIGURAZIONE INTERFACCIA WIDE
st.set_page_config(layout="wide", page_title="Assistente IA Mobilità - Modena", page_icon="🚌")

st.title("🚌 Assistente IA Mobilità - Modena")
st.markdown("---")

# Carichiamo il database esterno delle linee
try:
    from dati_linee import DATABASE_LINEE, COLORI_LINEE
except ImportError:
    st.error("⚠️ Errore: Manca il file 'dati_linee.py' nella stessa cartella.")
    st.stop()

# Estraiamo l'elenco di TUTTE le fermate uniche di Modena per i menu di viaggio
tutte_le_fermate = set()
for linea_nome, direzioni in DATABASE_LINEE.items():
    for dir_nome in ["andata", "ritorno"]:
        for f in direzioni.get(dir_nome, []):
            tutte_le_fermate.add(f["nome"])
elenco_fermate_ordinato = sorted(list(tutte_le_fermate))

# 2. GRIGLIA SUPERIORE (Assistente IA & Tabellone Live)
col_top1, col_top2 = st.columns(2)

with col_top1:
    st.subheader("🤖 Assistente IA")
    user_query = st.text_input("Domanda sulle linee urbane:", placeholder="Es: Quale bus prendo per andare in ospedale?")
    if st.button("Chiedi"):
        if user_query:
            st.info("L'assistente IA sta elaborando la rotta...")
        else:
            st.warning("Inserisci una domanda.")

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

# --- COLONNA 3: GESTIONE FERMATE (Menu a tendina a cascata) ---
with col_bot3:
    st.subheader("⚙️ Gestione Fermate")
    
    lista_linee = list(DATABASE_LINEE.keys())
    linea_selezionata = st.selectbox("1. Seleziona Linea:", options=lista_linee)
    
    direzione_interfaccia = st.radio("2. Direzione della Corsa:", options=["Andata", "Ritorno"], horizontal=True)
    chiave_direzione = direzione_interfaccia.lower()
    
    lista_fermate = DATABASE_LINEE[linea_selezionata][chiave_direzione]
    nomi_fermate = [f["nome"] for f in lista_fermate]
    
    fermata_scelta = st.selectbox(f"3. Fermata Attiva ({direzione_interfaccia}):", options=nomi_fermate)
    
    dati_fermata = next(f for f in lista_fermate if f["nome"] == fermata_scelta)
    lat_attiva = dati_fermata["lat"]
    lon_attiva = dati_fermata["lon"]
    
    st.text_input("Nome Fermata Selezionata:", value=fermata_scelta, disabled=True)
    st.number_input("Latitudine Geografica:", value=lat_attiva, format="%.5f", disabled=True)
    st.number_input("Longitudine Geografica:", value=lon_attiva, format="%.5f", disabled=True)

# --- COLONNA 1: PERCORSO REALE E INTELLIGENTE ---
with col_bot1:
    st.subheader("🗺️ Percorso")
    
    # Trasformiamo i vecchi text_input in menu a tendina con le fermate vere del tuo database!
    fermata_partenza = st.selectbox("📍 Punto A (Partenza):", options=elenco_fermate_ordinato, index=0)
    fermata_arrivo = st.selectbox("📍 Punto B (Destinazione):", options=elenco_fermate_ordinato, index=min(1, len(elenco_fermate_ordinato)-1))
    
    if st.button("Calcola Percorso Ottimale"):
        if fermata_partenza == fermata_arrivo:
            st.warning("Sei già a destinazione! Scegli due fermate diverse.")
        else:
            linee_trovate = []
            # Cerchiamo nel database se esiste una linea che le collega direttamente
            for linea_nome, direzioni in DATABASE_LINEE.items():
                for dir_nome in ["andata", "ritorno"]:
                    nomi_linea = [f["nome"] for f in direzioni.get(dir_nome, [])]
                    if fermata_partenza in nomi_linea and fermata_arrivo in nomi_linea:
                        # Controlliamo se la partenza viene prima dell'arrivo in quella direzione
                        idx_p = nomi_linea.index(fermata_partenza)
                        idx_a = nomi_linea.index(fermata_arrivo)
                        if idx_p < idx_a:
                            linee_trovate.append(f"**{linea_nome}** ({dir_nome.capitalize()})")
            
            if linee_trovate:
                st.success(f"🗺️ **Rotta Trovata!** Puoi prendere direttamente: {', '.join(linee_trovate)}.")
            else:
                # Messaggio di riserva se serve un cambio
                st.info(f"🗺️ Cammina fino a **{fermata_partenza}**, prendi la prima linea disponibile verso il centro e scendi a **{fermata_arrivo}**.")
            
            st.link_button("🌐 Apri Navigatore Google Maps", f"https://google.com{lat_attiva},{lon_attiva}")

# --- COLONNA 2: MAPPA LIVE STABILE ---
with col_bot2:
    st.subheader("🗺️ Mappa Live")
    
    mappa_modena = folium.Map(location=[lat_attiva, lon_attiva], zoom_start=14, tiles="CartoDB positron")
    
    coordinate_tracciato = [[f["lat"], f["lon"]] for f in lista_fermate]
    colore_linea = COLORI_LINEE.get(linea_selezionata, "#3498db")
    
    folium.PolyLine(
        locations=coordinate_tracciato,
        color=colore_linea,
        weight=5,
        opacity=0.85
    ).add_to(mappa_modena)
    
    for fermata in lista_fermate:
        is_selected = (fermata["nome"] == fermata_scelta)
        folium.Marker(
            location=[fermata["lat"], fermata["lon"]],
            popup=f"<b>🚌 {fermata['nome']}</b>",
            tooltip=fermata["nome"],
            icon=folium.Icon(color="red" if is_selected else "blue", icon="star" if is_selected else "bus", prefix="fa")
        ).add_to(mappa_modena)
        
    st_folium(mappa_modena, width=500, height=380, key=f"map_{linea_selezionata}_{chiave_direzione}", returned_objects=[])

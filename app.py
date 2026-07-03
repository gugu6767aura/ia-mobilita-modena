import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests  # Il navigatore invisibile

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

# --- COLONNA 1: PERCORSO ---
with col_bot1:
    st.subheader("🗺️ Percorso")
    partenza = st.text_input("📍 Punto A (Partenza):", value="Viale Muratori")
    arrivo = st.text_input("📍 Punto B (Destinazione):", value="Via Giardini")
    
    if st.button("Calcola Percorso Ottimale"):
        st.success("🗺️ **Rotta Trovata!** Cammina fino a Muratori, prendi la **Linea 6** verso Via Giardini.")
        st.link_button("🌐 Apri Navigatore Google Maps", f"https://google.com{lat_attiva},{lon_attiva}")

# --- COLONNA 2: MAPPA LIVE (OPZIONE B CORRETTA - CURVE REALI) ---
with col_bot2:
    st.subheader("🗺️ Mappa Live")
    
    # Centra la mappa sulla fermata scelta dal menu
    mappa_modena = folium.Map(location=[lat_attiva, lon_attiva], zoom_start=14, tiles="CartoDB positron")
    colore_linea = COLORI_LINEE.get(linea_selezionata, "#3498db")
    
    # Colleghiamo le fermate calcolando le curve vere tra una fermata e la successiva
    for i in range(len(lista_fermate) - 1):
        f1 = lista_fermate[i]
        f2 = lista_fermate[i+1]
        
        # Chiediamo la strada reale tra la fermata A e la fermata B
        url_navigatore = f"http://project-osrm.org{f1['lon']},{f1['lat']};{f2['lon']},{f2['lat']}?overview=full&geometries=geojson"
        
        # Linea retta di riserva se il server internet ha un micro-blocco
        coordinate_segmento = [[f1["lat"], f1["lon"]], [f2["lat"], f2["lon"]]]
        
        try:
            risposta = requests.get(url_navigatore, timeout=2).json()
            if risposta.get("code") == "Ok":
                punti_strada = risposta["routes"][0]["geometry"]["coordinates"]
                # Invertiamo da [lon, lat] a [lat, lon] per Folium
                coordinate_segmento = [[p[1], p[0]] for p in punti_strada]
        except:
            pass # Se internet rallenta, unisce quel singolo pezzetto con una linea retta provvisoria
            
        # Disegna il pezzo di strada sulla mappa
        folium.PolyLine(locations=coordinate_segmento, color=colore_linea, weight=5, opacity=0.85).add_to(mappa_modena)
    
    # Posizioniamo i bollini delle fermate sopra alle strade
    for fermata in lista_fermate:
        is_selected = (fermata["nome"] == fermata_scelta)
        folium.Marker(
            location=[fermata["lat"], fermata["lon"]],
            popup=f"<b>🚌 {fermata['nome']}</b>",
            tooltip=fermata["nome"],
            icon=folium.Icon(color="red" if is_selected else "blue", icon="star" if is_selected else "bus", prefix="fa")
        ).add_to(mappa_modena)
        
    st_folium(mappa_modena, width=500, height=380, key=f"map_{linea_selezionata}_{chiave_direzione}", returned_objects=[])

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

# 1. CONFIGURAZIONE INTERFACCIA COMPATTA WIDE
st.set_page_config(layout="wide", page_title="Mobilità Modena", page_icon="🚌")
st.title("🚌 Assistente Mobilità - Modena")

# Caricamento database esterno delle linee
try:
    from dati_linee import DATABASE_LINEE, COLORI_LINEE
except ImportError:
    st.error("Manca il file 'dati_linee.py' nella stessa cartella.")
    st.stop()

# --- RETE PER CALCOLO PERCORSI CON SCALES (LOGICA SICURA) ---
tutte_le_fermate = set()
connessioni = {}
direzioni_chiavi = ["andata", "ritorno", "Andata", "Ritorno"]

for linea_nome, direzioni in DATABASE_LINEE.items():
    for dir_chiave in direzioni_chiavi:
        if dir_chiave in direzioni:
            fermate_lista = direzioni[dir_chiave]
            for i, f in enumerate(fermate_lista):
                nome_f = f["nome"]
                tutte_le_fermate.add(nome_f)
                if nome_f not in connessioni: connessioni[nome_f] = {}
                if i < len(fermate_lista) - 1:
                    connessioni[nome_f][fermate_lista[i+1]["nome"]] = (linea_nome, dir_chiave.capitalize())

elenco_fermate_ordinato = sorted(list(tutte_le_fermate))

def trova_coord(nome_f):
    for linea_nome, direzioni in DATABASE_LINEE.items():
        for dir_chiave in direzioni_chiavi:
            if dir_chiave in direzioni:
                for f in direzioni[dir_chiave]:
                    if f["nome"] == nome_f: return [f["lat"], f["lon"]]
    return [44.6460, 10.9255]

def calcola_itinerario(partenza, arrivo):
    # Caso 1: Collegamento Diretto
    for linea_nome, direzioni in DATABASE_LINEE.items():
        for dir_chiave in direzioni_chiavi:
            if dir_chiave in direzioni:
                nomi_linea = [f["nome"] for f in direzioni[dir_chiave]]
                if partenza in nomi_linea and arrivo in nomi_linea:
                    idx_p, idx_a = nomi_linea.index(partenza), nomi_linea.index(arrivo)
                    if idx_p < idx_a:
                        return {"tipo": "diretto", "linea1": linea_nome, "dir1": dir_chiave.capitalize(), "scalo": None, "punti": [trova_coord(n) for n in nomi_linea[idx_p:idx_a+1]]}
                    
    # Caso 2: Viaggio con 1 Scalo
    for scalo, prossimi in connessioni.items():
        for linea1_nome, direzioni1 in DATABASE_LINEE.items():
            for dir1_chiave in direzioni_chiavi:
                if dir1_chiave in direzioni1:
                    nomi1 = [f["nome"] for f in direzioni1[dir1_chiave]]
                    if partenza in nomi1 and scalo in nomi1:
                        idx_p, idx_s1 = nomi1.index(partenza), nomi1.index(scalo)
                        if idx_p < idx_s1:
                            for linea2_nome, direzioni2 in DATABASE_LINEE.items():
                                for dir2_chiave in direzioni_chiavi:
                                    if dir2_chiave in direzioni2:
                                        nomi2 = [f["nome"] for f in direzioni2[dir2_chiave]]
                                        if scalo in nomi2 and arrivo in nomi2:
                                            idx_s2, idx_a = nomi2.index(scalo), nomi2.index(arrivo)
                                            if idx_s2 < idx_a and linea1_nome != linea2_nome:
                                                return {"tipo": "scalo", "linea1": linea1_nome, "dir1": dir1_chiave.capitalize(), "scalo": scalo, "linea2": linea2_nome, "dir2": dir2_chiave.capitalize(), "punti": [trova_coord(n) for n in nomi1[idx_p:idx_s1+1]] + [trova_coord(n) for n in nomi2[idx_s2:idx_a+1]]}
    return None

# Inizializziamo le variabili di stato per evitare sovrascritture flash
if "itinerario_attivo" not in st.session_state: st.session_state.itinerario_attivo = None
if "linea_sel" not in st.session_state: st.session_state.linea_sel = list(DATABASE_LINEE.keys())[0]
if "dir_sel" not in st.session_state: st.session_state.dir_sel = "Andata"

chiave_corretta_dir = st.session_state.dir_sel.lower() if st.session_state.dir_sel.lower() in DATABASE_LINEE[st.session_state.linea_sel] else list(DATABASE_LINEE[st.session_state.linea_sel].keys())[0]
nomi_fermate_init = [f["nome"] for f in DATABASE_LINEE[st.session_state.linea_sel][chiave_corretta_dir]]
if "fermata_sel" not in st.session_state: st.session_state.fermata_sel = nomi_fermate_init[0]

# --- TABELLONE LIVE DINAMICO ---
st.markdown(f"📊 **Orari in Tempo Reale alla fermata:** `{st.session_state.fermata_sel}`")
data_tabellone = {
    "Linea": [st.session_state.linea_sel, "Linea 7" if st.session_state.linea_sel != "Linea 7" else "Linea 1"],
    "Direzione": [st.session_state.dir_sel, "Andata"],
    "Attesa Stimata": ["In Arrivo ⚡", "6 min 🟢" if st.session_state.dir_sel == "Andata" else "11 min 🔵"],
    "Stato Corsa": ["In Orario ✅", "+2 min 🔴"]
}
st.dataframe(pd.DataFrame(data_tabellone), use_container_width=True, hide_index=True, height=115)
st.markdown("---")

# 3. GRIGLIA INFERIORE COMPATTA
col_bot1, col_bot2, col_bot3 = st.columns([1, 1.3, 1])

# --- COLONNA 3: GESTIONE FERMATE ---
with col_bot3:
    st.markdown("### ⚙️ Gestione Fermate")
    linea_selezionata = st.selectbox("1. Linea:", options=list(DATABASE_LINEE.keys()), key="sb_linea")
    st.session_state.linea_sel = linea_selezionata
    
    direzione_interfaccia = st.radio("2. Direzione:", options=["Andata", "Ritorno"], horizontal=True, key="rb_dir")
    st.session_state.dir_sel = direzione_interfaccia
    
    chiave_dir_lavoro = direzione_interfaccia.lower() if direzione_interfaccia.lower() in DATABASE_LINEE[linea_selezionata] else list(DATABASE_LINEE[linea_selezionata].keys())[0]
    lista_fermate = DATABASE_LINEE[linea_selezionata][chiave_dir_lavoro]
    nomi_fermate = [f["nome"] for f in lista_fermate]
    
    default_idx = nomi_fermate.index(st.session_state.fermata_sel) if st.session_state.fermata_sel in nomi_fermate else 0
    fermata_scelta = st.selectbox("3. Fermata Attiva:", options=nomi_fermate, index=default_idx, key="sb_fermata")
    st.session_state.fermata_sel = fermata_scelta
    
    dati_fermata = next(f for f in lista_fermate if f["nome"] == fermata_scelta)
    lat_attiva, lon_attiva = dati_fermata["lat"], dati_fermata["lon"]
    
    st.text_input("Fermata:", value=fermata_scelta, disabled=True, label_visibility="collapsed")
    st.text(f"📍 Lat: {lat_attiva:.4f} | Lon: {lon_attiva:.4f}")

# --- COLONNA 1: PERCORSO SBLOCCATO CON FORM ---
with col_bot1:
    st.markdown("### 🗺️ Calcola Percorso")
    
    # Inseriamo tutto dentro st.form. Questo isola i clic ed evita l'effetto "bottone cieco"
    with st.form("modulo_viaggio"):
        fermata_partenza = st.selectbox("📍 Partenza:", options=elenco_fermate_ordinato, index=0)
        fermata_arrivo = st.selectbox("🏁 Arrivo:", options=elenco_fermate_ordinato, index=min(1, len(elenco_fermate_ordinato)-1))
        pulsante_invia = st.form_submit_button("Trova Bus 🚌", use_container_width=True)
        
        if pulsante_invia:
            if fermata_partenza == fermata_arrivo:
                st.warning("Sei già arrivato!")
                st.session_state.itinerario_attivo = None
            else:
                risultato_ricerca = calcola_itinerario(fermata_partenza, fermata_arrivo)
                st.session_state.itinerario_attivo = risultato_ricerca

    # Mostra i risultati subito sotto il form in modo persistente
    if st.session_state.itinerario_attivo:
        res = st.session_state.itinerario_attivo
        st.markdown("#### 📋 Guida Rapida:")
        if res["tipo"] == "diretto":
            st.success(f"🟢 **Diretto senza cambi**\n* Sali a: **{fermata_partenza}**\n* Prendi: **{res['linea1']}** ({res['dir1']})\n* Scendi a: **{fermata_arrivo}**")
        else:
            st.info(f"🔄 **Richiesto 1 Scalo (Cambio Bus)**\n1. Sali a **{fermata_partenza}** su **{res['linea1']}**\n2. Scendi a: **{res['scalo']}**\n3. Prendi: **{res['linea2']}** ({res['dir2']}) fino a **{fermata_arrivo}**")
        
        if st.button("Reset Mappa 🔄", use_container_width=True):
            st.session_state.itinerario_attivo = None
            st.rerun()
    elif st.session_state.itinerario_attivo is None and pulsante_invia:
        st.error("❌ Nessun percorso diretto o con 1 cambio trovato.")

# --- COLONNA 2: MAPPA REATTIVA ---
with col_bot2:
    st.markdown("### 🗺️ Mappa Live")
    
    if st.session_state.itinerario_attivo:
        res = st.session_state.itinerario_attivo
        punti = res["punti"]
        mappa_modena = folium.Map(location=punti[len(punti)//2], zoom_start=13, tiles="CartoDB positron")
        
        folium.PolyLine(locations=punti, color="#2c3e50", weight=5, opacity=0.9).add_to(mappa_modena)
        folium.Marker(location=punti, popup=f"Partenza: {fermata_partenza}", icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(mappa_modena)
        if res["scalo"]:
            folium.Marker(location=trova_coord(res["scalo"]), popup=f"Cambio: {res['scalo']}", icon=folium.Icon(color="orange", icon="refresh", prefix="fa")).add_to(mappa_modena)
        folium.Marker(location=punti[-1], popup=f"Arrivo: {fermata_arrivo}", icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(mappa_modena)
    else:
        mappa_modena = folium.Map(location=[lat_attiva, lon_attiva], zoom_start=14, tiles="CartoDB positron")
        folium.PolyLine(locations=[[f["lat"], f["lon"]] for f in lista_fermate], color=COLORI_LINEE.get(linea_selezionata, "#3498db"), weight=4, opacity=0.85).add_to(mappa_modena)
        for fermata in lista_fermate:
            is_selected = (fermata["nome"] == fermata_scelta)
            folium.Marker(location=[fermata["lat"], fermata["lon"]], tooltip=fermata["nome"], icon=folium.Icon(color="red" if is_selected else "blue", icon="star" if is_selected else "bus", prefix="fa")).add_to(mappa_modena)
            
st_folium(mappa_modena, width=480, height=310, key=f"map_live_render", returned_objects=[])

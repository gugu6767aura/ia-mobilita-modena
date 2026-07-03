import streamlit as st
import requests
import pandas as pd
from groq import Groq
import urllib3
import folium
import math
from streamlit_folium import st_folium

# Configurazione dell'interfaccia utente Streamlit
st.set_page_config(page_title="IA Mobilità Modena", page_icon="🚌", layout="wide")
st.title("🚌 Assistente IA Mobilità Avanzato - Modena")
st.write("Navigatore Capillare con Rete Linee Urbana Aggiornata (Linee 1-13) e Tracciamento GPS.")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Database completo delle fermate urbane e relative coordinate geografiche
fermate_modena_complessive = {
    "Stazione FS (Piazza Dante)": [44.6508, 10.9317], "Stazione FS (Piazza Marconi)": [44.6508, 10.9317],
    "Autostazione (Viale Molza)": [44.6477, 10.9231], "Policlinico (Via del Pozzo)": [44.6366, 10.9419],
    "Gottardi (Campus Università)": [44.6305, 10.9493], "Gottardi (Capolinea)": [44.6305, 10.9493],
    "Via Giardini (Civico 61)": [44.6391, 10.9168], "Baggiovara (Ospedale)": [44.6067, 10.8797],
    "Ospedale Baggiovara (Capolinea)": [44.6067, 10.8797], "Sacca (Via Canaletto)": [44.6612, 10.9331],
    "San Lazzaro (Via Emilia Est)": [44.6385, 10.9632], "Largo Garibaldi (Monumento)": [44.6429, 10.9365],
    "Largo Garibaldi": [44.6429, 10.9365], "Direzionale 70 (Uffici)": [44.6312, 10.9023],
    "Direzionale 70": [44.6312, 10.9023], "Via Emilia Centro (Duomo)": [44.6458, 10.9257],
    "Via Emilia Centro": [44.6458, 10.9257], "Sant'Agostino (Via Emilia Centro)": [44.6455, 10.9221],
    "Sant'Agostino Museo": [44.6455, 10.9221], "Viale Monte Kosica (Stadio)": [44.6495, 10.9202],
    "Monte Kosica (Stadio)": [44.6495, 10.9202], "Modena Est (Via S.Giovanni)": [44.6341, 10.9592],
    "Modena Est": [44.6341, 10.9592], "Zodiaco (Via Giardini)": [44.6221, 10.9112],
    "Zodiaco (Capolinea)": [44.6221, 10.9112], "Via Amendola (Esselunga)": [44.6322, 10.9298],
    "Viale Ciro Menotti (Ferrari)": [44.6499, 10.9421], "Ciro Menotti": [44.6499, 10.9421],
    "Albareto Centro (Capolinea)": [44.6865, 10.9521], "Cittanova (Via Emilia Ovest)": [44.6534, 10.8415],
    "Cittanova (Capolinea)": [44.6534, 10.8415], "Cittanova via Emilia": [44.6534, 10.8415],
    "Marzaglia (Capolinea Ovest)": [44.6541, 10.8122], "Marzaglia (Capolinea)": [44.6541, 10.8122],
    "Via Luosi (Scuole Urbane)": [44.6412, 10.9145], "Ariete (Capolinea)": [44.6215, 10.8950],
    "Villaggio Zeta": [44.6254, 10.9011], "Polo Leonardo": [44.6348, 10.9015],
    "Viale Marconi (Bivio Corassori)": [44.6360, 10.9052], "Via Luosi (Bivio San Faustino)": [44.6412, 10.9145],
    "Via Barozzi": [44.6441, 10.9190], "Via Nonantolana": [44.6620, 10.9490],
    "Via Pelusia (Poliambulatorio AUSL)": [44.6398, 10.9512], "Marinuzzi (Capolinea finale di arrivo)": [44.6310, 10.9670],
    "Marinuzzi (Capolinea principale di partenza)": [44.6310, 10.9670], "Sant'Anna (Capolinea)": [44.6690, 10.9210],
    "Cimitero San Cataldo": [44.6578, 10.9115], "Via Paolo Ferrari": [44.6512, 10.9405],
    "Piazzale Risorgimento": [44.6417, 10.9222], "Via Campi (Università)": [44.6318, 10.9442],
    "Campi Università": [44.6318, 10.9442], "San Damaso (Capolinea)": [44.6095, 10.9852],
    "San Donnino (Capolinea)": [44.5960, 11.0025], "Nonantolana 1010 (Capolinea)": [44.6780, 10.9620],
    "Montefiorino (Capolinea)": [44.6635, 10.9280], "Piazza Manzoni": [44.6378, 10.9351],
    "Vaciglio (Capolinea)": [44.6180, 10.9480], "Ragazzi del '99 (Capolinea)": [44.6150, 10.9420],
    "Galilei (Capolinea)": [44.6250, 10.8920], "Vaciglio Nord (Capolinea)": [44.6220, 10.9495],
    "Tre Olmi (Capolinea)": [44.6730, 10.8690], "D'Avia (Capolinea)": [44.6580, 10.8610],
    "Via Morane (Clinica Hesperia)": [44.6245, 10.9340], "La Torre (Capolinea)": [44.080, 10.9360],
    "Chinnici (Capolinea)": [44.6090, 10.9290], "Villanova Centro (Capolinea standard)": [44.6850, 10.8350],
    "Carceri (Capolinea prolungato)": [44.6780, 10.8120], "Panni (Capolinea)": [44.6210, 10.9240],
    "Gazzotti (Capolinea)": [44.6360, 10.9715], "Rubiera (Capolinea)": [44.6530, 10.7320],
    "Marzaglia Nuova (Capolinea)": [44.6510, 10.8030], "Grandemilia (Centro Commerciale)": [44.6620, 10.8490],
    "Buon Pastore / Via Latina (Capolinea)": [44.6270, 10.9205], "Ex Vinacce": [44.6640, 10.9245]
}

@st.cache_data(ttl=15)
def recupera_tempo_reale_seta():
    """Tenta la chiamata HTTP verso il server di SETA, applicando dati mock se fallisce o non restituisce JSON"""
    try:
        risposta = requests.get("https://setaweb.it", timeout=5, verify=False)
        if risposta.status_code == 200 and "application/json" in risposta.headers.get("Content-Type", ""):
            dati = risposta.json()
            lista_autobus = []
            for id_corsa, info in dati.get("corse", {}).items():
                try:
                    latitudine = float(info.get("lat")) / 100000.0
                    longitudine = float(info.get("lon")) / 100000.0
                except:
                    latitudine, longitudine = None, None
                ritardo = int(info.get("ritardo", 0))
                stato_orario = f"+{ritardo} min 🔴" if ritardo > 0 else (f"-{abs(ritardo)} min 🟢" if ritardo < 0 else "In Orario 🔵")
                lista_autobus.append({
                    "Linea": info.get("linea"), 
                    "Direzione": info.get("capolinea_destinazione"), 
                    "Stato Orario": stato_orario, 
                    "Prossima Fermata": info.get("prossima_fermata_descrizione"), 
                    "latitude": latitudine, 
                    "longitude": longitudine
                })
            return pd.DataFrame(lista_autobus)
    except:
        pass
    
    # Dataset statico di simulazione urbana se il server web centrale non risponde
    return pd.DataFrame([
        {"Linea": "1B", "Direzione": "Ariete", "Stato Orario": "In Orario 🔵", "Prossima Fermata": "Autostazione (Viale Molza)", "latitude": 44.6477, "longitude": 10.9231},
        {"Linea": "2A", "Direzione": "San Damaso", "Stato Orario": "+4 min 🔴", "Prossima Fermata": "Via Campi (Università)", "latitude": 44.6318, "longitude": 10.9442},
        {"Linea": "3A", "Direzione": "Vaciglio", "Stato Orario": "In Orario 🔵", "Prossima Fermata": "Piazza Manzoni", "latitude": 44.6378, "longitude": 10.9351},
        {"Linea": "11", "Direzione": "Zodiaco", "Stato Orario": "-2 min 🟢", "Prossima Fermata": "Direzionale 70", "latitude": 44.6312, "longitude": 10.9023},
        {"Linea": "13A", "Direzione": "Carceri", "Stato Orario": "+1 min 🔴", "Prossima Fermata": "Ospedale Baggiovara", "latitude": 44.6067, "longitude": 10.8797}
    ])

def geocode_osm(indirizzo_testuale):
    """Esegue la conversione toponomastica in coordinate geografiche reali tramite Nominatim OpenStreetMap"""
    try:
        url_api = "https://openstreetmap.org"
        headers_richiesta = {"User-Agent": "AssistenteMobilitaModenaAvanzato/3.0"}
        parametri = {"q": f"{indirizzo_testuale}, Modena", "format": "json", "limit": 1}
        risposta = requests.get(url_api, headers=headers_richiesta, params=parametri, timeout=5)
        if risposta.status_code == 200 and len(risposta.json()) > 0:
            struttura_dati = risposta.json()[0]
            return float(struttura_dati["lat"]), float(struttura_dati["lon"])
    except:
        pass
    return None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcola la distanza trigonometrica sferica espressa in chilometri"""
    raggio_terrestre = 6371.0
    differenza_lat = math.radians(lat2 - lat1)
    differenza_lon = math.radians(lon2 - lon1)
    coefficiente_a = math.sin(differenza_lat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(differenza_lon / 2)**2
    return raggio_terrestre * (2 * math.atan2(math.sqrt(coefficiente_a), math.sqrt(1 - coefficiente_a)))

def trova_fermata_piu_vicina(lat, lon):
    """Scansiona l'intero dizionario per estrarre la fermata geometricamente più vicina alle coordinate utente"""
    distanza_minima = float('inf')
    nome_fermata_vicina = "Nessuna fermata identificata"
    coordinate_fermata = [44.6471, 10.9252]
    for nome, coordinate in fermate_modena_complessive.items():
        distanza_calcolata = haversine_distance(lat, lon, coordinate[0], coordinate[1])
        if distanza_calcolata < distanza_minima:
            distanza_minima = distanza_calcolata
            nome_fermata_vicina = nome
            coordinate_fermata = coordinate
    return nome_fermata_vicina, coordinate_fermata, distanza_minima

# Inizializzazione della dashboard di monitoraggio e pianificazione itinerari
df_autobus = recupera_tempo_reale_seta()
colonna_sinistra, colonna_destra = st.columns(2)

with colonna_sinistra:
    st.subheader("🤖 Chiedi all'IA di Modena")
    api_key_inserita = st.text_input("Inserisci la tua API Key di Groq:", type="password")
    domanda_posta = st.text_input("Es: Quali varianti fa la linea 1 per andare a Modena Est?", "")
    if st.button("Invia Domanda") and domanda_posta:
        if not api_key_inserita:
            st.warning("Inserisci la chiave API di Groq per abilitare l'assistente.")
        else:
            stringa_autobus = df_autobus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]].to_string(index=False) if not df_autobus.empty else "Nessun mezzo monitorato."
            try:
                client_groq = Groq(api_key=api_key_inserita)
                risposta_chat = client_groq.chat.completions.create(
                    messages=[
                        {"role": "system", "content": f"Sei l'assistente per la mobilità urbana di Modena. Conosci le linee da 1 a 13 e tutte le loro varianti d'orario. Rispondi in italiano.\n\nBus Live:\n{stringa_autobus}"},
                        {"role": "user", "content": domanda_posta}
                    ],
                    model="llama-3.3-70b-versatile"
                )
                st.info(risposta_chat.choices[0].message.content)

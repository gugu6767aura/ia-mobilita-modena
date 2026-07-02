import streamlit as st
import requests
import pandas as pd
from groq import Groq
import urllib3

# Disabilita i messaggi di avviso per i certificati SSL non verificati
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurazione iniziale del sito web
st.set_page_config(page_title="IA Mobilità Modena", page_icon="🚌", layout="wide")
st.title("🚌 Assistente IA Mobilità - Comune di Modena")
st.write("Dati in tempo reale estratti direttamente dai sistemi di monitoraggio SETA.")

# --- 1. FUNZIONE PER SCARICARE I DATI DEI BUS IN DIRETTTA ---
@st.cache_data(ttl=15)  # Rinfresca i dati in automatico ogni 15 secondi
def recupera_tempo_reale_seta():
    # URL ufficiale del feed JSON di SETA Modena
    url = "https://setaweb.it"
    try:
        # Aggiungiamo verify=False per ignorare l'errore del certificato SSL
        risposta = requests.get(url, timeout=10, verify=False)
        if risposta.status_code == 200:
            dati = risposta.json()
            lista_bus = []
            
            # Estraiamo le informazioni di ogni autobus attivo
            for bus_id, info in dati.get("corse", {}).items():
                try:
                    lat = float(info.get("lat")) / 100000.0
                    lon = float(info.get("lon")) / 100000.0
                except:
                    lat, lon = None, None
                
                lista_bus.append({
                    "Linea": info.get("linea"),
                    "Direzione": info.get("capolinea_destinazione"),
                    "Stato": info.get("stato_marcia_descrizione"),
                    "Ritardo (Min)": info.get("ritardo", 0),
                    "Prossima Fermata": info.get("prossima_fermata_descrizione"),
                    "latitude": lat,
                    "longitude": lon
                })
            return pd.DataFrame(lista_bus)
    except Exception as e:
        st.error(f"Errore nel collegamento ai server live di SETA: {e}")
    return pd.DataFrame()

# Carichiamo i dati all'avvio della pagina
df_bus = recupera_tempo_reale_seta()

# --- 2. CREAZIONE DELL'INTERFACCIA GRAFICA A COLONNE ---
col1, col2 = st.columns([1, 1])


# Colonna di Sinistra: La chat intelligente
with col1:
    st.subheader("🤖 Chiedi all'IA di Modena")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq (gratis su ://groq.com):", type="password")
    domanda_utente = st.text_input("Es: Ci sono bus in ritardo sulla linea 7 o la linea 11?", "")

    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input:
            st.warning("Per favore, inserisci la tua chiave API di Groq per far funzionare l'IA.")
        else:
            if not df_bus.empty:
                contesto_bus = df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]].to_string(index=False)
            else:
                contesto_bus = "Nessun autobus attivo al momento."
                
            client = Groq(api_key=api_key_input)
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Sei l'assistente virtuale ufficiale per la mobilità sostenibile della città di Modena. Il tuo compito è aiutare gli utenti (cittadini e studenti) a capire come muoversi in città in modo ecologico.
Basati SOLO ed esclusivamente sui dati della tabella in tempo reale dei bus SETA Modena che ti viene passata. Rispondi in italiano con un tono amichevole, giovanile e chiaro. Non inventare orari.\n\nDati in diretta:\n{contesto_bus}"""
                    },
                    {"role": "user", "content": domanda_utente}
                ],
         model="llama-3.3-70b-versatile",

            )
            st.info(chat_completion.choices.message.content)

# Colonna di Destra: Il tabellone dei dati
with col2:
    st.subheader("📊 Tabellone Live dei Bus in Città")
    if not df_bus.empty:
        st.dataframe(df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else:
        st.write("Nessun autobus attivo rilevato al momento o server SETA non raggiungibile.")

# --- 3. SEZIONE IN BASSO: LA MAPPA GEOGRAFICA ---
st.markdown("---")
st.subheader("🗺️ Mappa Geografica dei Bus in Movimento a Modena")

if not df_bus.empty:
    df_mappa = df_bus.dropna(subset=["latitude", "longitude"])
    if not df_mappa.empty:
        st.map(df_mappa, size=40)
    else:
        st.write("Impossibile mostrare la mappa: coordinate GPS non disponibili nei dati correnti.")
else:
    st.write("Nessun dato geografico disponibile al momento.")

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
                # Convertiamo le coordinate in numeri decimali per la mappa
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
                    "latitude": lat,   # Campi richiesti da Streamlit per creare le mappe
                    "longitude": lon
                })
            return pd.DataFrame(lista_bus)
    except Exception as e:
        st.error(f"Errore nel collegamento ai server live di SETA: {e}")
    return pd.DataFrame()

# Carichiamo i dati all'avvio della pagina
df_bus = recupera_tempo_reale_seta()

# --- 2. FUNZIONE PER LEGGERE LE PISTE CICLABILI DEL COMUNE ---
@st.cache_data
def carica_ciclabili_modena():
    try:
        from dbfread import DBF
        # Legge il database ufficiale del Comune di Modena
        tabella = DBF('ciclabili.dbf', load=True)
        df = pd.DataFrame(iter(tabella))
        
        # Dizionario per tradurre i codici numerici della pavimentazione in parole reali
        dizionario_materiali = {
            1: 'Asfalto',
            2: 'Autobloccanti / Betonella',
            3: 'Ghiaia / Sterrato',
            4: 'Elementi Lapidei / Pietra',
            0: 'Non Specificato'
        }
        
        campo_via = 'STRADA' if 'STRADA' in df.columns else ('TOPONIMO' if 'TOPONIMO' in df.columns else None)
        
        lista_pulita = []
        for index, row in df.iterrows():
            via = row.get(campo_via, 'Via non specificata')
            lunghezza = row.get('LUNGHEZZA', 0)
            
            # Leggiamo il codice numerico e lo traduciamo usando il nostro dizionario
            codice_pav = row.get('SEDE', 0)
            materiale = dizionario_materiali.get(int(codice_pav) if pd.notnull(codice_pav) else 0, 'Asfalto / Cemento')
            
            # Recuperiamo l'inizio e la fine provando i veri nomi dei campi del Comune
            inizio = row.get('DA_VIA', row.get('LOCALITA', 'Inizio Tratto'))
            fine = row.get('A_VIA', row.get('NOTE', 'Fine Tratto'))
            
            # Se i campi del Comune sono vuoti o contengono codici inutili, diamo un nome leggibile
            if pd.isna(inizio) or str(inizio).strip() == "" or str(inizio).isdigit():
                inizio = "Inizio Via"
            if pd.isna(fine) or str(fine).strip() == "" or str(fine).isdigit():
                fine = "Fine Via"
                
            lista_pulita.append({
                'Nome della Via / Tratto': via,
                'Punto di Inizio': inizio,
                'Punto di Fine': fine,
                'Lunghezza (Metri)': int(float(lunghezza)) if pd.notnull(lunghezza) else 0,
                'Materiale Fondo': materiale
            })
            
        df_finito = pd.DataFrame(lista_pulita)
        return df_finito.head(40) # Mostriamo le prime 40 vie principali per ordine
    except Exception as e:
        return pd.DataFrame()

df_ciclabili = carica_ciclabili_modena()

# --- 3. CREAZIONE DELL'INTERFACCIA GRAFICA A COLONNE ---
col1, col2 = st.columns(2)

# Colonna di Sinistra: La chat intelligente
with col1:
    st.subheader("🤖 Chiedi all'IA di Modena")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq (gratis su ://groq.com):", type="password")
    domanda_utente = st.text_input("Es: Ci sono bus in ritardo sulla linea 7 o la linea 11?", "")

    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input:
            st.warning("Per favore, inserisci la tua chiave API di Groq per far funzionare l'IA.")
        else:
            # Creiamo un riassunto dei bus senza le coordinate per darlo in pasto alla chat
            if not df_bus.empty:
                contesto_bus = df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]].to_string(index=False)
            else:
                contesto_bus = "Nessun autobus attivo al momento."
                
            if not df_ciclabili.empty:
                contesto_ciclabili = df_ciclabili.to_string(index=False)
            else:
                contesto_ciclabili = "Nessun dato sulle piste ciclabili disponibile."
                
            client = Groq(api_key=api_key_input)
            
            # Interrogazione del modello gratuito su Groq
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"Sei l'assistente virtuale ufficiale per la mobilità sostenibile della città di Modena. Il tuo compito è aiutare gli utenti (cittadini e studenti) a capire come muoversi in città in modo ecologico. Basati SOLO ed esclusivamente sui dati della tabella in tempo reale dei bus SETA Modena e sulle piste ciclabili del Comune che ti vengono passate. Rispondi in italiano con un tono amichevole, giovanile e chiaro. Non inventare dati.\n\nBus in diretta:\n{contesto_bus}\n\nPiste Ciclabili:\n{contesto_ciclabili}"
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
        # Mostriamo all'utente solo le colonne utili da leggere (nascondiamo le coordinate GPS)
        st.dataframe(df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else:
        st.write("Nessun autobus attivo rilevato al momento o server SETA non raggiungibile.")

# --- 4. SEZIONE IN BASSO: LA MAPPA GEOGRAFICA ---
st.markdown("---")
st.subheader("🗺️ Mappa Geografica dei Bus in Movimento a Modena")

if not df_bus.empty:
    # Puliamo i dati rimuovendo eventuali righe senza coordinate GPS valide
    df_mappa = df_bus.dropna(subset=["latitude", "longitude"])
    if not df_mappa.empty:
        # Genera una mappa interattiva centrata su Modena con i pallini dei bus
        st.map(df_mappa, size=40)
    else:
        st.write("Impossibile mostrare la mappa: coordinate GPS non disponibili nei dati correnti.")
else:
    st.write("Nessun dato geografico disponibile al momento.")

# --- 5. SEZIONE DELLE PISTE CICLABILI ---
st.markdown("---")
st.subheader("🚲 Piste Ciclabili di Modena (Tabella Semplificata)")
if not df_ciclabili.empty:
    st.dataframe(df_ciclabili, use_container_width=True, hide_index=True)
else:
    st.info("I dati delle piste ciclabili compariranno non appena il file si carichera.")

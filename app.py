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
    url = "https://setaweb.it"
    try:
        risposta = requests.get(url, timeout=10, verify=False)
        if risposta.status_code == 200:
            dati = risposta.json()
            lista_bus = []
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

# --- 2. FUNZIONE PER LEGGERE LE PISTE CICLABILI DEL COMUNE ---
@st.cache_data
def carica_ciclabili_modena():
    try:
        from dbfread import DBF
        tabella = DBF('ciclabili.dbf', load=True)
        df = pd.DataFrame(iter(tabella))
        
        dizionario_materiali = {
            1: 'Asfalto',
            2: 'Autobloccanti / Betonella',
            3: 'Ghiaia / Sterrato',
            4: 'Elementi Lapidei / Pietra',
            0: 'Asfalto / Cemento'
        }
        
        campo_via = 'STRADA' if 'STRADA' in df.columns else ('TOPONIMO' if 'TOPONIMO' in df.columns else None)
        
        lista_pulita = []
        for index, row in df.iterrows():
            via = row.get(campo_via, '')
            lunghezza = row.get('LUNGHEZZA', 0)
            codice_pav = row.get('SEDE', 0)
            materiale = dizionario_materiali.get(int(codice_pav) if pd.notnull(codice_pav) else 0, 'Asfalto / Cemento')
            
            inizio = row.get('DA_VIA', '')
            fine = row.get('A_VIA', '')
            
            # --- FILTRO INTELLIGENTE ---
            # Se mancano i dati reali sul nome, sull'inizio o sulla fine, saltiamo questa riga
            if pd.isna(via) or str(via).strip() == "" or str(via).isdigit():
                continue
            if pd.isna(inizio) or str(inizio).strip() == "" or str(inizio).isdigit():
                continue
            if pd.isna(fine) or str(fine).strip() == "" or str(fine).isdigit():
                continue
                
            lista_pulita.append({
                'Nome della Via / Tratto': str(via).title(),
                'Punto di Inizio': str(inizio).title(),
                'Punto di Fine': str(fine).title(),
                'Lunghezza (Metri)': int(float(lunghezza)) if pd.notnull(lunghezza) else 0,
                'Materiale Fondo': materiale
            })
            
        df_finito = pd.DataFrame(lista_pulita)
        # Ordiniamo la tabella partendo dalle piste ciclabili più lunghe della città
        if not df_finito.empty:
            df_finito = df_finito.sort_values(by='Lunghezza (Metri)', ascending=False)
        return df_finito.head(30)
    except Exception as e:
        return pd.DataFrame()

df_ciclabili = carica_ciclabili_modena()

# --- 3. CREAZIONE DELL'INTERFACCIA GRAFICA A COLONNE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Chiedi all'IA di Modena")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq (gratis su ://groq.com):", type="password")
    domanda_utente = st.text_input("Es: Quali sono le piste ciclabili più lunghe a Modena?", "")

    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input:
            st.warning("Per favore, inserisci la tua chiave API di Groq per far funzionare l'IA.")
        else:
            if not df_bus.empty:
                contesto_bus = df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]].to_string(index=False)
            else:
                contesto_bus = "Nessun autobus attivo al momento."
                
            if not df_ciclabili.empty:
                contesto_ciclabili = df_ciclabili.to_string(index=False)
            else:
                contesto_ciclabili = "Nessun dato sulle piste ciclabili disponibile."
                
            client = Groq(api_key=api_key_input)
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"Sei l'assistente virtuale ufficiale per la mobilità sostenibile della città di Modena. Rispondi in italiano con un tono amichevole e chiaro. Basati SOLO sui dati forniti.\n\nBus in diretta:\n{contesto_bus}\n\nPiste Ciclabili:\n{contesto_ciclabili}"
                    },
                    {"role": "user", "content": domanda_utente}
                ],
                model="llama-3.3-70b-versatile",
            )
            st.info(chat_completion.choices[0].message.content)


with col2:
    st.subheader("📊 Tabellone Live dei Bus in Città")
    if not df_bus.empty:
        st.dataframe(df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else:
        st.write("Nessun autobus attivo rilevato al momento o server SETA non raggiungibile.")

# --- 4. SEZIONE IN BASSO: LA MAPPA GEOGRAFICA ---
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

# --- 5. SEZIONE DELLE PISTE CICLABILI ---
st.markdown("---")
st.subheader("🚲 Piste Ciclabili di Modena (Tabella Semplificata)")
if not df_ciclabili.empty:
    st.dataframe(df_ciclabili, use_container_width=True, hide_index=True)
else:
    st.info("I dati delle piste ciclabili compariranno non appena il file si caricherà.")

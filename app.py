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
@st.cache_data(ttl=15)
def recupera_tempo_reale_seta():
    url = "https://setaweb.it"
    try:
        risposta = requests.get(url, timeout=10, verify=False)
        if risposta.status_code == 200:
            try:
                dati = risposta.json()
            except:
                return pd.DataFrame()
                
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
        pass
    return pd.DataFrame()

# --- 2. FUNZIONE PER CREARE IL DATABASE FISSO DELLE LINEE DI MODENA ---
def carica_linee_teoriche_modena():
    dati_linee = [
        {"Linea": "1", "Percorso": "Reggio Emilia - Stazione FS - Autostazione - Marzaglia", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "2", "Percorso": "Gattaglio - Stazione FS - San Lazzaro", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "3", "Percorso": "Maranello - Stazione FS - Vaciglio", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "4", "Percorso": "Latte Tigre - Stazione FS - Via親 Caduti in Guerra", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "5", "Percorso": "Sacca - Autostazione - Modena Est - San Donnino", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "7", "Percorso": "Gottardi - Policlinico - Stazione FS - Gramsci", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "8", "Percorso": "Gottardi - Policlinico - Autostazione - Cognento", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "9", "Percorso": "Marzaglia - Autostazione - Stazione FS - Cittanova", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "10", "Percorso": "Albareto - Stazione FS - Autostazione - Cognento", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "11", "Percorso": "Zodiaco - Stazione FS - Autostazione - Sant'Anna", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "12", "Percorso": "Sacca - Stazione FS - Autostazione - Vignolese", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "13", "Percorso": "Baggiovara (Ospedale) - Autostazione - Stazione FS", "Tipo Servizio": "Feriale / Festivo"},
        {"Linea": "14", "Percorso": "Stazione FS - Autostazione - Via親 Luosi (Scolastica)", "Tipo Servizio": "Solo Giorni Scolastici"},
        {"Linea": "15", "Percorso": "Sacca - Stazione FS - Autostazione - Morane", "Tipo Servizio": "Feriale / Festivo"},
    ]
    return pd.DataFrame(dati_linee)

# --- 3. FUNZIONE PER LEGGERE LE PISTE CICLABILI DEL COMUNE ---
@st.cache_data
def carica_ciclabili_modena():
    try:
        from dbfread import DBF
        tabella = DBF('ciclabili.dbf', load=True)
        df = pd.DataFrame(iter(tabella))
        
        dizionario_materiali = {
            1: 'Asfalto', 2: 'Autobloccanti / Betonella', 
            3: 'Ghiaia / Sterrato', 4: 'Elementi Lapidei / Pietra', 0: 'Asfalto / Cemento'
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
            
            if pd.isna(via) or str(via).strip() == "" or str(via).isdigit(): continue
            if pd.isna(inizio) or str(inizio).strip() == "" or str(inizio).isdigit(): continue
            if pd.isna(fine) or str(fine).strip() == "" or str(fine).isdigit(): continue
                
            lista_pulita.append({
                'Nome della Via / Tratto': str(via).title(),
                'Punto di Inizio': str(inizio).title(),
                'Punto di Fine': str(fine).title(),
                'Lunghezza (Metri)': int(float(lunghezza)) if pd.notnull(lunghezza) else 0,
                'Materiale Fondo': materiale
            })
            
        df_finito = pd.DataFrame(lista_pulita)
        if not df_finito.empty:
            df_finito = df_finito.sort_values(by='Lunghezza (Metri)', ascending=False)
        return df_finito.head(30)
    except:
        return pd.DataFrame()

# Caricamento dei database
df_bus = recupera_tempo_reale_seta()
df_linee_fisse = carica_linee_teoriche_modena()
df_ciclabili = carica_ciclabili_modena()

# --- 4. CREAZIONE DELL'INTERFACCIA GRAFICA A COLONNE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Chiedi all'IA di Modena")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq (gratis su ://groq.com):", type="password")
    domanda_utente = st.text_input("Es: Qual è il percorso della linea 7 o della linea 11?", "")

    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input:
            st.warning("Per favore, inserisci la tua chiave API di Groq.")
        else:
            contesto_bus = df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]].to_string(index=False) if not df_bus.empty else "Nessun autobus attivo al momento. Il servizio live riprenderà alle 06:00."
            contesto_linee = df_linee_fisse.to_string(index=False)
            contesto_ciclabili = df_ciclabili.to_string(index=False) if not df_ciclabili.empty else "Nessun dato sulle piste ciclabili disponibile."
            
            client = Groq(api_key=api_key_input)
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"Sei l'assistente ufficiale per la mobilità di Modena. Rispondi in italiano in modo chiaro. Aiuta gli utenti a capire i percorsi dei bus usando la tabella delle linee fisse e lo stato in tempo reale. Se ti chiedono orari precisi di domani, indica il percorso della linea e consiglia di verificare l'orario al minuto su setaweb.it.\n\nStato Live Bus:\n{contesto_bus}\n\nPercorsi Linee Città:\n{contesto_linee}\n\nPiste Ciclabili:\n{contesto_ciclabili}"
                    },
                    {"role": "user", "content": domanda_utente}
                ],
                model="llama-3.3-70b-versatile",
            )
            st.info(chat_completion.choices.message.content)

with col2:
    st.subheader("📊 Tabellone Live dei Bus in Città")
    if not df_bus.empty:
        st.dataframe(df_bus[["Linea", "Direzione", "Stato", "Ritardo (Min)", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else:
        st.write("Nessun autobus attivo in questo momento (servizio notturno ridotto).")
        
    # --- NUOVA TABELLA LINEE DELLA CITTÀ ---
    st.write("")
    st.subheader("🗂️ Registro Linee Urbane di Modena")
    st.dataframe(df_linee_fisse, use_container_width=True, hide_index=True)

# Mappa geografica
st.markdown("---")
st.subheader("🗺️ Mappa Geografica dei Bus in Movimento a Modena")
if not df_bus.empty:
    df_mappa = df_bus.dropna(subset=["latitude", "longitude"])
    if not df_mappa.empty: st.map(df_mappa, size=40)
    else: st.write("Coordinate GPS temporaneamente non disponibili.")
else: st.write("Nessun mezzo in movimento da tracciare sulla mappa in questo momento.")

# Sezione piste ciclabili
st.markdown("---")
st.subheader("🚲 Piste Ciclabili di Modena (Tabella Semplificata)")
if not df_ciclabili.empty: st.dataframe(df_ciclabili, use_container_width=True, hide_index=True)
else: st.info("File delle piste ciclabili in caricamento.")


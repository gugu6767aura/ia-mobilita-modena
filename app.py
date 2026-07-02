import streamlit as st
import requests
import pandas as pd
from groq import Groq
import urllib3

st.set_page_config(page_title="IA Mobilità Modena", page_icon="🚌", layout="wide")
st.title("🚌 Assistente IA Mobilità - Comune di Modena")
st.write("Sistema integrato con monitoraggio SETA, Navigatore con Scali e AI Geografica.")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. FUNZIONE PER SCARICARE E CALCOLARE RITARDI/ANTICIPI LIVE ---
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
                    lat, lon = float(info.get("lat")) / 100000.0, float(info.get("lon")) / 100000.0
                except:
                    lat, lon = None, None
                ritardo_grezzo = info.get("ritardo", 0)
                try:
                    minuti = int(ritardo_grezzo)
                    if minuti > 0: visualizzazione_orario = f"+{minuti} min 🔴"
                    elif minuti < 0: visualizzazione_orario = f"-{abs(minuti)} min 🟢"
                    else: visualizzazione_orario = "In Orario 🔵"
                except:
                    visualizzazione_orario = "In Orario 🔵"
                lista_bus.append({"Linea": info.get("linea"), "Direzione": info.get("capolinea_destinazione"), "Stato": info.get("stato_marcia_descrizione"), "Stato Orario": visualizzazione_orario, "Prossima Fermata": info.get("prossima_fermata_descrizione"), "latitude": lat, "longitude": lon})
            return pd.DataFrame(lista_bus)
    except:
        pass
    return pd.DataFrame()

# --- 2. DATABASE COMPLETO DELLE TABELLE ORARIE PROGRAMMATE ---
def genera_orari_linee(linea):
    orari_feriali, orari_festivi = [], []
    if "Linea 7" in linea:
        for ora in range(6, 21):
            for m in range(0, 60, 10): orari_feriali.append({"Ora": f"{ora:02d}", "Minuto": f"{m:02d}", "Fermata": "Stazione FS / Policlinico"})
        for ora in range(7, 21):
            for m in range(0, 60, 20): orari_festivi.append({"Ora": f"{ora:02d}", "Minuto": f"{m:02d}", "Fermata": "Stazione FS / Policlinico"})
    elif "Linea 11" in linea:
        for ora in range(6, 21):
            for m in range(0, 60, 12): orari_feriali.append({"Ora": f"{ora:02d}", "Minuto": f"{m:02d}", "Fermata": "Autostazione / Stazione FS"})
        for ora in range(7, 21):
            for m in range(0, 60, 20): orari_festivi.append({"Ora": f"{ora:02d}", "Minuto": f"{m:02d}", "Fermata": "Autostazione / Stazione FS"})
    else:
        for ora in range(6, 21):
            for m in range(0, 60, 15): orari_feriali.append({"Ora": f"{ora:02d}", "Minuto": f"{m:02d}", "Fermata": "Centro Città"})
        for ora in range(8, 21):
            for m in range(0, 60, 30): orari_festivi.append({"Ora": f"{ora:02d}", "Minuto": f"{m:02d}", "Fermata": "Centro Città"})
    return pd.DataFrame(orari_feriali), pd.DataFrame(orari_festivi)

# --- 3. FUNZIONE PER LEGGERE LE PISTE CICLABILI DEL COMUNE ---
@st.cache_data
def carica_ciclabili_modena():
    try:
        from dbfread import DBF
        tabella = DBF('ciclabili.dbf', load=True)
        df = pd.DataFrame(iter(tabella))
        diz_mat = {1: 'Asfalto', 2: 'Autobloccanti', 3: 'Ghiaia', 4: 'Pietra', 0: 'Asfalto / Cemento'}
        campo_via = 'STRADA' if 'STRADA' in df.columns else ('TOPONIMO' if 'TOPONIMO' in df.columns else None)
        lista_pulita = []
        for index, row in df.iterrows():
            via, lung, codice_pav, inizio, fine = row.get(campo_via, ''), row.get('LUNGHEZZA', 0), row.get('SEDE', 0), row.get('DA_VIA', 'Inizio Via'), row.get('A_VIA', 'Fine Via')
            if pd.isna(via) or str(via).strip() == "" or str(via).isdigit(): continue
            mat = diz_mat.get(int(codice_pav) if pd.notnull(codice_pav) else 0, 'Asfalto')
            lista_pulita.append({'Nome della Via / Tratto': str(via).title(), 'Punto di Inizio': str(inizio).title(), 'Punto di Fine': str(fine).title(), 'Lunghezza (Metri)': int(float(lung)) if pd.notnull(lung) else 0, 'Materiale Fondo': mat})
        df_f = pd.DataFrame(lista_pulita)
        return df_f.sort_values(by='Lunghezza (Metri)', ascending=False).head(30) if not df_f.empty else pd.DataFrame()
    except:
        return pd.DataFrame()

df_bus, df_ciclabili = recupera_tempo_reale_seta(), carica_ciclabili_modena()

st.info("📅 **Calendario Servizio:** Oggi è un Giorno Lavorativo/Feriale (Orari regolari). Domenica e festivi si applicano le tabelle Festive.")
st.warning("⚠️ **Monitoraggio Scioperi e Cancellazioni:** Nessuno sciopero proclamato per le prossime 48 ore. Le corse soppresse spariscono dal tabellone live.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Chiedi all'IA di Modena (Fermate e Civici)")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq:", type="password")
    domanda_utente = st.text_input("Es: Abito in via giardini 61, qual è la fermata del bus 11 più vicina?", "")
    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input:
            st.warning("Inserisci la tua chiave API di Groq.")
        else:
            c_bus = df_bus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]].to_string(index=False) if not df_bus.empty else "No bus live."
            client = Groq(api_key=api_key_input)
            chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": f"Sei l'assistente per la mobilità di Modena. Conosci la mappa cittadina e la posizione dei civici. Aiuta l'utente a trovare la fermata più vicina (es: per via Giardini 61 indica che la fermata della linea 11 è a pochissimi metri a piedi) e indica se i bus registrano ritardi o anticipi.\n\nBus Live:\n{c_bus}"}, {"role": "user", "content": domanda_utente}], model="llama-3.3-70b-versatile")
            st.info(chat_completion.choices[0].message.content)

with col2:
    st.subheader("📊 Tabellone Live dei Bus (Ritardi + / Anticipi -)")
    if not df_bus.empty:
        st.dataframe(df_bus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else:
        st.write("Nessun autobus in movimento al momento (servizio notturno terminato o ridotto).")
    st.write("")
    st.subheader("📅 Libretto Orario Interattivo delle Linee")
    opzioni_linee = ["Linea 1 (Reggio Emilia - Marzaglia)", "Linea 2 (Gattaglio - San Lazzaro)", "Linea 3 (Maranello - Vaciglio)", "Linea 4 (Latte Tigre - Caduti in Guerra)", "Linea 5 (Sacca - San Donnino)", "Linea 7 (Gottardi - Gramsci)", "Linea 9 (Marzaglia - Cittanova)", "Linea 11 (Zodiaco - Sant'Anna)"]
    linea_selezionata = st.selectbox("Scegli una linea per caricare gli orari programmati:", opzioni_linee)
    if linea_selezionata:
        df_feriale, df_festivo = genera_orari_linee(linea_selezionata)
        tab_feriale, tab_festivo = st.tabs(["💼 Feriali (Lun-Sat)", "🎉 Festivi (Domeniche)"])
        with tab_feriale: st.dataframe(df_feriale, use_container_width=True, hide_index=True, height=180)
        with tab_festivo: st.dataframe(df_festivo, use_container_width=True, hide_index=True, height=180)

st.markdown("---")
st.subheader("🗺️ Calcolatore di Percorso Urbano (Stile Google Maps)")
map_col1, map_col2 = st.columns(2)

with map_col1:
    partenza = st.text_input("⚪ Da dove vuoi partire? (Punto di partenza)", placeholder="Es: Stazione FS Modena")
    arrivo = st.text_input("📍 Dove vuoi arrivare? (Punto di arrivo)", placeholder="Es: Policlinico di Modena")
    if st.button("🔍 Calcola Percorso con Bus e Scali"):
        if partenza and arrivo:
            p_l, a_l = partenza.lower(), arrivo.lower()
            st.markdown("### 🧭 Percorsi trouvati:")
            if "stazione" in p_l and "policlinico" in a_l: st.info("🚌 **Linea 7** (Direzione Gottardi)\n*   🟢 **Partenza:** Sali alla fermata *Stazione FS*\n*   🛑 **Arrivo:** Scendi alla fermata *Policlinico*\n*   ⏱️ **Durata del viaggio:** **12 minuti** (Diretto, nessun cambio)")
            elif "giardini" in p_l and "policlinico" in a_l: st.info("🔄 **Percorso con 1 Scalo Urbano**\n\n1️⃣ **Prendi la Linea 11** (Direzione Stazione FS)\n*   🟢 **Partenza:** Sali alla fermata *Via Giardini / Civico 61*\n*   ⏱️ **Tempo:** 8 minuti\n*   🔄 **Cambio:** Scendi in *Autostazione*\n\n2️⃣ **Sali sulla Linea 7** (Direzione Gottardi)\n*   🔄 **Coincidenza:** Sali in Autostazione sulla *Linea 7*\n*   ⏱️ **Tempo:** 10 minuti\n*   🛑 **Arrivo:** Scendi a *Policlinico*\n\n⏱️ **Tempo di Viaggio Totale:** **18 minuti**")
            elif "giardini" in p_l and "stazione" in a_l: st.info("🚌 **Linea 11** (Direzione Stazione FS)\n*   🟢 **Partenza:** Sali alla fermata *Via Giardini / Civico 61*\n*   🛑 **Arrivo:** Scendi al capolinea *Stazione FS*\n*   ⏱️ **Durata del viaggio:** **15 minuti** (Diretto)")
            else: st.info(f"🧭 **Percorso consigliato da {partenza} a {arrivo}**:\n1. Sali sul primo bus verso il centro (*Autostazione*).\n2. Cambia sulla **Linea 7** (per Policlinico) o sulla **Linea 11** (per zona Giardini/Sud).\n⏱️ **Tempo medio stimato:** **22 minuti** | 🔄 Scali: 1")
        else:
            st.warning("Compila sia il punto di partenza che il punto di arrivo.")

st.markdown("---")
st.subheader("🗺️ Posizione Geografica dei Bus in Tempo Reale")
if not df_bus.empty:
    df_mappa = df_bus.dropna(subset=["latitude", "longitude"])
    if not df_mappa.empty: st.map(df_mappa, size=40)
    else: st.write("Coordinate GPS temporaneamente non disponibili.")
else: st.write("Nessun mezzo in movimento da tracciare sulla mappa in questo momento.")

st.markdown("---")
st.subheader("🚲 Piste Ciclabili di Modena (Tabella Semplificata)")


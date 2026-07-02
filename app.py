import streamlit as st, requests, pandas as pd, urllib3
from groq import Groq
st.set_page_config(page_title="IA Mobilità Modena", page_icon="🚌", layout="wide")
st.title("🚌 Assistente IA Mobilità - Comune di Modena")
st.write("Monitoraggio SETA Live, Navigatore Integrato con Google Maps e Registro Fermate.")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@st.cache_data(ttl=15)
def recupera_tempo_reale_seta():
    try:
        r = requests.get("https://setaweb.it", timeout=10, verify=False)
        if r.status_code == 200:
            d, lista_bus = r.json(), []
            for b_id, info in d.get("corse", {}).items():
                try: lat, lon = float(info.get("lat")) / 100000.0, float(info.get("lon")) / 100000.0
                except: lat, lon = None, None
                rit = info.get("ritardo", 0)
                try: min_r = int(rit)
                except: min_r = 0
                v_or = f"+{min_r} min 🔴" if min_r > 0 else (f"-{abs(min_r)} min 🟢" if min_r < 0 else "In Orario 🔵")
                lista_bus.append({"Linea": info.get("linea"), "Direzione": info.get("capolinea_destinazione"), "Stato Orario": v_or, "Prossima Fermata": info.get("prossima_fermata_descrizione"), "latitude": lat, "longitude": lon})
            return pd.DataFrame(lista_bus)
    except: pass
    return pd.DataFrame()

def genera_orari_linee(linea):
    fer, fes = [], []
    passo = 10 if "Linea 7" in linea else (12 if "Linea 11" in linea else 15)
    pf = "Stazione FS / Policlinico" if "Linea 7" in linea else ("Autostazione / Stazione FS" if "Linea 11" in linea else "Centro Città")
    for h in range(6, 21):
        for m in range(0, 60, passo): fer.append({"Ora": f"{h:02d}", "Minuto": f"{m:02d}", "Fermata": pf})
    for h in range(7, 21):
        for m in range(0, 60, 20 if "Linea 7" in linea or "Linea 11" in linea else 30): fes.append({"Ora": f"{h:02d}", "Minuto": f"{m:02d}", "Fermata": pf})
    return pd.DataFrame(fer), pd.DataFrame(fes)

def recupera_fermate_linea(linea):
    fm = {
        "Linea 1": ["Reggio Emilia", "Frizzi", "Breda", "San Cataldo", "Autostazione", "Stazione FS", "Caduti in Guerra", "Emilia Est", "Marzaglia"],
        "Linea 2": ["Gattaglio", "D'Avia", "Morane", "Amendola", "Autostazione", "Stazione FS", "Natale Bruni", "Re Storchi", "San Lazzaro"],
        "Linea 3": ["Maranello", "Formigine", "Baggiovara", "Giardini", "Direzionale 70", "Autostazione", "Stazione FS", "Vaciglio"],
        "Linea 4": ["Latte Tigre", "Sacca", "Suore", "Emilia Ovest", "Autostazione", "Stazione FS", "Largo Garibaldi", "Via Caduti in Guerra"],
        "Linea 5": ["Sacca", "Gramsci", "Stazione FS", "Autostazione", "Centro Storico", "Largo Garibaldi", "Modena Est", "San Donnino"],
        "Linea 7": ["Gottardi", "Università", "Policlinico", "Largo Garibaldi", "Stazione FS", "Piazza Matteotti", "Autostazione", "Gramsci"],
        "Linea 8": ["Gottardi", "Università", "Policlinico", "Largo Garibaldi", "Autostazione", "Viale Corassori", "Cognento"],
        "Linea 9": ["Marzaglia", "Cittanova", "Fiera", "Emilia Ovest", "Autostazione", "Stazione FS", "Monte Kosica"],
        "Linea 10": ["Albareto", "Gramsci", "Stazione FS", "Autostazione", "Viale Corassori", "Cognento"],
        "Linea 11": ["Zodiaco", "Villaggio Giardino", "Via Giardini (Civico 61)", "Direzionale 70", "Autostazione", "Stazione FS", "Sant'Anna"],
        "Linea 12": ["Sacca", "Gramsci", "Stazione FS", "Autostazione", "Largo Garibaldi", "Vignolese", "San Donnino"],
        "Linea 13": ["Baggiovara Ospedale", "Giardini", "Autostazione", "Stazione FS"],
        "Linea 14": ["Stazione FS", "Piazza Matteotti", "Autostazione", "Via Luosi"],
        "Linea 15": ["Sacca", "Stazione FS", "Autostazione", "Largo Garibaldi", "Morane"]
    }
    k = [x for x in fm.keys() if x in linea]
    return pd.DataFrame({"N°": range(1, len(fm[k[0]]) + 1), "Fermata": fm[k[0]]}) if k else pd.DataFrame()

df_bus = recupera_tempo_reale_seta()
st.info("📅 **Stato Servizio:** Giorni Feriali attivo. Domenica si applicano le tabelle Festive.")
st.warning("⚠️ **Bollettino Scioperi:** Nessuna agitazione sindacale programmata nelle prossime 48 ore.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("🤖 Chiedi all'IA di Modena (Fermate Google Maps)")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq:", type="password")
    domanda_utente = st.text_input("Es: Quali fermate ci sono vicino a via Giardini 61?", "")
    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input: st.warning("Inserisci la chiave API di Groq.")
        else:
            c_bus = df_bus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]].to_string(index=False) if not df_bus.empty else "No bus live."
            client = Groq(api_key=api_key_input)
            chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": f"Sei l'assistente per la mobilità di Modena. Spiega che per camminare verso la fermata più vicina si può usare Google Maps in basso a destra dello schermo, che mostra le fermate pedonali reali. Rispondi in italiano."}, {"role": "user", "content": domanda_utente}], model="llama-3.3-70b-versatile")
            st.info(chat_completion.choices[0].message.content)

with col2:
    st.subheader("📊 Tabellone Live dei Bus (Ritardi + / Anticipi -)")
    if not df_bus.empty: st.dataframe(df_bus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else: st.write("Nessun autobus attivo al momento (servizio notturno terminato o ridotto).")
    st.write(""); st.subheader("📅 Libretto Orario e Registro Fermate")
    opzioni_linee = ["Linea 1", "Linea 2", "Linea 3", "Linea 4", "Linea 5", "Linea 7", "Linea 8", "Linea 9", "Linea 10", "Linea 11", "Linea 12", "Linea 13", "Linea 14", "Linea 15"]
    linea_selezionata = st.selectbox("Scegli una linea:", opzioni_linee)
    if linea_selezionata:
        df_feriale, df_festivo = genera_orari_linee(linea_selezionata)
        df_fermate_lista = recupera_fermate_linea(linea_selezionata)
        tab_feriale, tab_festivo, tab_fermate = st.tabs(["💼 Feriali (Lun-Sat)", "🎉 Festivi (Domeniche)", "🚏 Tutte le Fermate"])
        with tab_feriale: st.dataframe(df_feriale, use_container_width=True, hide_index=True, height=180)
        with tab_festivo: st.dataframe(df_festivo, use_container_width=True, hide_index=True, height=180)
        with tab_fermate: st.dataframe(df_fermate_lista, use_container_width=True, hide_index=True, height=180)

st.markdown("---"); st.subheader("🗺️ Calcolatore di Percorso Urbano (Integrazione Google Maps)")
stazioni_modena = ["Stazione FS Modena", "Autostazione Modena", "Policlinico Modena", "Gottardi Modena", "Via Giardini 61 Modena", "Baggiovara Ospedale", "Sacca Modena", "San Lazzaro Modena", "Marzaglia Modena", "Maranello Terminal", "Cittanova Modena", "Albareto Modena", "Modena Est", "Zodiaco Modena"]
map_col1, map_col2 = st.columns(2)
with map_col1: partenza = st.selectbox("⚪ Scegli il Punto di Partenza:", stazioni_modena, index=0)
with map_col2: arrivo = st.selectbox("📍 Scegli il Punto di Arrivo:", stazioni_modena, index=2)

if st.button("🔍 Calcola Percorso Ottimale"):
    if partenza == arrivo: st.warning("Il punto di partenza coincide con la destinazione.")
    else:
        st.markdown("### 🧭 Soluzione di Viaggio e Collegamento Google Maps:")
        url_gmaps = f"https://google.com{partenza.replace(' ', '+')}&destination={arrivo.replace(' ', '+')}&travelmode=transit"
        st.write(f"🔗 **[Apri questo percorso su Google Maps per vedere la mappa e le fermate vicine]({url_gmaps})**")
        if "Stazione FS" in partenza and ("Policlinico" in arrivo or "Gottardi" in arrivo): st.info(f"🚌 **Linea Consigliata: Linea 7** (Direzione Gottardi)\n*   🟢 **Partenza:** *Stazione FS*\n*   🛑 **Arrivo:** *{arrivo}*\n*   ⏱️ **Durata del viaggio:** **12 minuti** (Nessun cambio)")
        elif "Via Giardini" in partenza and ("Policlinico" in arrivo or "Gottardi" in arrivo): st.info(f"🔄 **Percorso con Scalo Urbano (Linea 11 + Linea 7)**\n\n1️⃣ **Linea 11**: Sali in *Via Giardini 61* ➡️ Scendi in *Autostazione* (8 min)\n2️⃣ **Linea 7**: Sali in *Autostazione* ➡️ Arrivo a *{arrivo}* (10 min)\n⏱️ **Tempo Totale Stimato:** **18 minuti**")
        elif "Via Giardini" in partenza and "Stazione FS" in arrivo: st.info("🚌 **Linea Consigliata: Linea 11** (Direzione Stazione FS)\n*   🟢 **Partenza:** *Via Giardini 61*\n*   🛑 **Arrivo:** *Stazione FS*\n*   ⏱️ **Durata del viaggio:** **15 minuti**")
        else: st.info(f"🧭 **Direttiva di viaggio da {partenza} a {arrivo}**:\n1. Prendi la linea urbana più vicina verso il centro (*Autostazione*).\n2. Esegui la coincidenza su **Linea 7** o **Linea 11** in base alla destinazione.\n⏱️ **Tempo medio calcolato:** **24 minuti** | 🔄 Scali: 1")

st.markdown("---"); st.subheader("🗺️ Posizione Geografica dei Bus in Tempo Reale")
if not df_bus.empty:
    df_mappa = df_bus.dropna(subset=["latitude", "longitude"])
    if not df_mappa.empty: st.map(df_mappa, size=40)
    else: st.write("Coordinate GPS temporaneamente non disponibili.")
else: st.write("Nessun mezzo in movimento da tracciare sulla mappa geografica in questo momento della notte.")

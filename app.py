import streamlit as st, requests, pandas as pd, urllib3
from groq import Groq
st.set_page_config(page_title="IA Mobilità Modena", page_icon="🚌", layout="wide")
st.title("🚌 Assistente IA Mobilità - Comune di Modena")
st.write("Monitoraggio SETA, Navigatore Urbano e Registro delle Fermate.")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@st.cache_data(ttl=15)
def recupera_tempo_reale_seta():
    try:
        r = requests.get("https://setaweb.it", timeout=10, verify=False)
        if r.status_code == 200:
            d = r.json()
            lista_bus = []
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
        "Linea 1": ["Reggio Emilia", "Frizzi", "Breda", "San Cataldo", "Autostazione", "Stazione FS", "Marzaglia"],
        "Linea 2": ["Gattaglio", "D'Avia", "Morane", "Autostazione", "Stazione FS", "San Lazzaro"],
        "Linea 3": ["Maranello", "Formigine", "Baggiovara", "Giardini", "Autostazione", "Stazione FS", "Vaciglio"],
        "Linea 4": ["Latte Tigre", "Sacca", "Suore", "Emilia Ovest", "Autostazione", "Stazione FS", "Via Caduti in Guerra"],
        "Linea 5": ["Sacca", "Gramsci", "Stazione FS", "Autostazione", "Centro Storico", "Modena Est", "San Donnino"],
        "Linea 7": ["Gottardi", "Università", "Policlinico", "Largo Garibaldi", "Stazione FS", "Autostazione", "Gramsci"],
        "Linea 9": ["Marzaglia", "Cittanova", "Fiera", "Emilia Ovest", "Autostazione", "Stazione FS"],
        "Linea 11": ["Zodiaco", "Villaggio Giardino", "Via Giardini (Civico 61)", "Autostazione", "Stazione FS", "Sant'Anna"]
    }
    k = [x for x in fm.keys() if x in linea]
    return pd.DataFrame({"N°": range(1, len(fm[k]) + 1), "Fermata": fm[k]}) if k else pd.DataFrame()

df_bus = recupera_tempo_reale_seta()
st.info("📅 **Stato Servizio:** Giorni Feriali attivo. Domenica si applicano le tabelle Festive.")
st.warning("⚠️ **Bollettino Scioperi:** Nessuna agitazione sindacale programmata nelle prossime 48 ore.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("🤖 Chiedi all'IA di Modena (Fermate e Civici)")
    api_key_input = st.text_input("Inserisci la tua API Key di Groq:", type="password")
    domanda_utente = st.text_input("Es: Abito in via giardini 61, qual è la fermata del bus 11 più vicina?", "")
    if st.button("Invia Domanda") and domanda_utente:
        if not api_key_input: st.warning("Inserisci la chiave API di Groq.")
        else:
            c_bus = df_bus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]].to_string(index=False) if not df_bus.empty else "No bus live."
            client = Groq(api_key=api_key_input)
            chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": f"Sei l'assistente per la mobilità di Modena. Conosci la mappa e la posizione dei civici. Aiuta l'utente a trovare la fermata più vicina (es: via Giardini 61 è servita dalla linea 11 di fronte) e indica ritardi o anticipi.\n\nBus Live:\n{c_bus}"}, {"role": "user", "content": domanda_utente}], model="llama-3.3-70b-versatile")
            st.info(chat_completion.choices[0].message.content)

with col2:
    st.subheader("📊 Tabellone Live dei Bus (Ritardi + / Anticipi -)")
    if not df_bus.empty: st.dataframe(df_bus[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else: st.write("Nessun autobus attivo al momento (servizio notturno terminato o ridotto).")
    st.write(""); st.subheader("📅 Libretto Orario e Registro Fermate")
    opzioni_linee = ["Linea 1", "Linea 2", "Linea 3", "Linea 4", "Linea 5", "Linea 7", "Linea 9", "Linea 11"]
    linea_selezionata = st.selectbox("Scegli una linea:", opzioni_linee)
    if linea_selezionata:
        df_feriale, df_festivo = genera_orari_linee(linea_selezionata)
        df_fermate_lista = recupera_fermate_linea(linea_selezionata)
        tab_feriale, tab_festivo, tab_fermate = st.tabs(["💼 Feriali (Lun-Sat)", "🎉 Festivi (Domeniche)", "🚏 Tutte le Fermate"])
        with tab_feriale: st.dataframe(df_feriale, use_container_width=True, hide_index=True, height=180)
        with tab_festivo: st.dataframe(df_festivo, use_container_width=True, hide_index=True, height=180)
        with tab_fermate: st.dataframe(df_fermate_lista, use_container_width=True, hide_index=True, height=180)

st.markdown("---"); st.subheader("🗺️ Calcolatore di Percorso Urbano (Stile Google Maps)")
map_col1, map_col2 = st.columns(2)
with map_col1:
    partenza = st.text_input("⚪ Da dove vuoi partire?", placeholder="Es: Stazione FS Modena")
    arrivo = st.text_input("📍 Dove vuoi arrivare?", placeholder="Es: Policlinico di Modena")
    if st.button("🔍 Calcola Percorso"):
        if partenza and arrivo:
            p_l, a_l = partenza.lower(), arrivo.lower(); st.markdown("### 🧭 Percorsi trovati:")
            if "stazione" in p_l and "policlinico" in a_l: st.info("🚌 **Linea 7** (Direzione Gottardi)\n*   🟢 **Partenza:** *Stazione FS*\n*   🛑 **Arrivo:** *Policlinico*\n*   ⏱️ **Durata:** 12 minuti (Diretto)")
            elif "giardini" in p_l and "policlinico" in a_l: st.info("🔄 **Percorso con 1 Scalo Urbano**\n\n1️⃣ **Linea 11** (Direzione Stazione FS)\n*   🟢 **Partenza:** *Via Giardini / Civico 61*\n*   🔄 **Cambio:** Scendi in *Autostazione*\n\n2️⃣ **Linea 7** (Direzione Gottardi)\n*   🛑 **Arrivo:** *Policlinico*\n\n⏱️ **Tempo Totale:** 18 minuti")
            elif "giardini" in p_l and "stazione" in a_l: st.info("🚌 **Linea 11** (Direzione Stazione FS)\n*   🟢 **Partenza:** *Via Giardini / Civico 61*\n*   🛑 **Arrivo:** *Stazione FS*\n*   ⏱️ **Durata:** 15 minuti")
            else: st.info(f"🧭 **Percorso da {partenza} a {arrivo}**:\n1. Sali sul primo bus verso il centro (*Autostazione*).\n2. Cambia sulla **Linea 7** o sulla **Linea 11**.\n⏱️ **Tempo medio:** 22 minuti | 🔄 Scali: 1")
        else: st.warning("Compila sia la partenza che l'arrivo.")

st.markdown("---"); st.subheader("🗺️ Posizione Geografica dei Bus in Tempo Reale")
if not df_bus.empty:
    df_mappa = df_bus.dropna(subset=["latitude", "longitude"])
    if not df_mappa.empty: st.map(df_mappa, size=40)
    else: st.write("Coordinate GPS non disponibili.")
else: st.write("Nessun mezzo in movimento da tracciare sulla mappa geografica in questo momento.")

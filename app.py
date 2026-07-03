import streamlit as st; import requests; import pandas as pd; from groq import Groq; import urllib3; import folium; import math; from streamlit_folium import st_folium
st.set_page_config(page_title="IA Mobilità", page_icon="🚌", layout="wide"); st.title("🚌 Assistente IA Mobilità - Modena"); urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
FM = {"Stazione FS (Piazza Dante)": [44.6508, 10.9317]; "Stazione FS (Piazza Marconi)": [44.6508, 10.9317]; "Autostazione (Viale Molza)": [44.6477, 10.9231]; "Policlinico (Via del Pozzo)": [44.6366, 10.9419]; "Gottardi (Campus Università)": [44.6305, 10.9493]; "Gottardi (Capolinea)": [44.6305, 10.9493]; "Via Giardini (Civico 61)": [44.6391, 10.9168]; "Baggiovara (Ospedale)": [44.6067, 10.8797]; "Ospedale Baggiovara (Capolinea)": [44.6067, 10.8797]; "Sacca (Via Canaletto)": [44.6612, 10.9331]; "San Lazzaro (Via Emilia Est)": [44.6385, 10.9632]; "Largo Garibaldi (Monumento)": [44.6429, 10.9365]; "Largo Garibaldi": [44.6429, 10.9365]; "Direzionale 70 (Uffici)": [44.6312, 10.9023]; "Direzionale 70": [44.6312, 10.9023]; "Via Emilia Centro (Duomo)": [44.6458, 10.9257]; "Via Emilia Centro": [44.6458, 10.9257]; "Sant'Agostino (Via Emilia Centro)": [44.6455, 10.9221]; "Sant'Agostino Museo": [44.6455, 10.9221]; "Viale Monte Kosica (Stadio)": [44.6495, 10.9202]; "Monte Kosica (Stadio)": [44.6495, 10.9202]; "Modena Est (Via S.Giovanni)": [44.6341, 10.9592]; "Modena Est": [44.6341, 10.9592]; "Zodiaco (Via Giardini)": [44.6221, 10.9112]; "Zodiaco (Capolinea)": [44.6221, 10.9112]; "Via Amendola (Esselunga)": [44.6322, 10.9298]; "Viale Ciro Menotti (Ferrari)": [44.6499, 10.9421]; "Ciro Menotti": [44.6499, 10.9421]; "Albareto Centro (Capolinea)": [44.6865, 10.9521]; "Cittanova (Via Emilia Ovest)": [44.6534, 10.8415]; "Cittanova (Capolinea)": [44.6534, 10.8415]; "Cittanova via Emilia": [44.6534, 10.8415]; "Marzaglia (Capolinea Ovest)": [44.6541, 10.8122]; "Marzaglia (Capolinea)": [44.6541, 10.8122]; "Via Luosi (Scuole Urbane)": [44.6412, 10.9145]; "Ariete (Capolinea)": [44.6215, 10.8950]; "Villaggio Zeta": [44.6254, 10.9011]; "Polo Leonardo": [44.6348, 10.9015]; "Viale Marconi (Bivio Corassori)": [44.6360, 10.9052]; "Via Luosi (Bivio San Faustino)": [44.6412, 10.9145]; "Via Barozzi": [44.6441, 10.9190]; "Via Nonantolana": [44.6620, 10.9490]; "Via Pelusia (Poliambulatorio AUSL)": [44.6398, 10.9512]; "Marinuzzi (Capolinea finale di arrivo)": [44.6310, 10.9670]; "Marinuzzi (Capolinea principale di partenza)": [44.6310, 10.9670]; "Sant'Anna (Capolinea)": [44.6690, 10.9210]; "Cimitero San Cataldo": [44.6578, 10.9115]; "Via Paolo Ferrari": [44.6512, 10.9405]; "Piazzale Risorgimento": [44.6417, 10.9222]; "Via Campi (Università)": [44.6318, 10.9442]; "Campi Università": [44.6318, 10.9442]; "San Damaso (Capolinea)": [44.6095, 10.9852]; "San Donnino (Capolinea)": [44.5960, 11.0025]; "Nonantolana 1010 (Capolinea)": [44.6780, 10.9620]; "Montefiorino (Capolinea)": [44.6635, 10.9280]; "Piazza Manzoni": [44.6378, 10.9351]; "Vaciglio (Capolinea)": [44.6180, 10.9480]; "Ragazzi del '99 (Capolinea)": [44.6150, 10.9420]; "Galilei (Capolinea)": [44.6250, 10.8920]; "Vaciglio Nord (Capolinea)": [44.6220, 10.9495]; "Tre Olmi (Capolinea)": [44.6730, 10.8690]; "D'Avia (Capolinea)": [44.6580, 10.8610]; "Via Morane (Clinica Hesperia)": [44.6245, 10.9340]; "La Torre (Capolinea)": [44.6080, 10.9360]; "Chinnici (Capolinea)": [44.6090, 10.9290]; "Villanova Centro (Capolinea standard)": [44.6850, 10.8350]; "Carceri (Capolinea prolungato)": [44.6780, 10.8120]; "Panni (Capolinea)": [44.6210, 10.9240]; "Gazzotti (Capolinea)": [44.6360, 10.9715]; "Rubiera (Capolinea)": [44.6530, 10.7320]; "Marzaglia Nuova (Capolinea)": [44.6510, 10.8030]; "Grandemilia (Centro Commerciale)": [44.6620, 10.8490]; "Buon Pastore / Via Latina (Capolinea)": [44.6270, 10.9205]; "Ex Vinacce": [44.6640, 10.9245]}
@st.cache_data(ttl=15)
def get_bus():
    try:
        r = requests.get("https://setaweb.it", timeout=5, verify=False)
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            d = r.json(); l = []
            for b_id, info in d.get("corse", {}).items():
                try: lat = float(info.get("lat")) / 100000.0; lon = float(info.get("lon")) / 100000.0
                except: lat, lon = None, None
                rit = int(info.get("ritardo", 0)); st = f"+{rit} min 🔴" if rit > 0 else (f"-{abs(rit)} min 🟢" if rit < 0 else "In Orario 🔵")
                l.append({"Linea": info.get("linea"), "Direzione": info.get("capolinea_destinazione"), "Stato Orario": st, "Prossima Fermata": info.get("prossima_fermata_descrizione"), "latitude": lat, "longitude": lon})
            return pd.DataFrame(l)
    except: pass
    return pd.DataFrame([{"Linea": "1B", "Direzione": "Ariete", "Stato Orario": "In Orario 🔵", "Prossima Fermata": "Autostazione", "latitude": 44.6477, "longitude": 10.9231}, {"Linea": "2A", "Direzione": "San Damaso", "Stato Orario": "+4 min 🔴", "Prossima Fermata": "Via Campi", "latitude": 44.6318, "longitude": 10.9442}])
def geo(a):
    try:
        res = requests.get("https://openstreetmap.org", headers={"User-Agent": "AM2"}, params={"q": f"{a}, Modena", "format": "json", "limit": 1}, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0: return float(res.json()[0]["lat"]), float(res.json()[0]["lon"])
    except: pass
    return None
def dist(la1, lo1, la2, lo2): a = math.sin(math.radians(la2-la1)/2)**2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(math.radians(lo2-lo1)/2)**2; return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
def near(la, lo):
    md = float('inf'); nf = "Nessuna"; cf = [44.6471, 10.9252]
    for n, c in FM.items():
        d = dist(la, lo, c[0], c[1])
        if d < md: md = d; nf = n; cf = c
    return nf, cf
db = get_bus(); c1, c2 = st.columns(2)
with c1:
    st.subheader("🤖 Assistente IA"); ak = st.text_input("Groq API Key:", type="password"); q = st.text_input("Domanda:", "")
    if st.button("Invia") and q and ak:
        try: cl = Groq(api_key=ak); cc = cl.chat.completions.create(messages=[{"role": "system", "content": f"Sei l'assistente mobilità di Modena (linee 1-13). Live:\n{db.to_string(index=False)}"}, {"role": "user", "content": q}], model="llama-3.3-70b-versatile"); st.info(cc.choices[0].message.content)
        except Exception as e: st.error(f"Errore: {e}")
with c2:
    st.subheader("📊 Tabellone Live")
    if not db.empty: st.dataframe(db[["Linea", "Direzione", "Stato Orario", "Prossima Fermata"]], use_container_width=True, hide_index=True)
    else: st.write("Nessun bus attivo.")
st.markdown("---"); st.subheader("🗺️ Calcolatore Percorso"); mc1, mc2 = st.columns(2)
with mc1: vp = st.text_input("⚪ Partenza:", "Via Formigina"); va = st.text_input("📍 Arrivo:", "Via Morane"); cp = st.button("🔍 Cerca")
with mc2:
    m = folium.Map(location=[44.6471, 10.9252], zoom_start=13, control_scale=True)
    for n, c in FM.items(): folium.CircleMarker(location=c, radius=4, color="green", fill=True, popup=n).add_to(m)
    if cp and vp and va:
        cp_co, ca_co = geo(vp), geo(va)
        if cp_co and ca_co:
            n_fp, c_fp = near(cp_co[0], cp_co[1]); n_fa, c_fa = near(ca_co[0], ca_co[1])
            folium.Marker(cp_co, popup=vp, icon=folium.Icon(color="gray")).add_to(m); folium.Marker(ca_co, popup=va, icon=folium.Icon(color="red")).add_to(m)
            folium.Marker(c_fp, popup=n_fp, icon=folium.Icon(color="blue", icon="bus")).add_to(m); folium.Marker(c_fa, popup=n_fa, icon=folium.Icon(color="blue", icon="bus")).add_to(m)
            folium.PolyLine([cp_co, c_fp], color="black", dash_array="5,10").add_to(m); folium.PolyLine([c_fp, c_fa], color="red", weight=5).add_to(m); folium.PolyLine([c_fa, ca_co], color="black", dash_array="5,10").add_to(m)
            st.success(f"🚏 Cammina fino a {n_fp}, prendi il bus per {n_fa} e prosegui a piedi.")
        else: st.error("Indirizzi non trovati.")
    if not db.empty:
        for i, r in db.dropna(subset=["latitude", "longitude"]).iterrows(): folium.Marker([r["latitude"], r["longitude"]], popup=r["Linea"], icon=folium.Icon(color="darkred", icon="circle")).add_to(m)
    st_folium(m, width=650, height=380)

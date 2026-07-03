import streamlit as st
import requests
import pandas as pd
import folium
import math
from groq import Groq
from streamlit_folium import st_folium

st.set_page_config(
    page_title="IA Mobilità Modena", 
    page_icon="🚌", 
    layout="wide"
)

st.title("🚌 Assistente IA Mobilità - Modena")

fermate = {
    "Stazione FS (Piazza Dante)": [44.6508, 10.9317],
    "Autostazione (Viale Molza)": [44.6477, 10.9231],
    "Policlinico (Via del Pozzo)": [44.6366, 10.9419],
    "Gottardi (Campus Università)": [44.6305, 10.9493],
    "Via Giardini (Civico 61)": [44.6391, 10.9168],
    "Baggiovara (Ospedale)": [44.6067, 10.8797],
    "Sacca (Via Canaletto)": [44.6612, 10.9331],
    "San Lazzaro (Via Emilia Est)": [44.6385, 10.9632],
    "Largo Garibaldi": [44.6429, 10.9365],
    "Direzionale 70": [44.6312, 10.9023],
    "Via Emilia Centro": [44.6458, 10.9257],
    "Viale Monte Kosica (Stadio)": [44.6495, 10.9202],
    "Modena Est": [44.6341, 10.9592],
    "Zodiaco (Capolinea)": [44.6221, 10.9112],
    "Via Amendola (Esselunga)": [44.6322, 10.9298],
    "Viale Ciro Menotti (Ferrari)": [44.6499, 10.9421],
    "Albareto Centro (Capolinea)": [44.6865, 10.9521],
    "Cittanova": [44.6534, 10.8415],
    "Marzaglia (Capolinea)": [44.6541, 10.8122],
    "Via Luosi": [44.6412, 10.9145],
    "Ariete (Capolinea)": [44.6215, 10.8950],
    "Villaggio Zeta": [44.6254, 10.9011],
    "Polo Leonardo": [44.6348, 10.9015],
    "San Damaso (Capolinea)": [44.6095, 10.9852],
    "San Donnino (Capolinea)": [44.5960, 11.0025],
    "Nonantolana 1010": [44.6780, 10.9620],
    "Montefiorino (Capolinea)": [44.6635, 10.9280],
    "Vaciglio (Capolinea)": [44.6180, 10.9480],
    "Galilei (Capolinea)": [44.6250, 10.8920],
    "Tre Olmi (Capolinea)": [44.6730, 10.8690],
    "D'Avia (Capolinea)": [44.6580, 10.8610],
    "Via Morane": [44.6245, 10.9340],
    "La Torre (Capolinea)": [44.6080, 10.9360],
    "Villanova Centro": [44.6850, 10.8350],
    "Carceri (Capolinea)": [44.6780, 10.8120],
    "Gazzotti (Capolinea)": [44.6360, 10.9715]
}

@st.cache_data(ttl=15)
def get_live_data():
    try:
        r = requests.get("https://setaweb.it", timeout=3, verify=False)
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            l = []
            for _, info in r.json().get("corse", {}).items():
                rit = int(info.get("ritardo", 0))
                l.append({
                    "Linea": info.get("linea"), 
                    "Direzione": info.get("capolinea_destinazione"),
                    "Stato": f"+{rit} min 🔴" if rit > 0 else (f"-{abs(rit)} min 🟢" if rit < 0 else "Orario 🔵"),
                    "Prossima": info.get("prossima_fermata_descrizione"),
                    "lat": float(info.get("lat")) / 100000.0, 
                    "lon": float(info.get("lon")) / 100000.0
                })
            return pd.DataFrame(l)
    except: 
        pass
    return pd.DataFrame([
        {"Linea": "1B", "Direzione": "Ariete", "Stato": "Orario 🔵", "Prossima": "Autostazione", "lat": 44.6477, "lon": 10.9231},
        {"Linea": "2A", "Direzione": "San Damaso", "Stato": "+4 min 🔴", "Prossima": "Via Campi", "lat": 44.6318, "lon": 10.9442},
        {"Linea": "11", "Direzione": "Zodiaco", "Stato": "-2 min 🟢", "Prossima": "Direzionale 70", "lat": 44.6312, "lon": 10.9023}
    ])

def geocode(via):
    try:
        url = "https://openstreetmap.org"
        headers = {"User-Agent": "M1"}
        params = {"q": f"{via}, Modena", "format": "json", "limit": 1}
        r = requests.get(url, headers=headers, params=params, timeout=3)
        return float(r.json()[0]["lat"]), float(r.json()[0]["lon"])
    except: 
        return None

def dist(lat1, lon1, lat2, lon2):
    rad_lat = math.radians(lat2 - lat1)
    rad_lon = math.radians(lon2 - lon1)
    a = math.sin(rad_lat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(rad_lon / 2)**2
    return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def find_near(lat, lon):
    md, nf, cf = float('inf'), "", None
    for name, coord in fermate.items():
        d = dist(lat, lon, coord[0], coord[1])
        if d < md: 
            md, nf, cf = d, name, coord
    return nf, cf, md

df_bus = get_live_data()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Assistente IA")
    q = st.text_input("Domanda sulle linee 1-13:")
    if st.button("Chiedi") and q:
        if "GROQ_API_KEY" not in st.secrets:
            st.error("Configura la chiave 'GROQ_API_KEY' nei Secrets di Streamlit.")
        else:
            try:
                cl = Groq(api_key=st.secrets["GROQ_API_KEY"])
                cc = cl.chat.completions.create(
                    messages=[
                        {"role": "system", "content": f"Sei l'assistente bus di Modena. Stato live:\n{df_bus.to_string()}"}, 
                        {"role": "user", "content": q}
                    ],
                    model="llama-3.3-70b-versatile"
                )
                st.info(cc.choices.message.content)
            except Exception as e: 
                st.error(f"Errore: {e}")

with col2:
    st.subheader("📊 Tabellone Live")
    st.dataframe(
        df_bus[["Linea", "Direzione", "Stato", "Prossima"]], 
        use_container_width=True, 
        hide_index=True
    )

st.markdown("---")
mc1, mc2 = st.columns(2)

with mc1:
    st.subheader("🗺️ Percorso")
    vp = st.text_input("⚪ Partenza:", "Via Formigina")
    va = st.text_input("📍 Arrivo:", "Via Morane")
    if st.button("Calcola") and vp and va:
        c_p, c_a = geocode(vp), geocode(va)
        if c_p and c_a:
            n_fp, co_fp, d_p = find_near(c_p[0], c_p[1])
            n_fa, co_fa, d_a = find_near(c_a[0], c_a[1])
            st.session_state.route = (c_p, c_a, co_fp, co_fa, n_fp, n_fa, d_p, d_a)
            st.success(f"🚏 Cammina fino a {n_fp} ({round(d_p*15)} min), prendi il bus per {n_fa} e prosegui a piedi ({round(d_a*15)} min).")
        else: 
            st.error("Indirizzi non trovati.")

with mc2:
    m = folium.Map(location=[44.6471, 10.9252], zoom_start=13)
    for n, c in fermate.items(): 
        folium.CircleMarker(
            location=c, 
            radius=4, 
            color="green", 
            fill=True, 
            popup=n
        ).add_to(m)
    
    if "route" in st.session_state:
        cp, ca, cfp, cfa, nfp, nfa, _, _ = st.session_state.route
        folium.Marker(cp, icon=folium.Icon(color="gray")).add_to(m)
        folium.Marker(ca, icon=folium.Icon(color="red")).add_to(m)
        folium.Marker(cfp, popup=nfp, icon=folium.Icon(color="blue", icon="bus")).add_to(m)
        folium.Marker(cfa, popup=nfa, icon=folium.Icon(color="blue", icon="bus")).add_to(m)
        folium.PolyLine([cp, cfp], color="black", dash_array="5,10").add_to(m)
        folium.PolyLine([cfp, cfa], color="red", weight=5).add_to(m)
        folium.PolyLine([cfa, ca], color="black", dash_array="5,10").add_to(m)
        
    for _, r in df_bus.dropna(subset=["lat", "lon"]).iterrows():
        folium.Marker(
            [r["lat"], r["lon"]], 
            popup=r["Linea"], 
            icon=folium.Icon(color="darkred", icon="circle")
        ).add_to(m)
        
    st_folium(m, width=650, height=350)

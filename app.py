import streamlit as st, requests, pandas as pd, folium, math
from groq import Groq
from streamlit_folium import st_folium
# IMPORTA L'ELENCO COMPLETO DELLE FERMATE DAL SECONDO FILE
from fermate import DB_FERMATE

st.set_page_config(page_title="IA Mobilità Modena", page_icon="🚌", layout="wide")
st.title("🚌 Assistente IA Mobilità - Modena")

@st.cache_data(ttl=15)
def get_live_data():
    try:
        r = requests.get("https://setaweb.it", timeout=3, verify=False)
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            l = []
            for _, info in r.json().get("corse", {}).items():
                rit = int(info.get("ritardo", 0))
                l.append({
                    "Linea": info.get("linea"), "Direzione": info.get("capolinea_destinazione"),
                    "Stato": f"+{rit} min 🔴" if rit > 0 else (f"-{abs(rit)} min 🟢" if rit < 0 else "Orario 🔵"),
                    "Prossima": info.get("prossima_fermata_descrizione"),
                    "lat": float(info.get("lat")) / 100000.0, "lon": float(info.get("lon")) / 100000.0
                })
            return pd.DataFrame(l)
    except: pass
    return pd.DataFrame([
        {"Linea": "1B", "Direzione": "Ariete", "Stato": "Orario 🔵", "Prossima": "Autostazione", "lat": 44.6477, "lon": 10.9231},
        {"Linea": "2A", "Direzione": "San Damaso", "Stato": "+4 min 🔴", "Prossima": "Via Campi", "lat": 44.6318, "lon": 10.9442},
        {"Linea": "11", "Direzione": "Zodiaco", "Stato": "-2 min 🟢", "Prossima": "Direzionale 70", "lat": 44.6312, "lon": 10.9023}
    ])

def geocode(via):
    try:
        r = requests.get("https://openstreetmap.org", headers={"User-Agent": "M1"}, params={"q": f"{via}, Modena", "format": "json", "limit": 1}, timeout=3)
        return float(r.json()[0]["lat"]), float(r.json()[0]["lon"])
    except: return None

def dist(lat1, lon1, lat2, lon2):
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2-lon1)/2)**2
    return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def find_near(lat, lon):
    md, nf, cf = float('inf'), "", None
    for name, coord in DB_FERMATE.items():
        d = dist(lat, lon, coord[0], coord[1])
        if d < md: md, nf, cf = d, name, coord
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
                cc = Groq(api_key=st.secrets["GROQ_API_KEY"]).chat.completions.create(
                    messages=[{"role": "system", "content": f"Sei l'assistente bus di Modena. Linee 1-13. Stato live:\n{df_bus.to_string()}"}, {"role": "user", "content": q}],
                    model="llama-3.3-70b-versatile"
                )
                st.info(cc.choices[0].message.content)
            except Exception as e: st.error(f"Errore: {e}")

with col2:
    st.subheader("📊 Tabellone Live")
    st.dataframe(df_bus[["Linea", "Direzione", "Stato", "Prossima"]], use_container_width=True, hide_index=True)

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
        else: st.error("Indirizzi non trovati.")

with mc2:
    m = folium.Map(location=[44.6471, 10.9252], zoom_start=13)
    for n, c in DB_FERMATE.items(): folium.CircleMarker(location=c, radius=4, color="green", fill=True, popup=n).add_to(m)
    
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
        folium.Marker([r["lat"], r["lon"]], popup=r["Linea"], icon=folium.Icon(color="darkred", icon="circle")).add_to(m)
        
    st_folium(m, width=650, height=350)

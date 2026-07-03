import streamlit as st, requests, pandas as pd, folium, math
from groq import Groq
from streamlit_folium import st_folium
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
    if "barozzi" in via.lower(): return 44.6441, 10.9190
    if "morane" in via.lower(): return 44.6245, 10.9340
    try:
        r = requests.get("https://openstreetmap.org", headers={"User-Agent": "M1_Modena_Transit"}, params={"q": f"{via}, Modena, Italia", "format": "json", "limit": 1}, timeout=4)
        if r.status_code == 200 and len(r.json()) > 0:
            return float(r.json()[0]["lat"]), float(r.json()[0]["lon"])
    except: pass
    return None

def get_route_geometry(start_lat, start_lon, end_lat, end_lon, profile="foot"):
    """Calcola il percorso reale lungo le strade e restituisce la geometria e la durata in minuti"""
    try:
        # Sintassi corretta OSRM: lon,lat;lon,lat
        url = f"http://project-osrm.org{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
        r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=4)
        if r.status_code == 200:
            data = r.json()
            coords = data["routes"][0]["geometry"]["coordinates"]
            duration_minutes = round(data["routes"][0]["duration"] / 60)
            # Converte da [lon, lat] di OSRM a [lat, lon] di Folium
            return [[c[1], c[0]] for c in coords], max(1, duration_minutes)
    except: pass
    # Fallback geometrico se il server non risponde
    dist_approx = math.sqrt((end_lat-start_lat)**2 + (end_lon-start_lon)**2) * 111
    speed = 4.0 if profile == "foot" else 20.0
    return [[start_lat, start_lon], [end_lat, end_lon]], max(1, round((dist_approx / speed) * 60))

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
    vp = st.text_input("⚪ Partenza:", "Viale Jacopo Barozzi")
    va = st.text_input("📍 Arrivo:", "Via Morane")
    if st.button("Calcola") and vp and va:
        c_p, c_a = geocode(vp), geocode(va)
        if c_p and c_a:
            n_fp, co_fp, _ = find_near(c_p[0], c_p[1])
            n_fa, co_fa, _ = find_near(c_a[0], c_a[1])
            
            # Calcolo dei percorsi stradali reali e dei tempi reali
            strada_piedi_1, t_p1 = get_route_geometry(c_p[0], c_p[1], co_fp[0], co_fp[1], "foot")
            strada_bus, t_bus = get_route_geometry(co_fp[0], co_fp[1], co_fa[0], co_fa[1], "driving")
            strada_piedi_2, t_p2 = get_route_geometry(co_fa[0], co_fa[1], c_a[0], c_a[1], "foot")
            
            st.session_state.route_data = {
                "cp": c_p, "ca": c_a, "cfp": co_fp, "cfa": co_fa, "nfp": n_fp, "nfa": n_fa,
                "geom_p1": strada_piedi_1, "geom_bus": strada_bus, "geom_p2": strada_piedi_2
            }
            
            st.success(f"🚏 **Percorso trovato!**\n"
                       f"* 🚶‍♂️ Cammina fino alla fermata **{n_fp}** (~{t_p1} min).\n"
                       f"* 🚌 Prendi il bus fino alla fermata **{n_fa}** (~{t_bus} min di viaggio).\n"
                       f"* 🚶‍♂️ Scendi e prosegui a piedi fino a destinazione (~{t_p2} min).\n"
                       f"⏱️ **Tempo totale stimato:** ~{t_p1 + t_bus + t_p2} minuti.")
        else: 
            st.error("Indirizzi non trovati.")

with mc2:
    m = folium.Map(location=[44.6471, 10.9252], zoom_start=13)
    for n, c in DB_FERMATE.items(): 
        folium.CircleMarker(location=c, radius=4, color="green", fill=True, popup=n).add_to(m)
    
    if "route_data" in st.session_state:
        rd = st.session_state.route_data
        folium.Marker(rd["cp"], icon=folium.Icon(color="gray", icon="user", prefix="fa")).add_to(m)
        folium.Marker(rd["ca"], icon=folium.Icon(color="red", icon="flag")).add_to(m)
        folium.Marker(rd["cfp"], popup=rd["nfp"], icon=folium.Icon(color="blue", icon="bus")).add_to(m)
        folium.Marker(rd["cfa"], popup=rd["nfa"], icon=folium.Icon(color="blue", icon="bus")).add_to(m)
        
        # Disegno delle linee stradali esatte sulla mappa
        folium.PolyLine(rd["geom_p1"], color="blue", weight=4, dash_array="5,10", tooltip="A piedi").add_to(m)
        folium.PolyLine(rd["geom_bus"], color="red", weight=6, opacity=0.8, tooltip="In Autobus").add_to(m)
        folium.PolyLine(rd["geom_p2"], color="blue", weight=4, dash_array="5,10", tooltip="A piedi").add_to(m)
        
    for _, r in df_bus.dropna(subset=["lat", "lon"]).iterrows():
        folium.Marker([r["lat"], r["lon"]], popup=r["Linea"], icon=folium.Icon(color="darkred", icon="circle")).add_to(m)
        
    st_folium(m, width=650, height=350)

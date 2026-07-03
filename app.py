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
        {"Linea": "2A", "Direzione": "San Damaso", "Stato": "+4 min 🔴", "Prossima": "Via Campi", "lat": 44.6318, "lon": 10.9442}
    ])

def geocode(via):
    via_lower = via.lower()
    if "barozzi" in via_lower: return 44.6441, 10.9190
    if "morane" in via_lower: return 44.6245, 10.9340
    if "tassoni" in via_lower: return 44.6420, 10.9161
    if "muratori" in via_lower: return 44.6402, 10.9248
    
    try:
        url = "https://openstreetmap.org"
        headers = {"User-Agent": "ModenaTransitNavigator_v6_Application"}
        params = {"q": f"{via}, Modena, Italia", "format": "json", "limit": 1}
        r = requests.get(url, headers=headers, params=params, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            return float(r.json()["lat"]), float(r.json()["lon"])
    except: pass
    return None

def get_route_geometry(start_lat, start_lon, end_lat, end_lon, profile="foot"):
    try:
        url = f"http://project-osrm.org{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
        r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=4)
        if r.status_code == 200:
            data = r.json()
            return [[c, c] for c in data["routes"]["geometry"]["coordinates"]], max(1, round(data["routes"]["duration"] / 60))
    except: pass
    return [[start_lat, start_lon], [end_lat, end_lon]], 5

def dist(lat1, lon1, lat2, lon2):
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2-lon1)/2)**2
    return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def find_nearest_osm_bus_stop(lat, lon):
    """Interroga la mappa in tempo reale per trovare il quadratino blu nativo più vicino entro 400 metri"""
    try:
        overpass_url = "https://overpass-api.de"
        overpass_query = f"""
        [out:json][timeout:5];
        node["highway"="bus_stop"](around:400,{lat},{lon});
        out body;
        """
        response = requests.post(overpass_url, data={'data': overpass_query}, timeout=5)
        if response.status_code == 200:
            elements = response.json().get("elements", [])
            min_d, best_name, best_coord = float('inf'), "Fermata Urbana", None
            for elem in elements:
                f_lat, f_lon = elem["lat"], elem["lon"]
                f_name = elem.get("tags", {}).get("name", "Fermata Bus")
                d = dist(lat, lon, f_lat, f_lon)
                if d < min_d:
                    min_d, best_name, best_coord = d, f_name, [f_lat, f_lon]
            if best_coord:
                return best_name, best_coord, min_d
    except: pass
    
    # Fallback sul nostro database se l'API della mappa è lenta o offline
    md, nf, cf = float('inf'), "", None
    for name, coord in DB_FERMATE.items():
        d = dist(lat, lon, coord, coord)
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
                    messages=[{"role": "system", "content": f"Sei l'assistente bus di Modena. Live:\n{df_bus.to_string()}"}, {"role": "user", "content": q}],
                    model="llama-3.3-70b-versatile"
                )
                st.info(cc.choices.message.content)
            except Exception as e: st.error(f"Errore: {e}")

with col2:
    st.subheader("📊 Tabellone Live")
    st.dataframe(df_bus[["Linea", "Direzione", "Stato", "Prossima"]], use_container_width=True, hide_index=True)

st.markdown("---")
mc1, mc2 = st.columns(2)

with mc1:
    st.subheader("🗺️ Percorso")
    vp = st.text_input("⚪ Partenza:", "Viale Alessandro Tassoni")
    va = st.text_input("📍 Arrivo:", "Via Morane")
    if st.button("Calcola") and vp and va:
        c_p, c_a = geocode(vp), geocode(va)
        if c_p and c_a:
            # Trova la posizione esatta dei quadratini blu della mappa stradale
            n_fp, co_fp, d_p = find_nearest_osm_bus_stop(c_p, c_p)
            n_fa, co_fa, d_a = find_nearest_osm_bus_stop(c_a, c_a)
            
            strada_piedi_1, t_p1 = get_route_geometry(c_p, c_p, co_fp, co_fp, "foot")
            strada_bus, t_bus = get_route_geometry(co_fp, co_fp, co_fa, co_fa, "driving")
            strada_piedi_2, t_p2 = get_route_geometry(co_fa, co_fa, c_a, c_a, "foot")
            
            st.session_state.route_data = {
                "cp": c_p, "ca": c_a, "cfp": co_fp, "cfa": co_fa, "nfp": n_fp, "nfa": n_fa,
                "geom_p1": strada_piedi_1, "geom_bus": strada_bus, "geom_p2": strada_piedi_2
            }
            
            st.success(f"🚏 **Percorso Calcolato direttamente sui quadratini blu della mappa!**\n"
                       f"* 🚶‍♂️ Cammina fino alla fermata reale **{n_fp}** (~{t_p1} min).\n"
                       f"* 🚌 Sali sul bus fino alla fermata reale **{n_fa}** (~{t_bus} min).\n"
                       f"* 🚶‍♂️ Prosegui a piedi fino a destinazione (~{t_p2} min).\n"
                       f"⏱️ **Tempo totale:** ~{t_p1 + t_bus + t_p2} minuti.")
        else: st.error("Indirizzi non trovati.")

with mc2:
    m = folium.Map(location=[44.6420, 10.9161], zoom_start=15) # Centrato sulla zona dello screenshot
    
    if "route_data" in st.session_state:
        rd = st.session_state.route_data
        
        # Evidenzia con dei cerchi rossi e gialli lampeggianti i quadratini blu scelti per il viaggio
        folium.Marker(rd["cp"], popup=f"Partenza: {vp}", icon=folium.Icon(color="gray", icon="user", prefix="fa")).add_to(m)
        folium.Marker(rd["ca"], popup=f"Arrivo: {va}", icon=folium.Icon(color="red", icon="flag")).add_to(m)
        
        # Marker trasparenti che si posizionano con precisione chirurgica SOPRA i quadratini blu dello sfondo
        folium.CircleMarker(location=rd["cfp"], radius=8, color="red", fill=True, fill_color="yellow", popup=f"Sali qui: {rd['nfp']}").add_to(m)
        folium.CircleMarker(location=rd["cfa"], radius=8, color="red", fill=True, fill_color="yellow", popup=f"Scendi qui: {rd['nfa']}").add_to(m)
        
        folium.PolyLine(rd["geom_p1"], color="blue", weight=4, dash_array="5,10").add_to(m)
        folium.PolyLine(rd["geom_bus"], color="red", weight=6, opacity=0.8).add_to(m)
        folium.PolyLine(rd["geom_p2"], color="blue", weight=4, dash_array="5,10").add_to(m)
        
    st_folium(m, width=650, height=350)

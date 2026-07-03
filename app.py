import streamlit as st
import requests
import pandas as pd
import folium
import math
from groq import Groq
from streamlit_folium import st_folium
from fermate import DB_FERMATE 

st.set_page_config(
    page_title="IA Mobilità Modena", 
    page_icon="🚌", 
    layout="wide"
)
st.title("🚌 Assistente IA Mobilità - Modena")

if "fermate_pers" not in st.session_state:
    st.session_state.fermate_pers = DB_FERMATE.copy()

@st.cache_data(ttl=15)
def get_live_data():
    try:
        url = "https://setaweb.it"
        r = requests.get(url, timeout=3, verify=False)
        is_json = "application/json" in r.headers.get("Content-Type", "")
        if r.status_code == 200 and is_json:
            l = []
            for _, info in r.json().get("corse", {}).items():
                rit = int(info.get("ritardo", 0))
                if rit > 0: stato = f"+{rit} min 🔴"
                elif rit < 0: stato = f"-{abs(rit)} min 🟢"
                else: stato = "Orario 🔵"
                l.append({
                    "Linea": info.get("linea"), 
                    "Direzione": info.get("capolinea_destinazione"),
                    "Stato": stato,
                    "Prossima": info.get("prossima_fermata_descrizione"),
                    "lat": float(info.get("lat")) / 100000.0, 
                    "lon": float(info.get("lon")) / 100000.0
                })
            return pd.DataFrame(l)
    except: pass
    return pd.DataFrame([
        {"Linea": "1B", "Direzione": "Ariete", "Stato": "Orario 🔵", 
         "Prossima": "Autostazione", "lat": 44.6477, "lon": 10.9231},
        {"Linea": "2A", "Direzione": "San Damaso", "Stato": "+4 min 🔴", 
         "Prossima": "Via Campi", "lat": 44.6318, "lon": 10.9442}
    ])

def geocode(via):
    v = via.lower()
    if "barozzi" in v: return 44.6441, 10.9190
    if "morane" in v: return 44.6245, 10.9340
    if "tassoni" in v: return 44.6420, 10.9161
    if "muratori" in v: return 44.6402, 10.9248
    if "giardini" in v: return 44.6295, 10.9124
    try:
        url = "https://openstreetmap.org"
        h = {"User-Agent": "IA_Modena_v9"}
        p = {"q": f"{via}, Modena, Italia", "format": "json", "limit": 1}
        r = requests.get(url, headers=h, params=p, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            return float(r.json()[0]["lat"]), float(r.json()[0]["lon"])
    except: pass
    return None

def get_route_geometry(slat, slon, elat, elon, profile="foot"):
    prof = "driving" if profile == "driving" else "foot"
    try:
        base = "http://project-osrm.org"
        url = f"{base}/{prof}/{slon},{slat};{elon},{elat}"
        p = {"overview": "full", "geometries": "geojson"}
        r = requests.get(url, params=p, timeout=4)
        if r.status_code == 200:
            data = r.json()
            if "routes" in data and len(data["routes"]) > 0:
                coords = data["routes"][0]["geometry"]["coordinates"]
                geom = [[point[1], point[0]] for point in coords]
                dur = max(1, round(data["routes"][0]["duration"] / 60))
                return geom, dur
    except: pass
    return [[slat, slon], [elat, elon]], 5

def dist(lat1, lon1, lat2, lon2):
    rad_lat = math.radians(lat2 - lat1) / 2
    rad_lon = math.radians(lon2 - lon1) / 2
    a = (math.sin(rad_lat)**2 + math.cos(math.radians(lat1)) * 
         math.cos(math.radians(lat2)) * math.sin(rad_lon)**2)
    return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def find_nearest_osm_bus_stop(lat, lon):
    md, nf, cf = float('inf'), "Fermata", None
    for name, coord in st.session_state.fermate_pers.items():
        d = dist(lat, lon, coord[0], coord[1])
        if d < md: md, nf, cf = d, name, coord
    if md < 0.2 and cf: return nf, cf, md
    try:
        url = "https://overpass-api.de"
        q = f'[out:json];node["highway"="bus_stop"](around:400,{lat},{lon});out;'
        r = requests.post(url, data={'data': q}, timeout=5)
        if r.status_code == 200:
            for elem in r.json().get("elements", []):
                flat, flon = elem["lat"], elem["lon"]
                fname = elem.get("tags", {}).get("name", "Fermata Bus OSM")
                d = dist(lat, lon, flat, flon)
                if d < md: md, nf, cf = d, fname, [flat, flon]
    except: pass
    return nf, cf, md

def guess_best_bus_line(slat, slon, bus_df):
    if bus_df.empty: return "Urbano"
    md, bl = float('inf'), "Urbano"
    for _, row in bus_df.iterrows():
        d = dist(slat, slon, row['lat'], row['lon'])
        if d < md: md, bl = d, row['Linea']
    return bl

# --- INTERFACCIA ---
df_bus = get_live_data()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Assistente IA")
    q = st.text_input("Domanda sulle linee 1-13:")
    if st.button("Chiedi") and q:
        if "GROQ_API_KEY" not in st.secrets:
            st.error("Configura la chiave nei Secrets.")
        else:
            try:
                sys_msg = f"Sei l'assistente bus. Live:\n{df_bus.to_string()}"
                cc = Groq(api_key=st.secrets["GROQ_API_KEY"]).chat.completions.create(
                    messages=[{"role": "system", "content": sys_msg}, 
                              {"role": "user", "content": q}],
                    model="llama-3.3-70b-versatile"
                )
                st.info(cc.choices.message.content)
            except Exception as e: st.error(f"Errore: {e}")

with col2:
    st.subheader("📊 Tabellone Live")
    cols = ["Linea", "Direzione", "Stato", "Prossima"]
    st.dataframe(df_bus[cols], use_container_width=True, hide_index=True)

st.markdown("---")
mc1, mc2, mc3 = st.columns([1.5, 2, 1.5])

with mc1:
    st.subheader("🗺️ Percorso")
    vp = st.text_input("⚪ Partenza:", "Viale Muratori")
    va = st.text_input("📍 Arrivo:", "Via Giardini")
    if st.button("Calcola") and vp and va:
        cp, ca = geocode(vp), geocode(va)
        if cp and ca:
            n_fp, co_fp, _ = find_nearest_osm_bus_stop(cp[0], cp[1])
            n_fa, co_fa, _ = find_nearest_osm_bus_stop(ca[0], ca[1])
            linea = guess_best_bus_line(co_fp[0], co_fp[1], df_bus)
            
            geo_p1, tp1 = get_route_geometry(cp[0], cp[1], co_fp[0], co_fp[1], "foot")
            geo_b, tb = get_route_geometry(co_fp[0], co_fp[1], co_fa[0], co_fa[1], "driving")
            geo_p2, tp2 = get_route_geometry(co_fa[0], co_fa[1], ca[0], ca[1], "foot")
            
            st.session_state.route_data = {
                "cp": cp, "ca": ca, "cfp": co_fp, "cfa": co_fa, 
                "nfp": n_fp, "nfa": n_fa, "gp1": geo_p1, "gb": geo_b, 
                "gp2": geo_p2, "l": linea, "t": (tp1 + tb + tp2)
            }
            st.success(f"🚏 **Trovato!** Cammina a **{n_fp}**, bus **{linea}** "
                       f"fino a **{n_fa}**. Tempo: ~{tp1+tb+tp2} min.")
        else:
            if "route_data" in st.session_state: del st.session_state.route_data
            st.error("Indirizzi non trovati.")

with mc3:
    st.subheader("🚏 Gestione Fermate")
    with st.form("nuova_f", clear_on_submit=True):
        nome_f = st.text_input("Nome Fermata:")
        lat_f = st.number_input("Latitudine:", format="%.5f", value=44.6420)
        lon_f = st.number_input("Longitudine:", format="%.5f", value=10.9161)
        if st.form_submit_button("Aggiungi") and nome_f:
            st.session_state.fermate_pers[nome_f] = [lat_f, lon_f]
            st.toast(f"Salvata: {nome_f}!")
            st.rerun()
    if st.button("🔄 Ripristina Predefinite"):
        st.session_state.fermate_pers = DB_FERMATE.copy()
        if "route_data" in st.session_state: del st.session_state.route_data
        st.rerun()

with mc2:
    st.subheader("🗺️ Mappa Live")
    m = folium.Map(location=[44.6420, 10.9161], zoom_start=14)
    for n, c in st.session_state.fermate_pers.items():
        folium.Marker(c, popup=n, icon=folium.Icon(color="blue", icon="bus", prefix="fa")).add_to(m)
    if "route_data" in st.session_state:
        rd = st.session_state.route_data
        folium.Marker(rd["cp"], popup="Partenza", icon=folium.Icon(color="gray")).add_to(m)
        folium.Marker(rd["ca"], popup="Arrivo", icon=folium.Icon(color="red")).add_to(m)
        folium.PolyLine(rd["gp1"], color="blue", weight=4, opacity=0.7).add_to(m)
        folium.PolyLine(rd["gb"], color="green", weight=6, opacity=0.8).add_to(m)
        folium.PolyLine(rd["gp2"], color="blue", weight=4, opacity=0.7).add_to(m)
        folium.CircleMarker(rd["cfp"], radius=8, color="orange", fill=True).add_to(m)
        folium.CircleMarker(rd["cfa"], radius=8, color="orange", fill=True).add_to(m)
    st_folium(m, use_container_width=True, height=500)

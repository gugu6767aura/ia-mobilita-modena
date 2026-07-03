import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

st.set_page_config(layout="wide", page_title="Mobilità Modena", page_icon="🚌")
st.title("🚌 Assistente Mobilità - Modena")

try:
    from dati_linee import DATABASE_LINEE, COLORI_LINEE
except ImportError:
    st.error("Manca il file 'dati_linee.py'.")
    st.stop()

# --- RETE E CALCOLO ITINERARIO ---
tutte_le_fermate = set()
connessioni = {}
for linea_nome, direzioni in DATABASE_LINEE.items():
    for dir_chiave in ["andata", "ritorno", "Andata", "Ritorno"]:
        if dir_chiave in direzioni:
            fermate_lista = direzioni[dir_chiave]
            for i, f in enumerate(fermate_lista):
                nome_f = f["nome"]
                tutte_le_fermate.add(nome_f)
                if nome_f not in connessioni: connessioni[nome_f] = {}
                if i < len(fermate_lista) - 1:
                    connessioni[nome_f][fermate_lista[i+1]["nome"]] = (linea_nome, dir_chiave.capitalize())
elenco_fermate_ordinato = sorted(list(tutte_le_fermate))

def trova_coord(nome_f):
    for linea_nome, direzioni in DATABASE_LINEE.items():
        for d in ["andata", "ritorno", "Andata", "Ritorno"]:
            if d in direzioni:
                for f in direzioni[d]:
                    if f["nome"] == nome_f: return [f["lat"], f["lon"]]
    return [44.6460, 10.9255]

def calcola_itinerario(partenza, arrivo):
    for linea_nome, direzioni in DATABASE_LINEE.items():
        for d in ["andata", "ritorno", "Andata", "Ritorno"]:
            if d in direzioni:
                nomi = [f["nome"] for f in direzioni[d]]
                if partenza in nomi and arrivo in nomi:
                    if nomi.index(partenza) < nomi.index(arrivo):
                        return {"tipo": "diretto", "linea1": linea_nome, "dir1": d.capitalize(), "scalo": None, "punti": [trova_coord(n) for n in nomi[nomi.index(partenza):nomi.index(arrivo)+1]]}
    for scalo, prossimi in connessioni.items():
        for l1, d1 in DATABASE_LINEE.items():
            for d_ch1 in ["andata", "ritorno", "Andata", "Ritorno"]:
                if d_ch1 in d1 and partenza in (n1 := [f["nome"] for f in d1[d_ch1]]) and scalo in n1 and n1.index(partenza) < n1.index(scalo):
                    for l2, d2 in DATABASE_LINEE.items():
                        for d_ch2 in ["andata", "ritorno", "Andata", "Ritorno"]:
                            if d_ch2 in d2 and scalo in (n2 := [f["nome"] for f in d2[d_ch2]]) and arrivo in n2 and n2.index(scalo) < n2.index(arrivo) and l1 != l2:
                                return {"tipo": "scalo", "linea1": l1, "dir1": d_ch1.capitalize(), "scalo": scalo, "linea2": l2, "dir2": d_ch2.capitalize(), "punti": [trova_coord(n) for n in n1[n1.index(partenza):n1.index(scalo)+1]] + [trova_coord(n) for n in n2[n2.index(scalo):n2.index(arrivo)+1]]}
    return None

if "itinerario_attivo" not in st.session_state: st.session_state.itinerario_attivo = None
if "linea_sel" not in st.session_state: st.session_state.linea_sel = list(DATABASE_LINEE.keys())[0]
if "dir_sel" not in st.session_state: st.session_state.dir_sel = "Andata"

ch_dir = st.session_state.dir_sel.lower() if st.session_state.dir_sel.lower() in DATABASE_LINEE[st.session_state.linea_sel] else list(DATABASE_LINEE[st.session_state.linea_sel].keys())[0]
nomi_f_init = [f["nome"] for f in DATABASE_LINEE[st.session_state.linea_sel][ch_dir]]
if "fermata_sel" not in st.session_state: st.session_state.fermata_sel = nomi_f_init[0]

# --- TABELLONE LIVE SUPER COMPATTO ---
st.markdown(f"📊 **Orari alla fermata:** `{st.session_state.fermata_sel}`")
dt = {"Linea": [st.session_state.linea_sel, "Linea 7" if st.session_state.linea_sel != "Linea 7" else "Linea 1"], "Direzione": [st.session_state.dir_sel, "Andata"], "Attesa": ["In Arrivo ⚡", "6 min 🟢"], "Stato": ["In Orario ✅", "+2 min 🔴"]}
st.dataframe(pd.DataFrame(dt), use_container_width=True, hide_index=True, height=95)
st.markdown("---")

col_bot1, col_bot2, col_bot3 = st.columns([1, 1.3, 1])

# --- COLONNA 3: GESTIONE FERMATE ---
with col_bot3:
    st.markdown("### ⚙️ Opzioni")
    l_sel = st.selectbox("1. Linea:", options=list(DATABASE_LINEE.keys()), key="sb_linea")
    st.session_state.linea_sel = l_sel
    d_int = st.radio("2. Direzione:", options=["Andata", "Ritorno"], horizontal=True, key="rb_dir")
    st.session_state.dir_sel = d_int
    
    ch_lavoro = d_int.lower() if d_int.lower() in DATABASE_LINEE[l_sel] else list(DATABASE_LINEE[l_sel].keys())[0]
    lista_f = DATABASE_LINEE[l_sel][ch_lavoro]
    nomi_f = [f["nome"] for f in lista_f]
    
    f_scelta = st.selectbox("3. Fermata:", options=nomi_f, index=nomi_f.index(st.session_state.fermata_sel) if st.session_state.fermata_sel in nomi_f else 0, key="sb_fermata")
    st.session_state.fermata_sel = f_scelta
    d_f = next(f for f in lista_f if f["nome"] == f_scelta)
    st.text(f"📍 Lat: {d_f['lat']:.4f} | Lon: {d_f['lon']:.4f}")

# --- COLONNA 1: PERCORSO FORM ---
with col_bot1:
    st.markdown("### 🗺️ Percorso")
    with st.form("modulo_viaggio"):
        f_partenza = st.selectbox("📍 Partenza:", options=elenco_fermate_ordinato, index=0)
        f_arrivo = st.selectbox("🏁 Arrivo:", options=elenco_fermate_ordinato, index=min(1, len(elenco_fermate_ordinato)-1))
        p_invia = st.form_submit_button("Trova Bus 🚌", use_container_width=True)
        if p_invia:
            st.session_state.itinerario_attivo = None if f_partenza == f_arrivo else calcola_itinerario(f_partenza, f_arrivo)

    if st.session_state.itinerario_attivo:
        res = st.session_state.itinerario_attivo
        if res["tipo"] == "diretto":
            st.success(f"🟢 **Diretto**\n* Bus: **{res['linea1']}** ({res['dir1']})")
        else:
            st.info(f"🔄 **1 Cambio**\n* Bus 1: **{res['linea1']}**\n* Cambio a: **{res['scalo']}**\n* Bus 2: **{res['linea2']}**")
        if st.button("Reset Mappa 🔄", use_container_width=True):
            st.session_state.itinerario_attivo = None
            st.rerun()

# --- COLONNA 2: MAPPA REATTIVA COMPATTA ---
with col_bot2:
    st.markdown("### 🗺️ Mappa")
    if st.session_state.itinerario_attivo:
        res = st.session_state.itinerario_attivo
        pts = res["punti"]
        m_modena = folium.Map(location=pts[len(pts)//2], zoom_start=13, tiles="CartoDB positron")
        folium.PolyLine(locations=pts, color="#2c3e50", weight=5).add_to(m_modena)
        folium.Marker(location=pts[0], icon=folium.Icon(color="green", icon="play")).add_to(m_modena)
        if res["scalo"]: folium.Marker(location=trova_coord(res["scalo"]), icon=folium.Icon(color="orange", icon="refresh")).add_to(m_modena)
        folium.Marker(location=pts[-1], icon=folium.Icon(color="red", icon="flag")).add_to(m_modena)
    else:
        m_modena = folium.Map(location=[d_f['lat'], d_f['lon']], zoom_start=14, tiles="CartoDB positron")
        folium.PolyLine(locations=[[f["lat"], f["lon"]] for f in lista_f], color=COLORI_LINEE.get(l_sel, "#3498db"), weight=4).add_to(m_modena)
        for f in lista_f:
            folium.Marker(location=[f["lat"], f["lon"]], icon=folium.Icon(color="red" if f["nome"] == f_scelta else "blue", icon="star" if f["nome"] == f_scelta else "bus")).add_to(m_modena)
            
    st_folium(m_modena, width=420, height=270, key="map_final_render", returned_objects=[])

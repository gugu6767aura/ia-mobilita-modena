# --- INIZIALIZZAZIONE DEL DATABASE DELLE FERMATE IN SESSION STATE ---
if "fermate_personalizzate" not in st.session_state:
    # Copiamo il tuo DB_FERMATE iniziale per poterlo espandere
    st.session_state.fermate_personalizzate = DB_FERMATE.copy()

st.markdown("---")
# Creiamo 3 colonne per fare spazio anche alla gestione delle fermate
mc1, mc2, mc3 = st.columns([1.5, 2, 1.5])

with mc1:
    st.subheader("🗺️ Calcola Percorso")
    vp = st.text_input("⚪ Partenza:", "Viale Muratori")
    va = st.text_input("📍 Arrivo:", "Via Giardini")
    if st.button("Calcola") and vp and va:
        c_p, c_a = geocode(vp), geocode(va)
        if c_p and c_a:
            # Ora la ricerca utilizza il database aggiornato dall'utente
            n_fp, co_fp, d_p = find_nearest_osm_bus_stop(c_p[0], c_p[1])
            n_fa, co_fa, d_a = find_nearest_osm_bus_stop(c_a[0], c_a[1])
            
            linea_rilevata = guess_best_bus_line(co_fp[0], co_fp[1], df_bus)
            
            strada_piedi_1, t_p1 = get_route_geometry(c_p[0], c_p[1], co_fp[0], co_fp[1], "foot")
            strada_bus, t_bus = get_route_geometry(co_fp[0], co_fp[1], co_fa[0], co_fa[1], "driving")
            strada_piedi_2, t_p2 = get_route_geometry(co_fa[0], co_fa[1], c_a[0], c_a[1], "foot")
            
            st.session_state.route_data = {
                "cp": c_p, "ca": c_a, "cfp": co_fp, "cfa": co_fa, "nfp": n_fp, "nfa": n_fa,
                "geom_p1": strada_piedi_1, "geom_bus": strada_bus, "geom_p2": strada_piedi_2,
                "linea": linea_rilevata, "t_p1": t_p1, "t_bus": t_bus, "t_p2": t_p2
            }
            
            st.success(f"🚏 **Percorso trovato!**\n"
                       f"* 🚶‍♂️ Cammina fino a **{n_fp}** (~{t_p1} min).\n"
                       f"* 🚌 Linea **{linea_rilevata}** fino a **{n_fa}** (~{t_bus} min).\n"
                       f"⏱️ **Totale:** ~{t_p1 + t_bus + t_p2} min.")
        else:
            if "route_data" in st.session_state:
                del st.session_state.route_data
            st.error("Indirizzi non trovati.")

# --- NUOVA SEZIONE: AGGIUNGI FERMATE REALI ---
with mc3:
    st.subheader("🚏 Aggiungi Fermata")
    with st.form("nuova_fermata_form", clear_on_submit=True):
        nome_f = st.text_input("Nome della Fermata:")
        lat_f = st.number_input("Latitudine:", format="%.5f", value=44.6400)
        lon_f = st.number_input("Longitudine:", format="%.5f", value=10.9200)
        submit = st.form_submit_button("Inserisci nel Sistema")
        
        if submit and nome_f:
            # Salva la fermata nel database temporaneo dell'applicazione
            st.session_state.fermate_personalizzate[nome_f] = [lat_f, lon_f]
            st.success(f"Fermata '{nome_f}' inserita con successo!")
            st.rerun()

with mc2:
    st.subheader("🗺️ Mappa Live")
    m = folium.Map(location=[44.6420, 10.9161], zoom_start=15)
    
    # Disegna SEMPRE sulla mappa le tue fermate personalizzate salvate
    for nome, coord in st.session_state.fermate_personalizzate.items():
        folium.Marker(
            location=coord,
            popup=f"Fermata: {nome}",
            icon=folium.Icon(color="blue", icon="bus", prefix="fa")
        ).add_to(m)
    
    # Se c'è un percorso attivo, disegna i dettagli del viaggio
    if "route_data" in st.session_state:
        rd = st.session_state.route_data
        folium.Marker(rd["cp"], popup=f"Partenza: {vp}", icon=folium.Icon(color="gray", icon="user", prefix="fa")).add_to(m)
        folium.Marker(rd["ca"], popup=f"Arrivo: {va}", icon=folium.Icon(color="red", icon="flag")).add_to(m)
        
        folium.PolyLine(rd["geom_p1"], color="blue", weight=4, opacity=0.7).add_to(m)
        folium.PolyLine(rd["geom_bus"], color="green", weight=6, opacity=0.8).add_to(m)
        folium.PolyLine(rd["geom_p2"], color="blue", weight=4, opacity=0.7).add_to(m)
        
        folium.CircleMarker(location=rd["cfp"], radius=9, color="darkred", fill=True, fill_color="orange", popup=f"Sali: {rd['nfp']}").add_to(m)
        folium.CircleMarker(location=rd["cfa"], radius=9, color="darkred", fill=True, fill_color="orange", popup=f"Scendi: {rd['nfa']}").add_to(m)
    
    st_folium(m, use_container_width=True, height=500)

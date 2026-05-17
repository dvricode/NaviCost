"""
app.py — Aplicación principal de NaviCost (TripCalc AI).

Gestiona y compara opciones de viajes calculando el Coste Real Total:
alojamiento + gasolina + comida, con mapa interactivo y veredicto IA.

Ejecutar con: streamlit run app.py
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import pandas as pd
import altair as alt
from io import BytesIO
import json

import db_manager
import ai_helper
import weather_helper
import pdf_generator

# ─── Configuración de página ─────────────────────────────────────────────
st.set_page_config(
    page_title="NaviCost — Calculadora de Viajes",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS personalizado ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }

.main-title {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 2.8rem; font-weight: 700; text-align: center; margin-bottom: 0;
}
.subtitle {
    text-align: center; color: #888; font-size: 1.1rem; margin-bottom: 2rem;
}
.metric-card {
    background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
    border: 1px solid rgba(102,126,234,0.3); border-radius: 16px;
    padding: 1.2rem; text-align: center; margin-bottom: 0.5rem;
}
.metric-card h3 { color: #667eea; font-size: 0.85rem; margin: 0 0 0.3rem 0; }
.metric-card p { color: #fff; font-size: 1.6rem; font-weight: 700; margin: 0; }
.ai-box {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid rgba(102,126,234,0.4); border-radius: 16px;
    padding: 1.5rem; margin-top: 1rem; line-height: 1.7;
}
div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
}
.aloj-card {
    background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
    border: 1px solid rgba(102,126,234,0.25); border-radius: 16px;
    padding: 1.4rem; margin-bottom: 1rem; transition: transform 0.2s;
}
.aloj-card:hover { transform: translateY(-2px); }
.aloj-card h4 { color: #e0e0ff; margin: 0 0 0.3rem 0; font-size: 1.15rem; }
.aloj-card .aloj-meta { color: #999; font-size: 0.85rem; margin-bottom: 0.6rem; }
.aloj-card .aloj-price { color: #667eea; font-weight: 700; font-size: 1.3rem; }
.aloj-card .aloj-review { color: #ccc; margin-top: 0.6rem; line-height: 1.6; font-style: italic; }
.aloj-card .aloj-notes { color: #aaa; font-size: 0.85rem; margin-top: 0.4rem; }
.badge-repeat {
    display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px;
    font-size: 0.8rem; font-weight: 600;
}
.badge-yes { background: rgba(45,180,80,0.2); color: #4ade80; border: 1px solid rgba(45,180,80,0.4); }
.badge-no { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4); }
</style>
""", unsafe_allow_html=True)

# ─── Inicializar base de datos ────────────────────────────────────────────
db_manager.init_db()

# ─── Estado de sesión ─────────────────────────────────────────────────────
for key, default in {
    "punto_a": None, "punto_b": None,
    "seleccionando": "A", "last_calc": None,
    "gastos_extra_list": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def geocodificar(direccion: str):
    """Convierte una dirección en coordenadas (lat, lon)."""
    try:
        geo = Nominatim(user_agent="navicost_app", timeout=10)
        loc = geo.geocode(direccion)
        if loc:
            return (loc.latitude, loc.longitude, loc.address)
    except Exception:
        pass
    return None


@st.cache_data(ttl=600)
def obtener_ruta_osrm(lat1, lon1, lat2, lon2):
    """Consulta OSRM para obtener distancia y tiempo de conducción."""
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if data.get("code") == "Ok":
            route = data["routes"][0]
            return {
                "distancia_km": round(route["distance"] / 1000, 2),
                "tiempo_min": round(route["duration"] / 60, 1),
                "geometria": route["geometry"],
            }
    except Exception:
        pass
    return None


def calcular_costes(distancia_km, consumo, precio_comb, personas, reserva, comida_total, extras=0):
    """Calcula todos los costes del viaje."""
    ida_vuelta = distancia_km * 2
    gasolina = (ida_vuelta / 100) * consumo * precio_comb
    total = gasolina + reserva + comida_total + extras
    por_persona = total / max(personas, 1)
    return {
        "distancia_ida_vuelta": round(ida_vuelta, 2),
        "gasto_gasolina": round(gasolina, 2),
        "gasto_comida": round(comida_total, 2),
        "gasto_extras": round(extras, 2),
        "coste_total": round(total, 2),
        "coste_persona": round(por_persona, 2),
    }


def formatear_tiempo(minutos):
    """Formatea minutos a horas y minutos."""
    if not minutos:
        return "—"
    h, m = divmod(int(minutos), 60)
    return f"{h}h {m}min" if h else f"{m}min"


# ═══════════════════════════════════════════════════════════════════════════
# ENCABEZADO
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<h1 class="main-title">🧭 NaviCost</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Calcula el coste real de tus viajes — Alojamiento + Gasolina + Comida</p>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR — FORMULARIO DE VIAJE
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📝 Nueva Opción de Viaje")

    nombre = st.text_input("🏷️ Nombre de la opción", placeholder="Ej: Apartamento playa Valencia")

    st.markdown("---")
    st.markdown("### 📍 Ubicaciones")

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        if st.button("📌 Seleccionar Origen", use_container_width=True,
                      type="primary" if st.session_state.seleccionando == "A" else "secondary"):
            st.session_state.seleccionando = "A"
    with col_sel2:
        if st.button("🎯 Seleccionar Destino", use_container_width=True,
                      type="primary" if st.session_state.seleccionando == "B" else "secondary"):
            st.session_state.seleccionando = "B"

    sel = st.session_state.seleccionando
    st.info(f"🖱️ Haz clic en el mapa para fijar el **{'Origen (A)' if sel == 'A' else 'Destino (B)'}**")

    # Direcciones manuales
    dir_origen = st.text_input("Dirección origen (opcional)", placeholder="Ej: Madrid, España")
    dir_destino = st.text_input("Dirección destino (opcional)", placeholder="Ej: Valencia, España")

    col_geo1, col_geo2 = st.columns(2)
    with col_geo1:
        if st.button("🔍 Buscar origen", use_container_width=True) and dir_origen:
            result = geocodificar(dir_origen)
            if result:
                st.session_state.punto_a = {"lat": result[0], "lng": result[1]}
                st.success(f"✅ {result[2][:50]}")
            else:
                st.error("No encontrado")
    with col_geo2:
        if st.button("🔍 Buscar destino", use_container_width=True) and dir_destino:
            result = geocodificar(dir_destino)
            if result:
                st.session_state.punto_b = {"lat": result[0], "lng": result[1]}
                st.success(f"✅ {result[2][:50]}")
            else:
                st.error("No encontrado")

    pa = st.session_state.punto_a
    pb = st.session_state.punto_b
    if pa:
        st.success(f"📌 Origen: {pa['lat']:.4f}, {pa['lng']:.4f}")
    if pb:
        st.success(f"🎯 Destino: {pb['lat']:.4f}, {pb['lng']:.4f}")

    st.markdown("---")
    st.markdown("### ⛽ Transporte")
    consumo = st.number_input("Consumo (L/100km)", 1.0, 30.0, 7.0, 0.5)
    precio_comb = st.number_input("Precio combustible (€/L)", 0.5, 3.0, 1.55, 0.05)

    st.markdown("---")
    st.markdown("### 🏨 Estancia")
    mis_alojs = db_manager.obtener_alojamientos()
    opciones_aloj = {"Ninguno": None}
    for a in mis_alojs:
        opciones_aloj[f"{a['nombre']} ({a['precio_noche']:.0f}€/n)"] = a['id']
    aloj_seleccionado = st.selectbox("Vincular Alojamiento", list(opciones_aloj.keys()))
    aloj_id_vinculado = opciones_aloj[aloj_seleccionado]

    personas = st.number_input("Número de personas", 1, 20, 2)
    dias = st.number_input("Número de días", 1, 60, 3)
    reserva = st.number_input("Precio reserva alojamiento (€)", 0.0, 50000.0, 150.0, 10.0)
    comida_total = st.number_input("Presupuesto total comida (€)", 0.0, 50000.0, 200.0, 10.0)

    st.markdown("---")
    st.markdown("### 📅 Planificación")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        fecha_ida = st.date_input("Fecha Ida", value=None)
    with col_d2:
        fecha_vuelta = st.date_input("Fecha Vuelta", value=None)
    estado_viaje = st.selectbox("Estado del Viaje", ["Planificado", "Reservado", "Realizado"])

    st.markdown("---")
    st.markdown("### 💸 Gastos Extra")
    col_ge1, col_ge2, col_ge3 = st.columns([2, 1, 1])
    with col_ge1:
        ge_nombre = st.text_input("Concepto", placeholder="Peaje, Regalos...", key="ge_nom")
    with col_ge2:
        ge_cantidad = st.number_input("€", 0.0, 50000.0, 0.0, 5.0, key="ge_cant")
    with col_ge3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Añadir", key="add_ge") and ge_nombre.strip():
            st.session_state.gastos_extra_list.append({"nombre": ge_nombre.strip(), "cantidad": ge_cantidad})
            st.rerun()

    for i, ge in enumerate(st.session_state.gastos_extra_list):
        col_gx1, col_gx2 = st.columns([3, 1])
        with col_gx1:
            st.caption(f"📎 {ge['nombre']}: {ge['cantidad']:.2f} €")
        with col_gx2:
            if st.button("❌", key=f"del_ge_{i}"):
                st.session_state.gastos_extra_list.pop(i)
                st.rerun()

    total_extras = sum(g["cantidad"] for g in st.session_state.gastos_extra_list)
    if total_extras > 0:
        st.info(f"Total extras: **{total_extras:.2f} €**")

    st.markdown("---")

    btn_calcular = st.button("🚀 Calcular y Guardar Opción", use_container_width=True, type="primary")


# ═══════════════════════════════════════════════════════════════════════════
# MAPA INTERACTIVO
# ═══════════════════════════════════════════════════════════════════════════

tab_mapa, tab_dashboard, tab_aloj, tab_ia = st.tabs(["🗺️ Mapa", "📊 Comparador", "🏨 Mis Alojamientos", "🤖 Veredicto IA"])

with tab_mapa:
    st.markdown("#### Selecciona origen y destino en el mapa")

    # Centro del mapa: entre A y B si existen, sino España
    if pa and pb:
        center = [(pa["lat"] + pb["lat"]) / 2, (pa["lng"] + pb["lng"]) / 2]
        zoom = 6
    elif pa:
        center = [pa["lat"], pa["lng"]]
        zoom = 8
    elif pb:
        center = [pb["lat"], pb["lng"]]
        zoom = 8
    else:
        center = [40.4168, -3.7038]  # Madrid
        zoom = 6

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB dark_matter")

    if pa:
        folium.Marker(
            [pa["lat"], pa["lng"]],
            tooltip="📌 Origen (A)",
            icon=folium.Icon(color="blue", icon="home", prefix="fa"),
        ).add_to(m)

    if pb:
        folium.Marker(
            [pb["lat"], pb["lng"]],
            tooltip="🎯 Destino (B)",
            icon=folium.Icon(color="red", icon="flag", prefix="fa"),
        ).add_to(m)

    # Dibujar ruta si existen ambos puntos
    if pa and pb:
        ruta = obtener_ruta_osrm(pa["lat"], pa["lng"], pb["lat"], pb["lng"])
        if ruta and ruta.get("geometria"):
            coords = ruta["geometria"]["coordinates"]
            folium.PolyLine(
                locations=[[c[1], c[0]] for c in coords],
                color="#667eea", weight=4, opacity=0.8,
            ).add_to(m)

    map_data = st_folium(m, width=None, height=500, returned_objects=["last_clicked"])

    # Procesar clic en el mapa
    if map_data and map_data.get("last_clicked"):
        click = map_data["last_clicked"]
        if st.session_state.seleccionando == "A":
            st.session_state.punto_a = click
        else:
            st.session_state.punto_b = click
        st.rerun()

    # Widget del clima si hay destino
    if pb:
        clima = weather_helper.obtener_clima(pb["lat"], pb["lng"])
        if clima:
            st.markdown("---")
            st.markdown("#### 🌤️ Clima actual en destino")
            col_w1, col_w2, col_w3 = st.columns(3)
            with col_w1:
                st.metric("Temperatura", f"{clima['temp_c']} °C")
            with col_w2:
                st.metric("Estado", clima['descripcion'].capitalize() if clima['descripcion'] else "—")
            with col_w3:
                st.metric("Humedad", f"{clima['humedad']} %")


# ═══════════════════════════════════════════════════════════════════════════
# LÓGICA DE CÁLCULO Y GUARDADO
# ═══════════════════════════════════════════════════════════════════════════

if btn_calcular:
    pa = st.session_state.punto_a
    pb = st.session_state.punto_b

    if not pa or not pb:
        st.error("⚠️ Selecciona Origen (A) y Destino (B) en el mapa o por dirección.")
    elif not nombre.strip():
        st.error("⚠️ Escribe un nombre para esta opción de viaje.")
    else:
        ruta = obtener_ruta_osrm(pa["lat"], pa["lng"], pb["lat"], pb["lng"])

        if ruta:
            dist_ida = ruta["distancia_km"]
            tiempo = ruta["tiempo_min"]
        else:
            # Fallback: distancia lineal con geopy
            from geopy.distance import geodesic
            dist_ida = round(geodesic((pa["lat"], pa["lng"]), (pb["lat"], pb["lng"])).km, 2)
            tiempo = None
            st.warning("⚠️ OSRM no disponible. Se usa distancia lineal aproximada.")

        costes = calcular_costes(dist_ida, consumo, precio_comb, personas, reserva, comida_total, total_extras)

        datos = {
            "nombre": nombre.strip(),
            "origen": f"{pa['lat']:.4f}, {pa['lng']:.4f}",
            "destino": f"{pb['lat']:.4f}, {pb['lng']:.4f}",
            "lat_origen": pa["lat"], "lon_origen": pa["lng"],
            "lat_destino": pb["lat"], "lon_destino": pb["lng"],
            "distancia_km": costes["distancia_ida_vuelta"],
            "tiempo_min": tiempo * 2 if tiempo else 0,
            "consumo_l100": consumo,
            "precio_comb": precio_comb,
            "num_personas": personas,
            "num_dias": dias,
            "precio_reserva": reserva,
            "ppto_comida": comida_total,
            "gasto_gasolina": costes["gasto_gasolina"],
            "gasto_comida": costes["gasto_comida"],
            "coste_total": costes["coste_total"],
            "coste_persona": costes["coste_persona"],
            "fecha_ida": str(fecha_ida) if fecha_ida else "",
            "fecha_vuelta": str(fecha_vuelta) if fecha_vuelta else "",
            "estado": estado_viaje,
            "alojamiento_id": aloj_id_vinculado,
            "gastos_extra": json.dumps(st.session_state.gastos_extra_list, ensure_ascii=False),
            "gasto_extras": costes["gasto_extras"],
        }

        viaje_id = db_manager.guardar_viaje(datos)
        st.session_state.last_calc = datos
        st.success(f"✅ Opción **{nombre}** guardada correctamente (ID: {viaje_id})")
        st.balloons()

# Mostrar resumen del último cálculo
if st.session_state.last_calc:
    lc = st.session_state.last_calc
    st.markdown("### 📋 Último cálculo")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card"><h3>⛽ Gasolina</h3><p>{lc["gasto_gasolina"]:.2f} €</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><h3>🍽️ Comida</h3><p>{lc["gasto_comida"]:.2f} €</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><h3>💸 Extras</h3><p>{lc.get("gasto_extras", 0):.2f} €</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><h3>💰 Total</h3><p>{lc["coste_total"]:.2f} €</p></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card"><h3>👤 Por Persona</h3><p>{lc["coste_persona"]:.2f} €</p></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB — DASHBOARD COMPARADOR
# ═══════════════════════════════════════════════════════════════════════════

with tab_dashboard:
    st.markdown("### 📊 Comparación de Opciones Guardadas")

    viajes = db_manager.obtener_viajes()

    if not viajes:
        st.info("🗂️ Aún no hay opciones guardadas. Usa el formulario del sidebar para añadir una.")
    else:
        df = pd.DataFrame(viajes)
        if "gasto_extras" not in df.columns:
            df["gasto_extras"] = 0.0
        df["gasto_extras"] = df["gasto_extras"].fillna(0)
        df_display = df[[
            "id", "nombre", "destino", "fecha_ida", "fecha_vuelta", "estado", "distancia_km", "tiempo_min",
            "precio_reserva", "gasto_gasolina", "gasto_comida", "gasto_extras",
            "coste_total", "coste_persona", "num_personas", "num_dias",
        ]].copy()

        df_display.columns = [
            "ID", "Nombre", "Destino", "Ida", "Vuelta", "Estado", "Dist. I/V (km)", "Tiempo I/V (min)",
            "Reserva (€)", "Gasolina (€)", "Comida (€)", "Extras (€)",
            "Total (€)", "Por Persona (€)", "Personas", "Días",
        ]

        # Resaltar el más barato
        st.dataframe(
            df_display.style.highlight_min(subset=["Total (€)", "Por Persona (€)"], color="#2d5a27"),
            use_container_width=True,
            hide_index=True,
        )

        # Exportar a Excel y PDF
        col_ex, col_pdf = st.columns(2)
        
        with col_ex:
            excel_buffer = BytesIO()
            df_display.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button(
                "📤 Exportar a Excel (Todos)",
                data=excel_buffer.getvalue(),
                file_name="navicost_comparacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        with col_pdf:
            trip_names = {f"{v['nombre']} (ID: {v['id']})": v for v in viajes}
            selected_pdf = st.selectbox("Selecciona viaje para PDF", list(trip_names.keys()), label_visibility="collapsed")
            if selected_pdf:
                viaje_pdf = trip_names[selected_pdf]
                pdf_bytes = pdf_generator.generar_informe_viaje(viaje_pdf)
                st.download_button(
                    "📄 Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name=f"informe_viaje_{viaje_pdf['nombre'].replace(' ', '_').lower()}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # Gráfico de barras agrupadas (Altair)
        if len(viajes) >= 1:
            chart_df = df_display[["Nombre", "Reserva (€)", "Gasolina (€)", "Comida (€)", "Extras (€)"]].copy()
            chart_df["Nombre"] = chart_df["Nombre"] + " (" + df_display["ID"].astype(str) + ")"
            chart_melted = chart_df.melt(id_vars="Nombre", var_name="Concepto", value_name="Coste (€)")

            chart = alt.Chart(chart_melted).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("Coste (€):Q"),
                color=alt.Color("Concepto:N", scale=alt.Scale(
                    domain=["Reserva (€)", "Gasolina (€)", "Comida (€)", "Extras (€)"],
                    range=["#667eea", "#e74c8b", "#f0a500", "#22d3ee"]
                )),
                tooltip=["Concepto:N", "Coste (€):Q"]
            ).properties(width=200, height=200).facet(
                column=alt.Column("Nombre:N", header=alt.Header(title=None, labelOrient="bottom", labelFontSize=14))
            ).properties(title="Desglose Circular de Costes por Opción")

            st.altair_chart(chart, use_container_width=True)

        # Botones de gestión
        st.markdown("---")
        col_del1, col_del2, col_upd1, col_upd2 = st.columns([2, 1, 2, 1])
        with col_del1:
            ids_disponibles = [v["id"] for v in viajes]
            id_eliminar = st.selectbox("ID a eliminar", ids_disponibles)
        with col_del2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Eliminar", type="secondary", use_container_width=True):
                db_manager.eliminar_viaje(id_eliminar)
                st.success(f"Opción ID {id_eliminar} eliminada.")
                st.rerun()
        with col_upd1:
            id_estado = st.selectbox("ID a actualizar estado", ids_disponibles)
            nuevo_estado = st.selectbox("Nuevo Estado", ["Planificado", "Reservado", "Realizado"])
        with col_upd2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar", type="secondary", use_container_width=True):
                db_manager.actualizar_estado(id_estado, nuevo_estado)
                st.success(f"Estado de ID {id_estado} actualizado a {nuevo_estado}.")
                st.rerun()

        if st.button("🧹 Limpiar todo", type="secondary"):
            db_manager.limpiar_viajes()
            st.success("Todas las opciones eliminadas.")
            st.rerun()

        with st.expander("✏️ Editar Detalles de una Opción"):
            id_editar = st.selectbox("Selecciona ID a editar", ids_disponibles, key="sel_editar")
            viaje_editar = next((v for v in viajes if v["id"] == id_editar), None)
            if viaje_editar:
                with st.form("form_editar_viaje"):
                    st.markdown(f"**Editando: {viaje_editar['nombre']}**")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        e_nombre = st.text_input("Nombre", value=viaje_editar["nombre"])
                        e_personas = st.number_input("Personas", 1, 20, int(viaje_editar["num_personas"]))
                        e_dias = st.number_input("Días", 1, 60, int(viaje_editar["num_dias"]))
                        e_reserva = st.number_input("Reserva (€)", 0.0, 50000.0, float(viaje_editar["precio_reserva"]))
                    with col_e2:
                        e_comida = st.number_input("Comida Total (€)", 0.0, 50000.0, float(viaje_editar["ppto_comida"]))
                        e_consumo = st.number_input("Consumo (L/100km)", 1.0, 30.0, float(viaje_editar["consumo_l100"]))
                        e_precio_comb = st.number_input("Combustible (€/L)", 0.5, 3.0, float(viaje_editar["precio_comb"]))
                        e_extras = st.number_input("Extras (€)", 0.0, 50000.0, float(viaje_editar.get("gasto_extras", 0)))
                    
                    if st.form_submit_button("Guardar Cambios", type="primary", use_container_width=True):
                        ida_vuelta = float(viaje_editar["distancia_km"]) * 2
                        gasto_gasolina = (ida_vuelta / 100) * e_consumo * e_precio_comb
                        coste_total = gasto_gasolina + e_reserva + e_comida + e_extras
                        coste_persona = coste_total / max(e_personas, 1)

                        nuevos_datos = {
                            "nombre": e_nombre.strip(),
                            "consumo_l100": e_consumo,
                            "precio_comb": e_precio_comb,
                            "num_personas": e_personas,
                            "num_dias": e_dias,
                            "precio_reserva": e_reserva,
                            "ppto_comida": e_comida,
                            "gasto_gasolina": round(gasto_gasolina, 2),
                            "gasto_comida": e_comida,
                            "gasto_extras": e_extras,
                            "coste_total": round(coste_total, 2),
                            "coste_persona": round(coste_persona, 2)
                        }
                        db_manager.actualizar_viaje(id_editar, nuevos_datos)
                        st.success("✅ Opción actualizada.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB — MIS ALOJAMIENTOS
# ═══════════════════════════════════════════════════════════════════════════

with tab_aloj:
    st.markdown("### 🏨 Mis Alojamientos — Base de Datos Personal")
    st.caption("Guarda alojamientos con ubicación, precio y tu reseña personal para saber si repetir.")

    # ── Formulario para añadir alojamiento ────────────────────────────────
    with st.expander("➕ Añadir nuevo alojamiento", expanded=False):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            aloj_nombre = st.text_input("Nombre del alojamiento", placeholder="Ej: Hotel Mar Azul", key="aloj_nom")
            aloj_ubicacion = st.text_input("Ubicación / Dirección", placeholder="Ej: Valencia, España", key="aloj_ubi")
            aloj_tipo = st.selectbox("Tipo", ["Apartamento", "Hotel", "Hostal", "Casa rural", "Camping", "Airbnb", "Otro"], key="aloj_tipo")
            aloj_plataforma = st.text_input("Plataforma", placeholder="Ej: Booking, Airbnb...", key="aloj_plat")
        with col_a2:
            aloj_precio = st.number_input("Precio por noche (€)", 0.0, 10000.0, 60.0, 5.0, key="aloj_precio")
            aloj_puntuacion = st.slider("Tu puntuación", 1, 5, 3, key="aloj_punt")
            aloj_repetir = st.toggle("¿Repetirías?", value=True, key="aloj_rep")
            aloj_url = st.text_input("URL (opcional)", placeholder="https://...", key="aloj_url")
            aloj_color = st.color_picker("Color en el mapa", value="#667eea", key="aloj_color")

        aloj_resena = st.text_area("Tu reseña personal", placeholder="¿Qué tal fue la experiencia? ¿Limpieza, ubicación, trato...?", key="aloj_res")
        aloj_notas = st.text_input("Notas privadas", placeholder="Ej: Pedir habitación con vistas, evitar planta baja...", key="aloj_not")

        if st.button("💾 Guardar Alojamiento", type="primary", use_container_width=True, key="btn_aloj"):
            if not aloj_nombre.strip() or not aloj_ubicacion.strip():
                st.error("⚠️ Nombre y ubicación son obligatorios.")
            else:
                # Intentar geocodificar para guardar coordenadas
                geo_result = geocodificar(aloj_ubicacion)
                lat = geo_result[0] if geo_result else None
                lon = geo_result[1] if geo_result else None

                datos_aloj = {
                    "nombre": aloj_nombre.strip(),
                    "ubicacion": aloj_ubicacion.strip(),
                    "lat": lat, "lon": lon,
                    "tipo": aloj_tipo,
                    "precio_noche": aloj_precio,
                    "puntuacion": aloj_puntuacion,
                    "resena": aloj_resena.strip(),
                    "repetir": int(aloj_repetir),
                    "url": aloj_url.strip(),
                    "plataforma": aloj_plataforma.strip(),
                    "notas": aloj_notas.strip(),
                    "color": aloj_color,
                }
                aloj_id = db_manager.guardar_alojamiento(datos_aloj)
                st.success(f"✅ **{aloj_nombre}** guardado (ID: {aloj_id})")
                st.rerun()

    # ── Mapa de alojamientos ─────────────────────────────────────────────
    alojamientos = db_manager.obtener_alojamientos()
    alojs_con_coords = [a for a in alojamientos if a.get("lat") and a.get("lon")]

    if alojs_con_coords:
        st.markdown("#### 🗺️ Mapa de mis alojamientos")
        center_aloj = [sum(a["lat"] for a in alojs_con_coords) / len(alojs_con_coords),
                       sum(a["lon"] for a in alojs_con_coords) / len(alojs_con_coords)]
        m_aloj = folium.Map(location=center_aloj, zoom_start=6, tiles="CartoDB dark_matter")
        for a in alojs_con_coords:
            color_hex = a.get("color", "#667eea")
            estrellas_tip = "⭐" * a["puntuacion"]
            tip = f"{a['nombre']} — {a['precio_noche']:.0f}€/noche {estrellas_tip}"
            folium.CircleMarker(
                location=[a["lat"], a["lon"]],
                radius=10, color=color_hex, fill=True,
                fill_color=color_hex, fill_opacity=0.8,
                tooltip=tip,
            ).add_to(m_aloj)
        st_folium(m_aloj, width=None, height=400, key="mapa_aloj", returned_objects=[])

    # ── Listado de alojamientos ───────────────────────────────────────────
    if not alojamientos:
        st.info("🗂️ No hay alojamientos guardados. Usa el formulario de arriba para añadir uno.")
    else:
        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_tipo = st.multiselect("Filtrar por tipo", list(set(a["tipo"] for a in alojamientos)), key="f_tipo")
        with col_f2:
            filtro_punt = st.slider("Puntuación mínima", 1, 5, 1, key="f_punt")
        with col_f3:
            filtro_rep = st.selectbox("Repetir", ["Todos", "Sí repetiría", "No repetiría"], key="f_rep")

        # Aplicar filtros
        filtered = alojamientos
        if filtro_tipo:
            filtered = [a for a in filtered if a["tipo"] in filtro_tipo]
        filtered = [a for a in filtered if a["puntuacion"] >= filtro_punt]
        if filtro_rep == "Sí repetiría":
            filtered = [a for a in filtered if a["repetir"]]
        elif filtro_rep == "No repetiría":
            filtered = [a for a in filtered if not a["repetir"]]

        st.markdown(f"**{len(filtered)}** alojamiento(s) encontrado(s)")

        # Renderizar tarjetas
        for aloj in filtered:
            estrellas = "⭐" * aloj["puntuacion"] + "☆" * (5 - aloj["puntuacion"])
            badge_class = "badge-yes" if aloj["repetir"] else "badge-no"
            badge_text = "✅ Repetiría" if aloj["repetir"] else "❌ No repetiría"

            url_link = ""
            if aloj.get("url"):
                url_link = f' · <a href="{aloj["url"]}" target="_blank" style="color:#667eea;">🔗 Ver enlace</a>'

            review_html = ""
            if aloj.get("resena"):
                review_html = f'<div class="aloj-review">💬 "{aloj["resena"]}"</div>'

            notes_html = ""
            if aloj.get("notas"):
                notes_html = f'<div class="aloj-notes">📝 {aloj["notas"]}</div>'

            st.markdown(f"""
            <div class="aloj-card">
                <h4>{aloj["nombre"]} <span class="badge-repeat {badge_class}">{badge_text}</span></h4>
                <div class="aloj-meta">
                    📍 {aloj["ubicacion"]} · 🏷️ {aloj["tipo"]}
                    {f' · 🌐 {aloj["plataforma"]}' if aloj.get("plataforma") else ''}
                    {url_link}
                </div>
                <span class="aloj-price">{aloj["precio_noche"]:.0f} €/noche</span>
                <span style="margin-left:1rem;">{estrellas}</span>
                {review_html}
                {notes_html}
            </div>
            """, unsafe_allow_html=True)

            # Botones de acción por alojamiento
            col_e1, col_e2 = st.columns([4, 1])
            with col_e2:
                if st.button("🗑️", key=f"del_aloj_{aloj['id']}", help="Eliminar alojamiento"):
                    db_manager.eliminar_alojamiento(aloj["id"])
                    st.rerun()
            with col_e1:
                with st.expander(f"✏️ Editar reseña — {aloj['nombre']}", expanded=False):
                    new_punt = st.slider("Puntuación", 1, 5, aloj["puntuacion"], key=f"ep_{aloj['id']}")
                    new_res = st.text_area("Reseña", value=aloj.get("resena", ""), key=f"er_{aloj['id']}")
                    new_rep = st.toggle("¿Repetirías?", value=bool(aloj["repetir"]), key=f"erp_{aloj['id']}")
                    new_notas = st.text_input("Notas", value=aloj.get("notas", ""), key=f"en_{aloj['id']}")
                    if st.button("💾 Actualizar", key=f"upd_{aloj['id']}", use_container_width=True):
                        db_manager.actualizar_resena(aloj["id"], new_punt, new_res.strip(), new_rep, new_notas.strip())
                        st.success("✅ Reseña actualizada")
                        st.rerun()

        # Limpiar todos
        st.markdown("---")
        if st.button("🧹 Eliminar todos los alojamientos", type="secondary", key="limpiar_aloj"):
            db_manager.limpiar_alojamientos()
            st.success("Todos los alojamientos eliminados.")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB — VEREDICTO IA
# ═══════════════════════════════════════════════════════════════════════════

with tab_ia:
    st.markdown("### 🤖 Veredicto de Inteligencia Artificial")
    st.caption("Powered by Groq — Llama 3.1")

    viajes_ia = db_manager.obtener_viajes()

    if len(viajes_ia) < 2:
        st.info("📌 Necesitas al menos **2 opciones** guardadas para generar un veredicto.")
    else:
        # Selector de opciones a comparar
        opciones_disponibles = {f"{v['nombre']} (ID:{v['id']})": v for v in viajes_ia}
        seleccionadas = st.multiselect(
            "Selecciona las opciones que quieres comparar",
            options=list(opciones_disponibles.keys()),
            default=list(opciones_disponibles.keys()),
            key="ia_seleccion",
        )

        viajes_filtrados = [opciones_disponibles[s] for s in seleccionadas]

        if len(viajes_filtrados) < 2:
            st.warning("⚠️ Selecciona al menos **2 opciones** para comparar.")
        else:
            st.markdown(f"Se compararán **{len(viajes_filtrados)}** opciones de viaje.")

            if st.button("✨ Generar Veredicto con IA", type="primary", use_container_width=True):
                with st.spinner("🧠 Analizando opciones con Llama 3.1..."):
                    veredicto = ai_helper.generar_veredicto(viajes_filtrados)
                st.markdown(f'<div class="ai-box">{veredicto}</div>', unsafe_allow_html=True)

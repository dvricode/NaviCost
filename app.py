"""
app.py — Aplicación principal de NaviCost (TripCalc AI).

Gestiona y compara opciones de viajes calculando el Coste Real Total.
Ahora con sistema de usuarios, roles de administrador y viajes colaborativos.
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
import uuid
import logging

# Configuración básica de logs para que salgan en consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Iniciando la aplicación NaviCost...")

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

db_manager.init_db()

# ─── Estado de sesión ─────────────────────────────────────────────────────
for key, default in {
    "punto_a": None, "punto_b": None,
    "seleccionando": "A", "last_calc": None,
    "gastos_extra_list": [],
    "usuario_actual": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def geocodificar(direccion: str):
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

# ═══════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN (LOGIN / REGISTRO)
# ═══════════════════════════════════════════════════════════════════════════

def mostrar_pantalla_auth():
    # Contenedor principal para centrar
    _, col_centro, _ = st.columns([1, 1.5, 1])
    
    with col_centro:
        st.markdown('<h1 class="main-title" style="font-size:2.5rem; margin-bottom: 0.5rem;">🧭 NaviCost</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#888; font-size:1rem; text-align:center; margin-bottom:1.5rem;">Planificador Inteligente de Viajes Colaborativos</p>', unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta"])
        
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form"):
                user_login = st.text_input("Usuario", placeholder="Tu nombre de usuario")
                pass_login = st.text_input("Contraseña", type="password", placeholder="••••••••")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Acceder", type="primary", use_container_width=True):
                    if not user_login or not pass_login:
                        st.error("⚠️ Rellena todos los campos.")
                    else:
                        res = db_manager.verificar_login(user_login, pass_login)
                        if "success" in res:
                            st.session_state.usuario_actual = res["user"]
                            st.rerun()
                        else:
                            st.error(f"❌ {res['error']}")
        
        with tab_reg:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("register_form"):
                user_reg = st.text_input("Nuevo Usuario", placeholder="Elige un nombre de usuario")
                pass_reg = st.text_input("Nueva Contraseña", type="password", placeholder="Crea una contraseña segura")
                pass_reg2 = st.text_input("Repetir Contraseña", type="password", placeholder="Vuelve a escribirla")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Registrarse y Entrar", type="primary", use_container_width=True):
                    if not user_reg or not pass_reg:
                        st.error("⚠️ Rellena todos los campos.")
                    elif pass_reg != pass_reg2:
                        st.error("⚠️ Las contraseñas no coinciden.")
                    else:
                        res = db_manager.registrar_usuario(user_reg, pass_reg)
                        if "success" in res:
                            st.success("✅ ¡Cuenta creada! Ya puedes iniciar sesión en la otra pestaña.")
                        else:
                            st.error(f"❌ {res['error']}")

if not st.session_state.usuario_actual:
    mostrar_pantalla_auth()
    st.stop()


# ====================================================================================
# APP PRINCIPAL (USUARIO LOGUEADO)
# ====================================================================================

user_actual = st.session_state.usuario_actual
es_admin = user_actual.get("rol") == "admin"

st.markdown('<h1 class="main-title">🧭 NaviCost</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="subtitle">Bienvenido/a, <b>{user_actual["username"]}</b> (Rol: {user_actual["rol"]})</p>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📝 Nueva Opción de Viaje")

    nombre = st.text_input("🏷️ Nombre de la opción", placeholder="Ej: Apartamento playa Valencia")

    st.markdown("### 📍 Ubicaciones")

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        if st.button("📌 Origen", use_container_width=True, type="primary" if st.session_state.seleccionando == "A" else "secondary"):
            st.session_state.seleccionando = "A"
    with col_sel2:
        if st.button("🎯 Destino", use_container_width=True, type="primary" if st.session_state.seleccionando == "B" else "secondary"):
            st.session_state.seleccionando = "B"

    dir_origen = st.text_input("Dirección origen", placeholder="Ej: Madrid, España")
    dir_destino = st.text_input("Dirección destino", placeholder="Ej: Valencia, España")

    col_geo1, col_geo2 = st.columns(2)
    with col_geo1:
        if st.button("🔍 Buscar O", use_container_width=True) and dir_origen:
            result = geocodificar(dir_origen)
            if result:
                st.session_state.punto_a = {"lat": result[0], "lng": result[1]}
    with col_geo2:
        if st.button("🔍 Buscar D", use_container_width=True) and dir_destino:
            result = geocodificar(dir_destino)
            if result:
                st.session_state.punto_b = {"lat": result[0], "lng": result[1]}

    pa = st.session_state.punto_a
    pb = st.session_state.punto_b

    st.markdown("### ⛽ Transporte")
    consumo = st.number_input("Consumo (L/100km)", 1.0, 30.0, 7.0, 0.5)
    precio_comb = st.number_input("Precio comb. (€/L)", 0.5, 3.0, 1.55, 0.05)

    st.markdown("### 🏨 Estancia")
    mis_alojs = db_manager.obtener_alojamientos(user_actual["id"], es_admin)
    opciones_aloj = {"Ninguno": None}
    for a in mis_alojs:
        opciones_aloj[f"{a['nombre']} ({a['precio_noche']:.0f}€/n)"] = a['id']
    aloj_seleccionado = st.selectbox("Vincular Alojamiento", list(opciones_aloj.keys()))
    aloj_id_vinculado = opciones_aloj[aloj_seleccionado]

    personas = st.number_input("Personas", 1, 20, 2)
    dias = st.number_input("Días", 1, 60, 3)
    reserva = st.number_input("Reserva alojamiento (€)", 0.0, 50000.0, 150.0, 10.0)
    comida_total = st.number_input("Comida total (€)", 0.0, 50000.0, 200.0, 10.0)

    st.markdown("### 📅 Planificación")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        fecha_ida = st.date_input("Fecha Ida", value=None)
    with col_d2:
        fecha_vuelta = st.date_input("Fecha Vuelta", value=None)
    estado_viaje = st.selectbox("Estado del Viaje", ["Planificado", "Reservado", "Realizado"])

    st.markdown("### 💸 Gastos Extra")
    col_ge1, col_ge2 = st.columns([2, 1])
    with col_ge1:
        ge_nombre = st.text_input("Concepto", key="ge_nom")
    with col_ge2:
        ge_cantidad = st.number_input("€", 0.0, 50000.0, 0.0, 5.0, key="ge_cant")
    
    if st.button("➕ Añadir Extra", use_container_width=True) and ge_nombre.strip():
        st.session_state.gastos_extra_list.append({"nombre": ge_nombre.strip(), "cantidad": ge_cantidad})
        st.rerun()

    for i, ge in enumerate(st.session_state.gastos_extra_list):
        col_gx1, col_gx2 = st.columns([3, 1])
        with col_gx1:
            st.caption(f"{ge['nombre']}: {ge['cantidad']:.2f} €")
        with col_gx2:
            if st.button("❌", key=f"del_ge_{i}"):
                st.session_state.gastos_extra_list.pop(i)
                st.rerun()

    total_extras = sum(g["cantidad"] for g in st.session_state.gastos_extra_list)

    btn_calcular = st.button("🚀 Calcular y Guardar Opción", use_container_width=True, type="primary")

    st.markdown("---")
    
    # ── Mover gestión de usuario abajo del todo ──
    with st.expander("👤 Gestión de Cuenta"):
        st.markdown("#### Cambiar Contraseña")
        with st.form("change_pass_form"):
            nueva_pass = st.text_input("Nueva Contraseña", type="password")
            if st.form_submit_button("Actualizar", use_container_width=True):
                if nueva_pass:
                    db_manager.cambiar_password(user_actual["id"], nueva_pass)
                    st.success("Actualizada.")
                else:
                    st.error("Vacío.")
                    
        st.markdown("#### Unirse a un Viaje Colaborativo")
        codigo_union = st.text_input("Código de Invitación", placeholder="Ej: A1B2C3D4")
        if st.button("Unirse al Viaje", use_container_width=True) and codigo_union:
            res = db_manager.unirse_a_viaje(user_actual["id"], codigo_union.strip())
            if "success" in res:
                st.success("¡Te has unido al viaje!")
                st.rerun()
            else:
                st.error(res["error"])

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="primary"):
            st.session_state.usuario_actual = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════

tabs_names = ["🗺️ Mapa", "📊 Dashboard Viajes", "📅 Planificador Itinerario", "🏨 Alojamientos", "🤖 Veredicto IA"]
if es_admin:
    tabs_names.append("🛡️ Panel Admin")

tabs = st.tabs(tabs_names)
tab_mapa = tabs[0]
tab_dashboard = tabs[1]
tab_itinerario = tabs[2]
tab_aloj = tabs[3]
tab_ia = tabs[4]
if es_admin:
    tab_admin = tabs[5]

# ── LÓGICA DE GUARDADO DEL FORMULARIO ──
if btn_calcular:
    if not pa or not pb:
        st.error("⚠️ Selecciona Origen y Destino.")
    elif not nombre.strip():
        st.error("⚠️ Escribe un nombre.")
    else:
        ruta = obtener_ruta_osrm(pa["lat"], pa["lng"], pb["lat"], pb["lng"])
        dist_ida = ruta["distancia_km"] if ruta else 0
        tiempo = ruta["tiempo_min"] if ruta else 0

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
            "itinerario": "{}"
        }

        viaje_id = db_manager.guardar_viaje(datos, user_actual["id"])
        st.success(f"✅ Opción guardada. Código para invitar amigos: **{datos['codigo_compartido']}**")


# =================================================================================
# TAB - MAPA
# =================================================================================
with tab_mapa:
    if pa and pb:
        center = [(pa["lat"] + pb["lat"]) / 2, (pa["lng"] + pb["lng"]) / 2]
        zoom = 6
    elif pa: center, zoom = [pa["lat"], pa["lng"]], 8
    elif pb: center, zoom = [pb["lat"], pb["lng"]], 8
    else: center, zoom = [40.4168, -3.7038], 6

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB dark_matter")
    if pa: folium.Marker([pa["lat"], pa["lng"]], tooltip="📌 Origen", icon=folium.Icon(color="blue", icon="home", prefix="fa")).add_to(m)
    if pb: folium.Marker([pb["lat"], pb["lng"]], tooltip="🎯 Destino", icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(m)

    if pa and pb:
        ruta = obtener_ruta_osrm(pa["lat"], pa["lng"], pb["lat"], pb["lng"])
        if ruta and ruta.get("geometria"):
            coords = ruta["geometria"]["coordinates"]
            folium.PolyLine(locations=[[c[1], c[0]] for c in coords], color="#667eea", weight=4).add_to(m)

    map_data = st_folium(m, width=None, height=500, returned_objects=["last_clicked"])

    if map_data and map_data.get("last_clicked"):
        click = map_data["last_clicked"]
        if st.session_state.seleccionando == "A": st.session_state.punto_a = click
        else: st.session_state.punto_b = click
        st.rerun()

# =================================================================================
# TAB - DASHBOARD VIAJES
# =================================================================================
viajes_usuario = db_manager.obtener_viajes(user_actual["id"], es_admin)

with tab_dashboard:
    st.markdown("### 📊 Mis Viajes y Viajes Compartidos")
    
    with st.expander("📥 Importar Viajes desde Excel"):
        archivo_excel = st.file_uploader("Sube tu archivo .xlsx (descargado previamente)", type=["xlsx"])
        if archivo_excel and st.button("Importar Datos"):
            try:
                df = pd.read_excel(archivo_excel)
                importados = 0
                for index, row in df.iterrows():
                    datos = {
                        "nombre": str(row["Nombre"]),
                        "origen": "Origen importado",
                        "destino": str(row["Destino"]),
                        "distancia_km": float(row["Dist. I/V (km)"]),
                        "tiempo_min": float(row.get("Tiempo I/V (min)", 0)),
                        "consumo_l100": 7.0,
                        "precio_comb": 1.55,
                        "num_personas": int(row["Personas"]),
                        "num_dias": int(row["Días"]),
                        "precio_reserva": float(row["Reserva (€)"]),
                        "ppto_comida": float(row["Comida (€)"]),
                        "gasto_gasolina": float(row["Gasolina (€)"]),
                        "gasto_comida": float(row["Comida (€)"]),
                        "gasto_extras": float(row["Extras (€)"]),
                        "coste_total": float(row["Total (€)"]),
                        "coste_persona": float(row["Por Persona (€)"]),
                        "estado": str(row["Estado"]),
                        "gastos_extra": "[]",
                        "itinerario": "{}"
                    }
                    db_manager.guardar_viaje(datos, user_actual["id"])
                    importados += 1
                st.success(f"✅ ¡Se han importado {importados} viajes exitosamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

    if not viajes_usuario:
        st.info("No tienes viajes todavía.")
    else:
        # Restaurar tabla y gráficos
        df = pd.DataFrame(viajes_usuario)
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

        st.dataframe(
            df_display.style.highlight_min(subset=["Total (€)", "Por Persona (€)"], color="#2d5a27"),
            use_container_width=True,
            hide_index=True,
        )

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
            trip_names = {f"{v['nombre']} (ID: {v['id']})": v for v in viajes_usuario}
            selected_pdf = st.selectbox("Selecciona viaje para PDF", list(trip_names.keys()), label_visibility="collapsed")
            if selected_pdf:
                viaje_pdf = trip_names[selected_pdf]
                pdf_bytes = pdf_generator.generar_informe_viaje(viaje_pdf)
                st.download_button(
                    "📄 Descargar Informe PDF",
                    data=pdf_bytes,
                    file_name=f"informe_{viaje_pdf['nombre'].replace(' ', '_').lower()}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # Gráfico Circular
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
        ).properties(title="Desglose Circular de Costes")

        st.altair_chart(chart, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Detalles de los Viajes y Miembros")
        for v in viajes_usuario:
            colabs = db_manager.obtener_colaboradores(v["id"])
            colabs_str = ", ".join([f"{c['username']} ({c['rol']})" for c in colabs])
            
            with st.expander(f"🛫 {v['nombre']} | {v['estado']} | Total: {v['coste_total']:.2f}€"):
                st.markdown(f"**Destino:** {v['destino']} | **Días:** {v['num_dias']} | **Personas:** {v['num_personas']}")
                st.markdown(f"🔑 **Código de Invitación:** `{v.get('codigo_compartido', 'N/A')}`")
                st.markdown(f"👥 **Miembros:** {colabs_str}")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    nuevo_est = st.selectbox("Cambiar Estado", ["Planificado", "Reservado", "Realizado"], index=["Planificado", "Reservado", "Realizado"].index(v["estado"]), key=f"est_{v['id']}")
                    if st.button("Actualizar", key=f"upd_est_{v['id']}"):
                        db_manager.actualizar_estado(v['id'], nuevo_est)
                        st.rerun()
                with c3:
                    if st.button("🗑️ Eliminar Viaje", key=f"del_{v['id']}"):
                        db_manager.eliminar_viaje(v['id'])
                        st.rerun()

# =================================================================================
# TAB - PLANIFICADOR ITINERARIO (CALENDARIO)
# =================================================================================
with tab_itinerario:
    st.markdown("### 📅 Calendario del Viaje (Solo viajes Reservados)")
    viajes_reservados = [v for v in viajes_usuario if v["estado"] == "Reservado"]
    if not viajes_reservados:
        st.info("No tienes viajes en estado 'Reservado'. Cambia el estado de un viaje en el Dashboard para empezar a planificar su calendario.")
    else:
        trip_sel = st.selectbox("Selecciona un viaje reservado", [f"{v['nombre']} (ID: {v['id']})" for v in viajes_reservados])
        trip_data = next(v for v in viajes_reservados if f"{v['nombre']} (ID: {v['id']})" == trip_sel)
        
        num_dias = int(trip_data["num_dias"])
        st.markdown(f"Planificando **{num_dias} días** en {trip_data['destino']}")
        
        # Cargar itinerario (si existe)
        itinerario_guardado = {}
        if trip_data.get("itinerario") and trip_data["itinerario"] != "{}":
            try:
                itinerario_guardado = json.loads(trip_data["itinerario"])
            except: pass
            
        col_it1, col_it2 = st.columns([3, 1])
        with col_it2:
            if st.button("🔄 Refrescar Cambios", use_container_width=True):
                st.rerun()
                
        # Crear estructura base de horas
        horas = [f"{str(h).zfill(2)}:00" for h in range(8, 24)]
        columnas_dias = [f"Día {d}" for d in range(1, num_dias + 1)]
        
        # Preparar datos iniciales para el grid
        data_grid = {"Hora": horas}
        for dia in columnas_dias:
            # Si hay datos guardados para ese dia y esa hora, los carga. Si no, vacío.
            datos_dia = itinerario_guardado.get(dia, {})
            data_grid[dia] = [datos_dia.get(hora, "") for hora in horas]
            
        df_itinerario = pd.DataFrame(data_grid)
        
        st.markdown("📝 **Haz doble clic en una celda para editarla:**")
        # Mostrar como grid editable
        edited_df = st.data_editor(
            df_itinerario, 
            hide_index=True, 
            use_container_width=True,
            disabled=["Hora"] # No permitir editar la columna de Horas
        )
        
        if st.button("💾 Guardar Calendario", type="primary"):
            # Convertir el DataFrame editado de vuelta a un diccionario JSON
            nuevo_itinerario = {}
            for dia in columnas_dias:
                nuevo_itinerario[dia] = {}
                for idx, row in edited_df.iterrows():
                    if pd.notna(row[dia]) and str(row[dia]).strip() != "":
                        nuevo_itinerario[dia][row["Hora"]] = str(row[dia])
            
            db_manager.actualizar_itinerario(trip_data["id"], json.dumps(nuevo_itinerario, ensure_ascii=False))
            st.success("✅ Calendario guardado correctamente.")
            import time
            time.sleep(1)
            st.rerun()


# =================================================================================
# TAB - ALOJAMIENTOS
# =================================================================================
with tab_aloj:
    st.markdown("### 🏨 Mis Alojamientos — Base de Datos Personal")
    
    with st.expander("➕ Añadir nuevo alojamiento", expanded=False):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            aloj_nombre = st.text_input("Nombre del alojamiento", key="aloj_nom")
            aloj_ubicacion = st.text_input("Ubicación", key="aloj_ubi")
            aloj_tipo = st.selectbox("Tipo", ["Apartamento", "Hotel", "Hostal", "Casa rural", "Airbnb", "Otro"], key="aloj_tipo")
            aloj_plataforma = st.text_input("Plataforma", key="aloj_plat")
        with col_a2:
            aloj_precio = st.number_input("Precio noche (€)", 0.0, 10000.0, 60.0, 5.0, key="aloj_precio")
            aloj_puntuacion = st.slider("Tu puntuación", 1, 5, 3, key="aloj_punt")
            aloj_repetir = st.toggle("¿Repetirías?", value=True, key="aloj_rep")
            aloj_color = st.color_picker("Color en mapa", value="#667eea", key="aloj_color")

        aloj_resena = st.text_area("Reseña", key="aloj_res")
        aloj_notas = st.text_input("Notas privadas", key="aloj_not")

        if st.button("💾 Guardar Alojamiento", type="primary", use_container_width=True):
            if not aloj_nombre.strip() or not aloj_ubicacion.strip():
                st.error("⚠️ Nombre y ubicación son obligatorios.")
            else:
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
                    "plataforma": aloj_plataforma.strip(),
                    "notas": aloj_notas.strip(),
                    "color": aloj_color,
                }
                db_manager.guardar_alojamiento(datos_aloj, user_actual["id"])
                st.success("✅ Alojamiento guardado.")
                st.rerun()

    alojs_con_coords = [a for a in mis_alojs if a.get("lat") and a.get("lon")]
    if alojs_con_coords:
        st.markdown("#### 🗺️ Mapa de mis alojamientos")
        center_aloj = [sum(a["lat"] for a in alojs_con_coords) / len(alojs_con_coords),
                       sum(a["lon"] for a in alojs_con_coords) / len(alojs_con_coords)]
        m_aloj = folium.Map(location=center_aloj, zoom_start=6, tiles="CartoDB dark_matter")
        for a in alojs_con_coords:
            color_hex = a.get("color", "#667eea")
            estrellas_tip = "⭐" * a["puntuacion"]
            tip = f"{a['nombre']} — {a['precio_noche']:.0f}€/n {estrellas_tip}"
            folium.CircleMarker(
                location=[a["lat"], a["lon"]], radius=10, color=color_hex, fill=True,
                fill_color=color_hex, fill_opacity=0.8, tooltip=tip,
            ).add_to(m_aloj)
        st_folium(m_aloj, width=None, height=400, key="mapa_aloj", returned_objects=[])

    if not mis_alojs:
        st.info("🗂️ No hay alojamientos guardados.")
    else:
        st.markdown(f"**{len(mis_alojs)}** alojamiento(s) en tu cuenta.")
        for aloj in mis_alojs:
            estrellas = "⭐" * aloj["puntuacion"] + "☆" * (5 - aloj["puntuacion"])
            badge_class = "badge-yes" if aloj["repetir"] else "badge-no"
            badge_text = "✅ Repetiría" if aloj["repetir"] else "❌ No repetiría"

            st.markdown(f'''
            <div class="aloj-card">
                <h4>{aloj["nombre"]} <span class="badge-repeat {badge_class}">{badge_text}</span></h4>
                <div class="aloj-meta">📍 {aloj["ubicacion"]} · 🏷️ {aloj["tipo"]} · 🌐 {aloj["plataforma"]}</div>
                <span class="aloj-price">{aloj["precio_noche"]:.0f} €/noche</span>
                <span style="margin-left:1rem;">{estrellas}</span>
                <div class="aloj-review">💬 "{aloj.get("resena", "")}"</div>
                <div class="aloj-notes">📝 {aloj.get("notas", "")}</div>
            </div>
            ''', unsafe_allow_html=True)

            col_e1, col_e2 = st.columns([4, 1])
            with col_e2:
                if st.button("🗑️", key=f"del_aloj_{aloj['id']}"):
                    db_manager.eliminar_alojamiento(aloj["id"])
                    st.rerun()

# =================================================================================
# TAB - VEREDICTO IA
# =================================================================================
with tab_ia:
    st.markdown("### 🤖 Veredicto de Inteligencia Artificial")
    if len(viajes_usuario) >= 2:
        if st.button("✨ Generar Veredicto", type="primary"):
            st.info("Llamando a Groq API...")
            # ai_helper.generar_veredicto(viajes_usuario[:2]) # Demo
    else:
        st.info("Necesitas al menos 2 viajes para comparar.")

# =================================================================================
# TAB - PANEL ADMIN
# =================================================================================
if es_admin:
    with tab_admin:
        st.markdown("### 🛡️ Panel de Control Administrador")
        
        st.markdown("#### Gestión de Usuarios")
        todos_users = db_manager.obtener_todos_usuarios()
        for u in todos_users:
            with st.expander(f"Usuario: {u['username']} | Rol: {u['rol']}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_rol = st.selectbox("Rol", ["user", "admin"], index=0 if u["rol"]=="user" else 1, key=f"r_{u['id']}")
                    if st.button("Actualizar Rol", key=f"br_{u['id']}"):
                        db_manager.cambiar_rol(u["id"], new_rol)
                        st.rerun()
                with c2:
                    new_pass = st.text_input("Nueva Contraseña", key=f"p_{u['id']}", type="password")
                    if st.button("Forzar Cambio Password", key=f"bp_{u['id']}") and new_pass:
                        db_manager.cambiar_password(u["id"], new_pass)
                        st.success("Contraseña cambiada.")
                with c3:
                    if st.button("🗑️ Borrar Usuario", key=f"delu_{u['id']}", type="primary"):
                        db_manager.eliminar_usuario(u["id"])
                        st.rerun()
                        
        st.markdown("#### Todos los Viajes Globales")
        viajes_global = db_manager.obtener_viajes(0, es_admin=True)
        st.write(f"Total viajes en el sistema: {len(viajes_global)}")

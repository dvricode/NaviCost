# 🌍 NaviCost (TripCalc AI)

NaviCost es una herramienta integral desarrollada en Python con Streamlit para la planificación inteligente de viajes. Su objetivo es calcular el **"Coste Real Total"** de un viaje, teniendo en cuenta la distancia (calculada mediante mapas interactivos), el consumo de combustible, el precio de los alojamientos, el presupuesto para comida y gastos extra personalizados.

Además de ser una calculadora financiera, NaviCost actúa como tu gestor de viajes personal: permite guardar un registro de tus alojamientos favoritos y utiliza Inteligencia Artificial (Llama-3) para analizar tus opciones y recomendarte el mejor destino según tu presupuesto.

## ✨ Características Principales

*   🗺️ **Mapas Interactivos y Rutas:** Selecciona puntos de origen y destino en un mapa interactivo (Folium). Calcula la distancia de conducción utilizando OSRM.
*   💶 **Calculadora de Costes Avanzada:** Desglose automático de costes por viaje y por persona (gasolina, alojamiento, comida, peajes, regalos, etc.).
*   🏨 **Gestor de Alojamientos:** Base de datos integrada para guardar hoteles/apartamentos con notas, enlaces, puntuación y colores personalizados para verlos en el mapa.
*   📊 **Dashboard Comparador:** Panel interactivo con gráficos circulares (Altair) para comparar visualmente los desgloses de costes de múltiples opciones de viaje guardadas.
*   🤖 **Veredicto por IA:** Integración con Groq (Llama-3.1) para generar análisis detallados y recomendaciones sobre qué viaje es más rentable o conveniente.
*   🌤️ **Previsión Meteorológica:** Integración con wttr.in para obtener el clima en tiempo real del destino seleccionado sin necesidad de API keys.
*   📤 **Exportación a Excel:** Descarga tus tablas comparativas en `.xlsx` con un solo clic.

## 🛠️ Stack Tecnológico

*   **Frontend:** [Streamlit](https://streamlit.io/)
*   **Mapas y Geolocalización:** `folium`, `streamlit-folium`, `geopy`
*   **Base de Datos:** SQLite3 (Local)
*   **Visualización de Datos:** `pandas`, `altair`
*   **Inteligencia Artificial:** `groq` API (Llama-3)
*   **Clima:** `wttr.in` API

## 🚀 Instalación y Uso Local

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/navicost.git
   cd navicost
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno:
   Renombra el archivo `.env.example` a `.env` y añade tu clave de la API de Groq:
   ```env
   GROQ_API_KEY=tu_clave_aqui_para_ia
   ```

4. Ejecuta la aplicación:
   ```bash
   streamlit run app.py
   ```

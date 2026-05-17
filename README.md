# 🌍 NaviCost (TripCalc AI)

NaviCost es una herramienta integral en la nube desarrollada con Python (Streamlit) para la planificación inteligente de viajes. Su objetivo es calcular el **"Coste Real Total"** de un viaje, teniendo en cuenta la distancia (calculada mediante mapas interactivos y OSRM), el consumo de combustible, el precio de los alojamientos, el presupuesto para comida y gastos extra personalizados.

Además de ser una calculadora financiera muy precisa, NaviCost actúa como tu gestor de viajes personal: permite guardar un registro de tus alojamientos favoritos en una base de datos en la nube y utiliza **Inteligencia Artificial (Llama-3)** para analizar tus opciones y recomendarte el mejor destino según tu presupuesto.

## ✨ Características Principales

*   ☁️ **100% en la Nube:** Migrado a **Supabase (PostgreSQL)** para tener persistencia total de los datos en tiempo real, permitiendo su despliegue gratuito 24/7 en Streamlit Community Cloud.
*   🗺️ **Mapas Interactivos y Rutas:** Selecciona puntos de origen y destino en un mapa interactivo (`folium`). Calcula la distancia de conducción utilizando OSRM o distancias geodésicas automáticas.
*   💶 **Calculadora Avanzada:** Desglose automático de costes por viaje y por persona (gasolina, alojamiento, comida y un gestor dinámico de gastos extra como peajes o regalos).
*   🏨 **Gestor de Alojamientos:** Base de datos integrada para guardar hoteles o apartamentos con notas, enlaces, puntuación y colores personalizados para verlos en el mapa de planificación.
*   📊 **Dashboard Comparador:** Panel interactivo con gráficos circulares animados (`altair`) para comparar visualmente los desgloses de costes de múltiples opciones de viaje.
*   🤖 **Veredicto por IA:** Integración con Groq (Llama-3.1) para generar análisis detallados y recomendaciones imparciales sobre qué viaje es más rentable o conveniente.
*   📄 **Informes PDF Profesionales:** Generación nativa (con `fpdf2`) de documentos PDF súper limpios y maquetados con el desglose exacto de tu viaje para compartirlo fácilmente.
*   📤 **Exportación a Excel:** Descarga tus tablas comparativas completas en `.xlsx` con un solo clic.
*   🌤️ **Clima en Tiempo Real:** Integración directa con `wttr.in` para saber el tiempo que va a hacer en el destino elegido.

## 🛠️ Stack Tecnológico

*   **Frontend y Servidor Web:** [Streamlit](https://streamlit.io/)
*   **Base de Datos (BaaS):** [Supabase](https://supabase.com/) (`supabase-py`)
*   **Mapas y Geolocalización:** `folium`, `streamlit-folium`, `geopy`
*   **Visualización de Datos:** `pandas`, `altair`
*   **Inteligencia Artificial:** API de `groq` (Modelos Llama-3)
*   **Generación de Documentos:** `fpdf2`, `openpyxl`

## 🚀 Instalación y Despliegue en Streamlit Cloud

1. Clona este repositorio y súbelo a tu propio GitHub:
   ```bash
   git clone https://github.com/dvricode/NaviCost.git
   ```

2. Ejecuta el script `supabase_schema.sql` en el SQL Editor de tu proyecto de Supabase para generar las tablas. **Asegúrate de desactivar RLS** en las tablas `viajes` y `alojamientos` para permitir las operaciones anónimas, o configurar políticas personalizadas.

3. Sube la app a Streamlit Community Cloud (`share.streamlit.io`) conectando tu repositorio de GitHub.

4. Configura las siguientes variables de entorno en los **Secrets** de Streamlit:
   ```toml
   GROQ_API_KEY="gsk_tu_clave_de_groq"
   SUPABASE_URL="https://tu_proyecto.supabase.co"
   SUPABASE_KEY="eyJ..._tu_clave_anon_de_supabase"
   ```

¡Y listo! La aplicación se ejecutará de forma gratuita en internet 24/7.

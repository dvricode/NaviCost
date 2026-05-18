# 🌍 NaviCost (TripCalc AI)

NaviCost es una herramienta colaborativa integral desarrollada con Python (Streamlit) para la planificación de viajes. Su objetivo es calcular el **"Coste Real Total"** de un viaje, teniendo en cuenta la distancia (mapas interactivos y OSRM), el consumo de combustible, el precio de los alojamientos, el presupuesto para comida y gastos extra personalizados.

Con las recientes actualizaciones, NaviCost ha pasado de ser una calculadora financiera de uso individual a una **plataforma colaborativa completa** con gestión de usuarios, roles de administración y un sistema de invitaciones.

## ✨ Características Principales

*   ☁️ **Base de Datos Centralizada:** Integración total con **Supabase (PostgreSQL)** para tener persistencia de los datos en tiempo real.
*   🔒 **Sistema de Usuarios Propio:** Flujo de registro e inicio de sesión personalizado y seguro. Las contraseñas se almacenan cifradas (Hashing con `bcrypt`).
*   👥 **Viajes Colaborativos:** Generación automática de **Códigos de Invitación**. Los usuarios pueden compartir sus viajes; si un amigo introduce el código, ambos podrán editar y ver el mismo viaje en tiempo real.
*   📅 **Planificador de Itinerarios (Grid):** Un calendario interactivo editable (estilo Excel) donde todos los miembros de un viaje "Reservado" pueden organizar las horas y días del viaje.
*   🛡️ **Panel de Administrador:** Los administradores tienen acceso a una vista especial para gestionar a todos los usuarios, cambiar contraseñas forzosamente, asignar roles y ver estadísticas globales.
*   🗺️ **Mapas Interactivos y Rutas:** Selecciona puntos de origen y destino en un mapa interactivo (`folium`). Calcula la distancia de conducción utilizando OSRM.
*   🏨 **Gestor de Alojamientos Personal:** Base de datos exclusiva por usuario para guardar hoteles con notas, puntuación y renderizarlos en un mapa privado de alojamientos favoritos.
*   📊 **Dashboard Comparador:** Panel interactivo con gráficos circulares animados (`altair`) para comparar los costes, y herramientas para importar/exportar a `.xlsx` o `PDF`.
*   🤖 **Veredicto por IA:** Integración con Groq (Llama-3.1) para generar análisis detallados y recomendaciones sobre qué viaje es más conveniente.

## 🛠️ Stack Tecnológico

*   **Frontend y Backend:** [Streamlit](https://streamlit.io/)
*   **Seguridad:** `bcrypt`
*   **Base de Datos (BaaS):** [Supabase](https://supabase.com/) (`supabase-py`)
*   **Mapas y Geolocalización:** `folium`, `streamlit-folium`, `geopy`
*   **Visualización y UI:** `pandas`, `altair`
*   **Generación de Documentos:** `fpdf2`, `openpyxl`

## 🚀 Instalación y Despliegue

1. Clona este repositorio:
   ```bash
   git clone https://github.com/dvricode/NaviCost.git
   ```

2. Ejecuta el script `supabase_schema.sql` en el SQL Editor de tu proyecto de Supabase para generar las tablas y **desactivar RLS** (Row Level Security) para permitir que la aplicación gestione la autenticación y operaciones desde el backend en Streamlit.

3. Configura tus variables de entorno en el archivo `.env` o en los Secrets de tu servidor:
   ```toml
   GROQ_API_KEY="gsk_tu_clave_de_groq"
   SUPABASE_URL="https://tu_proyecto.supabase.co"
   SUPABASE_KEY="eyJ..._tu_clave_anon_de_supabase"
   ```

4. Ejecuta la aplicación localmente:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

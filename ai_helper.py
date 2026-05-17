"""
ai_helper.py — Módulo de integración con la API de Groq (Llama-3) para NaviCost.

Genera un veredicto inteligente comparando las opciones de viaje
del usuario usando el modelo Llama-3.1-8b-instant.
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─── Configuración de la API Key ─────────────────────────────────────────
# Coloca tu API key de Groq en un archivo .env en la raíz del proyecto:
#   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Puedes obtener tu key gratuita en: https://console.groq.com/keys
# ──────────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    "Eres un asesor de viajes experto. Analiza estas opciones de viaje "
    "comparando el coste real total (que incluye gasolina, alojamiento y comida), "
    "la distancia y el tiempo de conducción. Da un veredicto de 2 o 3 párrafos "
    "recomendando la mejor opción de forma objetiva para maximizar el tiempo "
    "de disfrute y optimizar el presupuesto. "
    "Responde siempre en español. Usa emojis para hacer la respuesta más visual."
)


def generar_veredicto(viajes: list[dict]) -> str:
    """
    Envía los datos de las opciones de viaje a Groq y devuelve
    el veredicto generado por la IA.

    Args:
        viajes: Lista de diccionarios con los datos de cada viaje.

    Returns:
        Texto del veredicto generado por Llama-3.
    """
    if not GROQ_API_KEY:
        return (
            "⚠️ **Error de configuración**: No se encontró la API Key de Groq.\n\n"
            "Crea un archivo `.env` en la carpeta del proyecto con:\n"
            "```\nGROQ_API_KEY=tu_key_aqui\n```\n"
            "Obtén tu key en [console.groq.com/keys](https://console.groq.com/keys)"
        )

    # Preparar un resumen limpio de los viajes para el prompt
    resumen_viajes = []
    for v in viajes:
        resumen_viajes.append({
            "nombre": v.get("nombre", "Sin nombre"),
            "destino": v.get("destino", "—"),
            "distancia_ida_km": round(v.get("distancia_km", 0) / 2, 1),
            "distancia_ida_vuelta_km": round(v.get("distancia_km", 0), 1),
            "tiempo_conduccion_min": round(v.get("tiempo_min", 0), 1),
            "num_personas": v.get("num_personas", 1),
            "num_dias": v.get("num_dias", 1),
            "coste_reserva_eur": round(v.get("precio_reserva", 0), 2),
            "coste_gasolina_eur": round(v.get("gasto_gasolina", 0), 2),
            "coste_comida_eur": round(v.get("gasto_comida", 0), 2),
            "coste_total_eur": round(v.get("coste_total", 0), 2),
            "coste_por_persona_eur": round(v.get("coste_persona", 0), 2),
        })

    user_message = (
        "Aquí tienes las opciones de viaje a comparar:\n\n"
        f"```json\n{json.dumps(resumen_viajes, indent=2, ensure_ascii=False)}\n```\n\n"
        "Analiza todos los datos y recomienda la mejor opción."
    )

    try:
        client = Groq(api_key=GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return chat_completion.choices[0].message.content

    except Exception as e:
        return f"❌ **Error al conectar con Groq**: {str(e)}"

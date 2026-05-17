"""
weather_helper.py — Módulo para obtener el clima en el destino.

Usa la API gratuita de wttr.in (no requiere API key).
"""

import requests


def obtener_clima(lat: float, lon: float) -> dict | None:
    """
    Obtiene el clima actual y previsión para unas coordenadas.

    Args:
        lat: Latitud del destino.
        lon: Longitud del destino.

    Returns:
        Diccionario con datos del clima o None si falla.
    """
    try:
        url = f"https://wttr.in/{lat},{lon}?format=j1&lang=es"
        r = requests.get(url, timeout=10)
        data = r.json()

        current = data.get("current_condition", [{}])[0]
        weather = data.get("weather", [])

        # Descripción en español
        desc_list = current.get("lang_es", [])
        desc = desc_list[0].get("value", "") if desc_list else current.get("weatherDesc", [{}])[0].get("value", "")

        result = {
            "temp_c": current.get("temp_C", "—"),
            "sensacion_c": current.get("FeelsLikeC", "—"),
            "humedad": current.get("humidity", "—"),
            "viento_kmh": current.get("windspeedKmph", "—"),
            "descripcion": desc,
            "prevision": [],
        }

        for dia in weather[:3]:
            desc_dia = dia.get("hourly", [{}])[4]  # Mediodía aprox
            desc_dia_list = desc_dia.get("lang_es", [])
            desc_dia_text = desc_dia_list[0].get("value", "") if desc_dia_list else desc_dia.get("weatherDesc", [{}])[0].get("value", "")

            result["prevision"].append({
                "fecha": dia.get("date", ""),
                "max_c": dia.get("maxtempC", "—"),
                "min_c": dia.get("mintempC", "—"),
                "descripcion": desc_dia_text,
            })

        return result

    except Exception:
        return None

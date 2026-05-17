import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

datos = {
    "nombre": "Test",
    "origen": "0.0, 0.0",
    "destino": "0.0, 0.0",
    "lat_origen": 0.0,
    "lon_origen": 0.0,
    "lat_destino": 0.0,
    "lon_destino": 0.0,
    "distancia_km": 10.0,
    "tiempo_min": 10.0,
    "consumo_l100": 7.0,
    "precio_comb": 1.5,
    "num_personas": 2,
    "num_dias": 3,
    "precio_reserva": 100.0,
    "ppto_comida": 50.0,
    "gasto_gasolina": 1.05,
    "gasto_comida": 50.0,
    "coste_total": 151.05,
    "coste_persona": 75.52,
    "fecha_ida": "",
    "fecha_vuelta": "",
    "estado": "Planificado",
    "alojamiento_id": None,
    "gastos_extra": "[]",
    "gasto_extras": 0.0,
}

try:
    res = supabase.table("viajes").insert(datos).execute()
    print("Success:", res)
except Exception as e:
    print("Error:", repr(e))
    import traceback
    traceback.print_exc()

"""
db_manager.py — Módulo de gestión de la base de datos Supabase para NaviCost.

Conecta directamente con la base de datos en la nube para persistencia total.
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan las credenciales de Supabase en el archivo .env")

# Cliente de conexión a Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db() -> None:
    """
    Ya no es necesario crear las tablas por código.
    En Supabase, las tablas se crean directamente desde el panel SQL.
    Esta función se mantiene vacía para no romper compatibilidad con app.py.
    """
    pass


# ═══════════════════════════════════════════════════════════════════════════
# VIAJES — CRUD
# ═══════════════════════════════════════════════════════════════════════════

def guardar_viaje(datos: dict) -> int:
    """Inserta una nueva opción de viaje en Supabase."""
    try:
        response = supabase.table("viajes").insert(datos).execute()
        return response.data[0]["id"] if response.data else -1
    except Exception as e:
        import streamlit as st
        st.error(f"Error detallado de Supabase: {getattr(e, 'message', str(e))} - {getattr(e, 'details', '')}")
        raise e


def obtener_viajes() -> list[dict]:
    """Lee todos los viajes guardados en Supabase."""
    response = supabase.table("viajes").select("*").order("fecha_creacion", desc=True).execute()
    return response.data


def actualizar_estado(viaje_id: int, estado: str) -> None:
    """Actualiza el estado de un viaje."""
    supabase.table("viajes").update({"estado": estado}).eq("id", viaje_id).execute()


def actualizar_viaje(viaje_id: int, datos: dict) -> None:
    """Actualiza todos los campos de un viaje modificado."""
    supabase.table("viajes").update(datos).eq("id", viaje_id).execute()


def eliminar_viaje(viaje_id: int) -> None:
    """Elimina un viaje por su ID."""
    supabase.table("viajes").delete().eq("id", viaje_id).execute()


def limpiar_viajes() -> None:
    """Elimina todos los viajes."""
    supabase.table("viajes").delete().neq("id", 0).execute()  # Borra todo


# ═══════════════════════════════════════════════════════════════════════════
# ALOJAMIENTOS — CRUD
# ═══════════════════════════════════════════════════════════════════════════

def guardar_alojamiento(datos: dict) -> int:
    """Guarda un nuevo alojamiento en la base de datos."""
    response = supabase.table("alojamientos").insert(datos).execute()
    return response.data[0]["id"] if response.data else -1


def obtener_alojamientos() -> list[dict]:
    """Obtiene la lista de alojamientos ordenados por los más recientes."""
    response = supabase.table("alojamientos").select("*").order("fecha_creacion", desc=True).execute()
    return response.data


def actualizar_alojamiento(aloj_id: int, datos: dict) -> None:
    """Actualiza un alojamiento existente."""
    supabase.table("alojamientos").update(datos).eq("id", aloj_id).execute()


def eliminar_alojamiento(aloj_id: int) -> None:
    """Elimina un alojamiento por su ID."""
    # Primero desvinculamos de los viajes para no romper relaciones si las hubiera (opcional)
    supabase.table("viajes").update({"alojamiento_id": None}).eq("alojamiento_id", aloj_id).execute()
    # Luego borramos el alojamiento
    supabase.table("alojamientos").delete().eq("id", aloj_id).execute()

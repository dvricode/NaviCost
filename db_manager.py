"""
db_manager.py — Módulo de gestión de la base de datos Supabase para NaviCost.

Conecta directamente con la base de datos en la nube para persistencia total.
"""

import os
import json
import uuid
import bcrypt
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan las credenciales de Supabase en el archivo .env")

# Cliente de conexión a Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db() -> None:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# USUARIOS Y AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════════════════════

def encriptar_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verificar_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def registrar_usuario(username: str, password: str, rol: str = 'user') -> dict:
    logger.info(f"Intentando registrar al usuario: {username}")
    # Comprobar si existe
    exist = supabase.table("usuarios").select("id").eq("username", username).execute()
    if exist.data:
        logger.warning(f"Fallo al registrar: El usuario '{username}' ya existe.")
        return {"error": "El nombre de usuario ya está en uso."}
    
    hashed = encriptar_password(password)
    try:
        res = supabase.table("usuarios").insert({
            "username": username,
            "password_hash": hashed,
            "rol": rol
        }).execute()
        logger.info(f"Usuario registrado exitosamente: {username}")
        return {"success": True, "user": res.data[0]}
    except Exception as e:
        logger.error(f"Excepción al registrar usuario '{username}': {str(e)}")
        return {"error": str(e)}

def verificar_login(username: str, password: str) -> dict:
    logger.info(f"Intento de inicio de sesión para el usuario: {username}")
    res = supabase.table("usuarios").select("*").eq("username", username).execute()
    if not res.data:
        logger.warning(f"Login fallido: Usuario '{username}' no encontrado.")
        return {"error": "Usuario no encontrado."}
    
    user = res.data[0]
    if verificar_password(password, user["password_hash"]):
        user.pop("password_hash") # No devolver el hash a la UI
        logger.info(f"Login exitoso para el usuario: {username}")
        return {"success": True, "user": user}
    else:
        logger.warning(f"Login fallido: Contraseña incorrecta para el usuario '{username}'.")
        return {"error": "Contraseña incorrecta."}

def cambiar_password(usuario_id: int, nueva_password: str) -> bool:
    hashed = encriptar_password(nueva_password)
    res = supabase.table("usuarios").update({"password_hash": hashed}).eq("id", usuario_id).execute()
    return bool(res.data)

def obtener_usuario_por_id(usuario_id: int) -> dict:
    res = supabase.table("usuarios").select("id, username, rol").eq("id", usuario_id).execute()
    if res.data:
        return res.data[0]
    return None

def obtener_todos_usuarios() -> list:
    res = supabase.table("usuarios").select("id, username, rol, fecha_creacion").order("fecha_creacion").execute()
    return res.data

def eliminar_usuario(usuario_id: int) -> None:
    supabase.table("usuarios").delete().eq("id", usuario_id).execute()

def cambiar_rol(usuario_id: int, nuevo_rol: str) -> None:
    supabase.table("usuarios").update({"rol": nuevo_rol}).eq("id", usuario_id).execute()


# ═══════════════════════════════════════════════════════════════════════════
# VIAJES — CRUD Y COLABORACIÓN
# ═══════════════════════════════════════════════════════════════════════════

def generar_codigo_viaje() -> str:
    return str(uuid.uuid4())[:8].upper()

def guardar_viaje(datos: dict, creador_id: int) -> int:
    logger.info(f"Guardando nuevo viaje por creador ID {creador_id}: {datos.get('nombre')}")
    datos["creador_id"] = creador_id
    datos["codigo_compartido"] = generar_codigo_viaje()
    
    try:
        response = supabase.table("viajes").insert(datos).execute()
        if response.data:
            viaje_id = response.data[0]["id"]
            logger.info(f"Viaje guardado exitosamente con ID {viaje_id}")
            # Añadir creador como colaborador con rol 'Creador'
            supabase.table("viajes_colaboradores").insert({
                "viaje_id": viaje_id,
                "usuario_id": creador_id,
                "rol_viaje": "Creador"
            }).execute()
            return viaje_id
        return -1
    except Exception as e:
        import streamlit as st
        st.error(f"Error detallado de Supabase: {getattr(e, 'message', str(e))} - {getattr(e, 'details', '')}")
        raise e

def obtener_viajes(usuario_id: int, es_admin: bool = False) -> list[dict]:
    if es_admin:
        # Admin ve todos
        response = supabase.table("viajes").select("*").order("fecha_creacion", desc=True).execute()
        return response.data
    else:
        # Usuario normal ve los que ha creado o a los que se ha unido
        colab_res = supabase.table("viajes_colaboradores").select("viaje_id").eq("usuario_id", usuario_id).execute()
        if not colab_res.data:
            return []
        
        viajes_ids = [c["viaje_id"] for c in colab_res.data]
        response = supabase.table("viajes").select("*").in_("id", viajes_ids).order("fecha_creacion", desc=True).execute()
        return response.data

def unirse_a_viaje(usuario_id: int, codigo: str) -> dict:
    viaje_res = supabase.table("viajes").select("id").eq("codigo_compartido", codigo).execute()
    if not viaje_res.data:
        return {"error": "Código no válido o viaje no existe."}
    
    viaje_id = viaje_res.data[0]["id"]
    
    # Comprobar si ya está unido
    check = supabase.table("viajes_colaboradores").select("id").eq("viaje_id", viaje_id).eq("usuario_id", usuario_id).execute()
    if check.data:
        return {"error": "Ya eres miembro de este viaje."}
    
    # Unirse
    try:
        supabase.table("viajes_colaboradores").insert({
            "viaje_id": viaje_id,
            "usuario_id": usuario_id,
            "rol_viaje": "Colaborador"
        }).execute()
        return {"success": True, "viaje_id": viaje_id}
    except Exception as e:
        return {"error": str(e)}

def obtener_colaboradores(viaje_id: int) -> list:
    # Usar sintaxis PostgREST para joins o hacer dos queries
    res = supabase.table("viajes_colaboradores").select("rol_viaje, usuarios(username)").eq("viaje_id", viaje_id).execute()
    colabs = []
    for c in res.data:
        username = c.get("usuarios", {}).get("username", "Desconocido")
        colabs.append({"username": username, "rol": c["rol_viaje"]})
    return colabs

def actualizar_estado(viaje_id: int, estado: str) -> None:
    supabase.table("viajes").update({"estado": estado}).eq("id", viaje_id).execute()

def actualizar_viaje(viaje_id: int, datos: dict) -> None:
    supabase.table("viajes").update(datos).eq("id", viaje_id).execute()

def actualizar_itinerario(viaje_id: int, itinerario_json: str) -> None:
    supabase.table("viajes").update({"itinerario": itinerario_json}).eq("id", viaje_id).execute()

def eliminar_viaje(viaje_id: int) -> None:
    supabase.table("viajes").delete().eq("id", viaje_id).execute()


# ═══════════════════════════════════════════════════════════════════════════
# ALOJAMIENTOS — CRUD
# ═══════════════════════════════════════════════════════════════════════════

def guardar_alojamiento(datos: dict, creador_id: int) -> int:
    datos["creador_id"] = creador_id
    response = supabase.table("alojamientos").insert(datos).execute()
    return response.data[0]["id"] if response.data else -1

def obtener_alojamientos(usuario_id: int, es_admin: bool = False) -> list[dict]:
    if es_admin:
        response = supabase.table("alojamientos").select("*").order("fecha_creacion", desc=True).execute()
    else:
        response = supabase.table("alojamientos").select("*").eq("creador_id", usuario_id).order("fecha_creacion", desc=True).execute()
    return response.data

def actualizar_alojamiento(aloj_id: int, datos: dict) -> None:
    supabase.table("alojamientos").update(datos).eq("id", aloj_id).execute()

def eliminar_alojamiento(aloj_id: int) -> None:
    supabase.table("viajes").update({"alojamiento_id": None}).eq("alojamiento_id", aloj_id).execute()
    supabase.table("alojamientos").delete().eq("id", aloj_id).execute()

def actualizar_resena(aloj_id: int, puntuacion: int, resena: str, repetir: bool, notas: str) -> None:
    supabase.table("alojamientos").update({
        "puntuacion": puntuacion,
        "resena": resena,
        "repetir": int(repetir),
        "notas": notas
    }).eq("id", aloj_id).execute()

def limpiar_alojamientos(usuario_id: int = None, es_admin: bool = False) -> None:
    if es_admin:
        supabase.table("alojamientos").delete().neq("id", 0).execute()
    elif usuario_id:
        supabase.table("alojamientos").delete().eq("creador_id", usuario_id).execute()

# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICACIONES
# ═══════════════════════════════════════════════════════════════════════════

def crear_notificacion_colaboradores(viaje_id: int, autor_id: int, mensaje: str) -> None:
    # Buscar todos los colaboradores del viaje que no sean el autor
    res = supabase.table("viajes_colaboradores").select("usuario_id").eq("viaje_id", viaje_id).execute()
    if not res.data:
        return
    
    for c in res.data:
        u_id = c["usuario_id"]
        if u_id != autor_id:
            supabase.table("notificaciones").insert({
                "user_id": u_id,
                "viaje_id": viaje_id,
                "mensaje": mensaje
            }).execute()

def obtener_notificaciones_usuario(user_id: int) -> list:
    res = supabase.table("notificaciones").select("*").eq("user_id", user_id).eq("leida", False).order("fecha", desc=True).execute()
    return res.data if res.data else []

def marcar_notificacion_leida(notif_id: int) -> None:
    supabase.table("notificaciones").update({"leida": True}).eq("id", notif_id).execute()

def marcar_todas_leidas(user_id: int) -> None:
    supabase.table("notificaciones").update({"leida": True}).eq("user_id", user_id).eq("leida", False).execute()

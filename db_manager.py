"""
db_manager.py — Módulo de gestión de la base de datos SQLite para NaviCost.

Maneja la creación de tablas, inserción de opciones de viaje
y lectura de todos los registros para la comparación.
Incluye gestión de alojamientos con reseñas personales.
"""

import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "viajes.db")


def _get_connection() -> sqlite3.Connection:
    """Crea y devuelve una conexión a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_exists(cursor, table: str, column: str) -> bool:
    """Comprueba si una columna existe en una tabla."""
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def init_db() -> None:
    """Crea las tablas de viajes y alojamientos si no existen."""
    conn = _get_connection()
    cursor = conn.cursor()

    # ── Tabla de viajes ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS viajes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT    NOT NULL,
            origen           TEXT    NOT NULL,
            destino          TEXT    NOT NULL,
            lat_origen       REAL,
            lon_origen       REAL,
            lat_destino      REAL,
            lon_destino      REAL,
            distancia_km     REAL    NOT NULL,
            tiempo_min       REAL,
            consumo_l100     REAL    NOT NULL,
            precio_comb      REAL    NOT NULL,
            num_personas     INTEGER NOT NULL,
            num_dias         INTEGER NOT NULL,
            precio_reserva   REAL    NOT NULL,
            ppto_comida      REAL    NOT NULL,
            gasto_gasolina   REAL    NOT NULL,
            gasto_comida     REAL    NOT NULL,
            coste_total      REAL    NOT NULL,
            coste_persona    REAL    NOT NULL,
            fecha_creacion   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Columnas nuevas para viajes (migraciones seguras)
    nuevas_cols_viajes = {
        "fecha_ida":       "TEXT DEFAULT ''",
        "fecha_vuelta":    "TEXT DEFAULT ''",
        "estado":          "TEXT DEFAULT 'Planificado'",
        "alojamiento_id":  "INTEGER DEFAULT NULL",
        "gastos_extra":    "TEXT DEFAULT '[]'",
        "gasto_extras":    "REAL DEFAULT 0",
    }
    for col, definition in nuevas_cols_viajes.items():
        if not _column_exists(cursor, "viajes", col):
            cursor.execute(f"ALTER TABLE viajes ADD COLUMN {col} {definition}")

    # ── Tabla de alojamientos ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alojamientos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT    NOT NULL,
            ubicacion        TEXT    NOT NULL,
            lat              REAL,
            lon              REAL,
            tipo             TEXT    DEFAULT 'Apartamento',
            precio_noche     REAL    NOT NULL,
            puntuacion       INTEGER DEFAULT 3,
            resena           TEXT    DEFAULT '',
            repetir          INTEGER DEFAULT 1,
            url              TEXT    DEFAULT '',
            plataforma       TEXT    DEFAULT '',
            notas            TEXT    DEFAULT '',
            color            TEXT    DEFAULT '#667eea',
            fecha_creacion   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migración para color
    if not _column_exists(cursor, "alojamientos", "color"):
        cursor.execute("ALTER TABLE alojamientos ADD COLUMN color TEXT DEFAULT '#667eea'")

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# VIAJES — CRUD
# ═══════════════════════════════════════════════════════════════════════════

def guardar_viaje(datos: dict) -> int:
    """Inserta una nueva opción de viaje en la base de datos."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO viajes (
            nombre, origen, destino,
            lat_origen, lon_origen, lat_destino, lon_destino,
            distancia_km, tiempo_min,
            consumo_l100, precio_comb,
            num_personas, num_dias,
            precio_reserva, ppto_comida,
            gasto_gasolina, gasto_comida,
            coste_total, coste_persona,
            fecha_ida, fecha_vuelta, estado,
            alojamiento_id, gastos_extra, gasto_extras
        ) VALUES (
            :nombre, :origen, :destino,
            :lat_origen, :lon_origen, :lat_destino, :lon_destino,
            :distancia_km, :tiempo_min,
            :consumo_l100, :precio_comb,
            :num_personas, :num_dias,
            :precio_reserva, :ppto_comida,
            :gasto_gasolina, :gasto_comida,
            :coste_total, :coste_persona,
            :fecha_ida, :fecha_vuelta, :estado,
            :alojamiento_id, :gastos_extra, :gasto_extras
        )
    """, datos)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def obtener_viajes() -> list[dict]:
    """Lee todos los viajes guardados en la base de datos."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viajes ORDER BY fecha_creacion DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def actualizar_estado(viaje_id: int, estado: str) -> None:
    """Actualiza el estado de un viaje."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE viajes SET estado = ? WHERE id = ?", (estado, viaje_id))
    conn.commit()
    conn.close()

def actualizar_viaje(viaje_id: int, datos: dict) -> None:
    """Actualiza todos los campos de un viaje modificado."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE viajes SET
            nombre = :nombre,
            consumo_l100 = :consumo_l100,
            precio_comb = :precio_comb,
            num_personas = :num_personas,
            num_dias = :num_dias,
            precio_reserva = :precio_reserva,
            ppto_comida = :ppto_comida,
            gasto_gasolina = :gasto_gasolina,
            gasto_comida = :gasto_comida,
            gasto_extras = :gasto_extras,
            coste_total = :coste_total,
            coste_persona = :coste_persona
        WHERE id = :id
    """, {**datos, "id": viaje_id})
    conn.commit()
    conn.close()


def eliminar_viaje(viaje_id: int) -> None:
    """Elimina un viaje por su ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM viajes WHERE id = ?", (viaje_id,))
    conn.commit()
    conn.close()


def limpiar_viajes() -> None:
    """Elimina TODOS los viajes de la base de datos."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM viajes")
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# ALOJAMIENTOS — CRUD
# ═══════════════════════════════════════════════════════════════════════════

def guardar_alojamiento(datos: dict) -> int:
    """Inserta un nuevo alojamiento en la base de datos."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alojamientos (
            nombre, ubicacion, lat, lon, tipo,
            precio_noche, puntuacion, resena,
            repetir, url, plataforma, notas, color
        ) VALUES (
            :nombre, :ubicacion, :lat, :lon, :tipo,
            :precio_noche, :puntuacion, :resena,
            :repetir, :url, :plataforma, :notas, :color
        )
    """, datos)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def obtener_alojamientos() -> list[dict]:
    """Lee todos los alojamientos guardados."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alojamientos ORDER BY fecha_creacion DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_alojamiento(aloj_id: int) -> dict | None:
    """Obtiene un alojamiento por su ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alojamientos WHERE id = ?", (aloj_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_resena(aloj_id: int, puntuacion: int, resena: str,
                      repetir: bool, notas: str) -> None:
    """Actualiza la reseña y puntuación de un alojamiento."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alojamientos
        SET puntuacion = ?, resena = ?, repetir = ?, notas = ?,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (puntuacion, resena, int(repetir), notas, aloj_id))
    conn.commit()
    conn.close()


def eliminar_alojamiento(aloj_id: int) -> None:
    """Elimina un alojamiento por su ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alojamientos WHERE id = ?", (aloj_id,))
    conn.commit()
    conn.close()


def limpiar_alojamientos() -> None:
    """Elimina TODOS los alojamientos de la base de datos."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alojamientos")
    conn.commit()
    conn.close()

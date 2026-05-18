import os
import uuid
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def importar_datos():
    archivo_excel = "navicost_comparacion (1).xlsx"
    
    if not os.path.exists(archivo_excel):
        print(f"No se encuentra el archivo {archivo_excel}")
        return

    # Buscar tu usuario (el primero que sea admin, o el ID 1)
    res_users = supabase.table("usuarios").select("id").order("id").limit(1).execute()
    if not res_users.data:
        print("¡Error! Debes registrarte en la aplicación antes de importar los datos.")
        return
        
    creador_id = res_users.data[0]["id"]
    print(f"Se importarán los viajes y se asignarán al usuario ID: {creador_id}")

    df = pd.read_excel(archivo_excel)
    
    viajes_importados = 0
    for index, row in df.iterrows():
        try:
            # Rellenar datos faltantes con valores por defecto ya que el Excel 
            # solo contiene un resumen y no los datos técnicos completos.
            datos = {
                "creador_id": creador_id,
                "codigo_compartido": str(uuid.uuid4())[:8].upper(),
                "nombre": str(row["Nombre"]),
                "origen": "Origen importado",  # No está en el Excel
                "destino": str(row["Destino"]),
                "distancia_km": float(row["Dist. I/V (km)"]),
                "tiempo_min": float(row.get("Tiempo I/V (min)", 0)),
                "consumo_l100": 7.0, # Por defecto
                "precio_comb": 1.55, # Por defecto
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
            
            # Guardar en viajes
            res_viaje = supabase.table("viajes").insert(datos).execute()
            viaje_id = res_viaje.data[0]["id"]
            
            # Añadirte como colaborador/creador del viaje para que puedas verlo
            supabase.table("viajes_colaboradores").insert({
                "viaje_id": viaje_id,
                "usuario_id": creador_id,
                "rol_viaje": "Creador"
            }).execute()
            
            print(f"✅ Importado: {row['Nombre']}")
            viajes_importados += 1
            
        except Exception as e:
            print(f"❌ Error al importar la fila {index}: {e}")
            
    print(f"\n¡Importación finalizada! Se han importado {viajes_importados} viajes.")

if __name__ == "__main__":
    importar_datos()

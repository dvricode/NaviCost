from fpdf import FPDF
import json

class PDFReport(FPDF):
    def header(self):
        # Header con fondo oscuro y texto blanco
        self.set_fill_color(33, 37, 41)
        self.rect(0, 0, 210, 40, 'F')
        self.set_y(15)
        self.set_font("helvetica", "B", 24)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "NaviCost - Informe de Viaje", border=0, align="C", fill=False)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}} - Generado con NaviCost AI", align="C")

def generar_informe_viaje(viaje: dict) -> bytes:
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    def s(txt):
        return str(txt).replace("€", "EUR")
    
    # Texto oscuro
    pdf.set_text_color(40, 40, 40)
    
    # ─── TÍTULO DEL VIAJE ───
    pdf.set_y(50)
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 10, s(viaje['nombre']).upper(), ln=True, align="C")
    pdf.ln(10)
    
    # ─── INFORMACIÓN GENERAL ───
    pdf.set_font("helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " DATOS PRINCIPALES", border=0, ln=True, fill=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(45, 8, "Estado:", border=0)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(50, 8, s(viaje.get('estado', 'Planificado')), border=0, ln=True)

    pdf.set_font("helvetica", "", 12)
    pdf.cell(45, 8, "Distancia I/V:", border=0)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(50, 8, f"{float(viaje.get('distancia_km', 0)):.1f} km", border=0)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(45, 8, "Tiempo I/V:", border=0)
    pdf.set_font("helvetica", "B", 12)
    t = float(viaje.get('tiempo_min', 0))
    tiempo_str = f"{int(t//60)}h {int(t%60)}m" if t else "N/A"
    pdf.cell(50, 8, tiempo_str, border=0, ln=True)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(45, 8, "Fechas:", border=0)
    pdf.set_font("helvetica", "B", 12)
    f_ida = s(viaje.get('fecha_ida')) or 'N/A'
    f_vue = s(viaje.get('fecha_vuelta')) or 'N/A'
    pdf.cell(50, 8, f"{f_ida} a {f_vue}", border=0)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(45, 8, "Personas / Días:", border=0)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(50, 8, f"{viaje.get('num_personas', 0)} pers. / {viaje.get('num_dias', 0)} días", border=0, ln=True)

    pdf.ln(10)
    
    # ─── DESGLOSE FINANCIERO ───
    pdf.set_font("helvetica", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " DESGLOSE DE COSTES", border=0, ln=True, fill=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.set_fill_color(102, 126, 234) # Color principal
    pdf.set_text_color(255, 255, 255)
    pdf.cell(140, 10, "Concepto", border=1, fill=True)
    pdf.cell(50, 10, "Importe (EUR)", border=1, align="R", fill=True, ln=True)
    
    pdf.set_text_color(40, 40, 40)
    pdf.set_font("helvetica", "", 12)
    
    def add_row(concepto, importe):
        pdf.cell(140, 10, concepto, border=1)
        pdf.cell(50, 10, f"{float(importe):.2f} EUR", border=1, align="R", ln=True)
        
    add_row("Alojamiento (Reserva total)", viaje.get('precio_reserva', 0))
    add_row("Transporte (Combustible ruta)", viaje.get('gasto_gasolina', 0))
    add_row("Dietas (Comida total del viaje)", viaje.get('gasto_comida', 0))
    add_row("Gastos Extra", viaje.get('gasto_extras', 0))
    
    # Sub-conceptos de extras si los hay
    extras_str = viaje.get('gastos_extra', '[]')
    if extras_str and extras_str != '[]':
        try:
            extras_list = json.loads(extras_str)
            if extras_list:
                pdf.set_font("helvetica", "I", 10)
                for ex in extras_list:
                    pdf.cell(140, 8, f"   - {ex['concepto']}", border="LR")
                    pdf.cell(50, 8, f"{float(ex['coste']):.2f} EUR", border="LR", align="R", ln=True)
                pdf.set_font("helvetica", "", 12)
                # Cerrar borde
                pdf.cell(140, 0, "", border="T")
                pdf.cell(50, 0, "", border="T", ln=True)
        except Exception:
            pass

    pdf.ln(10)
    
    # ─── TOTALES ───
    pdf.set_font("helvetica", "B", 16)
    pdf.set_fill_color(45, 90, 39) # Verde
    pdf.set_text_color(255, 255, 255)
    
    total = float(viaje.get('coste_total', 0))
    persona = float(viaje.get('coste_persona', 0))
    
    pdf.cell(140, 15, " COSTE TOTAL ESTIMADO", border=0, fill=True)
    pdf.cell(50, 15, f"{total:.2f} EUR", border=0, align="R", fill=True, ln=True)
    
    pdf.set_fill_color(220, 235, 220) # Verde claro
    pdf.set_text_color(40, 40, 40)
    pdf.cell(140, 12, " Coste exacto por persona", border=0, fill=True)
    pdf.cell(50, 12, f"{persona:.2f} EUR", border=0, align="R", fill=True, ln=True)
    
    # Devolver bytes
    return bytes(pdf.output())

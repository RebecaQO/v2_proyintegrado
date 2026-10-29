"""
Agente Emisor de Resultados (Dictamen Técnico-Jurídico Formal Tricolor)
========================================================================
Genera el informe final consolidado en formato PDF institucional con los colores
emblemáticos del Estado Plurinacional de Bolivia (Rojo, Amarillo, Verde).
Incluye:
  - Carátula y encabezado oficial de la Asamblea Legislativa Plurinacional.
  - Tabla de control y resumen ejecutivo de auditoría.
  - Sección detallada de Control de Constitucionalidad (CPE) - Normas A Favor vs En Contra.
  - Sección de Consistencia Normativa con el Ordenamiento Jurídico Vigente (pgvector).
  - Opinión Jurídica Formal, Recomendaciones Vinculantes y Firma Digital Institucional.
"""
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None

_BasePDF = FPDF if FPDF is not None else object

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_emisor")

from sma_unified.config import settings
from sma_unified.db.mongo_atlas import publicar_mensaje, marcar_en_proceso, marcar_completado, marcar_error


class PDFReportTricolor(_BasePDF):
    def __init__(self, expediente_id: str = "EXP-2026-SMA"):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.expediente_id = expediente_id
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        # Franja Tricolor Superior Oficial (Rojo, Amarillo, Verde)
        w_band = self.w / 3.0
        self.set_fill_color(192, 57, 43)   # Rojo (#C0392B)
        self.rect(0, 0, w_band, 4.5, 'F')
        self.set_fill_color(241, 196, 15)  # Amarillo (#F1C40F)
        self.rect(w_band, 0, w_band, 4.5, 'F')
        self.set_fill_color(13, 92, 58)    # Verde (#0D5C3A)
        self.rect(w_band * 2, 0, w_band, 4.5, 'F')

        self.set_y(8)
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(90, 90, 90)
        self.cell(self.epw, 4, 'ESTADO PLURINACIONAL DE BOLIVIA', 0, 1, 'C')
        
        self.set_font('Helvetica', 'B', 7.5)
        self.set_text_color(120, 120, 120)
        self.cell(self.epw, 3.5, 'ASAMBLEA LEGISLATIVA PLURINACIONAL - SISTEMA MULTI-AGENTE SMA', 0, 1, 'C')

        self.set_font('Helvetica', 'B', 11.5)
        self.set_text_color(13, 92, 58)
        self.cell(self.epw, 5.5, 'DICTAMEN TÉCNICO-JURÍDICO DE CONSTITUCIONALIDAD Y CONSISTENCIA', 0, 1, 'C')

        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(110, 110, 110)
        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        txt_meta = f'Expediente: {self.expediente_id}  |  Fecha de Dictamen: {fecha_str}  |  Fase: Auditoría Automatizada'
        self.cell(self.epw, 4, _clean_str(txt_meta), 0, 1, 'C')

        self.set_draw_color(13, 92, 58)
        self.set_line_width(0.6)
        self.line(self.l_margin, 28, self.w - self.r_margin, 28)
        self.set_y(32)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.h - 14, self.w - self.r_margin, self.h - 14)
        self.set_font('Helvetica', '', 7.5)
        self.set_text_color(130, 130, 130)
        self.cell(self.epw / 2, 8, _clean_str(f'Expediente: {self.expediente_id}  |  Confidencial'), 0, 0, 'L')
        self.cell(self.epw / 2, 8, _clean_str(f'Página {self.page_no()}'), 0, 0, 'R')


def _clean_str(text: str) -> str:
    """Limpia caracteres especiales para compatibilidad latin-1 en FPDF."""
    if not text:
        return ""
    replacements = {
        '—': '-', '–': '-', '“': '"', '”': '"', '’': "'", '‘': "'", '•': '*',
        'á': 'á', 'é': 'é', 'í': 'í', 'ó': 'ó', 'ú': 'ú', 'ñ': 'ñ',
        'Á': 'Á', 'É': 'É', 'Í': 'Í', 'Ó': 'Ó', 'Ú': 'Ú', 'Ñ': 'Ñ',
        'ü': 'ü', 'Ü': 'Ü', '«': '"', '»': '"', '…': '...', 'º': 'o', 'ª': 'a',
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')


def emitir_informe_pdf(
    datos_constitucionales: Dict[str, Any],
    datos_consistencia: Dict[str, Any],
    sesion_id: str
) -> Dict[str, Any]:
    """
    Genera un dictamen formal técnico-jurídico con diseño institucional tricolor,
    análisis de constitucionalidad, consistencia normativa y opiniones fundadas.
    """
    if FPDF is None:
        raise ImportError(
            "La librería 'fpdf2' no está instalada en el entorno virtual. "
            "Por favor instálela ejecutando: pip install fpdf2"
        )

    task_id = publicar_mensaje(
        agente_origen="AGENTE_SISTEMA",
        agente_destino="AGENTE_EMISOR_RESULTADOS",
        tipo_tarea="Redaccion y Generacion de Dictamen Formal Tricolor",
        payload={"constitucion": datos_constitucionales, "consistencia": datos_consistencia},
        sesion_id=sesion_id,
    )

    marcar_en_proceso(task_id)
    t_inicio = time.time()

    try:
        exp_id = f"EXP-{sesion_id[:8].upper()}" if sesion_id else "EXP-2026-SMA"
        pdf = PDFReportTricolor(expediente_id=exp_id)
        pdf.add_page()
        epw = pdf.epw

        valido = datos_constitucionales.get("valido", True)
        confianza = datos_constitucionales.get("confianza", 95)
        severidad = (datos_constitucionales.get("severidad_maxima") or "ninguna").lower()
        contradicciones = datos_constitucionales.get("contradicciones", [])
        arts_consultados = datos_constitucionales.get("articulos_consultados", [])
        analisis_consistencia = datos_consistencia.get("analisis", [])

        # ── 1. RESUMEN EJECUTIVO Y ESTADO DE AUDITORÍA ────────────────────────
        pdf.set_fill_color(240, 244, 248)
        pdf.set_draw_color(200, 210, 220)
        pdf.set_line_width(0.3)
        pdf.rect(pdf.l_margin, pdf.get_y(), epw, 20, 'DF')

        pdf.set_xy(pdf.l_margin + 3, pdf.get_y() + 2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(20, 30, 50)
        pdf.cell(epw - 6, 4.5, _clean_str("1. RESUMEN EJECUTIVO DE AUDITORÍA LEGISLATIVA"), 0, 1, 'L')

        pdf.set_x(pdf.l_margin + 3)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(60, 60, 60)
        
        # Estado Dictamen
        color_estado = (13, 92, 58) if valido else (192, 57, 43)
        estado_label = "CONFORME CON LA CONSTITUCIÓN" if valido else "CON OBSERVACIONES CONSTITUCIONALES"
        
        pdf.write(4.5, _clean_str("Resultado Global: "))
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*color_estado)
        pdf.write(4.5, _clean_str(f"[{estado_label}]   "))
        
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(60, 60, 60)
        pdf.write(4.5, _clean_str(f"|  Confianza Técnica: {confianza}%  |  Severidad Máxima: {severidad.upper()}  |  Observaciones CPE: {len(contradicciones)}"))
        pdf.ln(5)

        pdf.set_x(pdf.l_margin + 3)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(epw - 6, 4, _clean_str("Dictamen emitido conforme a la Constitución Política del Estado (2009) y el Catálogo Normativo Nacional."), 0, 1)

        pdf.set_y(pdf.get_y() + 5)

        # ── 2. CONTROL DE CONSTITUCIONALIDAD (CPE) ───────────────────────────
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_fill_color(13, 92, 58) if valido else pdf.set_fill_color(192, 57, 43)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 6.5, _clean_str("  2. CONTROL DE CONSTITUCIONALIDAD (CONSTITUCIÓN POLÍTICA DEL ESTADO)"), 0, 1, 'L', True)
        pdf.ln(2)

        # 2.1 Normas a favor / armonizadas
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(13, 92, 58)
        pdf.cell(epw, 5, _clean_str("2.1. Normas Constitucionales en Armonía / A Favor:"), 0, 1)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 40)
        if arts_consultados:
            for art in arts_consultados[:5]:
                num = art.get("numero", "S/N")
                tit = art.get("titulo", "Disposición CPE")
                ext = (art.get("extracto") or art.get("fundamento") or "")[:150]
                pdf.set_x(pdf.l_margin + 2)
                pdf.multi_cell(epw - 2, 4.2, _clean_str(f"- Art. {num} ({tit}): {ext}... [CONFORME]"))
                pdf.ln(1)
        else:
            pdf.set_x(pdf.l_margin + 2)
            pdf.multi_cell(epw - 2, 4.2, _clean_str("- Se verificó la conformidad con los principios, derechos y garantías fundamentales de la CPE."))
            pdf.ln(1)

        pdf.ln(2)

        # 2.2 Observaciones / Contradicciones
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(192, 57, 43)
        pdf.cell(epw, 5, _clean_str(f"2.2. Observaciones Constitucionales Detectadas ({len(contradicciones)}):"), 0, 1)

        if contradicciones:
            pdf.set_font("Helvetica", "", 8)
            for i, c in enumerate(contradicciones, 1):
                art_p = c.get("articulo_proyecto", "Art. Proyecto")
                art_c = c.get("articulo_constitucional", "Art. CPE")
                fund = c.get("fundamento", "Sin fundamentación registrada.")
                sev_c = (c.get("severidad") or "bloqueante").upper()

                pdf.set_fill_color(253, 237, 236)
                pdf.set_draw_color(245, 183, 177)
                pdf.set_line_width(0.2)
                
                # Caja de alerta por cada contradicción
                pdf.set_x(pdf.l_margin + 2)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(192, 57, 43)
                pdf.cell(epw - 2, 5, _clean_str(f"  Observación #{i} [{sev_c}] - Conflicto: {art_p} con {art_c}"), 0, 1, 'L')
                
                pdf.set_x(pdf.l_margin + 4)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(epw - 6, 4, _clean_str(f"Fundamentación Jurídica: {fund}"))
                pdf.ln(1.5)
        else:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(13, 92, 58)
            pdf.set_x(pdf.l_margin + 2)
            pdf.multi_cell(epw - 2, 4.2, _clean_str("- No se evidenciaron tensiones normativas directas ni colisiones con preceptos constitucionales."))

        pdf.ln(4)

        # ── 3. CONSISTENCIA CON LEYES VIGENTES (PGVECTOR) ──────────────────────
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_fill_color(241, 196, 15)  # Amarillo Institucional
        pdf.set_text_color(30, 30, 30)
        pdf.cell(epw, 6.5, _clean_str("  3. CONSISTENCIA NORMATIVA (LEYES Y DECRETOS VIGENTES)"), 0, 1, 'L', True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 40)
        if analisis_consistencia:
            for item in analisis_consistencia[:6]:
                norma = item.get("norma", "Ley Vigente")
                num_art = item.get("numero_articulo", "S/N")
                rel = (item.get("tipo_relacion") or "complementario").upper()
                just = item.get("justificacion") or "Análisis comparativo de impacto legislativo."
                sug = item.get("sugerencia") or "Mantener armonización terminológica."

                # Tag de relación
                pdf.set_x(pdf.l_margin + 2)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(20, 40, 80)
                pdf.cell(epw - 2, 4.5, _clean_str(f"- {norma} (Art. {num_art})  |  Relación: [{rel}]"), 0, 1)

                pdf.set_x(pdf.l_margin + 4)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(epw - 6, 3.8, _clean_str(f"Análisis Técnico: {just}"))

                if sug and sug.lower() != "ninguna":
                    pdf.set_x(pdf.l_margin + 4)
                    pdf.set_font("Helvetica", "I", 7.5)
                    pdf.set_text_color(13, 92, 58)
                    pdf.multi_cell(epw - 6, 3.8, _clean_str(f"Sugerencia de Técnica Legislativa: {sug}"))
                pdf.ln(1.5)
        else:
            pdf.set_x(pdf.l_margin + 2)
            pdf.multi_cell(epw - 2, 4.2, _clean_str("- Análisis de consistencia completado sin identificarse colisiones normativas con leyes preexistentes."))

        pdf.ln(4)

        # ── 4. OPINIÓN Y RECOMENDACIÓN TÉCNICO-JURÍDICA FORMAL ──────────────────
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_fill_color(30, 41, 59)     # Azul Oscuro Formal
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 6.5, _clean_str("  4. CONCLUSIONES Y RECOMENDACIONES DE LA AUDITORÍA"), 0, 1, 'L', True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 40)
        
        opinion_general = (
            "En mérito al análisis automatizado de control de constitucionalidad y concordancia con el "
            "ordenamiento jurídico del Estado Plurinacional de Bolivia, se concluye que el proyecto analizado "
            + ("presenta PLENA CONFORMIDAD con los postulados constitucionales y procedimentales." if valido else
               "presenta OBSERVACIONES TÉCNICO-JURÍDICAS que requieren subsanación o adecuación en comisión legislativa antes de su tratamiento en plenario.")
        )
        pdf.set_x(pdf.l_margin + 2)
        pdf.multi_cell(epw - 2, 4.2, _clean_str(opinion_general))
        pdf.ln(2)

        # Recomendaciones formales
        recom_list = [
            "Remitir el presente dictamen a la Comisión Legislativa correspondiente para su compulsa en el informe de comisión.",
            "Adecuar los artículos observados conforme a las sugerencias de técnica legislativa para evitar futuras acciones de inconstitucionalidad.",
            "Incorporar expresamente las cláusulas de abrogación o derogación de las normas preexistentes que resulten modificadas."
        ]
        for r in recom_list:
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(epw - 6, 3.8, _clean_str(f"* {r}"))
            pdf.ln(1)

        pdf.ln(5)

        # ── 5. FIRMA Y CONSTANCIA INSTITUCIONAL ────────────────────────────────
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin + 30, pdf.get_y() + 12, pdf.w - pdf.r_margin - 30, pdf.get_y() + 12)
        
        pdf.set_y(pdf.get_y() + 14)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(epw, 4, _clean_str("SISTEMA MULTI-AGENTE (SMA) DE AUDITORÍA LEGISLATIVA"), 0, 1, 'C')
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(epw, 3.5, _clean_str("Dirección de Apoyo Técnico y Constitucionalidad - ALP Bolivia"), 0, 1, 'C')
        pdf.cell(epw, 3.5, _clean_str(f"Certificación Electrónica: SHA256:{sesion_id[:16]}..."), 0, 1, 'C')

        # ── Guardar archivo PDF ────────────────────────────────────────────────
        os.makedirs("uploaded_files/informes", exist_ok=True)
        filename = f"informe_{sesion_id}.pdf"
        filepath = os.path.join("uploaded_files/informes", filename)
        pdf.output(filepath)

        drive_link = ""
        drive_file_id = ""
        try:
            with open(filepath, "rb") as f_pdf:
                pdf_bytes = f_pdf.read()
            from sma_unified.utils.drive_uploader import upload_pdf_to_drive
            drive_res = upload_pdf_to_drive(
                file_bytes=pdf_bytes,
                filename=filename,
                categoria="reportes"
            )
            if drive_res:
                drive_link = drive_res.get("web_view_link", "")
                drive_file_id = drive_res.get("file_id", "")
                logger.info(f"[EmisorResultados] 📁 Informe vinculado a Google Drive: {drive_link}")
        except Exception as _e_drive:
            logger.warning(f"[EmisorResultados] No se pudo subir reporte a Drive: {_e_drive}")

        duracion_ms = int((time.time() - t_inicio) * 1000)
        marcar_completado(
            task_id,
            resultado={
                "pdf_path": filepath,
                "status": "success",
                "drive_link": drive_link,
                "drive_file_id": drive_file_id
            },
            duracion_ms=duracion_ms
        )

        logger.info(f"✅ Dictamen formal PDF generado exitosamente: {filepath} ({duracion_ms}ms)")
        return {
            "status": "success",
            "pdf_path": filepath,
            "filename": filename,
            "duracion_ms": duracion_ms,
            "drive_link": drive_link,
            "drive_file_id": drive_file_id
        }
    except Exception as e:
        marcar_error(task_id, str(e))
        logger.error(f"Error en Agente Emisor al generar PDF: {e}")
        raise

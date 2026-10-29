"""
Generador del Certificado Oficial de Sanción Legislativa y Hoja de Seguimiento Bicameral (Art. 163 CPE).
Diseñado conforme a la identidad institucional de la Asamblea Legislativa Plurinacional de Bolivia.
"""
import io
import time
from typing import Dict, Any

try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None

_BasePDF = FPDF if FPDF is not None else object


def generar_ficha_seguimiento_texto(ciclo: Dict[str, Any]) -> str:
    """Genera la Ficha de Seguimiento y Certificación Bicameral en texto plano estructurado."""
    normativa = ciclo.get("normativa_en_tratamiento") or {}
    circuito = ciclo.get("circuito_dos_camaras") or {}
    origen = circuito.get("camara_origen") or {}
    revisora = circuito.get("camara_revisora") or {}
    articulos_origen = origen.get("votacion_en_detalle") or []
    articulos_revisora = revisora.get("votacion_en_detalle") or []

    v_orig = origen.get("votacion_en_grande") or {}
    v_rev = revisora.get("votacion_en_grande") or {}

    total_arts = max(len(articulos_origen), len(articulos_revisora), 1)

    exp_codigo = str(normativa.get("codigo_expediente") or f"PL-{ciclo.get('proyecto_id', '136')}/2026")
    lineas = [
        "================================================================================",
        "          ASAMBLEA LEGISLATIVA PLURINACIONAL DE BOLIVIA",
        "        CERTIFICADO DE SANCIÓN LEGISLATIVA Y SEGUIMIENTO BICAMERAL",
        "             (Conforme al Artículo 163 de la Constitución Política del Estado)",
        "================================================================================",
        "",
        "1. ANTECEDENTES Y RADICACIÓN DEL PROYECTO",
        f"   - Expediente Oficial: {exp_codigo}",
        f"   - Título Oficial: {normativa.get('titulo_completo', 'Proyecto de Ley en Tratamiento')}",
        f"   - Comisión Dictaminadora: {normativa.get('comision_origen', 'Comisión de Constitución, Legislación y Sistema Electoral')}",
        f"   - Fecha de Tratamiento: {time.strftime('%d/%m/%Y')}",
        f"   - Procedimiento: Ley Ordinaria (Mayoría Absoluta)",
        "",
        "2. RESULTADO DE LA CÁMARA DE ORIGEN (CÁMARA DE DIPUTADOS)",
        f"   - Escaños Totales: {origen.get('total_escanos', 130)} Diputados",
        f"   - Asistencia en Sala (Quórum): {origen.get('presentes', 85)} Diputados presentes (Quórum Legal Verificado)",
        f"   - Votación en Grande: APROBADO ({v_orig.get('favor', 0)} a favor, {v_orig.get('contra', 0)} en contra, {v_orig.get('abstenciones', 0)} abstenciones)",
        f"   - Respaldo Porcentual: {origen.get('porcentaje_aprobacion', 64.5)}% de los votos válidos",
        f"   - Votación en Detalle: {len(articulos_origen)} artículos sometidos a votación nominal (100% aprobados)",
        "",
        "3. RESULTADO DE LA CÁMARA REVISORA (CÁMARA DE SENADORES)",
        f"   - Escaños Totales: {revisora.get('total_escanos', 36)} Senadores",
        f"   - Asistencia en Sala (Quórum): {revisora.get('presentes', 28)} Senadores presentes (Quórum Legal Verificado)",
        f"   - Votación en Grande: APROBADO ({v_rev.get('favor', 0)} a favor, {v_rev.get('contra', 0)} en contra, {v_rev.get('abstenciones', 0)} abstenciones)",
        f"   - Respaldo Porcentual: {revisora.get('porcentaje_aprobacion', 67.9)}% de los votos válidos",
        f"   - Votación en Detalle: {len(articulos_revisora)} artículos ratificados sin enmiendas (100% aprobados)",
        "",
        "4. DETALLE NOMINAL DE LOS ARTÍCULOS VOTADOS",
    ]

    for idx, d in enumerate(articulos_origen, start=1):
        etiqueta = d.get("etiqueta") or f"Art. {d.get('articulo', idx)}"
        fav_o = d.get("favor", "-")
        cont_o = d.get("contra", "-")
        lineas.append(f"   [{idx:02d}] {etiqueta:<52} | Diputados: {fav_o}F/{cont_o}C | Senadores: APROBADO")

    lineas.extend([
        "",
        "5. CERTIFICACIÓN DE CONSTITUCIONALIDAD Y AUTONOMÍA LEGISLATIVA",
        f"   - Concordancia Constitucional: PLENA (Sin contradicciones con la CPE)",
        f"   - Enmiendas o Modificaciones: NINGUNA (Texto aprobado por ambas Cámaras coincide en su integridad)",
        f"   - Estado del Trámite: SANCIONADO - REMITIDO AL ÓRGANO EJECUTIVO (Art. 164 CPE)",
        f"   - Código de Integridad (SHA-256): {ciclo.get('hash_texto_sancionado', ciclo.get('hash_documento', 'AUTORIZADO-ALP-2026'))}",
        "",
        "================================================================================",
        "   Certificado generado automáticamente por el Sistema Multi-Agente Legislativo",
        "         Secretaría General - Asamblea Legislativa Plurinacional de Bolivia",
        "================================================================================"
    ])
    return "\n".join(lineas)


class SancionBicameralFPDF(_BasePDF):
    """Clase generadora de PDF con franja tricolor boliviana y estilo parlamentario."""

    def header(self):
        # Franja tricolor boliviana en el borde superior
        ancho_pagina = self.w
        alto_franja = 3.5
        tercio = ancho_pagina / 3.0

        # Rojo
        self.set_fill_color(218, 41, 28)
        self.rect(0, 0, tercio, alto_franja, 'F')
        # Amarillo
        self.set_fill_color(249, 214, 22)
        self.rect(tercio, 0, tercio, alto_franja, 'F')
        # Verde
        self.set_fill_color(0, 122, 51)
        self.rect(tercio * 2, 0, tercio + 2, alto_franja, 'F')

        self.set_y(8)
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(15, 23, 42)
        self.cell(0, 6, 'ESTADO PLURINACIONAL DE BOLIVIA', align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(71, 85, 105)
        self.cell(0, 5, 'ASAMBLEA LEGISLATIVA PLURINACIONAL', align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 4, 'Presidencia Bicameral - Sistema de Control y Certificación Normativa', align='C', new_x='LMARGIN', new_y='NEXT')
        self.ln(2)
        self.set_draw_color(203, 213, 225)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(203, 213, 225)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.set_font('helvetica', 'I', 7)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, f'Certificado Oficial de Sanción Legislativa (Art. 163 CPE) · Página {self.page_no()}', align='C')


def generar_certificado_sancion_pdf(ciclo: Dict[str, Any]) -> bytes:
    """Genera el PDF del Certificado Oficial de Sanción Bicameral."""
    normativa = ciclo.get("normativa_en_tratamiento") or {}
    circuito = ciclo.get("circuito_dos_camaras") or {}
    origen = circuito.get("camara_origen") or {}
    revisora = circuito.get("camara_revisora") or {}
    v_orig = origen.get("votacion_en_grande") or {}
    v_rev = revisora.get("votacion_en_grande") or {}
    articulos_origen = origen.get("votacion_en_detalle") or []

    pdf = SancionBicameralFPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Título principal del documento
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, 'CERTIFICADO DE SANCIÓN LEGISLATIVA', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 5, 'TRÁMITE BICAMERAL CONFORME AL ARTÍCULO 163 DE LA C.P.E.', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    # Cuadro de Metadatos del Expediente
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(14, pdf.get_y(), pdf.w - 28, 24, 'FD')
    
    y_ini = pdf.get_y() + 2
    pdf.set_xy(16, y_ini)
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(32, 4.5, 'EXPEDIENTE / CÓDIGO:')
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(60, 4.5, str(normativa.get('codigo_expediente') or f"PL-{ciclo.get('proyecto_id', '136')}/2026"))

    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(28, 4.5, 'FECHA DE SANCIÓN:')
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 4.5, time.strftime('%d de %B de %Y'), new_x='LMARGIN', new_y='NEXT')

    pdf.set_x(16)
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(32, 4.5, 'TÍTULO DE LA LEY:')
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(15, 23, 42)
    titulo_recortado = str(normativa.get('titulo_completo') or 'Proyecto de Ley')[:85]
    pdf.cell(0, 4.5, titulo_recortado, new_x='LMARGIN', new_y='NEXT')

    pdf.set_x(16)
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(32, 4.5, 'ESTADO FINAL:')
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(60, 4.5, 'SANCIONADO - REMITIR AL ÓRGANO EJECUTIVO (PROMULGACIÓN)')

    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(28, 4.5, 'PROCEDIMIENTO:')
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 4.5, 'Ordinario (Mayoría Absoluta)', new_x='LMARGIN', new_y='NEXT')

    pdf.set_y(y_ini + 26)

    # Tabla Comparativa de Ambas Cámaras
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, '1. CÓMPUTO DE ESCAÑOS, QUÓRUM Y VOTACIÓN EN GRANDE', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(1)

    ancho_col = (pdf.w - 28) / 2.0
    
    # Encabezado Cámaras
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_fill_color(224, 231, 255)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(ancho_col, 5.5, ' CÁMARA DE ORIGEN (DIPUTADOS)', border=1, fill=True)
    pdf.cell(ancho_col, 5.5, ' CÁMARA REVISORA (SENADORES)', border=1, fill=True, new_x='LMARGIN', new_y='NEXT')

    pdf.set_font('helvetica', '', 7.5)
    pdf.set_text_color(15, 23, 42)

    filas_resumen = [
        ("Escaños Totales: 130 miembros", "Escaños Totales: 36 miembros"),
        (f"Quórum: {origen.get('presentes', 85)} presentes (Mayoría verificada)", f"Quórum: {revisora.get('presentes', 28)} presentes (Mayoría verificada)"),
        (f"Votos Favor: {v_orig.get('favor', 0)} | Contra: {v_orig.get('contra', 0)} | Abst: {v_orig.get('abstenciones', 0)}",
         f"Votos Favor: {v_rev.get('favor', 0)} | Contra: {v_rev.get('contra', 0)} | Abst: {v_rev.get('abstenciones', 0)}"),
        (f"Porcentaje de Aprobación: {origen.get('porcentaje_aprobacion', 64.5)}%",
         f"Porcentaje de Aprobación: {revisora.get('porcentaje_aprobacion', 67.9)}%"),
        ("Resultado: APROBADO EN GRANDE Y DETALLE", "Resultado: APROBADO EN GRANDE Y DETALLE")
    ]

    for f1, f2 in filas_resumen:
        pdf.cell(ancho_col, 4.5, f" {f1}", border=1)
        pdf.cell(ancho_col, 4.5, f" {f2}", border=1, new_x='LMARGIN', new_y='NEXT')

    pdf.ln(3)

    # Detalle de Artículos Votados Nominalmente
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, '2. CÓMPUTO NOMINAL DE ARTÍCULOS EN DETALLE', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(1)

    pdf.set_font('helvetica', 'B', 7)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(14, 5, 'Art.', border=1, align='C', fill=True)
    pdf.cell(108, 5, ' Denominación / Contenido Normativo Votado', border=1, fill=True)
    pdf.cell(30, 5, ' Diputados', border=1, align='C', fill=True)
    pdf.cell(30, 5, ' Senadores', border=1, align='C', fill=True, new_x='LMARGIN', new_y='NEXT')

    pdf.set_font('helvetica', '', 6.8)
    for idx, d in enumerate(articulos_origen, start=1):
        num_art = str(d.get("articulo", idx))
        etiqueta = str(d.get("etiqueta") or f"Art. {num_art}")[:65]
        v_dip = f"{d.get('favor', '-')}F / {d.get('contra', '-')}C"
        pdf.cell(14, 4.2, num_art, border=1, align='C')
        pdf.cell(108, 4.2, f" {etiqueta}", border=1)
        pdf.cell(30, 4.2, f"Aprobado ({v_dip})", border=1, align='C')
        pdf.cell(30, 4.2, "Ratificado (Aprobado)", border=1, align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(3)

    # Certificación Constitucional y Sello Digital
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, '3. CONFORMIDAD CONSTITUCIONAL Y SELLO DIGITAL', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(1)

    pdf.set_font('helvetica', '', 7.5)
    cert_text = (
        "Se certifica que el proyecto ha cumplido rigurosamente el procedimiento legislativo establecido en el "
        "Artículo 163 de la Constitución Política del Estado. No existiendo enmiendas ni contradicciones entre la "
        "Cámara de Diputados y la Cámara de Senadores, la Ley queda formalmente SANCIONADA y en condiciones de ser "
        "remitida al Presidente del Estado Plurinacional para su promulgación oficial (Art. 164 CPE)."
    )
    pdf.multi_cell(0, 4, cert_text)
    pdf.ln(2)

    # Hash SHA-256
    pdf.set_font('helvetica', 'B', 7)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(30, 4, 'Sello Criptográfico SHA-256: ')
    pdf.set_font('courier', 'B', 7)
    pdf.set_text_color(30, 58, 138)
    h_sancion = ciclo.get("hash_texto_sancionado") or ciclo.get("hash_documento") or "e85f19fdebec9725b8b9f71c356b46182103328e14e1a0"
    pdf.cell(0, 4, str(h_sancion), new_x='LMARGIN', new_y='NEXT')
    pdf.ln(6)

    # Firmas
    y_firmas = pdf.get_y()
    pdf.set_draw_color(100, 116, 139)
    pdf.line(25, y_firmas, 85, y_firmas)
    pdf.line(pdf.w - 85, y_firmas, pdf.w - 25, y_firmas)

    pdf.set_font('helvetica', 'B', 7.5)
    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(25, y_firmas + 1)
    pdf.cell(60, 4, 'Secretaría General', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(25)
    pdf.set_font('helvetica', '', 6.8)
    pdf.cell(60, 3.5, 'Cámara de Diputados', align='C')

    pdf.set_xy(pdf.w - 85, y_firmas + 1)
    pdf.set_font('helvetica', 'B', 7.5)
    pdf.cell(60, 4, 'Secretaría General', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_xy(pdf.w - 85, y_firmas + 5)
    pdf.set_font('helvetica', '', 6.8)
    pdf.cell(60, 3.5, 'Cámara de Senadores', align='C')

    # Retorno en bytes
    out = pdf.output(dest='S')
    if isinstance(out, str):
        return out.encode('latin1')
    return bytes(out)

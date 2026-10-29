import os
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None


_BasePDF = FPDF if FPDF is not None else object

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def formatear_fecha_espanol(fecha_input: Any) -> str:
    """Convierte fecha a formato formal '10 de octubre de 2026'."""
    if not fecha_input:
        dt = datetime.now()
    elif isinstance(fecha_input, datetime):
        dt = fecha_input
    else:
        s = str(fecha_input).strip()
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except Exception:
            dt = datetime.now()
    
    mes_str = MESES_ES.get(dt.month, "enero")
    return f"{dt.day} de {mes_str} de {dt.year}"

def formatear_fecha_corta(fecha_input: Any) -> str:
    """Formato corto DD/MM/YYYY."""
    if not fecha_input:
        dt = datetime.now()
    elif isinstance(fecha_input, datetime):
        dt = fecha_input
    else:
        try:
            dt = datetime.strptime(str(fecha_input)[:10], "%Y-%m-%d")
        except Exception:
            dt = datetime.now()
    return dt.strftime("%d/%m/%Y")

def limpiar_titulo_ley(titulo: str) -> str:
    """Limpia el título para que sea 'LEY DE...' o 'LEY QUE...' en lugar de 'PROYECTO DE LEY QUE...'."""
    if not titulo:
        return "LEY GENERAL DEL ESTADO PLURINACIONAL"
    t = titulo.strip()
    t = re.sub(r'^(?:PROYECTO\s+DE\s+LEY\s*(?:N[°ºo]?\s*\d+)?\s*[:\-\.]?\s*)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(?:LEY\s*(?:N[°ºo]?\s*\d+)?\s*[:\-\.]?\s*)', '', t, flags=re.IGNORECASE)
    t = t.strip()
    if t.upper().startswith("QUE "):
        t = "LEY " + t
    elif not t.upper().startswith("LEY"):
        t = "LEY DE " + t
    return t.upper()

def normalizar_caracteres(texto: str) -> str:
    """Normaliza comillas tipográficas, guiones y viñetas para consistencia."""
    if not texto:
        return ""
    reemplazos = {
        '—': '-', '–': '-', '“': '"', '”': '"', '’': "'", '‘': "'", '•': '*',
        '«': '"', '»': '"', '…': '...', 'º': '°', 'ª': 'a',
    }
    for orig, dest in reemplazos.items():
        texto = texto.replace(orig, dest)
    return texto


class GacetaOficialPDF(_BasePDF):
    def __init__(self, numero_ley: str = "1548", edicion: str = "EDICIÓN OFICIAL"):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.numero_ley = numero_ley
        self.edicion = edicion
        
        # Registrar fuentes TrueType de Windows si existen
        self.has_arial = False
        font_regular = 'C:/Windows/Fonts/arial.ttf'
        font_bold = 'C:/Windows/Fonts/arialbd.ttf'
        font_italic = 'C:/Windows/Fonts/ariali.ttf'
        font_bi = 'C:/Windows/Fonts/arialbi.ttf'
        if os.path.exists(font_regular) and os.path.exists(font_bold):
            try:
                self.add_font('ArialCustom', '', font_regular)
                self.add_font('ArialCustom', 'B', font_bold)
                if os.path.exists(font_italic):
                    self.add_font('ArialCustom', 'I', font_italic)
                if os.path.exists(font_bi):
                    self.add_font('ArialCustom', 'BI', font_bi)
                self.has_arial = True
            except Exception as e:
                self.has_arial = False

        self.font_main = 'ArialCustom' if self.has_arial else 'Helvetica'
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(auto=True, margin=18)
        self.alias_nb_pages()

    def f_bold(self, size: float):
        self.set_font(self.font_main, 'B', size)

    def f_regular(self, size: float):
        self.set_font(self.font_main, '', size)

    def f_italic(self, size: float):
        self.set_font(self.font_main, 'I', size)

    def header(self):
        w_band = self.w / 3.0
        if self.page_no() == 1:
            # Franja Tricolor Superior Destacada
            self.set_fill_color(192, 57, 43)   # Rojo (#C0392B)
            self.rect(0, 0, w_band, 4.5, 'F')
            self.set_fill_color(241, 196, 15)  # Amarillo (#F1C40F)
            self.rect(w_band, 0, w_band, 4.5, 'F')
            self.set_fill_color(13, 92, 58)    # Verde (#0D5C3A)
            self.rect(w_band * 2, 0, w_band, 4.5, 'F')

            # Membrete Oficial Portada
            self.set_y(8.5)
            self.f_bold(9)
            self.set_text_color(50, 50, 50)
            self.cell(self.epw, 4, 'ESTADO PLURINACIONAL DE BOLIVIA', align='C', new_x="LMARGIN", new_y="NEXT")

            self.f_bold(14)
            self.set_text_color(13, 92, 58)
            self.cell(self.epw, 6, 'GACETA OFICIAL DE BOLIVIA', align='C', new_x="LMARGIN", new_y="NEXT")

            self.f_bold(7.5)
            self.set_text_color(90, 90, 90)
            self.cell(self.epw, 3.5, f'{self.edicion}   |   REGISTRO OFICIAL DE LEYES Y NORMAS', align='C', new_x="LMARGIN", new_y="NEXT")

            # Línea institucional
            self.set_draw_color(13, 92, 58)
            self.set_line_width(0.6)
            self.line(self.l_margin, 25.5, self.w - self.r_margin, 25.5)
            self.set_y(29)
        else:
            # Encabezado sutil en páginas subsiguientes
            self.set_fill_color(192, 57, 43)
            self.rect(0, 0, w_band, 1.8, 'F')
            self.set_fill_color(241, 196, 15)
            self.rect(w_band, 0, w_band, 1.8, 'F')
            self.set_fill_color(13, 92, 58)
            self.rect(w_band * 2, 0, w_band, 1.8, 'F')

            self.set_y(5)
            self.f_regular(7.5)
            self.set_text_color(100, 100, 100)
            self.cell(self.epw * 0.65, 4, 'GACETA OFICIAL DEL ESTADO PLURINACIONAL DE BOLIVIA', align='L', new_x="RIGHT", new_y="TOP")
            self.f_bold(7.5)
            self.set_text_color(13, 92, 58)
            self.cell(self.epw * 0.35, 4, f'LEY N° {self.numero_ley}', align='R', new_x="LMARGIN", new_y="NEXT")

            self.set_draw_color(210, 215, 220)
            self.set_line_width(0.2)
            self.line(self.l_margin, 10.5, self.w - self.r_margin, 10.5)
            self.set_y(14)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(200, 205, 210)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.h - 14, self.w - self.r_margin, self.h - 14)
        
        self.f_regular(7.5)
        self.set_text_color(110, 110, 110)
        self.cell(self.epw * 0.65, 6, f'Gaceta Oficial de Bolivia  -  Ley N° {self.numero_ley}', align='L', new_x="RIGHT", new_y="TOP")
        self.cell(self.epw * 0.35, 6, f'Página {self.page_no()} de {{nb}}', align='R', new_x="LMARGIN", new_y="NEXT")


def segmentar_documento_ley(texto_completo: str) -> Tuple[str, str, str]:
    """
    Segmenta el documento en tres partes:
    1. expo_motivos: Antecedentes o justificación previa al inicio del articulado
    2. cuerpo_normativo: El articulado legislativo decretado (Títulos, Capítulos, Artículos, Disposiciones)
    3. analisis_final: Estudios complementarios posteriores al último artículo (viabilidad, ROI, conclusiones del borrador)
    """
    if not texto_completo:
        return "", "", ""

    txt = texto_completo.strip()

    # 1. Punto de inicio del articulado normativo
    patron_inicio = re.compile(
        r'(?:^|\n)\s*(?:[-=*#]{3,}\s*)?'
        r'(?:ART[ÍI]CULOS|TEXTO\s+DE\s+LA\s+LEY|T[ÍI]TULO\s+(?:PRIMERO|[IVXLC\d]+)|CAP[ÍI]TULO\s+(?:PRIMERO|[IVXLC\d]+)|ART[ÍI]CULO\s+1\b)',
        re.IGNORECASE
    )
    m_ini = patron_inicio.search(txt)
    pos_ini = m_ini.start() if m_ini else 0

    # 2. Punto de fin del articulado normativo (notas de estudio/borrador que no son artículos)
    patron_fin = re.compile(
        r'(?:^|\n)\s*(?:[-=*#]{3,}\s*)?'
        r'(?:AN[ÁA]LISIS\s+JUR[ÍI]DICO|ESTUDIO\s+DE\s+COSTO|VIABILIDAD\s+PRESUPUESTARIA|PRECEDENTES\s+INTERNACIONALES|JUSTIFICACI[ÓO]N\s+T[ÉE]CNICA|CONCLUSI[ÓO]N\b|FECHA\s+DE\s+REDACCI[ÓO]N)',
        re.IGNORECASE
    )
    m_fin = patron_fin.search(txt[pos_ini:])
    pos_fin = (pos_ini + m_fin.start()) if m_fin else len(txt)

    expo_motivos = txt[:pos_ini].strip() if pos_ini > 80 else ""
    cuerpo_normativo = txt[pos_ini:pos_fin].strip()
    analisis_final = txt[pos_fin:].strip()

    return expo_motivos, cuerpo_normativo, analisis_final


def limpiar_parrafos_articulado(cuerpo_texto: str) -> List[str]:
    """
    Expande párrafos que contengan incisos concatenados (ej. 'a) ... b) ... c) ...')
    en líneas separadas para una presentación legislativa impecable.
    """
    lineas_res = []
    for lin in cuerpo_texto.split('\n'):
        lin_limpia = lin.strip()
        if not lin_limpia:
            lineas_res.append("")
            continue

        # Si contiene múltiples incisos en la misma línea como '... a) ... b) ...'
        if re.search(r'\b[a-z]\)\s+', lin_limpia):
            partes = re.split(r'(?=\b[a-z]\)\s+)', lin_limpia)
            for p in partes:
                p_s = p.strip()
                if p_s:
                    lineas_res.append(p_s)
        else:
            lineas_res.append(lin_limpia)
    return lineas_res


def formatear_cuerpo_normativo(pdf: GacetaOficialPDF, cuerpo_texto: str):
    """Renderiza el articulado normativo con jerarquía visual y técnica legislativa."""
    epw = pdf.epw
    lineas = limpiar_parrafos_articulado(cuerpo_texto)
    i = 0
    total = len(lineas)

    re_titulo_cap = re.compile(r'^\s*(T[ÍI]TULO|CAP[ÍI]TULO|PARTE|SECCI[ÓO]N)\s+([IVXLC\d]+|PRIMERO|SEGUNDO|TERCERO|CUARTO)[\s:\.\-]*(.*)$', re.IGNORECASE)
    re_articulo = re.compile(r'^\s*Art[íi]culo\s+(\d+(?:\s*(?:bis|ter))?)\s*[°º]?\s*[\.\-:]*\s*(.*)$', re.IGNORECASE)
    re_disposicion = re.compile(r'^\s*(DISPOSICI[ÓO]N(?:\s+TRANSITORIA|\s+FINAL|\s+DEROGATORIA|\s+ABROGATORIA|\s+ADICIONAL)?)\s+([A-ZÁÉÍÓÚ\d]+)[\s:\.\-]*(.*)$', re.IGNORECASE)
    re_inciso = re.compile(r'^\s*([a-z]\)|[0-9]+\)|\d+\.)\s+(.*)$', re.IGNORECASE)
    re_paragrafo = re.compile(r'^\s*([IVXLCDM]+\.)\s+(.*)$')

    while i < total:
        linea = normalizar_caracteres(lineas[i].strip())
        i += 1
        if not linea:
            pdf.ln(2.2)
            continue

        # Evitar imprimir texto redundante de borrador
        if linea.upper() in ["ARTÍCULOS", "ARTICULOS", "TEXTO DE LA LEY", "PROYECTO DE LEY"]:
            continue

        # 1. TÍTULO / CAPÍTULO / SECCIÓN
        m_tc = re_titulo_cap.match(linea)
        if m_tc:
            if pdf.get_y() > pdf.h - 35:
                pdf.add_page()
            pdf.ln(3)
            tipo_tc = m_tc.group(1).upper()
            num_tc = m_tc.group(2).upper()
            sub_tc = m_tc.group(3).strip()

            pdf.f_bold(10.5)
            pdf.set_text_color(13, 92, 58)
            pdf.multi_cell(epw, 5, f"{tipo_tc} {num_tc}", 0, 'C', new_x="LMARGIN", new_y="NEXT")

            if sub_tc:
                pdf.f_bold(9.5)
                pdf.set_text_color(30, 30, 30)
                pdf.multi_cell(epw, 4.5, sub_tc.upper(), 0, 'C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            continue

        # 2. DISPOSICIONES (Transitorias, Finales, Derogatorias, etc.)
        m_disp = re_disposicion.match(linea)
        if m_disp:
            if pdf.get_y() > pdf.h - 30:
                pdf.add_page()
            pdf.ln(3)
            disp_tipo = m_disp.group(1).upper()
            disp_num = m_disp.group(2).upper()
            disp_resto = m_disp.group(3).strip()

            pdf.f_bold(9.5)
            pdf.set_text_color(13, 92, 58)
            encabezado = f"{disp_tipo} {disp_num}.-"
            if disp_resto:
                pdf.multi_cell(epw, 4.6, encabezado, 0, 'L', new_x="LMARGIN", new_y="NEXT")
                pdf.f_regular(9)
                pdf.set_text_color(25, 25, 25)
                pdf.multi_cell(epw, 4.6, disp_resto, 0, 'J', new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.multi_cell(epw, 4.6, encabezado, 0, 'L', new_x="LMARGIN", new_y="NEXT")
            continue

        # 3. ARTÍCULO
        m_art = re_articulo.match(linea)
        if m_art:
            if pdf.get_y() > pdf.h - 28:
                pdf.add_page()
            pdf.ln(2.5)
            art_num = m_art.group(1).strip()
            art_resto = (m_art.group(2) or "").strip()

            # Extraer epígrafe
            epigrafe_str = ""
            if art_resto.startswith("(") and ")" in art_resto:
                fin_p = art_resto.index(")")
                epigrafe_str = f" {art_resto[:fin_p+1]}"
                art_resto = art_resto[fin_p+1:].strip(" .-:")
            elif art_resto and not art_resto.startswith(('El ', 'La ', 'Los ', 'Las ', 'En ', 'Se ', 'Para ', 'Son ', 'Queda ', 'Toda ', 'Todo ')):
                partes = art_resto.split('.', 1)
                if len(partes) > 1 and len(partes[0]) < 60:
                    epigrafe_str = f" ({partes[0].strip()})"
                    art_resto = partes[1].strip()
                elif len(art_resto) < 50:
                    epigrafe_str = f" ({art_resto.strip()})"
                    art_resto = ""

            header_art = f"ARTÍCULO {art_num}.{epigrafe_str}.-"
            
            pdf.f_bold(9.5)
            pdf.set_text_color(13, 92, 58)
            
            if art_resto:
                pdf.multi_cell(epw, 4.6, header_art, 0, 'L', new_x="LMARGIN", new_y="NEXT")
                pdf.f_regular(9)
                pdf.set_text_color(25, 25, 25)
                pdf.multi_cell(epw, 4.6, art_resto, 0, 'J', new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.multi_cell(epw, 4.6, header_art, 0, 'L', new_x="LMARGIN", new_y="NEXT")
            continue

        # 4. PARÁGRAFOS (I., II., etc.)
        m_par = re_paragrafo.match(linea)
        if m_par:
            num_par = m_par.group(1)
            txt_par = m_par.group(2)
            pdf.f_bold(9)
            pdf.set_text_color(13, 92, 58)
            pdf.set_x(pdf.l_margin + 4)
            pdf.cell(8, 4.6, num_par, align='L', new_x="RIGHT", new_y="TOP")
            pdf.f_regular(9)
            pdf.set_text_color(25, 25, 25)
            pdf.multi_cell(epw - 12, 4.6, txt_par, 0, 'J', new_x="LMARGIN", new_y="NEXT")
            continue

        # 5. INCISOS / LISTAS (a), b), 1., etc.)
        m_inc = re_inciso.match(linea)
        if m_inc:
            simbolo = m_inc.group(1)
            txt_inc = m_inc.group(2)
            pdf.f_bold(9)
            pdf.set_text_color(13, 92, 58)
            pdf.set_x(pdf.l_margin + 6)
            pdf.cell(8, 4.6, simbolo, align='L', new_x="RIGHT", new_y="TOP")
            pdf.f_regular(9)
            pdf.set_text_color(25, 25, 25)
            pdf.multi_cell(epw - 14, 4.6, txt_inc, 0, 'J', new_x="LMARGIN", new_y="NEXT")
            continue

        # 6. PÁRRAFO REGULAR
        pdf.f_regular(9)
        pdf.set_text_color(25, 25, 25)
        pdf.multi_cell(epw, 4.6, linea, 0, 'J', new_x="LMARGIN", new_y="NEXT")


def generar_pdf_ley_gaceta(
    id_proyecto: int,
    titulo_proyecto: str,
    numero_ley: int,
    texto_consolidado: str,
    fecha_promulgacion: Optional[str] = None,
    fecha_vigencia: Optional[str] = None,
    boletin_id: Optional[str] = None,
    correcciones_aplicadas: Optional[List[Dict[str, Any]]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Genera el PDF formal de la Ley publicada en la Gaceta Oficial del Estado Plurinacional de Bolivia.
    """
    correcciones_aplicadas = correcciones_aplicadas or []
    fecha_prom_str = formatear_fecha_espanol(fecha_promulgacion)
    fecha_vig_corta = formatear_fecha_corta(fecha_vigencia)
    fecha_prom_corta = formatear_fecha_corta(fecha_promulgacion)
    
    num_ley_str = str(numero_ley)
    bol_str = boletin_id or f"GAC-{datetime.now().year}-{numero_ley:04d}"

    # Directorio de salida
    if not output_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(base_dir, "uploaded_files", "informes")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"Ley_{numero_ley}_Gaceta_Oficial.pdf"
    file_path = os.path.join(output_dir, filename)

    pdf = GacetaOficialPDF(numero_ley=num_ley_str, edicion=f"EDICIÓN {bol_str}")
    pdf.add_page()
    epw = pdf.epw

    # 1. IDENTIFICACIÓN Y PROMULGACIÓN DE LA LEY
    pdf.f_bold(18)
    pdf.set_text_color(13, 92, 58)
    pdf.cell(epw, 8.5, f'LEY N° {num_ley_str}', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.f_bold(10.5)
    pdf.set_text_color(192, 57, 43)
    pdf.cell(epw, 6, f'LEY DE {fecha_prom_str.upper()}', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2.5)

    # Identificación de la Presidencia del Estado
    pdf.f_bold(10)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(epw, 4.5, 'LUIS ALBERTO ARCE CATACORA', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.f_regular(8.5)
    pdf.set_text_color(70, 70, 70)
    pdf.cell(epw, 4, 'PRESIDENTE CONSTITUCIONAL DEL ESTADO PLURINACIONAL DE BOLIVIA', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3.5)

    # Fórmula de Sanción Constitucional (ALP)
    pdf.f_italic(9)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        epw, 4.5,
        "Por cuanto, la Asamblea Legislativa Plurinacional, ha sancionado la siguiente Ley:",
        0, 'C', new_x="LMARGIN", new_y="NEXT"
    )

    pdf.ln(2)

    # LA ALP DECRETA
    pdf.f_bold(10)
    pdf.set_text_color(13, 92, 58)
    pdf.cell(epw, 4.8, 'LA ASAMBLEA LEGISLATIVA PLURINACIONAL,', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.f_bold(11)
    pdf.cell(epw, 5.2, 'DECRETA:', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # TÍTULO OFICIAL DE LA LEY
    titulo_limpio = limpiar_titulo_ley(titulo_proyecto)
    pdf.f_bold(11)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(epw, 5.2, titulo_limpio, 0, 'C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # Segmentar documento: exposición de motivos, articulado decretado, notas complementarias
    expo_motivos, cuerpo_normativo, analisis_final = segmentar_documento_ley(texto_consolidado)
    
    # 2. CUERPO DE LA LEY (ARTÍCULOS SANCIONADOS)
    formatear_cuerpo_normativo(pdf, cuerpo_normativo)

    # 3. FÓRMULAS DE CIERRE, SANCIÓN Y PROMULGACIÓN (ART. 164 CPE)
    # Deben ubicarse INMEDIATAMENTE tras el último artículo de la Ley
    if pdf.get_y() > pdf.h - 85:
        pdf.add_page()
    else:
        pdf.ln(6)

    # Fórmula de remisión de la ALP
    pdf.f_italic(9)
    pdf.set_text_color(40, 40, 40)
    cierre_alp = (
        "Remítase al Órgano Ejecutivo para fines constitucionales.\n"
        f"Es dada en la Sala de Sesiones de la Asamblea Legislativa Plurinacional, "
        f"a los {fecha_prom_str}."
    )
    pdf.multi_cell(epw, 4.8, cierre_alp, 0, 'J', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # Firmas ALP (2 columnas)
    y_firmas_alp = pdf.get_y()
    w_col = (epw - 10) / 2
    
    # Línea Senadores
    pdf.set_draw_color(160, 160, 160)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin + 5, y_firmas_alp + 10, pdf.l_margin + 5 + w_col - 10, y_firmas_alp + 10)
    pdf.set_xy(pdf.l_margin + 5, y_firmas_alp + 11)
    pdf.f_bold(7.5)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(w_col - 10, 3.5, 'CÁMARA DE SENADORES', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 5)
    pdf.f_regular(7)
    pdf.cell(w_col - 10, 3, 'Presidente de la Cámara de Senadores', align='C', new_x="LMARGIN", new_y="NEXT")

    # Línea Diputados
    x_dip = pdf.l_margin + w_col + 10
    pdf.line(x_dip + 5, y_firmas_alp + 10, x_dip + 5 + w_col - 10, y_firmas_alp + 10)
    pdf.set_xy(x_dip + 5, y_firmas_alp + 11)
    pdf.f_bold(7.5)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(w_col - 10, 3.5, 'CÁMARA DE DIPUTADOS', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x_dip + 5)
    pdf.f_regular(7)
    pdf.cell(w_col - 10, 3, 'Presidente de la Cámara de Diputados', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y_firmas_alp + 24)

    # Fórmula de Promulgación Presidencial
    if pdf.get_y() > pdf.h - 55:
        pdf.add_page()

    pdf.f_bold(9.5)
    pdf.set_text_color(13, 92, 58)
    cierre_ejecutivo = (
        "POR TANTO, la promulgo para que se tenga y cumpla como Ley del Estado Plurinacional de Bolivia.\n"
        f"Casa Grande del Pueblo de la ciudad de La Paz, a los {fecha_prom_str}."
    )
    pdf.multi_cell(epw, 4.8, cierre_ejecutivo, 0, 'C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # Firmas Ejecutivo (2 columnas)
    y_firmas_ej = pdf.get_y()
    pdf.line(pdf.l_margin + 5, y_firmas_ej + 10, pdf.l_margin + 5 + w_col - 10, y_firmas_ej + 10)
    pdf.set_xy(pdf.l_margin + 5, y_firmas_ej + 11)
    pdf.f_bold(7.5)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(w_col - 10, 3.5, 'LUIS ALBERTO ARCE CATACORA', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 5)
    pdf.f_regular(7)
    pdf.cell(w_col - 10, 3, 'Presidente Constitucional del Estado Plurinacional', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.line(x_dip + 5, y_firmas_ej + 10, x_dip + 5 + w_col - 10, y_firmas_ej + 10)
    pdf.set_xy(x_dip + 5, y_firmas_ej + 11)
    pdf.f_bold(7.5)
    pdf.cell(w_col - 10, 3.5, 'MINISTERIO DE LA PRESIDENCIA', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x_dip + 5)
    pdf.f_regular(7)
    pdf.cell(w_col - 10, 3, 'Ministra de la Presidencia - Refrenda Ministerial', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y_firmas_ej + 23)

    # 4. REGISTRO OFICIAL Y CERTIFICADO DE INTEGRIDAD DE LA GACETA
    if pdf.get_y() > pdf.h - 32:
        pdf.add_page()
    else:
        pdf.ln(4)

    hash_cert = hashlib.sha256(texto_consolidado.encode('utf-8')).hexdigest()
    
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(pdf.l_margin, pdf.get_y(), epw, 18, 'DF')

    y_box = pdf.get_y() + 2
    pdf.set_xy(pdf.l_margin + 4, y_box)
    pdf.f_bold(7.5)
    pdf.set_text_color(13, 92, 58)
    pdf.cell(epw - 8, 3.5, f'DIRECCIÓN GENERAL DE LA GACETA OFICIAL — REGISTRO N° {bol_str}', align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(pdf.l_margin + 4)
    pdf.f_regular(7)
    pdf.set_text_color(90, 100, 115)
    enmiendas_note = f"  |  Enmiendas Sancionadas y Armonizadas: {len(correcciones_aplicadas)}" if correcciones_aplicadas else ""
    pdf.cell(epw - 8, 3.5, f'Fecha de Publicación Oficial: {fecha_prom_corta}  |  Entrada en Vigencia: {fecha_vig_corta}{enmiendas_note}', align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(pdf.l_margin + 4)
    pdf.f_italic(6.5)
    pdf.cell(epw - 8, 3, f'Certificado Digital de Integridad SHA-256: {hash_cert}', align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(pdf.l_margin + 4)
    pdf.f_regular(6.5)
    pdf.cell(epw - 8, 3, 'Documento oficial con validez y autenticidad jurídica plenas (Art. 164 CPE y Ley N° 164).', align='L', new_x="LMARGIN", new_y="NEXT")

    # 5. ANEXO DE ANTECEDENTES Y MEMORIA TÉCNICA (Si existía en el proyecto)
    antecedentes_unidos = []
    if expo_motivos and len(expo_motivos) > 80:
        antecedentes_unidos.append(("EXPOSICIÓN DE MOTIVOS DEL PROYECTO DE ORIGEN", expo_motivos))
    if analisis_final and len(analisis_final) > 80:
        antecedentes_unidos.append(("MEMORIA TÉCNICA Y EVALUACIÓN JURÍDICA PRELIMINAR", analisis_final))

    if antecedentes_unidos:
        pdf.add_page()
        pdf.f_bold(12)
        pdf.set_text_color(13, 92, 58)
        pdf.cell(epw, 6, 'ANEXO DE ANTECEDENTES PARLAMENTARIOS', align='C', new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_draw_color(13, 92, 58)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin + 20, pdf.get_y() + 1, pdf.w - pdf.r_margin - 20, pdf.get_y() + 1)
        pdf.ln(3)

        for subtitulo, bloque_txt in antecedentes_unidos:
            pdf.ln(2)
            pdf.f_bold(9.5)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(epw, 5, subtitulo, align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            for lin in bloque_txt.split('\n'):
                l_str = normalizar_caracteres(lin.strip())
                if not l_str:
                    pdf.ln(2)
                    continue
                if l_str.upper() in ["PROYECTO DE LEY", "EXPOSICIÓN DE MOTIVOS", "EXPOSICION DE MOTIVOS"]:
                    continue
                if l_str.upper().startswith(('I.', 'II.', 'III.', 'IV.', 'V.', 'DIAGNÓSTICO', 'DIAGNOSTICO', 'FUNDAMENTO', 'OBJETIVO', 'VIABILIDAD', 'PRECEDENTES', 'CONCLUSIÓN', 'CONCLUSION')):
                    if pdf.get_y() > pdf.h - 25:
                        pdf.add_page()
                    pdf.ln(2.5)
                    pdf.f_bold(9)
                    pdf.set_text_color(13, 92, 58)
                    pdf.multi_cell(epw, 4.5, l_str, 0, 'L', new_x="LMARGIN", new_y="NEXT")
                elif l_str.startswith(('-', '*', '•')):
                    pdf.f_regular(8.5)
                    pdf.set_text_color(35, 35, 35)
                    pdf.set_x(pdf.l_margin + 4)
                    pdf.cell(5, 4.2, '•', align='L', new_x="RIGHT", new_y="TOP")
                    pdf.multi_cell(epw - 9, 4.2, l_str.lstrip('-*• '), 0, 'J', new_x="LMARGIN", new_y="NEXT")
                else:
                    pdf.f_regular(8.5)
                    pdf.set_text_color(35, 35, 35)
                    pdf.multi_cell(epw, 4.2, l_str, 0, 'J', new_x="LMARGIN", new_y="NEXT")

    pdf.output(file_path)

    # ── Subida a Google Drive (Categoría: Leyes Editadas y Promulgadas - Gaceta Oficial) ──
    drive_link = ""
    drive_file_id = ""
    try:
        with open(file_path, "rb") as f_pdf:
            pdf_bytes = f_pdf.read()
        from sma_unified.utils.drive_uploader import upload_pdf_to_drive
        drive_res = upload_pdf_to_drive(
            file_bytes=pdf_bytes,
            filename=filename,
            categoria="leyes_editadas",
            subcarpeta=f"Ley_{numero_ley}"
        )
        if drive_res:
            drive_link = drive_res.get("web_view_link", "")
            drive_file_id = drive_res.get("file_id", "")
    except Exception as _e_drive:
        pass

    return {
        "success": True,
        "filename": filename,
        "url_descarga": f"http://127.0.0.1:8085/uploaded_files/informes/{filename}",
        "numero_ley": numero_ley,
        "numero_ley_str": f"Ley N° {numero_ley}",
        "boletin_oficial": bol_str,
        "fecha_promulgacion": fecha_prom_str,
        "fecha_vigencia": fecha_vig_corta,
        "hash_integridad": hash_cert,
        "total_enmiendas_aplicadas": len(correcciones_aplicadas),
        "drive_link": drive_link,
        "drive_file_id": drive_file_id
    }


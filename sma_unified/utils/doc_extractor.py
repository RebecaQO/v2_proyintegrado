"""
Extractor de Documentos (PDF, DOCX, TXT) para el SMA Congreso
================================================================
Extrae texto limpio y metadatos (número de páginas, palabras, caracteres)
usando pdfplumber, pypdf y python-docx con fallbacks automáticos.
"""
import io
import os
from typing import Dict, Any, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("doc_extractor")


def extraer_texto_pdf(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extrae texto de un archivo PDF en bytes.
    Intenta primero con pdfplumber y usa pypdf/PyPDF2 como fallback.
    """
    texto_completo = []
    num_paginas = 0

    # Intento 1: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            num_paginas = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text()
                if txt:
                    texto_completo.append(txt)
        if texto_completo:
            resultado = "\n\n".join(texto_completo)
            return resultado, {
                "num_paginas": num_paginas,
                "motor": "pdfplumber",
                "caracteres": len(resultado),
                "palabras": len(resultado.split()),
            }
    except Exception as e:
        logger.warning(f"Fallo extracción con pdfplumber: {e}. Intentando con pypdf...")

    # Intento 2: pypdf / PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        num_paginas = len(reader.pages)
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                texto_completo.append(txt)
        resultado = "\n\n".join(texto_completo)
        return resultado, {
            "num_paginas": num_paginas,
            "motor": "pypdf",
            "caracteres": len(resultado),
            "palabras": len(resultado.split()),
        }
    except Exception as e:
        logger.error(f"Fallo extracción con pypdf: {e}")
        return "", {"num_paginas": 0, "motor": "error", "error": str(e)}


def extraer_texto_docx(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extrae texto de un archivo DOCX en bytes."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        parrafos = [p.text for p in doc.paragraphs if p.text.strip()]
        resultado = "\n\n".join(parrafos)
        return resultado, {
            "num_paginas": 1,
            "motor": "python-docx",
            "caracteres": len(resultado),
            "palabras": len(resultado.split()),
        }
    except Exception as e:
        logger.error(f"Fallo extracción DOCX: {e}")
        return "", {"num_paginas": 0, "motor": "error", "error": str(e)}


def _buscar_variante_ocr(filename: str) -> Optional[Tuple[str, bytes]]:
    """Busca una variante ya OCR-izada del PDF cuando el original no tiene texto.

    Un escaneo sin capa de texto devuelve 0 caracteres y el pipeline seguiría
    ejecutándose contra el marcador de posición "[No se pudo extraer texto...]",
    comparando ese placeholder con la CPE y con el corpus normativo. Si junto al
    documento existe una variante OCR (``{stem}_OCR.pdf`` y equivalentes), se usa
    como fuente de texto.

    Devuelve ``(nombre_encontrado, bytes)`` o ``None`` si no hay variante.
    """
    stem, _ = os.path.splitext(os.path.basename(filename))
    if not stem:
        return None

    sufijos = ("_OCR", "-OCR", "_ocr", "-ocr", ".OCR", ".ocr")
    nombres = [f"{stem}{s}.pdf" for s in sufijos]

    # Directorio del propio archivo, directorio de trabajo y carpeta de subidas.
    base_dir = os.path.dirname(filename)
    buscados = [base_dir] if base_dir else []
    for extra in (".", "uploaded_files"):
        if extra not in buscados:
            buscados.append(extra)

    for directorio in buscados:
        for nombre in nombres:
            ruta = os.path.join(directorio, nombre)
            try:
                if os.path.isfile(ruta):
                    with open(ruta, "rb") as fh:
                        datos = fh.read()
                    if datos:
                        return nombre, datos
            except OSError:
                continue
    return None


def extraer_texto_archivo(filename: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Función general para extraer texto de cualquier formato soportado (.pdf, .docx, .txt, .md).

    Si un PDF devuelve texto vacío (escaneo sin capa de texto) se intenta una
    variante OCR hermana antes de rendirse; el metadato ``motor`` y la bandera
    ``ocr_fallback`` dejan constancia de qué fuente se usó realmente.
    """
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        texto, meta = extraer_texto_pdf(file_bytes)
        if texto and texto.strip():
            return texto, meta

        variante = _buscar_variante_ocr(filename)
        if variante:
            nombre_ocr, bytes_ocr = variante
            texto_ocr, meta_ocr = extraer_texto_pdf(bytes_ocr)
            if texto_ocr and texto_ocr.strip():
                logger.info(
                    f"{filename}: sin texto extraíble; se usa la variante OCR {nombre_ocr} "
                    f"({len(texto_ocr)} caracteres)."
                )
                meta_ocr = dict(meta_ocr)
                meta_ocr["motor_origen"] = meta.get("motor", "desconocido")
                meta_ocr["ocr_fallback"] = True
                meta_ocr["ocr_fuente"] = nombre_ocr
                meta_ocr["motor"] = f"{meta_ocr.get('motor', 'ocr')}+ocr_fallback"
                return texto_ocr, meta_ocr

            logger.warning(
                f"{filename}: variante OCR {nombre_ocr} encontrada pero sin texto usable."
            )
        return texto, meta
    elif ext in [".docx", ".doc"]:
        return extraer_texto_docx(file_bytes)
    else:
        # Texto plano / Markdown
        try:
            texto = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                texto = file_bytes.decode("latin-1")
            except Exception:
                texto = str(file_bytes)
        return texto, {
            "num_paginas": 1,
            "motor": "plain_text",
            "caracteres": len(texto),
            "palabras": len(texto.split()),
        }

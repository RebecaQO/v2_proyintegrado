# sma_unified/agents/concentrador.py
"""
Agente Concentrador y Emisor de Proyecto con Observaciones — Modelo Prometheus
===============================================================================
Tipo de razonamiento: Síntesis fidedigna paso a paso (Chain of Thought) y
Pensamiento Analítico Ampliado (Extended Deep Reasoning).

Mejoras incorporadas:
  1. Integración de insumos de verificación de Constitucionalidad (CPE) y
     Consistencia Normativa (Leyes Vigentes).
  2. Generación y adjunción de Dictamen Oficial en PDF de alta solidez, con
     estilo sobrio y letra negra formal de la Asamblea Legislativa Plurinacional.
  3. Resumen sustantivo del proyecto, síntesis de observaciones y conclusiones
     técnico-jurídicas vinculantes.
  4. Mención explícita de que la auditoría fue realizada por Agentes de Análisis
     Especializados con razonamiento y pensamiento analítico ampliado.
  5. Cliente OpenAI integrado con NVIDIA NIM: modelo configurado en LLM_MODEL_NVIDIA.
     y fallback resiliente.
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("concentrador")

import openai
from openai import OpenAI
from fpdf import FPDF

from sma_unified.agents.llm_client import chat_completion_resiliente, extraer_json_de_llm
from sma_unified.config import settings
from sma_unified.db.neon_postgres import get_conn, registrar_bitacora
from sma_unified.db.neon_client import get_neon_client
from sma_unified.db.mongo_atlas import get_db


# ── Constantes y Configuración ────────────────────────────────────────────────
CAMPOS_REQUERIDOS_INSUMO = {"hallazgos", "agente_origen"}
NIVEL_CONFIANZA_MINIMO = 0.70  # Hallazgos < 70% se descartan

DEFAULT_NVIDIA_API_KEY = settings.NVIDIA_API_KEY
NVIDIA_BASE_URL = getattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODELO_RAZONAMIENTO_AMPLIADO = getattr(
    settings, "LLM_MODEL_CREW", "nvidia/nemotron-3.5-lightning-30b-a3b"
)


def _clean_str(text: Any) -> str:
    """Limpia caracteres especiales para compatibilidad latin-1 en FPDF."""
    if text is None:
        return ""
    text = str(text)
    replacements = {
        '—': '-', '–': '-', '“': '"', '”': '"', '’': "'", '‘': "'", '•': '*',
        'á': 'á', 'é': 'é', 'í': 'í', 'ó': 'ó', 'ú': 'ú', 'ñ': 'ñ',
        'Á': 'Á', 'É': 'É', 'Í': 'Í', 'Ó': 'Ó', 'Ú': 'Ú', 'Ñ': 'Ñ',
        'ü': 'ü', 'Ü': 'Ü', '«': '"', '»': '"', '…': '...', 'º': 'o', 'ª': 'a',
        '–': '-', '§': 'Art.', '¿': '¿', '¡': '¡'
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')


# ── FPDF: Informe Oficial Sobrio en Letra Negra ────────────────────────────────
# ── FPDF: Informe Oficial Sobrio en Letra Negra ────────────────────────────────
class InformeConcentradorFormalPDF(FPDF):
    """
    Generador de Informe Parlamentario Oficial en PDF con estética formal y letra negra.
    Diseñado para el cuerpo legislativo y comisiones dictaminadoras.
    """
    def __init__(self, numero_expediente: str = "EXP-2026-001"):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.numero_expediente = numero_expediente

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
            except Exception:
                self.has_arial = False

        self.font_main = 'ArialCustom' if self.has_arial else 'Helvetica'
        self.set_margins(15, 14, 15)
        self.set_auto_page_break(auto=True, margin=16)
        self.alias_nb_pages()

    def f_bold(self, size: float):
        self.set_font(self.font_main, 'B', size)

    def f_regular(self, size: float):
        self.set_font(self.font_main, '', size)

    def f_italic(self, size: float):
        self.set_font(self.font_main, 'I', size)

    def safe(self, text: Any) -> str:
        if text is None:
            return ""
        text = str(text)
        repl = {
            '\u2014': '-', '\u2013': '-', '\u201c': '"', '\u201d': '"',
            '\u2018': "'", '\u2019': "'", '\u2022': '*', '\u00ab': '"',
            '\u00bb': '"', '\u2026': '...', '\u00ba': '°', '\u00aa': 'a'
        }
        for k, v in repl.items():
            text = text.replace(k, v)
        if not self.has_arial:
            return text.encode('latin-1', 'replace').decode('latin-1')
        return text

    def seccion_titulo(self, texto: str):
        if self.get_y() > self.h - 38:
            self.add_page()
        self.ln(2.5)
        self.f_bold(9.2)
        self.set_text_color(0, 0, 0)
        self.cell(self.epw, 5.2, self.safe(texto), 0, align='L', new_x="LMARGIN", new_y="NEXT")
        self.set_line_width(0.35)
        self.set_draw_color(0, 0, 0)
        self.line(self.l_margin, self.get_y(), self.l_margin + self.epw, self.get_y())
        self.ln(2)

    def subseccion_titulo(self, texto: str):
        if self.get_y() > self.h - 26:
            self.add_page()
        self.f_bold(8.3)
        self.set_text_color(20, 20, 20)
        self.cell(self.epw, 4.4, self.safe(texto), 0, align='L', new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


    def header(self):
        w_epw = self.epw
        if self.page_no() == 1:
            self.set_y(8)
            self.f_bold(9.5)
            self.set_text_color(0, 0, 0)
            self.cell(w_epw, 4.2, self.safe("ESTADO PLURINACIONAL DE BOLIVIA"), 0, align='C', new_x="LMARGIN", new_y="NEXT")

            self.f_bold(8.5)
            self.set_text_color(30, 30, 30)
            self.cell(w_epw, 3.8, self.safe("ASAMBLEA LEGISLATIVA PLURINACIONAL"), 0, align='C', new_x="LMARGIN", new_y="NEXT")

            self.f_regular(7.5)
            self.set_text_color(70, 70, 70)
            self.cell(w_epw, 3.4, self.safe("SISTEMA MULTIAGENTE DE AUDITORÍA LEGISLATIVA (SMA)"), 0, align='C', new_x="LMARGIN", new_y="NEXT")

            self.f_bold(8.5)
            self.set_text_color(0, 0, 0)
            self.cell(w_epw, 4.2, self.safe("INFORME OFICIAL CONSOLIDADO DE AUDITORÍA TÉCNICO-JURÍDICA"), 0, align='C', new_x="LMARGIN", new_y="NEXT")

            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.6)
            self.line(self.l_margin, 25.5, self.w - self.r_margin, 25.5)
            self.set_line_width(0.2)
            self.line(self.l_margin, 26.5, self.w - self.r_margin, 26.5)
            self.set_y(29)
        else:
            self.set_y(6)
            self.f_regular(7)
            self.set_text_color(80, 80, 80)
            self.cell(w_epw * 0.7, 4, self.safe("ASAMBLEA LEGISLATIVA PLURINACIONAL — DICTAMEN OFICIAL CONSOLIDADO"), 0, align='L', new_x="RIGHT", new_y="TOP")
            self.f_bold(7.5)
            self.set_text_color(0, 0, 0)
            self.cell(w_epw * 0.3, 4, self.safe(f"EXP. {self.numero_expediente}"), 0, align='R', new_x="LMARGIN", new_y="NEXT")

            self.set_draw_color(180, 180, 180)
            self.set_line_width(0.25)
            self.line(self.l_margin, 11, self.w - self.r_margin, 11)
            self.set_y(14)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(140, 140, 140)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.h - 12, self.w - self.r_margin, self.h - 12)

        self.f_regular(7.2)
        self.set_text_color(70, 70, 70)
        self.cell(self.epw * 0.75, 5.5, self.safe(f"Expediente: {self.numero_expediente}  |  Auditoría por Agentes de Análisis con Pensamiento Ampliado"), 0, align='L', new_x="RIGHT", new_y="TOP")
        self.cell(self.epw * 0.25, 5.5, self.safe(f"Página {self.page_no()} de {{nb}}"), 0, align='R', new_x="LMARGIN", new_y="NEXT")


def _validar_insumo(obs: Dict) -> tuple[bool, str]:
    """
    PASO 1 — Verifica que el reporte tenga estructura esperada.
    Retorna (valido, razon).
    """
    if not isinstance(obs, dict):
        return False, "El insumo no es un dict"
    faltantes = CAMPOS_REQUERIDOS_INSUMO - set(obs.keys())
    if faltantes:
        return False, f"Faltan campos: {faltantes}"
    if "confianza" in obs or "nivel_confianza" in obs:
        conf = obs.get("confianza") if "confianza" in obs else obs.get("nivel_confianza")
        if isinstance(conf, bool):
            return False, "Confianza no puede ser booleano"
        try:
            val = float(conf)
            import math
            if math.isnan(val) or val > 1.0:
                return False, f"Confianza {conf} fuera de rango [{NIVEL_CONFIANZA_MINIMO}, 1.0]"
            if val < NIVEL_CONFIANZA_MINIMO:
                # Un resultado parcial puede incluir hallazgos con verificación
                # individual válida. Preservarlo y etiquetarlo como pendiente;
                # el filtro por fila descarta lo no verificado más adelante.
                tiene_respaldo = bool(
                    obs.get("estado") == "PENDIENTE_REVISION"
                    and (obs.get("pendientes_revision") or obs.get("hallazgos")
                         or obs.get("contradicciones"))
                )
                if not tiene_respaldo:
                    return False, f"Confianza {conf} fuera de rango [{NIVEL_CONFIANZA_MINIMO}, 1.0]"
        except (TypeError, ValueError):
            return False, f"Confianza no numérica: {conf}"
    return True, "OK"


def _extraer_observaciones_de_insumo(obs: Dict, start_id: int = 1) -> List[Dict]:
    """PASO 3 — INDEXACIÓN: Normaliza el insumo asignando id, fuente, articulo_afectado y cita_original literal."""
    agente = obs.get("agente_origen", obs.get("agente", "desconocido"))
    hallazgos = obs.get("hallazgos", obs.get("contradicciones", obs.get("articulos", [])))

    if isinstance(hallazgos, list):
        items = hallazgos
    elif isinstance(hallazgos, dict):
        items = [hallazgos]
    else:
        items = [{"contenido": str(hallazgos)}]

    resultado = []
    for idx, h in enumerate(items, start=start_id):
        if isinstance(h, dict):
            art = (
                h.get("articulo_proyecto") or
                h.get("articulo_afectado") or
                h.get("articulo_constitucional") or
                h.get("articulo_cpe") or
                h.get("articulo") or
                h.get("articulo_num") or
                "N/A"
            )
            # No convertir el fundamento del agente en una supuesta cita legal.
            cita = (h.get("cita_original") if h.get("cita_original") is not None else
                    h.get("cita_proyecto") or h.get("fragmento_proyecto") or h.get("contenido") or "")
            cita_str = str(cita)
            resultado.append({
                "id": f"OBS-{idx:03d}",
                "fuente": agente,
                "agente_origen": agente,
                "articulo": art,
                "articulo_afectado": art,
                "articulo_proyecto": art,
                "cita_original": cita_str,
                "contenido": cita_str.strip(),
                "tipo": h.get("tipo_conflicto", h.get("tipo_relacion", h.get("clasificacion", h.get("tipo", "OBSERVACION")))),
                "riesgo": h.get("severidad", h.get("riesgo", "leve")),
                "verificado": h.get("verificado", True),
                "norma": h.get("norma", ""),
                "numero_articulo": h.get("numero_articulo", ""),
                "articulo_cpe": h.get("articulo_cpe") or h.get("articulo_constitucional", ""),
                "texto_cpe_literal": h.get("texto_cpe_literal") or h.get("texto_constitucional_verificado") or h.get("cita_constitucional", ""),
                "fragmento_proyecto": h.get("fragmento_proyecto", ""),
                "accion_recomendada": h.get("accion_recomendada") or h.get("recomendacion", ""),
                "cita_constitucional": h.get("cita_constitucional", ""),
                "explicacion": h.get("analisis_constitucional") or h.get("fundamento") or h.get("razon", ""),
                "evaluacion_criterios": h.get("evaluacion_criterios", {}),
                "articulos_cpe_relacionados": h.get("articulos_cpe_relacionados", []),
                "alcance_vicio": h.get("alcance_vicio", ""),
                "analisis_profundo": h.get("analisis_profundo", {}),
                "similitud": h.get("similitud", 0),
            })
    return resultado


def _fusionar_redundancias(observaciones: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """
    PASO 4 — Fusiona observaciones que apuntan al mismo artículo + tipo + cita_original.
    Conserva AMBAS fuentes en 'fuentes': []. Nunca elimina una fuente ni citas distintas.
    """
    clave_a_grupo: Dict[str, List[Dict]] = {}
    for obs in observaciones:
        clave = f"{obs.get('articulo_afectado', '')}|{obs.get('tipo', '')}|{obs.get('cita_original', '')}"
        clave_a_grupo.setdefault(clave, []).append(obs)


    integradas = []
    fusionadas = []
    for clave, grupo in clave_a_grupo.items():
        if len(grupo) == 1:
            integradas.append(grupo[0])
        else:
            fusionado = {
                "fuentes": [g["fuente"] for g in grupo],
                "articulo_afectado": grupo[0]["articulo_afectado"],
                "cita_original": grupo[0]["cita_original"],  # Cita primaria (de primera fuente)
                "citas_adicionales": [g["cita_original"] for g in grupo[1:]],
                "tipo": grupo[0]["tipo"],
                "riesgo": max((g.get("riesgo", "leve") for g in grupo),
                              key=lambda r: {"bloqueante": 3, "grave": 2, "leve": 1, "ninguna": 0}.get(r, 0)),
                "verificado": all(g.get("verificado", True) for g in grupo),
                "_fusion": True,
            }
            integradas.append(fusionado)
            fusionadas.append(fusionado)
    return integradas, fusionadas


def _calcular_riesgo_global(obs_integradas: List[Dict]) -> str:
    """Calcula el nivel de riesgo general basado en los hallazgos verificados."""
    niveles = [o.get("riesgo", "leve") for o in obs_integradas if o.get("verificado")]
    if "bloqueante" in niveles:
        return "CRÍTICO"
    if "grave" in niveles:
        return "ALTO"
    if "leve" in niveles:
        return "MEDIO"
    return "BAJO"


# ── LLM con Pensamiento Analítico Ampliado (Nemotron Super 120B) ─────────────
def _analizar_con_pensamiento_ampliado_llm(
    titulo: str,
    id_proyecto: int,
    riesgo_global: str,
    obs_verificadas: List[Dict],
    insumos_validos: List[Dict],
    proyecto_info: Dict
) -> Dict[str, str]:
    """
    Invoca el modelo LLM de razonamiento configurado en LLM_MODEL_NVIDIA
    mediante el cliente OpenAI con fallback resiliente.
    Genera resumen sustantivo del proyecto, síntesis de constitucionalidad y normativa,
    y conclusiones técnico-jurídicas vinculantes.
    """
    agentes_presentes = list({v.get("agente_origen", "Evaluador") for v in insumos_validos if isinstance(v, dict)})
    obs_cpe = [o for o in obs_verificadas if "constitucional" in str(o.get("fuente", "")).lower() or "constitucional" in str(o.get("tipo", "")).lower()]
    obs_normativas = [o for o in obs_verificadas if "consistencia" in str(o.get("fuente", "")).lower() or "normat" in str(o.get("tipo", "")).lower()]

    system_prompt = (
        "Eres el Asesor Jurídico Principal del Sistema Multiagente de la Asamblea Legislativa Plurinacional de Bolivia. "
        "Tu misión es elaborar un dictamen institucional formal de máxima rigurosidad técnica en LETRA FORMAL. "
        "El análisis integra el trabajo del Agente Verificador de Constitucionalidad (CPE) y del Agente de Consistencia Normativa. "
        "DEBES APLICAR PENSAMIENTO ANALÍTICO AMPLIADO (Extended Deep Reasoning / Chain-of-Thought). "
        "REGLAS OBLIGATORIAS:\n"
        "1. Mantén estricto tono jurídico formal parlamentario boliviano.\n"
        "2. Menciona expresamente que el análisis fue elaborado por 'Agentes de Análisis Especializados del Sistema Legislativo con Pensamiento Analítico Ampliado'.\n"
        "3. NO alteres ni inventes citas normativas. Fundamenta sobre los hechos e insumos suministrados.\n"
        "4. Devuelve ÚNICAMENTE un objeto JSON válido con los campos requeridos."
    )

    user_prompt = f"""
DATOS DEL PROYECTO:
- Título: "{titulo}"
- ID Radicación: {id_proyecto}
- Nivel de Riesgo Global Determinado: {riesgo_global}
- Agentes de Análisis Involucrados: {agentes_presentes}
- Estado y resumen reportado por cada agente (respeta COMPLETADO/PENDIENTE_REVISION):
{json.dumps([{'agente': v.get('agente_origen'), 'estado': v.get('estado'), 'resumen': v.get('resumen'), 'pendientes_revision': (v.get('pendientes_revision') or [])[:5]} for v in insumos_validos], ensure_ascii=False)[:7000]}
- Total Observaciones Verificadas: {len(obs_verificadas)}
- Observaciones de Constitucionalidad (CPE): {len(obs_cpe)}
- Observaciones de Consistencia Normativa: {len(obs_normativas)}

DETALLE DE OBSERVACIONES VERIFICADAS:
{json.dumps(obs_verificadas[:15], ensure_ascii=False, indent=2)}

INFORME PROFESIONAL COMPLEMENTARIO (orientación, no auditoría verificada;
no modificar el riesgo global ni convertirlo en observaciones verificadas):
{json.dumps(proyecto_info.get('informe_profesional', {}), ensure_ascii=False)}

INSTRUCCIÓN: Devuelve un JSON estructurado con exactamente estas claves:
{{
  "resumen_ejecutivo": "Síntesis ejecutiva de 2 a 3 frases en español formal",
  "resumen_proyecto_detallado": "Explicación sustantiva del objeto, alcance, justificación e impacto legislativo del proyecto",
  "sintesis_constitucional": "Evaluación técnico-jurídica de la remisión del Agente Verificador de Constitucionalidad (artículos en armonía o vicios detectados)",
  "sintesis_normativa": "Evaluación técnico-jurídica de la remisión del Agente de Consistencia Normativa (leyes vigentes, derogaciones, jerarquía)",
  "conclusiones_juridicas": "Conclusiones formales concluyentes sobre la viabilidad o necesidad de subsanación previa del proyecto",
  "recomendaciones_vinculantes": "Recomendaciones específicas directas y vinculantes para la Comisión Legislativa y el Pleno camaral",
  "declaracion_metodologia": "Declaración formal certificando que el informe fue producido por Agentes de Análisis Especializados utilizando Razonamiento Analítico y Pensamiento Ampliado"
}}
"""

    try:
        from sma_unified.agents.base_agent import get_prompt_templates, render_prompt
        sys_tpl, usr_tpl = get_prompt_templates("Concentrador")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = render_prompt(
                usr_tpl,
                titulo=titulo,
                id_proyecto=id_proyecto,
                riesgo_global=riesgo_global,
                agentes_presentes=", ".join(agentes_presentes) if agentes_presentes else "Evaluador",
                total_observaciones=len(obs_verificadas),
                observaciones_verificadas=json.dumps(obs_verificadas[:15], ensure_ascii=False, indent=2),
                informe_profesional=json.dumps(proyecto_info.get('informe_profesional', {}), ensure_ascii=False)
            )
    except Exception as e_tpl:
        logger.debug(f"[Concentrador] Usando prompt local por fallback: {e_tpl}")

    # 1. Intento primario con cliente OpenAI oficial hacia NVIDIA NIM
    try:
        client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=DEFAULT_NVIDIA_API_KEY,
            timeout=90.0,
        )
        completion = client.chat.completions.create(
            model=MODELO_RAZONAMIENTO_AMPLIADO,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            top_p=0.95,
            max_tokens=2200,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            stream=False
        )
        msg_obj = completion.choices[0].message
        content = msg_obj.content or getattr(msg_obj, "reasoning_content", "") or ""
        parsed = extraer_json_de_llm(content)
        if isinstance(parsed, dict) and parsed.get("resumen_ejecutivo"):
            logger.info(f"[Concentrador] Análisis con pensamiento ampliado exitoso ({MODELO_RAZONAMIENTO_AMPLIADO})")
            return parsed
    except Exception as e_nem:
        logger.warning(f"[Concentrador] OpenAI/Nemotron NIM falló ({e_nem}). Recurriendo a fallback resiliente.")

    # 2. Intento de respaldo con chat_completion_resiliente del sistema
    try:
        raw_resiliente, modelo_usado = chat_completion_resiliente(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1500
        )
        parsed = extraer_json_de_llm(raw_resiliente)
        if isinstance(parsed, dict) and parsed.get("resumen_ejecutivo"):
            logger.info(f"[Concentrador] Fallback resiliente exitoso usando modelo: {modelo_usado}")
            return parsed
    except Exception as e_fb:
        logger.warning(f"[Concentrador] Fallback resiliente también falló ({e_fb}). Usando síntesis determinista.")

    # 3. Retorno determinista de máxima seguridad si ambas llamadas de red fallan
    return {
        "resumen_ejecutivo": f"Expediente consolidado para el proyecto '{titulo}' (ID: {id_proyecto}). Nivel de riesgo global: {riesgo_global}.",
        "resumen_proyecto_detallado": f"El proyecto de ley '{titulo}' propone regulaciones sustantivas que fueron sometidas a control de legalidad y técnica legislativa.",
        "sintesis_constitucional": f"Se remitieron {len(obs_cpe)} observaciones por el Agente Verificador de Constitucionalidad relativas al apego a la Constitución Política del Estado.",
        "sintesis_normativa": f"Se remitieron {len(obs_normativas)} observaciones por el Agente de Consistencia Normativa respecto a leyes y decretos vigentes.",
        "conclusiones_juridicas": f"El expediente presenta un nivel de riesgo {riesgo_global}. Las observaciones consolidadas requieren análisis prioritario por la Comisión competente.",
        "recomendaciones_vinculantes": "Remitir el presente expediente unificado a la Presidencia de Comisión con carácter previo a su consideración en Plenaria camaral.",
        "declaracion_metodologia": "Dictamen procesado por los Agentes de Análisis Especializados del Sistema Legislativo con Pensamiento Analítico Ampliado."
    }


# ── Generador de PDF en Letra Negra y Alta Formalidad ─────────────────────────
def generar_pdf_informe_concentrador(
    id_proyecto: int,
    titulo_proyecto: str,
    riesgo_global: str,
    estado_siguiente: str,
    analisis_dict: Dict[str, str],
    observaciones_finales: List[Dict],
    redundancias_count: int,
    insumos_no_validos: List[Dict],
    obs_cpe_detalle: Optional[List[Dict]] = None,
    obs_normativas_detalle: Optional[List[Dict]] = None,
    informe_profesional: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Construye y almacena el documento oficial en formato PDF institucional en letra negra.
    Guarda el archivo en uploaded_files/informes/ y genera metadatos completos con SHA-256.

    Secciones:
      1. Declaracion Institucional de Auditoria
      2. Resumen Sustantivo del Proyecto de Ley
      3. Observaciones de Constitucionalidad (CPE 2009) -- itemizadas
      4. Observaciones de Consistencia Normativa (Leyes Vigentes) -- itemizadas
      5. Recomendaciones de Documentacion y Tecnica Legislativa
      6. Sintesis de Dictamenes (textuales)
      7. Matriz Consolidada de Observaciones y Trazabilidad Forense
      8. Conclusiones y Recomendaciones Vinculantes
      9. Certificacion de Inmutabilidad y Validez Legal
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(base_dir, "uploaded_files", "informes")
    os.makedirs(output_dir, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    expediente_codigo = f"EXP-{id_proyecto:04d}" if id_proyecto else "EXP-2026-SMA"
    filename = f"INFORME_CONCENTRADOR_{expediente_codigo}_{timestamp_str}.pdf"
    filepath = os.path.join(output_dir, filename)

    pdf = InformeConcentradorFormalPDF(numero_expediente=expediente_codigo)
    pdf.add_page()
    epw = pdf.epw

    # ── Cuadro de Metadatos y Radicacion (Bordes Negros, Letra Negra) ────────
    pdf.set_fill_color(248, 248, 248)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.4)
    y_inicio_meta = pdf.get_y()
    pdf.rect(pdf.l_margin, y_inicio_meta, epw, 24, 'DF')

    pdf.set_xy(pdf.l_margin + 3, y_inicio_meta + 2.5)
    pdf.f_bold(8.5)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(epw - 6, 4, pdf.safe(f"EXPEDIENTE OFICIAL: {expediente_codigo}   |   FECHA DE EMISION: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"), 0, align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(pdf.l_margin + 3)
    pdf.f_regular(8)
    pdf.cell(epw - 6, 4, pdf.safe(f"PROYECTO DE LEY: {titulo_proyecto[:95]}"), 0, align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(pdf.l_margin + 3)
    pdf.f_bold(8)
    pdf.cell(epw - 6, 4, pdf.safe(f"NIVEL DE RIESGO GLOBAL: [{riesgo_global}]   |   ESTADO PROCESAL SIGUIENTE: [{estado_siguiente}]"), 0, align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(pdf.l_margin + 3)
    pdf.f_italic(7.5)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(epw - 6, 4, pdf.safe("Control de legalidad e integracion forense parlamentaria conforme a los Arts. 156-161 de la CPE."), 0, align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y_inicio_meta + 28)

    # ══ SECCION 1: DECLARACION INSTITUCIONAL ══════════════════════════════════
    pdf.seccion_titulo("1. DECLARACION INSTITUCIONAL DE AUDITORIA POR AGENTES DE ANALISIS")
    pdf.f_regular(8)
    pdf.set_text_color(20, 20, 20)
    decl_texto = (
        "Se deja constancia formal que la presente auditoria fue ejecutada por los Agentes de Analisis Especializados "
        "del Sistema Legislativo Plurinacional (SMA), integrando en primer termino los dictamenes del Agente Verificador de "
        "Constitucionalidad y del Agente de Consistencia Normativa. La evaluacion opero bajo un regimen de razonamiento analitico "
        "y pensamiento ampliado (Extended Analytical Thinking / Deep Multi-Agent CoT), garantizando maxima exhaustividad "
        "en la contrastacion contra la Constitucion Politica del Estado (CPE 2009, Arts. 1-410) y el catalogo normativo nacional vigente."
    )
    pdf.multi_cell(epw, 4.2, pdf.safe(decl_texto))
    estados = analisis_dict.get("estado_auditorias") or {}
    estado_cpe = estados.get("constitucionalidad", "DESCONOCIDO")
    estado_norm = estados.get("consistencia_normativa", "DESCONOCIDO")
    pendientes_cpe = estados.get("pendientes_constitucionalidad", 0)
    pendientes_norm = estados.get("pendientes_normativa", 0)
    pdf.f_bold(8)
    pdf.multi_cell(epw, 4.2, pdf.safe(
        f"Estado de revisión: Constitucionalidad {estado_cpe} ({pendientes_cpe} pendiente(s)); "
        f"Consistencia normativa {estado_norm} ({pendientes_norm} pendiente(s))."
    ))
    pdf.ln(2)

    # ══ SECCION 2: RESUMEN SUSTANTIVO ═════════════════════════════════════════
    pdf.seccion_titulo("2. RESUMEN SUSTANTIVO DEL PROYECTO DE LEY")
    pdf.subseccion_titulo("2.1. Resumen Ejecutivo:")
    pdf.f_regular(8)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(epw, 4.2, pdf.safe(analisis_dict.get("resumen_ejecutivo", "")))
    pdf.ln(1.5)
    pdf.subseccion_titulo("2.2. Alcance y Objeto Material del Proyecto:")
    pdf.f_regular(8)
    pdf.multi_cell(epw, 4.2, pdf.safe(analisis_dict.get("resumen_proyecto_detallado", "")))
    pdf.ln(2)

    # ══ SECCION 3: OBSERVACIONES DE CONSTITUCIONALIDAD (CPE 2009) ═════════════
    obs_cpe = obs_cpe_detalle or [o for o in observaciones_finales
                                   if "constitucional" in str(o.get("fuente", "")).lower()
                                   or "constitucional" in str(o.get("tipo", "")).lower()]
    pdf.seccion_titulo(f"3. OBSERVACIONES DE CONSTITUCIONALIDAD (CPE 2009) -- {len(obs_cpe)} HALLAZGO(S)")
    if not obs_cpe:
        pdf.f_italic(8)
        pdf.set_text_color(60, 60, 60)
        estado_cpe = (analisis_dict.get("estado_auditorias") or {}).get("constitucionalidad", "DESCONOCIDO")
        mensaje_cpe = ("Auditoría constitucional pendiente de revisión; este informe no concluye ausencia de contradicciones."
                       if estado_cpe == "PENDIENTE_REVISION" else
                       "No se registraron contradicciones constitucionales en la auditoría completada."
                       if estado_cpe == "COMPLETADO" else
                       "No hay dictamen constitucional completo disponible para este expediente.")
        pdf.cell(epw, 5, pdf.safe(mensaje_cpe), 0, align='L', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        pdf.f_regular(7.8)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(epw, 4, pdf.safe(
            "Las siguientes observaciones fueron emitidas por el Agente Verificador de Constitucionalidad mediante "
            "cotejo literal articulo por articulo contra la CPE 2009. Severidad: BLOQUEANTE, GRAVE o LEVE."
        ))
        pdf.ln(2)
        for idx, obs in enumerate(obs_cpe, 1):
            if pdf.get_y() > pdf.h - 55:
                pdf.add_page()
            riesgo_obs = str(obs.get("riesgo", obs.get("severidad", "leve"))).upper()
            art_proy = str(obs.get("articulo_proyecto") or obs.get("articulo") or obs.get("articulo_afectado") or "N/A")[:35]
            art_cpe  = str(obs.get("articulo_cpe", ""))[:25]
            pdf.set_fill_color(235, 235, 235)
            pdf.set_draw_color(80, 80, 80)
            pdf.set_line_width(0.25)
            y_card = pdf.get_y()
            pdf.rect(pdf.l_margin, y_card, epw, 5.5, 'DF')
            pdf.set_xy(pdf.l_margin + 2, y_card + 0.8)
            pdf.f_bold(8)
            pdf.set_text_color(0, 0, 0)
            header_txt = f"OBS-CPE-{idx:03d}  |  Art. Proyecto: {art_proy}  |  Art. CPE: {art_cpe}  |  Severidad: {riesgo_obs}"
            pdf.cell(epw - 4, 4, pdf.safe(header_txt), 0, align='L', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)
            campos_cpe = [
                ("Norma / Referencia", str(obs.get("norma", "CPE 2009"))[:120]),
                ("Texto CPE Literal", str(obs.get("texto_cpe_literal") or obs.get("cita_constitucional") or "")[:280]),
                ("Fragmento del Proyecto", str(obs.get("fragmento_proyecto") or obs.get("contenido") or "")[:280]),
                ("Fundamento / Explicacion", str(obs.get("explicacion") or obs.get("fundamento") or "")[:280]),
                ("Criterios evaluados", "; ".join(
                    f"{clave}: {valor}" for clave, valor in (obs.get("evaluacion_criterios") or {}).items()
                )[:280]),
                ("Análisis de impacto", str((obs.get("analisis_profundo") or {}).get("impacto_juridico") or "")[:280]),
                ("Dictamen preliminar", str((obs.get("analisis_profundo") or {}).get("dictamen") or "")[:120]),
                ("Alcance del hallazgo", str(obs.get("alcance_vicio") or "")[:100]),
                ("Artículos CPE conexos", ", ".join(
                    str(ref.get("numero") or ref.get("articulo") or "") if isinstance(ref, dict) else str(ref)
                    for ref in (obs.get("articulos_cpe_relacionados") or [])
                    if not isinstance(ref, dict) or ref.get("numero") or ref.get("articulo")
                )[:220]),
                ("Accion Correctiva Recomendada", str(obs.get("accion_recomendada") or obs.get("accion_correctiva") or "Subsanar antes de la siguiente etapa procesal.")[:220]),
            ]
            for etiqueta, valor in campos_cpe:
                if not valor or valor.strip() in ("", "N/A"):
                    continue
                pdf.f_bold(7.5)
                pdf.set_text_color(20, 20, 20)
                pdf.set_x(pdf.l_margin + 3)
                pdf.cell(48, 4, pdf.safe(f"{etiqueta}:"), 0, align='L', new_x="RIGHT", new_y="TOP")
                pdf.f_regular(7.5)
                pdf.set_text_color(35, 35, 35)
                pdf.multi_cell(epw - 51, 4, pdf.safe(valor))
            pdf.set_draw_color(160, 160, 160)
            pdf.set_line_width(0.15)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + epw, pdf.get_y())
            pdf.ln(3)

    articulos_favor = analisis_dict.get("articulos_a_favor_cpe", []) or []
    pdf.subseccion_titulo(f"3.1 CONCORDANCIAS CONSTITUCIONALES A FAVOR — {len(articulos_favor)}")
    if articulos_favor:
        for item in articulos_favor:
            art_cpe = item.get("numero") or item.get("articulo_constitucional") or "N/D"
            art_proy = item.get("articulo_proyecto") or "Artículo del proyecto no identificado"
            relacionados = item.get("articulos_cpe_relacionados", []) or []
            relacionados_txt = ", ".join(
                f"Art. {ref.get('numero')} {ref.get('titulo', '')}".strip()
                for ref in relacionados if ref.get("numero")
            ) or "Sin artículos conexos adicionales verificados"
            pdf.f_bold(7.8)
            pdf.multi_cell(epw, 4, pdf.safe(f"A FAVOR — Proyecto {art_proy} ↔ CPE Art. {art_cpe} {item.get('titulo', '')}"))
            pdf.f_regular(7.5)
            pdf.multi_cell(epw, 4, pdf.safe(f"Fundamento: {item.get('analisis_constitucional') or item.get('fundamento', 'Sin fundamento detallado')}"))
            pdf.multi_cell(epw, 4, pdf.safe(f"Cita del proyecto: {item.get('cita_proyecto', 'No disponible')}"))
            pdf.multi_cell(epw, 4, pdf.safe(f"Cita CPE: {item.get('cita_constitucional', 'No disponible')}"))
            pdf.multi_cell(epw, 4, pdf.safe(f"Artículos CPE relacionados: {relacionados_txt}"))
            criterios = item.get("evaluacion_criterios") or {}
            if criterios:
                pdf.multi_cell(epw, 4, pdf.safe("Criterios: " + "; ".join(f"{k}: {v}" for k,v in criterios.items())))
            pdf.ln(1)
    else:
        pdf.f_italic(7.5)
        pdf.multi_cell(epw, 4, pdf.safe("No se identificaron concordancias positivas verificadas en los artículos cotejados."))

    analisis_fondo = analisis_dict.get("analisis_fondo_cpe", []) or []
    pdf.subseccion_titulo(f"3.2 ASUNTOS QUE REQUIEREN ANÁLISIS DE FONDO — {len(analisis_fondo)}")
    for item in analisis_fondo:
        pdf.f_regular(7.5)
        pdf.multi_cell(epw, 4, pdf.safe(
            f"{item.get('articulo_constitucional', 'Artículo CPE N/D')} — "
            f"{item.get('razon', 'Requiere ponderación o información adicional')} "
            f"Recomendación: {item.get('recomendacion', 'Revisión jurídica especializada')}"
        ))

    # ══ SECCION 4: OBSERVACIONES DE CONSISTENCIA NORMATIVA ════════════════════
    obs_norm = obs_normativas_detalle or [o for o in observaciones_finales
                                           if "consistencia" in str(o.get("fuente", "")).lower()
                                           or "normat" in str(o.get("tipo", "")).lower()]
    pdf.seccion_titulo(f"4. OBSERVACIONES DE CONSISTENCIA NORMATIVA (LEYES VIGENTES) -- {len(obs_norm)} HALLAZGO(S)")
    if not obs_norm:
        pdf.f_italic(8)
        pdf.set_text_color(60, 60, 60)
        estado_norm = (analisis_dict.get("estado_auditorias") or {}).get("consistencia_normativa", "DESCONOCIDO")
        mensaje_norm = ("Auditoría de consistencia normativa pendiente de revisión; no se concluye ausencia de colisiones."
                        if estado_norm == "PENDIENTE_REVISION" else
                        "No se registraron colisiones normativas en la auditoría completada."
                        if estado_norm == "COMPLETADO" else
                        "No hay dictamen normativo completo disponible para este expediente.")
        pdf.cell(epw, 5, pdf.safe(mensaje_norm), 0, align='L', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        pdf.f_regular(7.8)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(epw, 4, pdf.safe(
            "Las siguientes observaciones fueron emitidas por el Agente de Consistencia Normativa mediante analisis "
            "semantico vectorial (pgvector) sobre el corpus de leyes bolivianas vigentes. "
            "Se identifican antinomias, derogaciones tacitas y redundancias."
        ))
        pdf.ln(2)
        for idx, obs in enumerate(obs_norm, 1):
            if pdf.get_y() > pdf.h - 55:
                pdf.add_page()
            riesgo_obs = str(obs.get("riesgo", obs.get("severidad", "leve"))).upper()
            art_proy   = str(obs.get("articulo_proyecto") or obs.get("articulo") or obs.get("articulo_afectado") or "N/A")[:30]
            norma_choc = str(obs.get("norma") or obs.get("norma_vigente") or "Ley vigente")[:30]
            tipo_rel   = str(obs.get("tipo") or obs.get("tipo_relacion") or obs.get("tipo_conflicto") or "COLISION")[:20]
            num_art    = str(obs.get("numero_articulo") or obs.get("articulo_vigente") or "")
            similitud  = obs.get("similitud", obs.get("similitud_semantica", 0))
            sim_str    = f"  |  Similitud: {float(similitud)*100:.1f}%" if similitud else ""
            pdf.set_fill_color(235, 235, 235)
            pdf.set_draw_color(80, 80, 80)
            pdf.set_line_width(0.25)
            y_card = pdf.get_y()
            pdf.rect(pdf.l_margin, y_card, epw, 5.5, 'DF')
            pdf.set_xy(pdf.l_margin + 2, y_card + 0.8)
            pdf.f_bold(8)
            pdf.set_text_color(0, 0, 0)
            header_txt = f"OBS-NORM-{idx:03d}  |  Art. Proyecto: {art_proy}  |  Norma: {norma_choc}  |  Tipo: {tipo_rel}{sim_str}"
            pdf.cell(epw - 4, 4, pdf.safe(header_txt), 0, align='L', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)
            campos_norm = [
                ("Ley / Norma Vigente", str(norma_choc)[:120]),
                ("Articulo Vigente Afectado", num_art[:80] if num_art else None),
                ("Tipo de Relacion", tipo_rel[:80]),
                ("Analisis / Justificacion", str(obs.get("analisis") or obs.get("cita_original") or obs.get("contenido") or obs.get("explicacion") or "")[:280]),
                ("Sugerencia de Redaccion", str(obs.get("sugerencia_redaccion") or obs.get("accion_recomendada") or "")[:220]),
            ]
            for etiqueta, valor in campos_norm:
                if not valor or str(valor).strip() in ("", "N/A", "None"):
                    continue
                pdf.f_bold(7.5)
                pdf.set_text_color(20, 20, 20)
                pdf.set_x(pdf.l_margin + 3)
                pdf.cell(48, 4, pdf.safe(f"{etiqueta}:"), 0, align='L', new_x="RIGHT", new_y="TOP")
                pdf.f_regular(7.5)
                pdf.set_text_color(35, 35, 35)
                pdf.multi_cell(epw - 51, 4, pdf.safe(str(valor)))
            pdf.set_draw_color(160, 160, 160)
            pdf.set_line_width(0.15)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + epw, pdf.get_y())
            pdf.ln(3)

    # ══ SECCION 5: RECOMENDACIONES DE DOCUMENTACION Y TECNICA LEGISLATIVA ═════
    pdf.seccion_titulo("5. RECOMENDACIONES DE DOCUMENTACION Y TECNICA LEGISLATIVA")
    pdf.f_regular(7.8)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(epw, 4, pdf.safe(
        "Conforme a los principios de tecnica legislativa del Estado Plurinacional de Bolivia, el presente "
        "expediente requiere la subsanacion de los siguientes documentos y diligencias ANTES de su aprobacion en Plenaria:"
    ))
    pdf.ln(2)
    recomendaciones_doc = [
        (
            "5.1. VIABILIDAD PRESUPUESTARIA -- Art. 321 CPE / MEFP",
            "SUBSANACION OBLIGATORIA",
            "El proyecto debera acreditar la disponibilidad de recursos fiscales mediante dictamen del Ministerio de "
            "Economia y Finanzas Publicas (MEFP), conforme al Art. 321 CPE y la Ley 1178 (SAFCO). El dictamen debe incluir: "
            "(a) identificacion de la fuente de financiamiento en el PGE o credito externo; "
            "(b) estimacion del costo de implementacion inicial y costo operativo anual en Bolivianos (Bs.); "
            "(c) cronograma de ejecucion presupuestaria multianual. Sin este dictamen, el proyecto no puede ser sancionado."
        ),
        (
            "5.2. DICTAMENES TECNICOS SECTORIALES",
            "RECOMENDADO / NECESARIO",
            "Adjuntar dictamenes de ministerios o entidades sectoriales con competencia directa sobre la materia, "
            "conforme al Art. 158 num. 3 CPE. Deben incluir: (a) analisis de impacto regulatorio; "
            "(b) compatibilidad con planes sectoriales vigentes; (c) identificacion de entidades ejecutoras y sus capacidades."
        ),
        (
            "5.3. CUADRO COMPARATIVO DE ENMIENDAS",
            "RECOMENDADO",
            "Elaborar tabla comparativa (texto original vs. enmienda) para cada modificacion sugerida por los Agentes de Analisis "
            "y/o legisladores durante el debate en comision. Exigible conforme al Reglamento General de la Camara de Diputados. "
            "Facilita la trazabilidad de cambios y la fidelidad del acta parlamentaria."
        ),
        (
            "5.4. ACREDITACION DE SOCIALIZACION Y CONSULTA PREVIA (CPLI)",
            "OBLIGATORIO SI APLICA (Art. 30.II.15 CPE / Convenio 169 OIT)",
            "Si el proyecto afecta derechos o competencias de naciones y pueblos indigena originario campesinos (NPIOC), "
            "debe acreditarse la consulta previa, libre e informada segun Art. 30 num. II.15 CPE y Ley 1257. "
            "La acreditacion debe incluir: (a) actas de socializacion con firmas de asistentes; "
            "(b) informe de incorporacion de observaciones ciudadanas al texto del proyecto."
        ),
        (
            "5.5. FOLIACION Y REGISTRO EN MESA DE ENTRADAS",
            "REQUISITO FORMAL PREVIO",
            "Verificar que el expediente haya sido debidamente foliado y registrado en Mesa de Entradas de la Camara de Origen. "
            "Debe incluir: (a) nota de presentacion firmada por el asambleista proponente o el Organo Ejecutivo; "
            "(b) exposicion de motivos completa; (c) articulado del proyecto; (d) anexos tecnicos correspondientes. "
            "La ausencia de foliatura completa es causal de devolucion por Secretaria."
        ),
    ]
    for subtitulo, nivel, texto in recomendaciones_doc:
        if pdf.get_y() > pdf.h - 55:
            pdf.add_page()
        pdf.set_fill_color(240, 240, 240)
        pdf.set_draw_color(60, 60, 60)
        pdf.set_line_width(0.2)
        y_rec = pdf.get_y()
        pdf.rect(pdf.l_margin, y_rec, epw, 5.2, 'DF')
        pdf.set_xy(pdf.l_margin + 2, y_rec + 0.7)
        pdf.f_bold(8)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(epw * 0.72, 3.8, pdf.safe(subtitulo), 0, align='L', new_x="RIGHT", new_y="TOP")
        pdf.f_bold(7.5)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(epw * 0.27, 3.8, pdf.safe(f"[{nivel}]"), 0, align='R', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)
        pdf.set_x(pdf.l_margin + 3)
        pdf.f_regular(7.6)
        pdf.set_text_color(25, 25, 25)
        pdf.multi_cell(epw - 3, 3.9, pdf.safe(texto))
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.12)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + epw, pdf.get_y())
        pdf.ln(3)

    # ══ SECCION 6: SINTESIS DE DICTAMENES (TEXTUALES) ════════════════════════
    pdf.seccion_titulo("6. SINTESIS DE DICTAMENES DE CONSTITUCIONALIDAD Y CONSISTENCIA NORMATIVA")
    pdf.subseccion_titulo("6.1. Dictamen del Agente de Verificacion Constitucional (CPE):")
    pdf.f_regular(8)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(epw, 4.2, pdf.safe(analisis_dict.get("sintesis_constitucional", "")))
    pdf.ln(1.5)
    pdf.subseccion_titulo("6.2. Dictamen del Agente de Consistencia Normativa (Leyes Vigentes):")
    pdf.f_regular(8)
    pdf.multi_cell(epw, 4.2, pdf.safe(analisis_dict.get("sintesis_normativa", "")))
    pdf.ln(2)

    # ══ SECCION 7: MATRIZ CONSOLIDADA DE TRAZABILIDAD FORENSE ════════════════
    pdf.seccion_titulo("7. MATRIZ CONSOLIDADA DE OBSERVACIONES Y TRAZABILIDAD FORENSE")

    col_w = [18, 40, 22, 75, 25]  # Total: 180mm
    pdf.f_bold(7.5)
    pdf.set_fill_color(220, 220, 220)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)

    pdf.cell(col_w[0], 5.5, pdf.safe("ID"), 1, 0, 'C', True)
    pdf.cell(col_w[1], 5.5, pdf.safe("Agente Emisor"), 1, 0, 'C', True)
    pdf.cell(col_w[2], 5.5, pdf.safe("Articulo"), 1, 0, 'C', True)
    pdf.cell(col_w[3], 5.5, pdf.safe("Cita Literal / Fundamento"), 1, 0, 'C', True)
    pdf.cell(col_w[4], 5.5, pdf.safe("Riesgo"), 1, 1, 'C', True)

    pdf.f_regular(7)
    if observaciones_finales:
        for obs in observaciones_finales[:25]:
            if pdf.get_y() > pdf.h - 25:
                pdf.add_page()
                pdf.f_bold(7.5)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(col_w[0], 5.5, pdf.safe("ID"), 1, 0, 'C', True)
                pdf.cell(col_w[1], 5.5, pdf.safe("Agente Emisor"), 1, 0, 'C', True)
                pdf.cell(col_w[2], 5.5, pdf.safe("Articulo"), 1, 0, 'C', True)
                pdf.cell(col_w[3], 5.5, pdf.safe("Cita Literal / Fundamento"), 1, 0, 'C', True)
                pdf.cell(col_w[4], 5.5, pdf.safe("Riesgo"), 1, 1, 'C', True)
                pdf.f_regular(7)

            o_id = obs.get("id", "OBS-000")
            fuentes_list = obs.get("fuentes") or [obs.get("fuente", "?")]
            fuente_str = ", ".join(str(f) for f in fuentes_list)[:35]
            art_str = str(obs.get("articulo") or obs.get("articulo_afectado") or "N/A")[:18]
            cita_str = str(obs.get("cita_original") or obs.get("fundamento") or "Sin cita registrada")[:120]
            riesgo_str = str(obs.get("riesgo", "leve")).upper()

            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_w[0], 5, pdf.safe(o_id), 1, 0, 'C')
            pdf.cell(col_w[1], 5, pdf.safe(fuente_str), 1, 0, 'L')
            pdf.cell(col_w[2], 5, pdf.safe(art_str), 1, 0, 'C')
            pdf.cell(col_w[3], 5, pdf.safe(cita_str), 1, 0, 'L')
            pdf.cell(col_w[4], 5, pdf.safe(riesgo_str), 1, 1, 'C')
    else:
        pdf.cell(epw, 5.5, pdf.safe("No se registraron observaciones formales en el expediente."), 1, 1, 'C')

    pdf.ln(3)

    # ══ SECCION 8: CONCLUSIONES Y RECOMENDACIONES VINCULANTES ════════════════
    pdf.seccion_titulo("8. CONCLUSIONES Y RECOMENDACIONES VINCULANTES")
    pdf.subseccion_titulo("8.1. Conclusiones Tecnico-Juridicas:")
    pdf.f_regular(8)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(epw, 4.2, pdf.safe(analisis_dict.get("conclusiones_juridicas", "")))
    pdf.ln(1.5)
    pdf.subseccion_titulo("8.2. Recomendaciones Especificas a la Comision Legislativa:")
    pdf.f_regular(8)
    pdf.multi_cell(epw, 4.2, pdf.safe(analisis_dict.get("recomendaciones_vinculantes", "")))
    pdf.ln(3)

    # ══ SECCION 9: CERTIFICACION DE INMUTABILIDAD Y VALIDEZ LEGAL ═════════════
    if pdf.get_y() > pdf.h - 38:
        pdf.add_page()
    pdf.seccion_titulo("9. CERTIFICACION DE INMUTABILIDAD Y VALIDEZ LEGAL")
    pdf.f_regular(7.5)
    pdf.set_text_color(20, 20, 20)
    cert_txt = (
        "El presente informe formal fue consolidado sin alteracion ni parafraseo del texto original del proyecto de ley. "
        "Las firmas digitales y registros de bitacora han sido asentados en la capa de persistencia relacional PostgreSQL (Neon) "
        "y documental MongoDB Atlas, garantizando trazabilidad parlamentaria plena. "
        f"Observaciones integradas: {len(observaciones_finales)}  |  "
        f"Obs. CPE: {len(obs_cpe)}  |  "
        f"Obs. Normativas: {len(obs_norm)}  |  "
        f"Redundancias fusionadas: {redundancias_count}."
    )
    pdf.multi_cell(epw, 3.8, pdf.safe(cert_txt))
    pdf.ln(5)

    # Espacio para firmas formales
    if pdf.get_y() > pdf.h - 30:
        pdf.add_page()
    y_firmas = pdf.get_y()
    pdf.set_line_width(0.3)
    pdf.set_draw_color(0, 0, 0)
    pdf.line(pdf.l_margin + 10, y_firmas + 8, pdf.l_margin + 75, y_firmas + 8)
    pdf.line(pdf.l_margin + 105, y_firmas + 8, pdf.l_margin + 170, y_firmas + 8)

    pdf.set_xy(pdf.l_margin + 10, y_firmas + 9)
    pdf.f_bold(7)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(65, 3.5, pdf.safe("Agente Concentrador y Emisor"), 0, 1, 'C')
    pdf.set_x(pdf.l_margin + 10)
    pdf.f_regular(6.5)
    pdf.cell(65, 3, pdf.safe("Sistema Multiagente Legislativo SMA"), 0, 1, 'C')

    pdf.set_xy(pdf.l_margin + 105, y_firmas + 9)
    pdf.f_bold(7)
    pdf.cell(65, 3.5, pdf.safe("Consorcio de Agentes de Analisis"), 0, 1, 'C')
    pdf.set_x(pdf.l_margin + 105)
    pdf.f_regular(6.5)
    pdf.cell(65, 3, pdf.safe("Razonamiento Ampliado (CoT / Nemotron)"), 0, 1, 'C')

    if informe_profesional and informe_profesional.get('estado') != 'NO_APLICA':
        pdf.add_page()
        pdf.seccion_titulo("ANEXO: ORIENTACION PROFESIONAL COMPLEMENTARIA")
        pdf.f_regular(8)
        pdf.multi_cell(epw, 4.2, pdf.safe(
            "Este informe complementa las auditorias; sus interpretaciones no constituyen cotejos verificados.\n"
            + (informe_profesional.get('informe') or
               'Revision pendiente: ' + informe_profesional.get('error', 'Sin informe'))))
        for fuente in informe_profesional.get('fuentes', []):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(epw, 4.2, pdf.safe(
                f"[{fuente['referencia']}] {fuente['titulo']} - {fuente['archivo']}, pagina PDF {fuente['pagina']}"))

    # Guardar en disco
    pdf.output(filepath)

    with open(filepath, "rb") as f_pdf:
        pdf_bytes = f_pdf.read()
    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

    url_descarga = f"http://127.0.0.1:8085/uploaded_files/informes/{filename}"
    logger.info(f"[Concentrador] ✅ Dictamen formal PDF emitido exitosamente: {filename} ({len(pdf_bytes)} bytes)")

    # ── Subida a Google Drive (Categoría: Reportes y Dictámenes Legislativos) ──
    drive_link = ""
    drive_file_id = ""
    try:
        from sma_unified.utils.drive_uploader import upload_pdf_to_drive
        drive_res = upload_pdf_to_drive(
            file_bytes=pdf_bytes,
            filename=filename,
            categoria="reportes",
            subcarpeta=expediente_codigo,
        )
        if drive_res:
            drive_link = drive_res.get("web_view_link", "")
            drive_file_id = drive_res.get("file_id", "")
            logger.info(f"[Concentrador] 📁 Reporte formal vinculado a Google Drive: {drive_link}")
    except Exception as _e_drive:
        logger.warning(f"[Concentrador] No se pudo subir reporte a Drive (opcional): {_e_drive}")

    return {
        "filename": filename,
        "filepath": filepath,
        "url_descarga": url_descarga,
        "sha256": sha256_hash,
        "tamano_bytes": len(pdf_bytes),
        "fecha_emision": timestamp_str,
        "drive_link": drive_link,
        "drive_file_id": drive_file_id,
    }


def _persistir_en_neon(
    conn,
    id_proyecto: int,
    resumen: str,
    riesgo: str,
    t0: float,
    pdf_url: str = "",
    drive_link: str = "",
    drive_file_id: str = ""
) -> None:
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE sistema.proyecto_ley SET
                estado_actual = 'AUDITORIA_COMPLETADA',
                drive_link = COALESCE(NULLIF(%s, ''), drive_link),
                drive_file_id = COALESCE(NULLIF(%s, ''), drive_file_id),
                observaciones_generales = COALESCE(observaciones_generales,'') ||
                    E'\\n[Concentrador] Riesgo: ' || %s || ' — ' || %s ||
                    E'\\n[PDF Informe Formal]: ' || %s
            WHERE id_proyecto = %s
        """, (drive_link or None, drive_file_id or None, riesgo, resumen[:300], pdf_url, id_proyecto))
        conn.commit()
        cur.close()

        registrar_bitacora(
            id_proyecto=id_proyecto,
            agente_accion="Agente_Concentrador",
            accion_realizada="Consolidación de Expediente y Emisión de Informe Formal PDF",
            descripcion=f"Riesgo: {riesgo} | PDF: {pdf_url} | {resumen[:180]}",
            tiempo_segundos=max(1, int(time.time() - t0)),
        )
    except Exception as e:
        logger.warning(f"[Concentrador] Error en Neon: {e}")


def _persistir_en_mongo(id_proyecto: int, resultado: Dict, tiempo_ms: int) -> None:
    try:
        db = get_db()
        db["expedientes_concentrados"].insert_one({
            "id_proyecto": id_proyecto,
            "agente": "Agente_Concentrador",
            "resultado": resultado,
            "tiempo_ms": tiempo_ms,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
    except Exception as e:
        logger.warning(f"[Concentrador] Error en MongoDB: {e}")


# ── Clase Principal: Agente Concentrador y Emisor ─────────────────────────────
class AgenteConcentrador:
    """
    Agente Concentrador y Emisor — Modelo Prometheus Mejorado.
    Sintetiza de manera fidedigna los dictámenes de los Agentes de Análisis
    (Constitucionalidad y Consistencia Normativa) y adjunta un Informe Oficial
    en PDF en letra negra formal respaldado por Pensamiento Analítico Ampliado.
    """

    SYSTEM_PROMPT = (
        "Eres el editor técnico del sistema legislativo. Tu función es PRESERVAR, no crear. "
        "REGLAS ABSOLUTAS:\n"
        "1. PROHIBIDO redactar, parafrasear o corregir el articulado del proyecto.\n"
        "2. PROHIBIDO agregar observaciones no documentadas en los insumos recibidos.\n"
        "3. PROHIBIDO omitir observaciones verificadas por criterio propio.\n"
        "4. Toda 'cita_original' debe ser texto literal copiado del reporte emisor.\n"
        "5. Responde ÚNICAMENTE con JSON válido, sin texto adicional."
    )

    def __init__(self, base_agent: Optional[Any] = None):
        self.base = base_agent
        if base_agent:
            try:
                self.agent = base_agent.crear_agente("Concentrador")
            except Exception:
                self.agent = None

    def ejecutar(self, observaciones: List[Dict], proyecto_info: Dict) -> Dict:
        """
        Pipeline CoT de 7 pasos mejorado con Pensamiento Analítico Ampliado y emisión de PDF:
          1. Validación rigurosa de insumos (umbral >= 0.70).
          2. Normalización de observaciones con cita literal.
          3. Deduplicación y fusión sin pérdida de fuentes.
          4. Cálculo determinista de riesgo global.
          5. Pensamiento analítico ampliado con Nemotron-3 Super 120B (síntesis y conclusiones).
          6. Generación de informe parlamentario en PDF en letra negra.
          7. Persistencia en Neon/MongoDB y encolamiento a Presidencia de Comisión.
        """
        t0 = time.time()
        id_proyecto = int(proyecto_info.get("id") or proyecto_info.get("id_proyecto") or 0)
        titulo = proyecto_info.get("titulo") or proyecto_info.get("titulo_proyecto") or "Proyecto de Ley"
        from sma_unified.agents.reglamentos_profesionales import analizar_documento
        informe_profesional = analizar_documento(
            proyecto_info.get('texto_proyecto') or proyecto_info.get('texto_documento') or '',
            titulo=titulo, sesion_id=proyecto_info.get('sesion_id'))
        proyecto_info = {**proyecto_info, 'informe_profesional': informe_profesional}

        # ── PASO 1: VALIDACIÓN DE INSUMOS ─────────────────────────────────────
        validos = []
        no_validos = []
        for obs in (observaciones or []):
            validacion = _validar_insumo(obs)
            if not isinstance(validacion, tuple) or len(validacion) != 2:
                ok, razon = False, "El validador no devolvió el par (válido, razón)"
            else:
                ok, razon = validacion
            if ok:
                validos.append(obs)
            else:
                no_validos.append({
                    "agente_origen": obs.get("agente_origen", "desconocido") if isinstance(obs, dict) else "?",
                    "razon_exclusion": razon,
                })
                logger.warning(f"[Concentrador] Insumo excluido: {razon}")

        if not validos:
            logger.warning("[Concentrador] Sin insumos válidos — expediente no puede consolidarse")
            return {
                "informe_profesional": informe_profesional,
                "expediente_consolidado": {
                    "estado": "ERROR_INSUFICIENTE",
                    "informe_profesional": informe_profesional,
                    "insumos_no_validos": no_validos,
                    "resumen_ejecutivo": "ERROR: No hay insumos válidos para consolidar.",
                    "observaciones_integradas": [],
                    "nivel_riesgo_general": "DESCONOCIDO",
                    "estado_siguiente": "REQUIERE_REVISION_HUMANA",
                }
            }

        # ── PASO 2 + 3: INDEXACIÓN (normalizar observaciones con fuente + cita literal) ─
        todas_obs_normalizadas = []
        for v in validos:
            todas_obs_normalizadas.extend(_extraer_observaciones_de_insumo(v, start_id=len(todas_obs_normalizadas) + 1))

        # ── PASO 4: FUSIÓN DE REDUNDANCIAS ────────────────────────────────────
        obs_integradas, fusionadas = _fusionar_redundancias(todas_obs_normalizadas)

        # ── PASO 5: VERIFICACIÓN DE FIDELIDAD (confianza mínima y citas) ─────
        obs_verificadas = [o for o in obs_integradas if o.get("verificado", True)]
        obs_descartadas = [o for o in obs_integradas if not o.get("verificado", True)]

        # ── PASO 6: EVALUACIÓN CON PENSAMIENTO ANALÍTICO AMPLIADO ─────────────
        riesgo_global = _calcular_riesgo_global(obs_verificadas)
        estado_siguiente = (
            "BLOQUEADO_PARA_DEBATE" if riesgo_global == "CRÍTICO"
            else "LISTO_PARA_DEBATE"
        )

        analisis_ampliado = _analizar_con_pensamiento_ampliado_llm(
            titulo=titulo,
            id_proyecto=id_proyecto,
            riesgo_global=riesgo_global,
            obs_verificadas=obs_verificadas,
            insumos_validos=validos,
            proyecto_info=proyecto_info
        )
        analisis_ampliado["estado_auditorias"] = {
            "constitucionalidad": next((v.get("estado", "DESCONOCIDO") for v in validos
                if "constitucional" in str(v.get("agente_origen", "")).lower()), "NO_EJECUTADA"),
            "consistencia_normativa": next((v.get("estado", "DESCONOCIDO") for v in validos
                if "consistencia" in str(v.get("agente_origen", "")).lower()
                or "normat" in str(v.get("agente_origen", "")).lower()), "NO_EJECUTADA"),
            "pendientes_constitucionalidad": sum(len(v.get("pendientes_revision") or []) for v in validos
                if "constitucional" in str(v.get("agente_origen", "")).lower()),
            "pendientes_normativa": sum(len(v.get("pendientes_revision") or []) for v in validos
                if "consistencia" in str(v.get("agente_origen", "")).lower()
                or "normat" in str(v.get("agente_origen", "")).lower()),
        }
        resumen_cpe = next((v.get("resumen", {}) for v in validos
            if "constitucional" in str(v.get("agente_origen", "")).lower()), {})
        analisis_ampliado["articulos_a_favor_cpe"] = resumen_cpe.get("articulos_a_favor", [])
        analisis_ampliado["analisis_fondo_cpe"] = resumen_cpe.get("requieren_analisis_fondo", [])

        resumen_ejecutivo = analisis_ampliado.get(
            "resumen_ejecutivo",
            f"Expediente consolidado para: {titulo}. Riesgo global: {riesgo_global}."
        )

        # Formato Prometheus de observaciones
        lista_observaciones_final = [
            {
                "id": o.get("id") or f"OBS-{i+1:03d}",
                "fuente": (o.get("fuentes")[0] if isinstance(o.get("fuentes"), list) and o.get("fuentes") else o.get("fuente", "?")),
                "fuentes": o.get("fuentes", [o.get("fuente", "?")]),
                "agente_origen": (o.get("fuentes")[0] if isinstance(o.get("fuentes"), list) and o.get("fuentes") else o.get("fuente", "Agente")),
                "articulo": o.get("articulo") or o.get("articulo_afectado", "N/A"),
                "articulo_afectado": o.get("articulo_afectado") or o.get("articulo", "N/A"),
                "cita_original": o.get("cita_original", ""),
                "contenido": o.get("cita_original") or o.get("articulo_afectado", ""),
                "tipo": o.get("tipo", "OBSERVACION"),
                "riesgo": o.get("riesgo", "leve"),
                "verificado": o.get("verificado", True),
            }
            for i, o in enumerate(obs_integradas)
        ]

        bitacora_trazabilidad = [
            {
                "id": o.get("id"),
                "fuentes": o.get("fuentes"),
                "articulo": o.get("articulo"),
                "tipo": o.get("tipo"),
                "verificado": o.get("verificado"),
            }
            for o in lista_observaciones_final
        ]

        # ── PASO 7: GENERACIÓN DEL DICTAMEN OFICIAL EN PDF (LETRA NEGRA) ───────
        # Separar las observaciones por tipo de agente para las nuevas secciones
        obs_cpe_raw = [o for o in obs_verificadas
                       if "constitucional" in str(o.get("fuente", "")).lower()
                       or "constitucional" in str(o.get("agente_origen", "")).lower()]
        obs_norm_raw = [o for o in obs_verificadas
                       if "consistencia" in str(o.get("fuente", "")).lower()
                       or "consistencia" in str(o.get("agente_origen", "")).lower()
                       or "normat" in str(o.get("tipo", "")).lower()]
        try:
            pdf_info = generar_pdf_informe_concentrador(
                id_proyecto=id_proyecto,
                titulo_proyecto=titulo,
                riesgo_global=riesgo_global,
                estado_siguiente=estado_siguiente,
                analisis_dict=analisis_ampliado,
                observaciones_finales=lista_observaciones_final,
                redundancias_count=len(fusionadas),
                insumos_no_validos=no_validos,
                obs_cpe_detalle=obs_cpe_raw or None,
                obs_normativas_detalle=obs_norm_raw or None,
                informe_profesional=informe_profesional,
            )

        except Exception as e_pdf:
            logger.error(f"[Concentrador] Error generando informe PDF: {e_pdf}")
            pdf_info = {
                "error": str(e_pdf),
                "url_descarga": "",
                "filename": "",
                "filepath": ""
            }

        # ── RESULTADO FINAL CON EXPEDIENTE, RESUMEN, CONCLUSIONES Y PDF ───────
        resultado = {
            "estado": "CONSOLIDADO_COMPLETADO",
            "informe_profesional": informe_profesional,
            "consolidado": {
                "observaciones": lista_observaciones_final,
                "redundancias_fusionadas": len(fusionadas),
                "insumos_no_validos": no_validos,
            },
            "bitacora": bitacora_trazabilidad,
            "analisis_ampliado": analisis_ampliado,
            "pdf_informe": pdf_info,
            "pdf": pdf_info,
            "pdf_filename": pdf_info.get("filename", ""),
            "expediente_consolidado": {
                "informe_profesional": informe_profesional,
                "resumen_ejecutivo": resumen_ejecutivo,
                "resumen_proyecto_detallado": analisis_ampliado.get("resumen_proyecto_detallado", ""),
                "sintesis_constitucional": analisis_ampliado.get("sintesis_constitucional", ""),
                "sintesis_normativa": analisis_ampliado.get("sintesis_normativa", ""),
                "conclusiones_juridicas": analisis_ampliado.get("conclusiones_juridicas", ""),
                "recomendaciones_vinculantes": analisis_ampliado.get("recomendaciones_vinculantes", ""),
                "declaracion_metodologia": analisis_ampliado.get("declaracion_metodologia", ""),
                "observaciones_integradas": lista_observaciones_final,
                "observaciones_pendientes": lista_observaciones_final,
                "redundancias_fusionadas": len(fusionadas),
                "insumos_no_validos": no_validos,
                "obs_descartadas_baja_confianza": obs_descartadas,
                "nivel_riesgo_general": riesgo_global,
                "estado_siguiente": estado_siguiente,
                "bitacora_trazabilidad": bitacora_trazabilidad,
                "pdf_informe": pdf_info,
                "pdf": pdf_info,
                "pdf_filename": pdf_info.get("filename", ""),
            },
            "texto_proyecto_intacto": True
        }

        # ── PASO 8: PERSISTENCIA EN NEON POSTGRESQL & MONGO ATLAS ─────────────
        tiempo_ms = int((time.time() - t0) * 1000)
        conn = None
        pdf_url = pdf_info.get("url_descarga", "")
        if id_proyecto:
            try:
                conn = get_conn()
                drive_link = pdf_info.get("drive_link", "")
                drive_file_id = pdf_info.get("drive_file_id", "")
                _persistir_en_neon(
                    conn,
                    id_proyecto,
                    resumen_ejecutivo,
                    riesgo_global,
                    t0,
                    pdf_url=pdf_url,
                    drive_link=drive_link,
                    drive_file_id=drive_file_id
                )
            except Exception as e:
                logger.warning(f"[Concentrador] Neon no disponible: {e}")
            try:
                neon_client = get_neon_client()
                if hasattr(neon_client, "guardar_insumo_legislativo"):
                    neon_client.guardar_insumo_legislativo(
                        id_proyecto,
                        "EXPEDIENTE_CONSOLIDADO",
                        {"expediente_consolidado": resultado["expediente_consolidado"]},
                        "Concentrador",
                        estado_siguiente
                    )
            except Exception as e_neon:
                logger.warning(f"[Concentrador] Error guardando insumo en Neon: {e_neon}")
        _persistir_en_mongo(id_proyecto, resultado, tiempo_ms)

        # ── PASO 9: NOTIFICACIÓN FORMAL A MIEMBROS DE COMISIÓN Y ENCARGADOS ─────
        notificacion_res = None
        if proyecto_info.get("notificar_comision", True) and pdf_info.get("filename"):
            try:
                from sma_unified.agents.notificador_comision import notificar_miembros_comision
                notificacion_res = notificar_miembros_comision(
                    sesion_id=proyecto_info.get("sesion_id") or f"sesion_{id_proyecto}",
                    id_proyecto=id_proyecto,
                    datos_comision=proyecto_info.get("comision_data") or {"nombre_comision": proyecto_info.get("comision", "Comisión Legislativa Asignada")},
                    datos_constitucionales={"valido": riesgo_global != "CRÍTICO", "severidad_maxima": riesgo_global},
                    datos_consistencia={"total_hallazgos": len(lista_observaciones_final), "nivel_riesgo_global": riesgo_global},
                    pdf_filename=pdf_info.get("filename"),
                    destinatario_extra=proyecto_info.get("destinatario_extra"),
                    mensaje_extra=proyecto_info.get("mensaje_extra"),
                    asunto_personalizado=f"Dictamen Oficial Consolidado de Auditoría Legislativa — {titulo[:60]}"
                )
                resultado["notificacion_comision"] = notificacion_res
                logger.info(f"[Concentrador] ✅ Notificación formal y PDF despachados a los miembros de comisión")
            except Exception as _notif_err:
                logger.warning(f"[Concentrador] No se pudo despachar correo a comisión: {_notif_err}")
                resultado["notificacion_comision"] = {"enviado": False, "error": str(_notif_err)}

        # Enviar Mensaje a Presidencia de Comisión con enlace al PDF adjunto
        try:
            db = get_db()
            db["mensajes_sistema"].insert_one({
                "mensaje": "Proyecto Consolidado con Dictamen PDF",
                "origen": "Agente_Concentrador",
                "destino": "Agente_Presidencia_Comision",
                "id_proyecto": id_proyecto,
                "estado_siguiente": estado_siguiente,
                "nivel_riesgo_general": riesgo_global,
                "total_observaciones": len(lista_observaciones_final),
                "pdf_filename": pdf_info.get("filename", ""),
                "pdf_url": pdf_url,
                "resumen_ejecutivo": resumen_ejecutivo,
                "conclusiones": analisis_ampliado.get("conclusiones_juridicas", ""),
                "notificacion_despachada": bool(notificacion_res and notificacion_res.get("enviado")),
                "metodologia": "Agentes de Análisis Especializados con Pensamiento Ampliado",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            logger.info("[Concentrador] Notificación con PDF registrada en bitácora de mensajes")
        except Exception as m_err:
            logger.warning(f"[Concentrador] No se pudo encolar mensaje a Presidencia: {m_err}")

        logger.info(
            f"[Concentrador] ✅ Expediente, PDF formal y Notificación completados | "
            f"Obs: {len(obs_verificadas)} | Riesgo: {riesgo_global} | {tiempo_ms}ms"
        )
        return resultado


def ejecutar_concentrador_emisor_notificador(
    sesion_id: str,
    id_proyecto: Optional[int],
    datos_constitucionales: Optional[Dict[str, Any]] = None,
    datos_consistencia: Optional[Dict[str, Any]] = None,
    datos_fondo: Optional[Dict[str, Any]] = None,
    datos_comision: Optional[Dict[str, Any]] = None,
    texto_proyecto: Optional[str] = None,
    titulo_proyecto: Optional[str] = None,
    notificar: bool = True,
    destinatario_extra: Optional[str] = None,
    mensaje_extra: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de orquestación unificada para el Agente Concentrador, Emisor y Notificador.
    1. Agrupa los insumos de Constitucionalidad, Consistencia Normativa y Fondo.
    2. Ejecuta la consolidación fidedigna con Pensamiento Analítico Ampliado.
    3. Emite el Dictamen Formal Oficial en PDF con letra negra institucional.
    4. Despacha la notificación formal por correo HTML con el PDF adjunto a los encargados.
    """
    insumos = []
    if datos_constitucionales:
        pendiente_cpe = bool(datos_constitucionales.get("error") or datos_constitucionales.get("estado") == "PENDIENTE_REVISION")
        confianza_cpe = datos_constitucionales.get("confianza", 95)
        try:
            confianza_cpe = float(confianza_cpe)
            if confianza_cpe > 1:
                confianza_cpe /= 100.0
            confianza_cpe = max(0.0, min(confianza_cpe, 1.0))
        except (TypeError, ValueError):
            confianza_cpe = 0.0 if pendiente_cpe else 0.90
        insumos.append({
            "agente_origen": "Agente_Verificador_Constitucional",
            "hallazgos": datos_constitucionales.get("contradicciones", []) or datos_constitucionales.get("hallazgos", []),
            "confianza": 0 if pendiente_cpe else confianza_cpe,
            "nivel_confianza": 0 if pendiente_cpe else confianza_cpe,
            "valido": False if pendiente_cpe else datos_constitucionales.get("valido", True),
            "estado": "PENDIENTE_REVISION" if pendiente_cpe else "COMPLETADO",
            "pendientes_revision": datos_constitucionales.get("pendientes_revision", []),
            "resumen": {
                "dictamen": datos_constitucionales.get("resultado_final", ""),
                "estado": datos_constitucionales.get("estado", "COMPLETADO"),
                "riesgo": datos_constitucionales.get("nivel_riesgo_global") or
                          (datos_constitucionales.get("resumen_ejecutivo", {}).get("nivel_riesgo", "DESCONOCIDO")
                           if isinstance(datos_constitucionales.get("resumen_ejecutivo"), dict) else "DESCONOCIDO"),
                "resumen_ejecutivo": datos_constitucionales.get("resumen_ejecutivo", {}),
                "pendientes_revision": datos_constitucionales.get("pendientes_revision", []),
                "articulos_a_favor": datos_constitucionales.get("articulos_a_favor", []),
                "requieren_analisis_fondo": datos_constitucionales.get("requieren_analisis_fondo", []),
            },
        })

    if datos_consistencia:
        pendiente_normas = bool(datos_consistencia.get("error") or datos_consistencia.get("estado") == "PENDIENTE_REVISION")
        insumos.append({
            "agente_origen": "Agente_Consistencia_Normativa",
            "hallazgos": datos_consistencia.get("hallazgos", []),
            "confianza": 0 if pendiente_normas else 0.90,
            "nivel_confianza": 0 if pendiente_normas else 0.90,
            "estado": "PENDIENTE_REVISION" if pendiente_normas else "COMPLETADO",
            "pendientes_revision": datos_consistencia.get("pendientes_revision", []),
            "nivel_riesgo_global": datos_consistencia.get("nivel_riesgo_global", "OK"),
            "resumen": {
                "estado": datos_consistencia.get("estado", "COMPLETADO"),
                "nivel_riesgo_global": datos_consistencia.get("nivel_riesgo_global", "DESCONOCIDO"),
                "resumen_por_tipo": datos_consistencia.get("resumen_por_tipo", {}),
                "total_hallazgos": datos_consistencia.get("total_hallazgos", 0),
                "pendientes_revision": datos_consistencia.get("pendientes_revision", []),
            },
        })

    if datos_fondo:
        insumos.append({
            "agente_origen": "Comision_Constitucion_Fondo",
            "hallazgos": datos_fondo.get("enmiendas_de_fondo_sugeridas", []) or datos_fondo.get("hallazgos", []),
            "confianza": 0.92,
            "nivel_confianza": 0.92,
            "dictamen_fondo": datos_fondo.get("dictamen_fondo_detallado", ""),
        })

    proyecto_info = {
        "id": id_proyecto or 0,
        "id_proyecto": id_proyecto or 0,
        "titulo": titulo_proyecto or "Proyecto de Ley",
        "sesion_id": sesion_id,
        "texto_proyecto": texto_proyecto or "",
        "comision": (datos_comision or {}).get("comision_principal") or (datos_comision or {}).get("nombre_comision", "Comisión de Constitución"),
        "comision_data": datos_comision or {},
        "notificar_comision": notificar,
        "destinatario_extra": destinatario_extra,
        "mensaje_extra": mensaje_extra,
    }

    agente = AgenteConcentrador()
    return agente.ejecutar(insumos, proyecto_info)

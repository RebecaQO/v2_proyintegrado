"""
Agente Verificador de Constitucionalidad (CPE).

Recupera artículos de sistema.articulos_constitucion y coteja los candidatos
con cada párrafo del proyecto en una sola llamada estructurada a NVIDIA.
Clasifica relaciones, valida citas literales y conserva los fundamentos y
recomendaciones. Los cotejos exitosos se reutilizan durante 30 minutos;
los errores y resultados incompletos quedan pendientes y se reintentan.

Las auditorías incompletas tienen riesgo DESCONOCIDO y confianza cero tanto
en el dictamen como en su resumen. Solo se persisten correcciones cuando
se completa la evaluación. Se conservan los métodos auxiliares de análisis
individual para llamadas específicas, fuera del flujo conjunto habitual.
"""

import time
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger("verificador_constitucional")

from sma_unified.config import settings
from sma_unified.agents.llm_client import (
    chat_completion_auditoria,
    extraer_json_de_llm,
    map_con_contexto_auditoria,
)
from sma_unified.agents.embeddings_nvidia import embeber_pregunta
from sma_unified.db.mongo_atlas import (
    publicar_mensaje,
    marcar_en_proceso,
    marcar_completado,
    marcar_error,
)
from sma_unified.db.neon_postgres import (
    obtener_articulos_constitucion,
    guardar_observacion_constitucional,
    guardar_correccion_proyecto,
    obtener_email_autor_proyecto,
    ANALISIS_NEON_LOCK,
)

# ── Constantes ────────────────────────────────────────────────────────────────
TOP_K_CPE = 15  # Artículos CPE relacionados que se muestran por disposición
TOP_K_COTEJO_CPE = 15  # Cada candidato relacionado recibe cotejo y dictamen binario
UMBRAL_CPE = 0.40  # Similitud mínima (más permisivo → mayor cobertura)
MAX_CHARS_BLOQUE = 2500  # Chars máximos para embedding
MAX_TOKENS_CRIBA = 800  # Fase A: cribado rápido (JSON compacto)
MAX_TOKENS_DEEPCHECK = 900  # Fase B: deep-check con citas extendidas
MAX_TOKENS_ANALISIS = 1400  # Fase C: análisis profundo por hallazgo
MAX_CHARS_CPE_TEXTO = 800  # Texto CPE enviado al LLM (completo)
MAX_CHARS_PROYECTO = 3500  # Texto proyecto enviado al LLM
MAX_CHARS_PROYECTO_C = 2000  # Chars proyecto en Fase C (contexto focalizado)

# ── Consulta de recuperación ─────────────────────────────────────────────────
_MARCAS_FONDO = (
    "(OBJETO)",
    "ARTICULO 1.",
    "ARTÍCULO 1.",
    "EXPOSICION DE MOTIVOS",
    "EXPOSICIÓN DE MOTIVOS",
)

_RE_TITULO = re.compile(r'["“”]([^"“”]{40,400})["“”]')


def _titulo_corto(texto: str) -> str:
    """Título de la ley: el fragmento entre comillas redactado en MAYÚSCULAS.

    En los expedientes bolivianos el nombre corto va entrecomillado y en
    mayúsculas dentro del oficio de tramitación (p. ej. «LEY DE INCORPORACIÓN
    DEL TIPO PENAL …»). Es la señal de **materia** más densa del documento.
    """
    mejor = ""
    for m in _RE_TITULO.finditer(texto):
        candidato = " ".join(m.group(1).split())
        letras = [c for c in candidato if c.isalpha()]
        if len(letras) < 30:
            continue
        if sum(c.isupper() for c in letras) / len(letras) < 0.7:
            continue
        if len(candidato) > len(mejor):
            mejor = candidato
    return mejor


def _consulta_fondo(texto: str, largo: int = 700) -> str:
    """Devuelve el tramo del proyecto que describe **el fondo de la norma**.

    Antes se consultaba con ``texto[:700]``, que en un PDF escaneado es el
    membrete y el oficio de tramitación (sello, remitente, CITE, "REPOSICIÓN DE
    PROYECTO DE LEY"). Con esa consulta la búsqueda devolvía artículos de
    procedimiento parlamentario (composición de las Cámaras, trámite, recesos)
    ajenos al objeto de la ley, y el cotejo no encontraba en ellos ninguna
    disposición sobre la materia: todo quedaba como A_FAVOR provisional sin
    evidencia.

    ``obtener_articulos_constitucion`` puntúa por coincidencia de palabras y
    sólo considera las **primeras 14** no vacías, así que el orden manda: por
    eso el título (materia) va primero y la ventana del Art. 1 (que empieza por
    palabras genéricas como «objeto», «presente» o «disposiciones») después.
    """
    t = (texto or "").strip()
    if not t:
        return ""
    mayus = t.upper()
    pos = -1
    for marca in _MARCAS_FONDO:
        pos = mayus.find(marca)
        if pos >= 0:
            break
    if pos < 0:
        pos = len(t) // 3 if len(t) > largo * 3 else 0
    fondo = t[pos:pos + largo]
    titulo = _titulo_corto(t)
    if titulo:
        return titulo if len(titulo) >= 60 else f"{titulo} {fondo}"
    return fondo

# ── Prompts reutilizables ─────────────────────────────────────────────────────

_SISTEMA_CRIBA = (
    "Eres un filtro lógico determinista de constitucionalidad boliviana. "
    "Clasifica la relación entre el artículo CPE y el fragmento del proyecto de ley. "
    "NO interpretes, NO pongas, NO infieras intención. Solo texto literal.\n\n"
    "REGLA RÁPIDA (aplica la primera que coincida):\n"
    "1. ¿El proyecto PERMITE u ORDENA algo que el CPE PROHÍBE, o viceversa? → EN_CONTRA\n"
    "2. ¿El proyecto OMITE una obligación que el CPE IMPONE expresamente? → EN_CONTRA\n"
    "3. ¿El proyecto desarrolla o garantiza lo que el CPE manda? → A_FAVOR\n"
    "4. Si no hay colisión directa probada, decide A_FAVOR provisional y marca evidencia_suficiente=false.\n\n"
    "SALIDA: JSON mínimo de una línea, sin markdown; clasificación binaria obligatoria:\n"
    '{"c":"A_FAVOR|EN_CONTRA","evidencia_suficiente":true|false,"s":"bloqueante|grave|leve|ninguna","ok":true|false}'
)

_SISTEMA_DEEPCHECK = (
    "ROL: filtro lógico determinista de constitucionalidad boliviana (CPE 2009).\n"
    "FUENTE ÚNICA DE VERDAD: texto literal del artículo CPE y del proyecto. "
    "Lo que no esté copiado textualmente NO EXISTE.\n\n"
    "PROHIBICIONES ABSOLUTAS:\n"
    "- Prohibido inferir 'espíritu', 'finalidad' o 'intención' de la norma.\n"
    "- Prohibido citar artículos, incisos o frases que no estén en el input.\n"
    "- Prohibido usar conocimiento constitucional externo.\n"
    "- Prohibido emitir juicio de constitucionalidad de fondo.\n"
    "- Prohibido parafrasear citas: deben ser copia literal.\n\n"
    "ÁRBOL DE DECISIÓN (aplica en orden, la primera que coincida gana):\n"
    "1) ¿Proyecto PERMITE/ORDENA algo que CPE PROHÍBE, o viceversa? "
    "→ EN_CONTRA (bloqueante=derecho fundamental; grave=competencia/procedimiento; leve=formal)\n"
    "2) ¿Proyecto OMITE obligación que CPE IMPONE expresamente? → EN_CONTRA\n"
    "3) ¿Proyecto contradice jerarquía normativa o competencia citada en el artículo? → EN_CONTRA\n"
    "4) ¿Proyecto desarrolla, reglamenta o garantiza lo que CPE manda? → A_FAVOR\n"
    "5) Si falta prueba suficiente de colisión directa, elige A_FAVOR provisional con evidencia_suficiente=false, "
    "confianza baja y limitacion explícita. No existe clasificación neutral ni pendiente.\n\n"
    "REGLA DE VALIDACIÓN: cita literalmente las fuentes disponibles; si la respuesta no permite validar el cotejo, "
    "no inventes una colisión: usa A_FAVOR provisional, evidencia_suficiente=false y declara la limitación.\n\n"
    "SALIDA: SOLO JSON válido, sin markdown:\n"
    '{"clasificacion":"A_FAVOR|EN_CONTRA","evidencia_suficiente":true|false,"confianza":0-100,"motivo_limitacion":"...",'
    '"fundamento":"descripcion precisa <=80 palabras citando la regla aplicada (1-6)",'
    '"severidad":"bloqueante|grave|leve|ninguna",'
    '"cita_proyecto":"fragmento LITERAL del proyecto",'
    '"cita_constitucional":"fragmento LITERAL del artículo CPE",'
    '"tipo_colision":"prohibicion_vs_permiso|omision_obligacion|jerarquia|desarrollo|ponderacion|ninguna",'
    '"recomendacion":"accion concreta <=60 palabras",'
    '"verificado":true|false}'
)

_SISTEMA_ANALISIS_PROFUNDO = (
    "Eres un jurista constitucionalista boliviano de primer nivel, experto en la CPE 2009 y "
    "en el Tribunal Constitucional Plurinacional (TCP). Tu tarea es elaborar un ANÁLISIS "
    "JURÍDICO COMPLETO Y DETALLADO de la relación entre el artículo CPE indicado y el "
    "fragmento del proyecto de ley.\n\n"
    "Contexto: se te provee una clasificación binaria previa; profundiza solo sobre los hallazgos EN_CONTRA verificados. "
    "y las citas literales ya extraídas. Profundiza en los siguientes aspectos:\n\n"
    "ANÁLISIS REQUERIDO (responde TODOS los campos):\n"
    "1. impacto_juridico: ¿Qué consecuencia jurídica concreta tendría aprobar el proyecto "
    "   con esta disposición? ¿A qué sujetos afecta y cómo? (≤120 palabras)\n"
    "2. argumento_constitucional: Argumentación formal para sostener la contradicción/tensión. "
    "   Cita el tipo de norma constitucional afectada (derecho fundamental, garantía, "
    "   principio, competencia). (≤140 palabras)\n"
    "3. argumento_defensa: ¿Qué argumento podría usar el legislador para defender el "
    "   proyecto y por qué no resulta suficiente desde la perspectiva constitucional? "
    "   (≤100 palabras)\n"
    "4. articulos_cpe_relacionados: Lista solo referencias conexas provistas y verificadas en "
    "   <articulos_conexos_validados>. Si esa lista está vacía, no agregues referencias de memoria.\n"
    "5. redaccion_corregida: Texto alternativo CONCRETO que reemplazaría el fragmento "
    "   del proyecto para resolver la contradicción y cumplir la CPE. Debe ser redacción "
    "   legislativa formal boliviana. (≤120 palabras)\n"
    "6. precedentes_tcp: Cita solo precedentes TCP cuyo número y fuente verificable "
    "   se hayan proporcionado; si no, indica 'Sin precedente verificado en los insumos'. "
    "   (≤60 palabras)\n"
    "7. dictamen: Veredicto jurídico formal del artículo analizado.\n"
    "   Opciones: INCONSTITUCIONAL | CONDICIONALMENTE_CONSTITUCIONAL | "
    "   CONSTITUCIONAL | REQUIERE_CONSULTA_TCP\n"
    "8. nivel_urgencia_correccion: INMEDIATA | ANTES_DEBATE_COMISION | "
    "   ANTES_SEGUNDA_LECTURA | RECOMENDADA | NO_REQUERIDA\n\n"
    "IMPORTANTE: basa todo en los textos literales provistos. No inventes artículos ni precedentes TCP. "
    "La conclusión es preliminar y no sustituye el control de constitucionalidad del TCP.\n\n"
    "SALIDA: JSON válido con exactamente estos campos, sin markdown:\n"
    '{"impacto_juridico":"...",'
    '"argumento_constitucional":"...",'
    '"argumento_defensa":"...",'
    '"articulos_cpe_relacionados":["..."],'
    '"redaccion_corregida":"...",'
    '"precedentes_tcp":"...",'
    '"dictamen":"INCONSTITUCIONAL|CONDICIONALMENTE_CONSTITUCIONAL|CONSTITUCIONAL|REQUIERE_CONSULTA_TCP",'
    '"nivel_urgencia_correccion":"INMEDIATA|ANTES_DEBATE_COMISION|ANTES_SEGUNDA_LECTURA|RECOMENDADA|NO_REQUERIDA"}'
)

_SISTEMA_ANALISIS_AFAVOR = (
    "Eres un jurista constitucionalista boliviano de primer nivel, redactor y asesor de la Asamblea "
    "Legislativa Plurinacional, experto en la CPE 2009 y el marco jurídico boliviano. "
    "Tu tarea es elaborar una JUSTIFICACIÓN DETALLADA Y EXHAUSTIVA de por qué el proyecto de ley es "
    "CONFORME y se encuentra A FAVOR del artículo de la Constitución Política del Estado (CPE) evaluado. "
    "La evaluación es técnica preliminar; no inventes jurisprudencia TCP ni citas constitucionales.\n\n"
    "METODOLOGÍA DE EVALUACIÓN (debes evaluar PÁRRAFO POR PÁRRAFO Y ARTÍCULO POR ARTÍCULO):\n"
    "1. justificacion_por_que: Fundamentación jurídica detallada y rigurosa explicando el POR QUÉ "
    "   este artículo constitucional respalda al proyecto de ley y cómo el proyecto materializa, desarrolla "
    "   o garantiza el mandato constitucional. (120 a 180 palabras).\n"
    "2. evaluacion_detallada_articulos_parrafos: Lista estructurada de cada artículo y párrafo del proyecto de ley "
    "   que guardan consonancia con este artículo de la CPE. Para CADA fragmento identificado debes indicar:\n"
    "   - articulo_proyecto: Identificador del artículo o acápite del proyecto (ej: 'Artículo 2, Parágrafo I').\n"
    "   - texto_parrafo: Cita literal o extracto representativo del párrafo del proyecto analizado.\n"
    "   - explicacion_concordancia: Justificación minuciosa de cómo este párrafo específico ejecuta o desarrolla "
    "     el artículo de la CPE (≤60 palabras por párrafo).\n"
    "   (Incluye de 1 a 4 párrafos/artículos relevantes del proyecto).\n"
    "3. fortaleza_constitucional: 'ALTA' (cumplimiento directo y vinculante), 'MEDIA' (cumplimiento por principio o mandato general) o 'MODERADA'.\n"
    "4. principios_constitucionales_aplicados: Principios o valores de la CPE 2009 fortalecidos (ej: Vivir Bien - Suma Qamaña, "
    "   Descolonización, Soberanía, Legalidad, Debido Proceso, Igualdad y no Discriminación).\n"
    "5. articulos_cpe_conexos: Lista solo los artículos incluidos en <articulos_conexos_validados>; "
    "   si no hay, devuelve lista vacía.\n"
    "6. recomendacion_blindaje: Recomendación de técnica legislativa para robustecer aún más la solidez constitucional "
    "   del articulado y evitar cualquier ambigüedad en su aplicación futura (≤70 palabras).\n\n"
    "SALIDA: JSON válido con exactamente estos campos, sin markdown ni texto adicional:\n"
    "{\n"
    '  "justificacion_por_que": "...",\n'
    '  "evaluacion_detallada_articulos_parrafos": [\n'
    "    {\n"
    '      "articulo_proyecto": "...",\n'
    '      "texto_parrafo": "...",\n'
    '      "explicacion_concordancia": "..."\n'
    "    }\n"
    "  ],\n"
    '  "fortaleza_constitucional": "ALTA|MEDIA|MODERADA",\n'
    '  "principios_constitucionales_aplicados": ["..."],\n'
    '  "articulos_cpe_conexos": ["..."],\n'
    '  "recomendacion_blindaje": "..."\n'
    "}"
)


class VerificadorConstitucional:
    """
    Coteja un proyecto de ley contra la CPE artículo por artículo.

    Cotejo conjunto por párrafo: clasificación, fundamento y citas en una
    llamada. Valida las citas y reutiliza únicamente resultados completos.
    """

    # ── Embedding ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extraer_unidades_proyecto(texto_proyecto: str) -> List[Dict[str, str]]:
        """Separa el proyecto por artículo y, cuando están identificados, por parágrafo."""
        from sma_unified.utils.parser_normativa import parsear_articulos

        articulos: List[Dict[str, str]] = []
        encabezados = list(
            re.finditer(
                r"(?im)^\s*art[ií]culo\s+([0-9]+(?:\s*(?:bis|ter))?)\s*[°ºo]?\s*\.?\s*-?\s*(?:\([^)]+\)\s*\.?\s*)?",
                texto_proyecto or "",
            )
        )
        if encabezados:
            for indice, match in enumerate(encabezados):
                fin = (
                    encabezados[indice + 1].start()
                    if indice + 1 < len(encabezados)
                    else len(texto_proyecto)
                )
                cuerpo = texto_proyecto[match.end() : fin].strip()
                if cuerpo:
                    articulos.append(
                        {"numero": match.group(1).strip(), "texto": cuerpo}
                    )
        if not articulos:
            try:
                articulos = [
                    {
                        "numero": str(item.get("numero_articulo", "")),
                        "texto": str(item.get("texto", "")),
                    }
                    for item in parsear_articulos(texto_proyecto or "")
                    if item.get("texto")
                ]
            except Exception as exc:
                logger.warning(
                    f"[VerificadorCPE] No se pudo separar el articulado: {exc}"
                )

        if not articulos and (texto_proyecto or "").strip():
            articulos = [
                {"numero": "Documento completo", "texto": texto_proyecto.strip()}
            ]

        unidades: List[Dict[str, str]] = []
        marcador_parrafo = re.compile(
            r"(?<!\w)(?:(?:par[aá]grafo|p[aá]rrafo)\s+)?"
            r"(I{1,3}|IV|V|VI{0,3}|IX|X|[0-9]+)\s*[.)]\s+",
            re.IGNORECASE,
        )
        for articulo in articulos:
            contenido = articulo["texto"]
            # Si el artículo tiene una extensión moderada (<= 2500 caracteres),
            # se evalúa como unidad jurídica integral para preservar el contexto normativo
            # y optimizar el tiempo de auditoría.
            if len(contenido) <= 2500:
                unidades.append(
                    {
                        "articulo": articulo["numero"],
                        "parrafo": "Artículo completo",
                        "texto": contenido,
                    }
                )
                continue

            bloques = [
                bloque.strip()
                for bloque in re.split(r"\n\s*\n+", contenido)
                if bloque.strip()
            ]
            if len(bloques) == 1:
                marcas = list(marcador_parrafo.finditer(bloques[0]))
                if len(marcas) > 1 or (marcas and marcas[0].start() < 3):
                    texto = bloques[0]
                    prefijo = texto[: marcas[0].start()].strip()
                    if prefijo:
                        unidades.append(
                            {
                                "articulo": articulo["numero"],
                                "parrafo": "Párrafo introductorio",
                                "texto": prefijo,
                            }
                        )
                    for indice, marca in enumerate(marcas):
                        fin = (
                            marcas[indice + 1].start()
                            if indice + 1 < len(marcas)
                            else len(texto)
                        )
                        fragmento = texto[marca.end() : fin].strip()
                        if fragmento:
                            unidades.append(
                                {
                                    "articulo": articulo["numero"],
                                    "parrafo": f"Parágrafo {marca.group(1).upper()}",
                                    "texto": fragmento,
                                }
                            )
                    continue
            for indice, bloque in enumerate(bloques, start=1):
                unidades.append(
                    {
                        "articulo": articulo["numero"],
                        "parrafo": f"Párrafo {indice}"
                        if len(bloques) > 1
                        else "Párrafo único",
                        "texto": bloque,
                    }
                )
        return [unidad for unidad in unidades if unidad["texto"].strip()]

    def _embed(self, texto: str) -> List[float]:
        return embeber_pregunta(texto[:MAX_CHARS_BLOQUE])

    # ── Recuperación de artículos CPE ──────────────────────────────────────────

    def _recuperar_articulos_cpe(self, texto_proyecto: str) -> List[Dict[str, Any]]:
        """Búsqueda semántica con fallback por palabras clave generales."""
        try:
            # Neon usa una conexión psycopg2 compartida: proteger solo la
            # consulta permite solapar el resto del cotejo sin cruzar cursores.
            with ANALISIS_NEON_LOCK:
                articulos = obtener_articulos_constitucion(
                    texto_query=_consulta_fondo(texto_proyecto),
                    limit=TOP_K_CPE,
                )
                if not articulos:
                    articulos = obtener_articulos_constitucion(
                        texto_query="derechos garantias principios estado bolivia",
                        limit=TOP_K_CPE,
                    )
            # Deduplicación por número de artículo
            vistos: set = set()
            unicos: List[Dict] = []
            for a in articulos or []:
                num = str(a.get("numero", "")).strip()
                if num and num not in vistos:
                    vistos.add(num)
                    unicos.append(a)
            return unicos
        except Exception as e:
            logger.warning(f"Error recuperando artículos CPE: {e}")
            return []

    # ── FASE A: Cribado rápido ─────────────────────────────────────────────────

    def _solicitar_criba_json(self, usuario: str) -> Dict[str, Any]:
        """Reintenta una respuesta mal formada una vez, sin repetir fallos de red."""
        for intento in range(2):
            try:
                contenido, _ = chat_completion_auditoria(
                    messages=[
                        {"role": "system", "content": _SISTEMA_CRIBA},
                        {"role": "user", "content": usuario},
                    ],
                    temperature=0.0,
                    max_tokens=MAX_TOKENS_CRIBA * (intento + 1),
                    response_format={"type": "json_object"},
                    modelo_preferido=settings.LLM_MODEL_CONSISTENCIA,
                )
                data = extraer_json_de_llm(contenido)
                clases = {"A_FAVOR", "EN_CONTRA"}
                if (
                    not isinstance(data, dict)
                    or data.get("c") not in clases
                    or data.get("s") not in {"bloqueante", "grave", "leve", "ninguna"}
                    or not isinstance(data.get("ok"), bool)
                ):
                    raise ValueError("Criba constitucional incompleta o invalida")
                return data
            except ValueError:
                if intento == 1:
                    raise
                logger.warning(
                    "[Criba] Formato JSON invalido; reintentando una vez con mayor presupuesto de tokens"
                )

    def _cribar_relacion_cpe(
        self, texto_proyecto: str, articulo_cpe: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cribado estructurado con un reintento de formato.
        Devuelve {'clasificacion', 'severidad', 'verificado', '_fase'}.
        Todo candidato recibe una de las dos etiquetas binarias; la evidencia insuficiente se marca aparte.
        """
        num = articulo_cpe.get("numero", "")
        titulo = articulo_cpe.get("titulo", "")
        texto_cpe = articulo_cpe.get("texto", "")[:MAX_CHARS_CPE_TEXTO]

        usuario = (
            f"<cpe art='{num}' titulo='{titulo}'>\n{texto_cpe}\n</cpe>\n\n"
            f"<proyecto>\n{texto_proyecto[:1800]}\n</proyecto>\n\n"
            "Aplica la REGLA RÁPIDA. Solo JSON."
        )

        try:
            data = self._solicitar_criba_json(usuario)
            return {
                "clasificacion": data.get("c", "A_FAVOR"),
                "severidad": data.get("s", "ninguna"),
                "verificado": bool(data.get("ok", False)),
                "evidencia_suficiente": bool(data.get("evidencia_suficiente", False)),
                "_fase": "criba",
            }
        except Exception as e:
            logger.debug(
                f"[Criba] Art. {num}: pendiente por error LLM o formato JSON: {e}"
            )
            return {
                "clasificacion": "A_FAVOR",
                "severidad": "ninguna",
                "verificado": False,
                "evidencia_suficiente": False,
                "_fase": "criba_fallback",
                "motivo_limitacion": str(e),
            }

    # ── FASE B: Deep-check de candidatos ──────────────────────────────────────

    def _verificar_profundo_cpe(
        self, texto_proyecto: str, articulo_cpe: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Segunda pasada binaria con árbol de decisión, citas obligatorias y
        campo 'recomendacion'.
        """
        num = articulo_cpe.get("numero", "")
        titulo = articulo_cpe.get("titulo", "")
        texto_cpe = articulo_cpe.get("texto", "")[:MAX_CHARS_CPE_TEXTO]

        usuario = (
            f'<articulo_cpe numero="{num}" titulo="{titulo}">\n'
            f"{texto_cpe}\n"
            f"</articulo_cpe>\n\n"
            f"<proyecto_ley>\n{texto_proyecto[:MAX_CHARS_PROYECTO]}\n</proyecto_ley>\n\n"
            "TAREA: aplica el ÁRBOL DE DECISIÓN en orden. Devuelve SOLO el JSON. "
            "No afirmes EN_CONTRA sin colisión directa tipificada ni A_FAVOR sin nexo explícito y dos citas literales. "
            "La clasificación debe ser A_FAVOR o EN_CONTRA. Si no se prueba una incompatibilidad directa, usa A_FAVOR "
            "provisional con evidencia_suficiente=false, baja confianza y motivo_limitacion; nunca uses neutral ni pendiente."
        )

        try:
            from sma_unified.agents.base_agent import get_prompt_templates

            sys_yaml, _ = get_prompt_templates("Verificador_Constitucional")
            sys_prompt = sys_yaml or _SISTEMA_DEEPCHECK
        except Exception:
            sys_prompt = _SISTEMA_DEEPCHECK

        try:
            contenido, _ = chat_completion_auditoria(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": usuario},
                ],
                temperature=0.0,
                timeout=(5, 30),
                max_model_attempts=2,
                max_tokens=MAX_TOKENS_DEEPCHECK,
                modelo_preferido=settings.LLM_MODEL_CONSISTENCIA,
            )
            data = extraer_json_de_llm(contenido)
            if not isinstance(data, dict):
                raise ValueError("Respuesta constitucional invalida")
            if data.get("clasificacion") not in {"A_FAVOR", "EN_CONTRA"}:
                raise ValueError("Cotejo constitucional incompleto")
        except Exception as e:
            logger.warning(
                f"[DeepCheck] Art. {num}: cotejo pendiente por error LLM: {e}"
            )
            return {
                "clasificacion": "A_FAVOR",
                "base_decision": "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA",
                "evidencia_suficiente": False,
                "confianza": 10,
                "verificado": False,
                "motivo_limitacion": str(e),
                "fundamento": "A_FAVOR provisional: el cotejo no pudo validarse y no se acreditó una colisión directa.",
            }

        # Validación de citas: una contradicción sin cita verificable no es admisible.
        if (
            not data.get("cita_constitucional")
            and data.get("clasificacion") == "EN_CONTRA"
        ):
            logger.warning(
                f"[VerificadorCPE] Art. {num}: EN_CONTRA sin cita; degradado a A_FAVOR provisional"
            )
            data["clasificacion"] = "A_FAVOR"
            data["base_decision"] = (
                "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA"
            )
            data["evidencia_suficiente"] = False
            data["confianza"] = 10
            data["motivo_limitacion"] = (
                "No se pudo validar la cita constitucional para una contradicción."
            )

        # Normalización de clasificación
        if data.get("clasificacion") not in {"A_FAVOR", "EN_CONTRA"}:
            data["clasificacion"] = "A_FAVOR"
            data["base_decision"] = (
                "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA"
            )
            data["evidencia_suficiente"] = False
            data["confianza"] = 10
            data["motivo_limitacion"] = (
                "La salida del clasificador no pertenecía al esquema binario."
            )

        data["_fase"] = "deep_check"
        return data

    # ── FASE C: Análisis profundo por hallazgo crítico ────────────────────────

    def _analizar_impacto_profundo(
        self,
        texto_proyecto: str,
        articulo_cpe: Dict[str, Any],
        deep_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Fase C: análisis jurídico narrativo completo por cada hallazgo EN_CONTRA o RAF.
        Genera: impacto_juridico, argumento_constitucional, argumento_defensa,
        articulos_cpe_relacionados, redaccion_corregida, precedentes_tcp,
        dictamen y nivel_urgencia_correccion.
        Se ejecuta en paralelo sólo para hallazgos críticos (EN_CONTRA / RAF).
        """
        num = articulo_cpe.get("numero", "")
        titulo = articulo_cpe.get("titulo", "")
        texto_cpe = articulo_cpe.get("texto", "")[:MAX_CHARS_CPE_TEXTO]
        clasificacion = deep_result.get("clasificacion", "")
        cita_proy = deep_result.get("cita_proyecto", "") or texto_proyecto[:600]
        cita_cpe = deep_result.get("cita_constitucional", "") or texto_cpe[:400]
        fundamento = deep_result.get("fundamento", "")
        tipo_colision = deep_result.get("tipo_colision", "")

        usuario = (
            f"<contexto_previo>\n"
            f"  Clasificación Fase B: {clasificacion}\n"
            f"  Tipo de colisión: {tipo_colision}\n"
            f"  Fundamento previo: {fundamento}\n"
            f"  Criterios evaluados: {deep_result.get('evaluacion_criterios', {})}\n"
            f"  Artículos conexos validados en el lote: {deep_result.get('articulos_cpe_relacionados', [])}\n"
            f"</contexto_previo>\n\n"
            f"<articulo_cpe numero=\"{num}\" titulo=\"{titulo}\">\n"
            f"{texto_cpe}\n"
            f"</articulo_cpe>\n\n"
            f"<cita_constitucional_detectada>\n{cita_cpe}\n</cita_constitucional_detectada>\n\n"
            f"<fragmento_proyecto_afectado>\n{cita_proy}\n</fragmento_proyecto_afectado>\n\n"
            f"<articulos_conexos_validados>\n{deep_result.get('articulos_cpe_relacionados', [])}\n</articulos_conexos_validados>\n\n"
            f"<proyecto_ley_completo>\n{texto_proyecto[:MAX_CHARS_PROYECTO_C]}\n</proyecto_ley_completo>\n\n"
            "TAREA: Elabora el análisis jurídico profundo y completo. "
            "Responde TODOS los campos. Solo JSON."
        )

        try:
            contenido, _ = chat_completion_auditoria(
                messages=[
                    {"role": "system", "content": _SISTEMA_ANALISIS_PROFUNDO},
                    {"role": "user", "content": usuario},
                ],
                temperature=0.1,  # Leve creatividad para redacción corregida
                timeout=(5, 30),
                max_model_attempts=2,
                max_tokens=MAX_TOKENS_ANALISIS,
                modelo_preferido=settings.LLM_MODEL_CONSISTENCIA,
            )
            analisis = extraer_json_de_llm(contenido)
            # Garantizar que todos los campos clave existen
            analisis.setdefault("impacto_juridico", "No disponible.")
            analisis.setdefault("argumento_constitucional", "No disponible.")
            analisis.setdefault("argumento_defensa", "No disponible.")
            analisis.setdefault("articulos_cpe_relacionados", [])
            analisis.setdefault("redaccion_corregida", "No disponible.")
            analisis.setdefault("precedentes_tcp", "Sin precedente conocido.")
            analisis.setdefault("dictamen", "REQUIERE_CONSULTA_TCP")
            analisis.setdefault("nivel_urgencia_correccion", "ANTES_DEBATE_COMISION")
            analisis["articulos_cpe_relacionados"] = deep_result.get(
                "articulos_cpe_relacionados", []
            )
            logger.info(
                f"[VerificadorCPE] Fase C completada para Art. {num}: dictamen={analisis.get('dictamen','?')}"
            )
            return analisis
        except Exception as e:
            logger.warning(f"[AnálisisProfundo] Art. {num}: error LLM en Fase C: {e}")
            return {
                "pendiente_revision": True,
                "motivo": str(e),
                "impacto_juridico": "No se pudo completar el análisis profundo.",
                "argumento_constitucional": "No disponible (error en análisis).",
                "argumento_defensa": "No disponible.",
                "articulos_cpe_relacionados": [],
                "redaccion_corregida": "No disponible.",
                "precedentes_tcp": "Sin precedente conocido.",
                "dictamen": "REQUIERE_CONSULTA_TCP",
                "nivel_urgencia_correccion": "ANTES_DEBATE_COMISION",
            }

    # ── FASE C (A FAVOR): Análisis y Justificación Detallada ──────────────────

    def _analizar_afavor_profundo(
        self,
        texto_proyecto: str,
        articulo_cpe: Dict[str, Any],
        deep_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Fase C para artículos A_FAVOR:
        Genera fundamentación jurídica profunda explicando el POR QUÉ respalda a la CPE,
        con evaluación detallada PÁRRAFO POR PÁRRAFO y ARTÍCULO POR ARTÍCULO del proyecto,
        identificando citas, principios fortalecidos y recomendaciones de blindaje.
        """
        num = articulo_cpe.get("numero", "")
        titulo = articulo_cpe.get("titulo", "")
        texto_cpe = articulo_cpe.get("texto", "")[:MAX_CHARS_CPE_TEXTO]
        fundamento = deep_result.get("fundamento", "")
        cita_proy = deep_result.get("cita_proyecto", "") or ""
        cita_cpe = deep_result.get("cita_constitucional", "") or texto_cpe[:400]

        usuario = (
            f"<articulo_cpe numero=\"{num}\" titulo=\"{titulo}\">\n"
            f"{texto_cpe}\n"
            f"</articulo_cpe>\n\n"
            f"<fundamento_fase_previa>\n{fundamento}\n</fundamento_fase_previa>\n\n"
            f"<evaluacion_criterios>\n{deep_result.get('evaluacion_criterios', {})}\n</evaluacion_criterios>\n\n"
            f"<articulos_conexos_validados>\n{deep_result.get('articulos_cpe_relacionados', [])}\n</articulos_conexos_validados>\n\n"
            f"<fragmento_proyecto_detectado>\n{cita_proy}\n</fragmento_proyecto_detectado>\n\n"
            f"<proyecto_ley_completo>\n{texto_proyecto[:MAX_CHARS_PROYECTO_C]}\n</proyecto_ley_completo>\n\n"
            "TAREA: Evalúa minuciosamente el proyecto de ley frente a este artículo CPE. "
            "Justifica con detalle el POR QUÉ y desglosa la concordancia PÁRRAFO POR PÁRRAFO y ARTÍCULO POR ARTÍCULO. "
            "Responde TODOS los campos del JSON requerido, sin markdown."
        )

        try:
            contenido, _ = chat_completion_auditoria(
                messages=[
                    {"role": "system", "content": _SISTEMA_ANALISIS_AFAVOR},
                    {"role": "user", "content": usuario},
                ],
                temperature=0.1,
                timeout=(5, 30),
                max_model_attempts=2,
                max_tokens=MAX_TOKENS_ANALISIS,
                modelo_preferido=settings.LLM_MODEL_CONSISTENCIA,
            )
            analisis = extraer_json_de_llm(contenido)
            analisis.setdefault(
                "justificacion_por_que",
                fundamento
                or "El articulado del proyecto materializa y garantiza de forma directa los preceptos constitucionales evaluados.",
            )
            analisis.setdefault("evaluacion_detallada_articulos_parrafos", [])
            analisis.setdefault("fortaleza_constitucional", "ALTA")
            analisis.setdefault(
                "principios_constitucionales_aplicados",
                ["Seguridad Jurídica", "Supremacía Constitucional"],
            )
            analisis.setdefault("articulos_cpe_conexos", [])
            analisis["articulos_cpe_conexos"] = deep_result.get(
                "articulos_cpe_relacionados", []
            )
            analisis.setdefault(
                "recomendacion_blindaje",
                "Mantener concordancia explícita con las reservas de ley y competencias constitucionales.",
            )
            logger.info(
                f"[VerificadorCPE] Análisis A_FAVOR completado para Art. {num}: "
                f"{len(analisis.get('evaluacion_detallada_articulos_parrafos', []))} párrafos/artículos evaluados."
            )
            return analisis
        except Exception as e:
            logger.warning(f"[AnalisisAFavor] Art. {num}: error LLM: {e}")
            return {"pendiente_revision": True, "motivo": str(e)}

    # ── Fallback heurístico (sin LLM) ─────────────────────────────────────────

    @staticmethod
    def _fallback_heuristico(
        texto_proyecto: str, articulo_cpe: Dict[str, Any]
    ) -> Dict[str, Any]:
        num = articulo_cpe.get("numero", "")
        texto_cpe = (articulo_cpe.get("texto") or "").lower()
        proy_txt = texto_proyecto.lower()

        prohibe = any(
            p in texto_cpe
            for p in ["prohíbe", "prohibe", "impedirá", "vedado", "no se permite"]
        )
        obliga = any(
            o in proy_txt for o in ["deberá", "debera", "se obliga", "establece"]
        )
        garantiza = any(
            g in texto_cpe
            for g in [
                "derecho",
                "garantiza",
                "reconoce",
                "salud",
                "educación",
                "trabajo",
            ]
        )

        if prohibe and obliga:
            return {
                "clasificacion": "EN_CONTRA",
                "fundamento": f"Tensión detectada: CPE Art. {num} restringe lo que el proyecto ordena (heurístico).",
                "severidad": "grave",
                "cita_proyecto": texto_proyecto[:200],
                "cita_constitucional": articulo_cpe.get("texto", "")[:200],
                "recomendacion": "Revisar manualmente la colisión detectada entre el proyecto y la CPE.",
                "verificado": False,
            }
        if garantiza:
            return {
                "clasificacion": "A_FAVOR",
                "fundamento": f"El proyecto se alinea con las garantías del Art. {num} CPE (heurístico).",
                "severidad": "ninguna",
                "cita_proyecto": "",
                "cita_constitucional": articulo_cpe.get("texto", "")[:200],
                "recomendacion": "Sin acción requerida. Garantía constitucional respaldada.",
                "verificado": False,
            }
        return {
            "clasificacion": "A_FAVOR",
            "base_decision": "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA",
            "evidencia_suficiente": False,
            "confianza": 10,
            "fundamento": "A_FAVOR provisional: las reglas heurísticas no acreditaron colisión directa ni apoyo constitucional expreso.",
            "severidad": "ninguna",
            "cita_proyecto": "",
            "cita_constitucional": "",
            "recomendacion": "",
            "verificado": False,
        }

    # ── Resumen ejecutivo ─────────────────────────────────────────────────────

    @staticmethod
    def _generar_resumen_ejecutivo(
        contradicciones: List[Dict],
        a_favor: List[Dict],
        requieren_fondo: List[Dict],
        articulos_consultados: List[Dict],
    ) -> Dict[str, Any]:
        """
        Calcula nivel_riesgo, score_confianza calibrado, score_cobertura,
        matriz_riesgo por artículo y recomendaciones_globales con emojis.
        """
        # Valor seguro para cualquier ruta de cálculo; se reemplaza al calcular
        # la cobertura con el conjunto de artículos realmente consultados.
        cobertura = 0.0
        sevs = [c.get("severidad", "ninguna") for c in contradicciones]

        nivel_riesgo = (
            "BLOQUEANTE"
            if "bloqueante" in sevs
            else "ALTO"
            if "grave" in sevs
            else "MEDIO"
            if "leve" in sevs and len(contradicciones) > 0
            else "BAJO"
            if len(requieren_fondo) > 0
            else "NINGUNO"
        )

        # Cobertura CPE: % de artículos consultados con resultado conclusivo.
        total_consultados = len(articulos_consultados)
        conclusivos = len(contradicciones) + len(a_favor)
        cobertura = (
            min(100.0, round(conclusivos / total_consultados * 100, 1))
            if total_consultados
            else 0.0
        )

        # La confianza mide cobertura de cotejos con conclusión jurídica,
        # no ausencia de hallazgos. Muchos neutrales no prueban conformidad.
        score = round(40 + min(cobertura, 100) * 0.5)
        score -= sum({"bloqueante": 20, "grave": 12, "leve": 6}.get(s, 0) for s in sevs)
        score = max(0, min(score, 90))

        bloqueantes = [c for c in contradicciones if c.get("severidad") == "bloqueante"]
        graves = [c for c in contradicciones if c.get("severidad") == "grave"]
        leves = [c for c in contradicciones if c.get("severidad") == "leve"]

        recomendaciones_globales: List[str] = []
        if bloqueantes:
            recomendaciones_globales.append(
                f"⛔ DETENER TRAMITACIÓN: {len(bloqueantes)} contradicción(es) bloqueante(s) "
                "con derecho(s) fundamental(es). Corrección obligatoria antes de continuar."
            )
        if graves:
            recomendaciones_globales.append(
                f"⚠️ CORRECCIÓN PRIORITARIA: {len(graves)} contradicción(es) grave(s) de "
                "competencia/procedimiento. Subsanar antes del debate en comisión."
            )
        if leves:
            recomendaciones_globales.append(
                f"📋 AJUSTE FORMAL: {len(leves)} observación(es) leve(s). "
                "Corregir en la revisión de estilo legislativo."
            )
        if requieren_fondo:
            recomendaciones_globales.append(
                f"🔍 ANÁLISIS DE FONDO: {len(requieren_fondo)} artículo(s) CPE requieren "
                "ponderación jurídica especializada. Derivar al Tribunal Constitucional Plurinacional (TCP)."
            )
        if not contradicciones and not requieren_fondo:
            recomendaciones_globales.append(
                "No se identificó incompatibilidad directa en los pares proyecto/CPE cotejados. "
                "Resultado preliminar; no equivale a una declaración de constitucionalidad integral."
            )

        # Matriz de riesgo por artículo (para visualización en frontend)
        matriz_riesgo: List[Dict[str, Any]] = []
        for c in contradicciones:
            dictamen_fc = (c.get("analisis_profundo") or {}).get(
                "dictamen", "REQUIERE_CONSULTA_TCP"
            )
            urgencia_fc = (c.get("analisis_profundo") or {}).get(
                "nivel_urgencia_correccion", "ANTES_DEBATE_COMISION"
            )
            matriz_riesgo.append(
                {
                    "articulo_cpe": c.get("articulo_constitucional", ""),
                    "tipo": "EN_CONTRA",
                    "severidad": c.get("severidad", "leve"),
                    "dictamen": dictamen_fc,
                    "urgencia": urgencia_fc,
                    "tipo_colision": c.get("tipo_colision", ""),
                }
            )
        for r in requieren_fondo:
            dictamen_fc = (r.get("analisis_profundo") or {}).get(
                "dictamen", "REQUIERE_CONSULTA_TCP"
            )
            urgencia_fc = (r.get("analisis_profundo") or {}).get(
                "nivel_urgencia_correccion", "ANTES_DEBATE_COMISION"
            )
            matriz_riesgo.append(
                {
                    "articulo_cpe": r.get("articulo_constitucional", ""),
                    "tipo": "A_FAVOR",
                    "severidad": "medio",
                    "dictamen": dictamen_fc,
                    "urgencia": urgencia_fc,
                    "tipo_colision": r.get("tipo_colision", ""),
                }
            )
        for f in a_favor:
            analisis_af = f.get("analisis_profundo") or {}
            fortaleza = analisis_af.get("fortaleza_constitucional", "ALTA")
            matriz_riesgo.append(
                {
                    "articulo_cpe": f"Art. {f.get('numero','')} - {f.get('titulo','')}",
                    "tipo": "A_FAVOR",
                    "severidad": "ninguna",
                    "dictamen": f"CONSTITUCIONAL ({fortaleza})",
                    "urgencia": "NO_REQUERIDA",
                    "tipo_colision": f.get("tipo_colision", "desarrollo"),
                }
            )

        return {
            "nivel_riesgo": nivel_riesgo,
            "score_confianza": score,
            "score_cobertura_cpe_pct": cobertura,
            "total_consultados": total_consultados,
            "total_a_favor": len(a_favor),
            "total_contradicciones": len(contradicciones),
            "total_requieren_fondo": len(requieren_fondo),
            "distribucion_severidad": {
                "bloqueante": len(bloqueantes),
                "grave": len(graves),
                "leve": len(leves),
            },
            "recomendaciones_globales": recomendaciones_globales,
            "matriz_riesgo": matriz_riesgo,
        }

    # ── Análisis completo del documento ───────────────────────────────────────

    def analizar(
        self,
        texto_proyecto: str,
        sesion_id: str,
        id_proyecto: Optional[int] = None,
        task_id_mongo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evalúa cada unidad párrafo por párrafo contra artículos CPE relevantes."""
        unidades = self._extraer_unidades_proyecto(texto_proyecto)
        if not unidades:
            unidades = [
                {
                    "articulo": "Documento completo",
                    "parrafo": "Párrafo único",
                    "texto": texto_proyecto or "",
                }
            ]

        def _analizar_unidad_proyecto(unidad):
            parcial = self._analizar_unidad(
                unidad["texto"],
                sesion_id,
                id_proyecto=id_proyecto,
                task_id_mongo=task_id_mongo,
            )
            return unidad, parcial

        # Cada párrafo se coteja de forma independiente. Dos workers permiten
        # solapar búsqueda y preparación; el cliente LLM limita llamadas externas.
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as executor:
            parciales = map_con_contexto_auditoria(
                executor, _analizar_unidad_proyecto, unidades
            )

        contradicciones, a_favor, requieren_fondo = [], [], []
        articulos_consultados, analisis, pendientes = [], [], []
        evaluaciones_unidad, limitaciones_revision = [], []
        consultados_vistos = set()

        def numero_cpe(item):
            numero = item.get("numero")
            if numero:
                return str(numero).strip()
            texto = str(item.get("articulo_constitucional", ""))
            match = re.search(
                r"(?:Art(?:ículo)?\.?\s*)([0-9]+(?:\s*(?:bis|ter))?)",
                texto,
                re.IGNORECASE,
            )
            return match.group(1).strip() if match else ""

        for unidad, parcial in parciales:
            dictamen_unidad = parcial.get("dictamen_articulo", {})
            clasificacion_binaria_unidad = dictamen_unidad.get(
                "clasificacion", "A_FAVOR"
            )
            evaluaciones_unidad.append(
                {
                    "articulo": str(unidad.get("articulo", "Documento completo")),
                    "parrafo": str(unidad.get("parrafo", "")),
                    "texto": str(unidad.get("texto", "")),
                    **parcial.get("dictamen_articulo", {}),
                }
            )
            limitaciones_revision.extend(
                {
                    **limitacion,
                    "articulo_proyecto": f"Artículo {unidad['articulo']}",
                    "parrafo_proyecto": unidad["parrafo"],
                }
                for limitacion in parcial.get("limitaciones_revision", [])
            )
            pendientes.extend(
                {
                    **pendiente,
                    "articulo_proyecto": f"Artículo {unidad['articulo']}",
                    "parrafo_proyecto": unidad["parrafo"],
                }
                for pendiente in parcial.get("pendientes_revision", [])
            )

            relaciones = {}
            for contra in parcial.get("contradicciones", []):
                cpe_num = numero_cpe(contra)
                contra.update(
                    {
                        "articulo_proyecto": f"Artículo {unidad['articulo']}",
                        "parrafo_proyecto": unidad["parrafo"],
                        "texto_parrafo": unidad["texto"],
                        "fragmento_proyecto": contra.get("cita_proyecto")
                        or unidad["texto"],
                    }
                )
                contradicciones.append(contra)
                relaciones[cpe_num] = ("contradiccion", contra)
            for favorable in parcial.get("articulos_a_favor", []):
                cpe_num = numero_cpe(favorable)
                favorable["evaluacion_detallada_articulos_parrafos"] = [
                    {
                        "articulo_proyecto": f"Artículo {unidad['articulo']}",
                        "parrafo_proyecto": unidad["parrafo"],
                        "texto_parrafo": unidad["texto"],
                        "explicacion_concordancia": favorable.get("fundamento", ""),
                    }
                ]
                favorable.update(
                    {
                        "articulo_proyecto": f"Artículo {unidad['articulo']}",
                        "parrafo_proyecto": unidad["parrafo"],
                    }
                )
                a_favor.append(favorable)
                relaciones[cpe_num] = ("complementario", favorable)
            for pendiente_fondo in parcial.get("requieren_analisis_fondo", []):
                cpe_num = numero_cpe(pendiente_fondo)
                pendiente_fondo.update(
                    {
                        "articulo_proyecto": f"Artículo {unidad['articulo']}",
                        "parrafo_proyecto": unidad["parrafo"],
                        "texto_parrafo": unidad["texto"],
                    }
                )
                requieren_fondo.append(pendiente_fondo)
                relaciones[cpe_num] = ("requiere_analisis_de_fondo", pendiente_fondo)

            for cpe in parcial.get("articulos_consultados", []):
                cpe_num = str(cpe.get("numero", "")).strip()
                if not cpe_num:
                    continue
                if cpe_num not in consultados_vistos:
                    consultados_vistos.add(cpe_num)
                    articulos_consultados.append(
                        {
                            **cpe,
                            "norma": "CPE 2009",
                            "clasificacion": clasificacion_binaria_unidad,
                            "clasificacion_articulo_proyecto": clasificacion_binaria_unidad,
                        }
                    )
                tipo_relacion, relacionado = relaciones.get(
                    cpe_num, ("sin_relacion", cpe)
                )
                deep = relacionado.get("analisis_profundo", {}) or {}
                cita_proyecto = (
                    relacionado.get("cita_proyecto")
                    or relacionado.get("fragmento_proyecto")
                    or unidad["texto"]
                )
                cita_cpe = relacionado.get("cita_constitucional") or cpe.get(
                    "texto", cpe.get("extracto", "")
                )
                severidad = relacionado.get("severidad", "ninguna")
                riesgo = {
                    "bloqueante": "alto",
                    "grave": "alto",
                    "leve": "medio",
                    "ninguna": "ninguno",
                }.get(str(severidad).lower(), "medio")
                analisis.append(
                    {
                        "articulo_proyecto": f"Artículo {unidad['articulo']}",
                        "parrafo_proyecto": unidad["parrafo"],
                        "texto_parrafo": unidad["texto"],
                        "cita_proyecto": cita_proyecto,
                        "fragmento_proyecto": cita_proyecto,
                        "numero_articulo": cpe_num,
                        "articulo_constitucional": f"Art. {cpe_num} - {cpe.get('titulo', '')}".strip(
                            " -"
                        ),
                        "norma": "Constitución Política del Estado (CPE 2009)",
                        "cita_constitucional": cita_cpe,
                        "texto_constitucional_verificado": cita_cpe,
                        "similitud": float(cpe.get("similitud", 0) or 0),
                        "tipo_relacion": tipo_relacion,
                        "clasificacion": clasificacion_binaria_unidad,
                        "tipo_relacion_cotejo": tipo_relacion,
                        "evaluacion_criterios": relacionado.get(
                            "evaluacion_criterios", {}
                        ),
                        "analisis_constitucional": relacionado.get(
                            "analisis_constitucional", ""
                        ),
                        "comentario_analitico": relacionado.get(
                            "comentario_analitico", relacionado.get("fundamento", "")
                        ),
                        "alcance_vicio": relacionado.get("alcance_vicio", "no_aplica"),
                        "articulos_cpe_relacionados": relacionado.get(
                            "articulos_cpe_relacionados", []
                        ),
                        "verificado": bool(cpe.get("verificado", False)),
                        "estado": "COMPLETADO"
                        if cpe.get("verificado")
                        else "LIMITADO_PROVISIONAL",
                        "justificacion": relacionado.get("fundamento")
                        or relacionado.get("razon")
                        or deep.get(
                            "argumento_constitucional",
                            "Sin colisión directa detectada en este cotejo.",
                        ),
                        "sugerencia": relacionado.get("recomendacion")
                        or deep.get(
                            "redaccion_corregida",
                            "Revisar el texto con base en las citas constitucionales.",
                        ),
                        "riesgo": riesgo,
                        "severidad": severidad,
                        "tipo_colision": relacionado.get("tipo_colision", ""),
                        "analisis_profundo": deep,
                    }
                )

            for pendiente in parcial.get("pendientes_revision", []):
                cpe_num = str(pendiente.get("articulo_constitucional", "")).strip()
                cpe_label = (
                    f"Art. {cpe_num}" if cpe_num else "Artículo CPE no recuperado"
                )
                if any(
                    fila.get("articulo_proyecto") == f"Artículo {unidad['articulo']}"
                    and fila.get("parrafo_proyecto") == unidad["parrafo"]
                    and (
                        fila.get("numero_articulo") == cpe_num
                        or (
                            not cpe_num
                            and fila.get("tipo_relacion") == "pendiente_revision"
                        )
                    )
                    for fila in analisis
                ):
                    continue
                analisis.append(
                    {
                        "articulo_proyecto": f"Artículo {unidad['articulo']}",
                        "parrafo_proyecto": unidad["parrafo"],
                        "texto_parrafo": unidad["texto"],
                        "cita_proyecto": unidad["texto"],
                        "fragmento_proyecto": unidad["texto"],
                        "numero_articulo": cpe_num or "N/D",
                        "articulo_constitucional": cpe_label,
                        "norma": "Constitución Política del Estado (CPE 2009)",
                        "cita_constitucional": "Cotejo pendiente: no se pudo recuperar o validar el texto constitucional.",
                        "texto_constitucional_verificado": "",
                        "similitud": 0,
                        "tipo_relacion": "pendiente_revision",
                        "verificado": False,
                        "estado": "PENDIENTE_REVISION",
                        "motivo": pendiente.get("motivo"),
                        "justificacion": pendiente.get(
                            "motivo", "Requiere revisión manual."
                        ),
                        "sugerencia": "Reintentar el cotejo o remitirlo a revisión jurídica manual.",
                        "riesgo": "desconocido",
                        "severidad": "desconocida",
                        "tipo_colision": "",
                        "analisis_profundo": {},
                    }
                )

        # Consolidar unidades (párrafos) en un dictamen binario por artículo del proyecto.
        evaluaciones_por_articulo = {}
        for evaluacion in evaluaciones_unidad:
            clave = evaluacion["articulo"]
            grupo = evaluaciones_por_articulo.setdefault(clave, [])
            grupo.append(evaluacion)
        dictamenes_por_articulo = []
        for articulo, grupo in evaluaciones_por_articulo.items():
            en_contra = [e for e in grupo if e.get("clasificacion") == "EN_CONTRA"]
            favor = [e for e in grupo if e.get("clasificacion") == "A_FAVOR"]
            # Un conflicto directo verificado en cualquier párrafo prevalece para el artículo.
            elegido = en_contra or favor
            citas = [cita for e in elegido for cita in (e.get("citas") or [])]
            justificaciones = [
                e.get("justificacion_tecnica", "")
                for e in elegido
                if e.get("justificacion_tecnica")
            ]
            comentarios = [
                e.get("comentario_analitico", "")
                for e in elegido
                if e.get("comentario_analitico")
            ]
            sugerencias = [
                e.get("sugerencia", "") for e in elegido if e.get("sugerencia")
            ]
            hay_limitacion = any(
                not e.get("evidencia_suficiente", False) for e in grupo
            )
            if en_contra:
                base = "INCOMPATIBILIDAD_DIRECTA_VERIFICADA"
                justificacion = " ".join(justificaciones)
                suficiente = True
                confianza_art = max(
                    (float(e.get("confianza", 0) or 0) for e in en_contra), default=80
                )
            elif favor and not hay_limitacion:
                base = "COMPATIBILIDAD_CONSTITUCIONAL_IDENTIFICADA"
                justificacion = " ".join(justificaciones)
                suficiente = True
                confianza_art = min(
                    (float(e.get("confianza", 0) or 0) for e in favor), default=70
                )
            else:
                base = "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA"
                justificacion = "No se acreditó una contradicción directa con los textos constitucionales cotejados. La etiqueta A_FAVOR es provisional porque la evidencia disponible no permite afirmar apoyo constitucional expreso; consulte las limitaciones y citas recuperadas."
                suficiente = False
                confianza_art = min(
                    (float(e.get("confianza", 0) or 0) for e in grupo), default=20
                )
            relacionados_por_numero = {}
            for evaluacion in grupo:
                for relacionado in evaluacion.get("articulos_relacionados", []):
                    numero = str(relacionado.get("numero", "")).strip()
                    if numero:
                        anterior = relacionados_por_numero.get(numero)
                        if anterior is None or (
                            relacionado.get("estado_cotejo") == "COTEJADO"
                            and anterior.get("estado_cotejo") != "COTEJADO"
                        ):
                            relacionados_por_numero[numero] = relacionado
            dictamenes_por_articulo.append(
                {
                    "articulo_proyecto": articulo,
                    "clasificacion": "EN_CONTRA" if en_contra else "A_FAVOR",
                    "base_decision": base,
                    "justificacion_tecnica": justificacion
                    or "La evaluación binaria se basa en la evidencia constitucional citada; no constituye declaración vinculante del TCP.",
                    "comentario_analitico": " ".join(dict.fromkeys(comentarios))
                    or "No se acreditó colisión directa en las fuentes recuperadas; la etiqueta favorable es provisional y requiere validar la evidencia relacionada.",
                    "sugerencia": " ".join(dict.fromkeys(sugerencias))
                    or "Confirmar los artículos CPE relacionados y completar el cotejo antes de usar el dictamen como fundamento legislativo.",
                    "evidencia_suficiente": suficiente,
                    "confianza": confianza_art,
                    "parrafos_evaluados": [e["parrafo"] for e in grupo],
                    "citas": citas,
                    "articulos_relacionados": list(relacionados_por_numero.values())[
                        :TOP_K_CPE
                    ],
                    "total_articulos_relacionados": min(
                        len(relacionados_por_numero), TOP_K_CPE
                    ),
                    "limitaciones": [
                        l
                        for l in limitaciones_revision
                        if l.get("articulo_proyecto") == f"Artículo {articulo}"
                    ],
                }
            )

        resumen = self._generar_resumen_ejecutivo(
            contradicciones, a_favor, requieren_fondo, articulos_consultados
        )
        resumen_por_tipo = {}
        for fila in analisis:
            resumen_por_tipo[fila["tipo_relacion"]] = (
                resumen_por_tipo.get(fila["tipo_relacion"], 0) + 1
            )
        riesgo_global = (
            "ALTO"
            if any(fila["riesgo"] == "alto" for fila in analisis)
            else "MEDIO"
            if requieren_fondo
            or limitaciones_revision
            or any(fila["riesgo"] == "medio" for fila in analisis)
            else "NINGUNO"
        )
        resumen.update(
            {
                "nivel_riesgo": riesgo_global,
                "nivel_riesgo_global": riesgo_global,
                "score_confianza": min(resumen.get("score_confianza", 0), 35)
                if limitaciones_revision
                else resumen.get("score_confianza", 0),
                "resumen_por_tipo": resumen_por_tipo,
                "total_hallazgos": sum(
                    fila["tipo_relacion"] != "sin_relacion" for fila in analisis
                ),
                "total_parrafos_evaluados": len(unidades),
                "total_cotejos": len(analisis),
                "score_cobertura_cpe_pct": round(
                    100
                    * sum(1 for fila in analisis if fila["verificado"])
                    / max(1, len(analisis)),
                    1,
                ),
                "total_a_favor": len(a_favor),
                "total_contradicciones": len(contradicciones),
                "total_requieren_analisis_fondo": len(requieren_fondo),
                "articulos_cpe_relacionados": list(
                    {
                        str(ref.get("numero"))
                        for fila in analisis
                        for ref in fila.get("articulos_cpe_relacionados", [])
                        if isinstance(ref, dict) and ref.get("numero")
                    }
                ),
            }
        )
        if pendientes:
            resumen["score_confianza"] = 0
            for fila in analisis:
                fila["verificado"] = False

        valido = (
            not pendientes
            and not contradicciones
            and not requieren_fondo
            and not limitaciones_revision
        )
        severidad_maxima = (
            "bloqueante"
            if any(c.get("severidad") == "bloqueante" for c in contradicciones)
            else (
                "grave"
                if any(c.get("severidad") == "grave" for c in contradicciones)
                else "leve"
                if contradicciones
                else "ninguna"
            )
        )
        return {
            "estado": "PENDIENTE_REVISION" if pendientes else "COMPLETADO",
            "pendientes_revision": pendientes,
            "total_pendientes": len(pendientes),
            "resultado_final": "PENDIENTE_REVISION"
            if pendientes
            else (
                "CONTRADICCIONES_DETECTADAS"
                if contradicciones
                else "EVALUACION_BINARIA_COMPLETADA"
            ),
            "alcance_revision": "Cotejo preliminar de los artículos CPE recuperados; no sustituye el control del TCP ni acredita por sí solo la constitucionalidad integral del proyecto.",
            "valido": valido,
            "confianza": 0 if pendientes else resumen.get("score_confianza", 0),
            "severidad_maxima": severidad_maxima,
            "num_contradicciones": len(contradicciones),
            "total_a_favor": len(a_favor),
            "total_requieren_analisis_fondo": len(requieren_fondo),
            "contradicciones": contradicciones,
            "requieren_analisis_fondo": requieren_fondo,
            "articulos_a_favor": a_favor,
            "articulos_consultados": articulos_consultados,
            "analisis": analisis,
            "evaluaciones_por_articulo": dictamenes_por_articulo,
            "limitaciones_revision": limitaciones_revision,
            "total_hallazgos": resumen["total_hallazgos"],
            "total_parrafos_evaluados": len(unidades),
            "total_cotejos": len(analisis),
            "articulos_cpe_relacionados": resumen.get("articulos_cpe_relacionados", []),
            "nivel_riesgo_global": riesgo_global,
            "resumen_por_tipo": resumen_por_tipo,
            "resumen_ejecutivo": resumen,
        }

    def _analizar_unidad(
        self,
        texto_proyecto: str,
        sesion_id: str,
        id_proyecto: Optional[int] = None,
        task_id_mongo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recupera hasta 15 candidatos CPE relacionados, los coteja en lotes
        concurrentes acotados y consolida clasificación, comentarios y sugerencias.
        """
        articulos_recuperados = self._recuperar_articulos_cpe(texto_proyecto)
        articulos_cpe = articulos_recuperados[:TOP_K_COTEJO_CPE]
        if not articulos_recuperados:
            logger.warning("[VerificadorCPE] Sin artículos CPE recuperados.")

        from concurrent.futures import ThreadPoolExecutor

        # Un solo lote por disposición evita tres solicitudes paralelas de cinco
        # candidatos. El worker externo limita a dos las disposiciones concurrentes.
        from sma_unified.agents.cotejo_constitucional import (
            cotejar_lote,
            _fallback_binario,
        )

        deep_resultados = (
            cotejar_lote(
                texto_proyecto,
                articulos_cpe,
                solicitar=chat_completion_auditoria,
                parsear=extraer_json_de_llm,
            )
            if articulos_cpe
            else []
        )
        pendientes_revision = []
        if not articulos_recuperados:
            pendientes_revision.append(
                {
                    "fase": "recuperacion",
                    "motivo": "Sin artículos CPE recuperados desde la base de datos para este texto.",
                }
            )
        logger.info(
            f"[VerificadorCPE] Recuperados {len(articulos_recuperados)} artículos relacionados; cotejo profundo de {len(articulos_cpe)}"
        )

        # ── Consolidación Fase B ───────────────────────────────────────────────
        contradicciones: List[Dict[str, Any]] = []
        a_favor: List[Dict[str, Any]] = []
        requieren_fondo: List[Dict[str, Any]] = []
        articulos_consultados: List[Dict[str, Any]] = []
        vistos_consultados: set = set()

        # Guardar referencias art↔deep para Fase C
        criticos_para_fase_c: List[
            Tuple[Dict, Dict, Dict]
        ] = []  # (art, deep_result, entrada)
        afavor_para_fase_c: List[
            Tuple[Dict, Dict, Dict]
        ] = []  # (art, deep_result, entrada)

        for art, clasificacion in deep_resultados:
            if clasificacion.get("pendiente_revision"):
                # Migración segura de salidas legacy: mantener clase binaria y
                # registrar el fallo como limitación de evidencia.
                clasificacion = _fallback_binario(
                    clasificacion.get("motivo")
                    or "El cotejo anterior quedó sin validar.",
                    texto_proyecto,
                    art,
                )
            num = art.get("numero", "")
            titulo = art.get("titulo", "")
            texto_cpe = art.get("texto", "")

            if num in vistos_consultados:
                continue
            vistos_consultados.add(num)

            extracto = texto_cpe[:250] if texto_cpe else ""
            articulos_consultados.append(
                {
                    "numero": num,
                    "titulo": titulo,
                    "extracto": extracto,
                    "texto": texto_cpe,
                    "similitud": float(art.get("similitud", 0) or 0),
                }
            )

            tipo = clasificacion.get("clasificacion", "A_FAVOR")
            if tipo not in {"A_FAVOR", "EN_CONTRA"}:
                tipo = "A_FAVOR"
                clasificacion.update(
                    {
                        "base_decision": "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA",
                        "evidencia_suficiente": False,
                        "confianza": 10,
                        "motivo_limitacion": "Respuesta fuera del esquema binario; normalizada a A_FAVOR provisional.",
                    }
                )
            if not clasificacion.get("verificado") or not clasificacion.get(
                "evidencia_suficiente", False
            ):
                pendientes_revision.append(
                    {
                        "articulo_constitucional": art.get("numero"),
                        "fase": "validacion_binaria",
                        "motivo": clasificacion.get("motivo_limitacion")
                        or "Evidencia insuficiente; salida binaria provisional.",
                    }
                )
            articulos_consultados[-1].update(
                {
                    "clasificacion": tipo,
                    "fundamento": clasificacion.get("fundamento", ""),
                    "evaluacion_criterios": clasificacion.get(
                        "evaluacion_criterios", {}
                    ),
                    "analisis_constitucional": clasificacion.get(
                        "analisis_constitucional", ""
                    ),
                    "alcance_vicio": clasificacion.get("alcance_vicio", "no_aplica"),
                    "articulos_cpe_relacionados": clasificacion.get(
                        "articulos_cpe_relacionados", []
                    ),
                    "evidencia_suficiente": clasificacion.get(
                        "evidencia_suficiente", False
                    ),
                    "comentario_analitico": clasificacion.get(
                        "comentario_analitico", clasificacion.get("fundamento", "")
                    ),
                    "recomendacion": clasificacion.get(
                        "recomendacion",
                        "Revisar el cotejo con las citas constitucionales recuperadas.",
                    ),
                    "verificado": clasificacion.get("verificado", False),
                }
            )

            if tipo == "EN_CONTRA":
                if clasificacion.get("verificado", True):
                    entrada = {
                        "clasificacion": tipo,
                        "articulo_proyecto": clasificacion.get(
                            "cita_proyecto", "Documento evaluado"
                        ),
                        "articulo_constitucional": f"Art. {num} - {titulo}",
                        "cita_proyecto": clasificacion.get("cita_proyecto", ""),
                        "cita_constitucional": clasificacion.get(
                            "cita_constitucional", texto_cpe[:400]
                        ),
                        "texto_constitucional_verificado": texto_cpe[:400],
                        "fundamento": clasificacion.get("fundamento", ""),
                        "tipo_colision": clasificacion.get("tipo_colision", ""),
                        "evaluacion_criterios": clasificacion.get(
                            "evaluacion_criterios", {}
                        ),
                        "analisis_constitucional": clasificacion.get(
                            "analisis_constitucional", ""
                        ),
                        "alcance_vicio": clasificacion.get("alcance_vicio", "articulo"),
                        "articulos_cpe_relacionados": clasificacion.get(
                            "articulos_cpe_relacionados", []
                        ),
                        "severidad": clasificacion.get("severidad", "leve"),
                        "recomendacion": clasificacion.get("recomendacion", ""),
                        "verificado": clasificacion.get("verificado", True),
                        "analisis_profundo": {},  # se rellena en Fase C
                    }
                    contradicciones.append(entrada)
                    criticos_para_fase_c.append((art, clasificacion, entrada))
                else:
                    logger.info(
                        f"[VerificadorCPE] Art. {num}: EN_CONTRA no verificado — excluido."
                    )

            elif tipo == "A_FAVOR":
                if not clasificacion.get("verificado") or not clasificacion.get(
                    "evidencia_suficiente", False
                ):
                    continue
                fundamento_favor = clasificacion.get("fundamento", "")
                cita_proyecto_favor = clasificacion.get("cita_proyecto", "")
                cita_cpe_favor = clasificacion.get("cita_constitucional", "")
                entrada_af = {
                    "clasificacion": tipo,
                    "numero": num,
                    "titulo": titulo,
                    "extracto": extracto,
                    "fundamento": clasificacion.get("fundamento", ""),
                    "cita_proyecto": clasificacion.get("cita_proyecto", ""),
                    "cita_constitucional": clasificacion.get("cita_constitucional", ""),
                    "tipo_colision": clasificacion.get("tipo_colision", "desarrollo"),
                    "evaluacion_criterios": clasificacion.get(
                        "evaluacion_criterios", {}
                    ),
                    "analisis_constitucional": clasificacion.get(
                        "analisis_constitucional", ""
                    ),
                    "articulos_cpe_relacionados": clasificacion.get(
                        "articulos_cpe_relacionados", []
                    ),
                    "recomendacion": clasificacion.get("recomendacion", ""),
                    "justificacion_detallada": fundamento_favor,
                    "parrafos_evaluados": [
                        {
                            "articulo_proyecto": clasificacion.get(
                                "articulo_proyecto", "Disposición cotejada"
                            ),
                            "texto_parrafo": cita_proyecto_favor,
                            "cita_constitucional": cita_cpe_favor,
                            "explicacion_concordancia": fundamento_favor,
                        }
                    ],
                    "fortaleza_constitucional": "MEDIA",
                    "principios": [],
                    "recomendacion_blindaje": clasificacion.get("recomendacion", ""),
                    # El cotejo por lote ya aporta citas y criterios verificados;
                    # no repetir una llamada generativa por cada resultado favorable.
                    "analisis_profundo": {
                        "justificacion_por_que": fundamento_favor,
                        "argumento_constitucional": fundamento_favor,
                        "evaluacion_detallada_articulos_parrafos": [
                            {
                                "articulo_proyecto": clasificacion.get(
                                    "articulo_proyecto", "Disposición cotejada"
                                ),
                                "texto_parrafo": cita_proyecto_favor,
                                "cita_constitucional": cita_cpe_favor,
                                "explicacion_concordancia": fundamento_favor,
                            }
                        ],
                        "fortaleza_constitucional": "MEDIA",
                        "principios_constitucionales_aplicados": [],
                        "articulos_cpe_conexos": clasificacion.get(
                            "articulos_cpe_relacionados", []
                        ),
                        "recomendacion_blindaje": clasificacion.get(
                            "recomendacion", ""
                        ),
                        "metodo": "Cotejo por lote con citas literales validadas; sin segunda llamada generativa.",
                    },
                }
                a_favor.append(entrada_af)

        logger.info(
            "[VerificadorCPE] Clasificación por lote: "
            f"A_FAVOR_SUSTENTADO={sum(1 for _,r in deep_resultados if r.get('clasificacion') == 'A_FAVOR' and r.get('evidencia_suficiente') and r.get('verificado'))}, "
            f"A_FAVOR_PROVISIONAL={sum(1 for _,r in deep_resultados if r.get('clasificacion') == 'A_FAVOR' and (not r.get('evidencia_suficiente') or not r.get('verificado')))}, "
            f"EN_CONTRA_VERIFICADO={len(contradicciones)}, LIMITACIONES_EVIDENCIA={len(pendientes_revision)}"
        )

        # ── Fase C: análisis adicional solo para contradicciones/fondo ────────
        logger.info(
            f"[VerificadorCPE] Fase C: análisis profundo de {len(criticos_para_fase_c)} hallazgo(s) crítico(s); "
            f"{len(afavor_para_fase_c)} A_FAVOR requieren llamada adicional."
        )

        def _analizar_profundo_critico(triple: Tuple) -> Dict[str, Any]:
            art, deep_result, _ = triple
            return deep_result.get(
                "analisis_profundo"
            ) or self._analizar_impacto_profundo(texto_proyecto, art, deep_result)

        def _analizar_profundo_afavor(triple: Tuple) -> Dict[str, Any]:
            art, deep_result, _ = triple
            return deep_result.get("analisis_profundo") or {}

        # Ejecución concurrente Fase C
        with ThreadPoolExecutor(max_workers=2) as exe:
            futuros_criticos = (
                map_con_contexto_auditoria(
                    exe, _analizar_profundo_critico, criticos_para_fase_c
                )
                if criticos_para_fase_c
                else []
            )
            futuros_afavor = (
                map_con_contexto_auditoria(
                    exe, _analizar_profundo_afavor, afavor_para_fase_c
                )
                if afavor_para_fase_c
                else []
            )

        for (art, _, _), analisis in zip(
            criticos_para_fase_c + afavor_para_fase_c, futuros_criticos + futuros_afavor
        ):
            if analisis.get("pendiente_revision"):
                pendientes_revision.append(
                    {
                        "articulo_constitucional": art.get("numero"),
                        "fase": "analisis_profundo",
                        "motivo": analisis.get("motivo"),
                    }
                )

        # Inyectar análisis profundo en hallazgos críticos
        for i, (_, _, entrada_ref) in enumerate(criticos_para_fase_c):
            entrada_ref["analisis_profundo"] = futuros_criticos[i]

        # Compatibilidad para resultados A_FAVOR antiguos que sí usaban Fase C.
        for i, (_, _, entrada_ref) in enumerate(afavor_para_fase_c):
            af_res = futuros_afavor[i]
            entrada_ref["analisis_profundo"] = af_res
            if af_res.get("justificacion_por_que"):
                entrada_ref["justificacion_detallada"] = af_res["justificacion_por_que"]
                if len(entrada_ref.get("fundamento", "")) < 40:
                    entrada_ref["fundamento"] = af_res["justificacion_por_que"]
            if af_res.get("evaluacion_detallada_articulos_parrafos"):
                entrada_ref["parrafos_evaluados"] = af_res[
                    "evaluacion_detallada_articulos_parrafos"
                ]
            if af_res.get("fortaleza_constitucional"):
                entrada_ref["fortaleza_constitucional"] = af_res[
                    "fortaleza_constitucional"
                ]
            if af_res.get("principios_constitucionales_aplicados"):
                entrada_ref["principios"] = af_res[
                    "principios_constitucionales_aplicados"
                ]
            if af_res.get("recomendacion_blindaje"):
                entrada_ref["recomendacion_blindaje"] = af_res["recomendacion_blindaje"]

        # ── Resumen ejecutivo ─────────────────────────────────────────────────
        resumen = self._generar_resumen_ejecutivo(
            contradicciones, a_favor, requieren_fondo, articulos_consultados
        )

        # La salida por disposición siempre es binaria. Las incidencias de recuperación,
        # cotejo o análisis profundo se conservan como limitaciones, nunca como tercera etiqueta.
        limitaciones_revision = list(pendientes_revision)
        en_contra_verificado = [c for c in contradicciones if c.get("verificado", True)]
        if en_contra_verificado:
            clasificacion_articulo = "EN_CONTRA"
            base_decision = "INCOMPATIBILIDAD_DIRECTA_VERIFICADA"
            fundamento_binario = " ".join(
                c.get("fundamento", "")
                for c in en_contra_verificado
                if c.get("fundamento")
            )
            citas_binarias = [
                {
                    "norma": "CPE",
                    "articulo": c.get("articulo_constitucional", ""),
                    "texto": c.get("cita_constitucional", ""),
                    "cita_proyecto": c.get("cita_proyecto", ""),
                }
                for c in en_contra_verificado
            ]
            evidencia_suficiente = True
            confianza_binaria = 85
        elif a_favor and not limitaciones_revision and not requieren_fondo:
            clasificacion_articulo = "A_FAVOR"
            base_decision = "COMPATIBILIDAD_CONSTITUCIONAL_IDENTIFICADA"
            fundamento_binario = " ".join(
                a.get("fundamento", "") for a in a_favor if a.get("fundamento")
            )
            citas_binarias = [
                {
                    "norma": "CPE",
                    "articulo": f"Art. {a.get('numero', '')} - {a.get('titulo', '')}",
                    "texto": a.get("cita_constitucional", ""),
                    "cita_proyecto": a.get("cita_proyecto", ""),
                }
                for a in a_favor
            ]
            evidencia_suficiente = True
            confianza_binaria = 75
        else:
            clasificacion_articulo = "A_FAVOR"
            base_decision = "COMPATIBILIDAD_PROVISIONAL_SIN_INCOMPATIBILIDAD_ACREDITADA"
            fundamento_binario = "No se acreditó una contradicción directa con la evidencia CPE recuperada. Esta etiqueta A_FAVOR es provisional y no afirma apoyo constitucional expreso; la revisión queda limitada por la falta de evidencia suficiente o por cotejos que requieren ponderación."
            citas_binarias = [
                {
                    "norma": "CPE",
                    "articulo": f"Art. {a.get('numero', '')} - {a.get('titulo', '')}",
                    "texto": a.get("texto", ""),
                    "cita_proyecto": texto_proyecto,
                }
                for a in articulos_consultados
            ]
            evidencia_suficiente = False
            confianza_binaria = 20
            if requieren_fondo:
                limitaciones_revision.extend(
                    {
                        "fase": "ponderacion",
                        "motivo": r.get(
                            "razon",
                            "El cotejo requiere ponderación jurídica adicional.",
                        ),
                        "articulo_constitucional": r.get("articulo_constitucional", ""),
                    }
                    for r in requieren_fondo
                )
        cotejados_por_numero = {
            str(a.get("numero", "")): a
            for a in articulos_consultados
            if a.get("numero")
        }
        articulos_relacionados = [
            {
                "numero": str(a.get("numero", "")),
                "titulo": str(a.get("titulo", "")),
                "texto": str(a.get("texto", ""))[:1200],
                "texto_completo_disponible": len(str(a.get("texto", ""))) > 1200,
                "relevancia_busqueda": a.get("relevancia", a.get("similitud", 0)),
                "estado_cotejo": (
                    "COTEJADO"
                    if cotejados_por_numero.get(str(a.get("numero", "")), {}).get(
                        "verificado"
                    )
                    else "COTEJADO_PROVISIONAL"
                )
                if str(a.get("numero", "")) in cotejados_por_numero
                else "RELACIONADO_NO_COTEJADO",
                "clasificacion_cotejo": cotejados_por_numero.get(
                    str(a.get("numero", "")), {}
                ).get("clasificacion", "A_FAVOR"),
                "evidencia_suficiente": cotejados_por_numero.get(
                    str(a.get("numero", "")), {}
                ).get("evidencia_suficiente", False),
                "comentario_analitico": cotejados_por_numero.get(
                    str(a.get("numero", "")), {}
                ).get(
                    "comentario_analitico",
                    "Relación temática recuperada; no se pudo validar un análisis individual.",
                ),
                "sugerencia": cotejados_por_numero.get(
                    str(a.get("numero", "")), {}
                ).get("sugerencia")
                or cotejados_por_numero.get(str(a.get("numero", "")), {}).get(
                    "recomendacion",
                    "Revisar el artículo CPE junto con el texto del proyecto y confirmar su pertinencia.",
                ),
                "justificacion_tecnica": cotejados_por_numero.get(
                    str(a.get("numero", "")), {}
                ).get("fundamento", ""),
                "fundamento_relacion": (
                    "Candidato cotejado individualmente contra esta disposición."
                    if str(a.get("numero", "")) in cotejados_por_numero
                    else "Recuperado por coincidencia temática en la CPE; no hay conclusión jurídica individual validada."
                ),
            }
            for a in articulos_recuperados[:TOP_K_CPE]
        ]
        dictamen_articulo = {
            "clasificacion": clasificacion_articulo,
            "base_decision": base_decision,
            "justificacion_tecnica": fundamento_binario
            or (
                "No se acreditó una incompatibilidad directa. La clasificación favorable se limita a la compatibilidad identificada en los artículos CPE citados."
                if clasificacion_articulo == "A_FAVOR"
                else "Se verificó una colisión directa; véanse los fundamentos y citas CPE adjuntos."
            ),
            "evidencia_suficiente": evidencia_suficiente,
            "confianza": confianza_binaria,
            "citas": citas_binarias,
            "comentario_analitico": " ".join(
                e.get("comentario_analitico", "")
                for e in (en_contra_verificado or a_favor)
                if e.get("comentario_analitico")
            )
            or "No se comprobó una colisión directa con la evidencia disponible; se registra A_FAVOR provisional.",
            "sugerencia": " ".join(
                e.get("recomendacion", "")
                for e in (en_contra_verificado or a_favor)
                if e.get("recomendacion")
            )
            or "Validar los artículos CPE relacionados y completar el cotejo antes de usar esta conclusión como fundamento legislativo.",
            "articulos_relacionados": articulos_relacionados,
        }
        valido = clasificacion_articulo == "A_FAVOR" and evidencia_suficiente
        resultado_final = (
            "CONTRADICCIONES_DETECTADAS"
            if clasificacion_articulo == "EN_CONTRA"
            else "EVALUACION_BINARIA_COMPLETADA"
        )
        resumen["score_confianza"] = (
            min(resumen.get("score_confianza", 0), 35)
            if limitaciones_revision
            else resumen.get("score_confianza", 0)
        )
        dist_sev = resumen["distribucion_severidad"]
        severidad_maxima = (
            "bloqueante"
            if dist_sev["bloqueante"] > 0
            else "grave"
            if dist_sev["grave"] > 0
            else "leve"
            if dist_sev["leve"] > 0
            else "ninguna"
        )

        return {
            "estado": "COMPLETADO",
            "pendientes_revision": [],
            "total_pendientes": 0,
            "limitaciones_revision": limitaciones_revision,
            "dictamen_articulo": dictamen_articulo,
            "resultado_final": resultado_final,
            "alcance_revision": "Cotejo preliminar de los artículos CPE recuperados; no sustituye el control del TCP ni acredita por sí solo la constitucionalidad integral del proyecto.",
            "valido": valido,
            "confianza": resumen["score_confianza"],
            "severidad_maxima": severidad_maxima,
            "num_contradicciones": len(contradicciones),
            "contradicciones": contradicciones,
            "requieren_analisis_fondo": requieren_fondo,
            "articulos_a_favor": a_favor,
            "articulos_consultados": articulos_consultados,
            "resumen_ejecutivo": resumen,
        }


# ── Punto de entrada del pipeline ────────────────────────────────────────────


def verificar_constitucionalidad(
    texto_documento: str,
    sesion_id: str,
    id_proyecto: Optional[int] = None,
    task_id_distribuidor: Optional[str] = None,
    persistir: bool = True,
) -> Dict[str, Any]:
    """
    Función de entrada usada por server.py (run_agent_constitucional).
    Publica en MongoDB, ejecuta el análisis de dos fases y persiste el dictamen.
    """
    task_id = publicar_mensaje(
        agente_origen="AGENTE_SISTEMA",
        agente_destino="AGENTE_CONSTITUCIONAL",
        tipo_tarea="Verificacion de Constitucionalidad CPE",
        payload={
            "preview": texto_documento[:300],
            "task_id_dist": task_id_distribuidor,
        },
        sesion_id=sesion_id,
        metadata={"etapa": "verificacion_constitucional"},
    )
    marcar_en_proceso(task_id)
    t0 = time.time()

    try:
        agente = VerificadorConstitucional()
        resultado = agente.analizar(
            texto_documento,
            sesion_id=sesion_id,
            id_proyecto=id_proyecto,
            task_id_mongo=task_id,
        )

        if persistir and id_proyecto and not resultado.get("total_pendientes"):
            guardar_observacion_constitucional(
                sesion_id=sesion_id,
                dictamen=resultado,
                id_proyecto=id_proyecto,
                task_id_mongo=task_id,
                modelo_llm=settings.LLM_MODEL_CREW,
                duracion_ms=int((time.time() - t0) * 1000),
                articulos_consultados=resultado.get("articulos_consultados"),
            )

            # ── Correcciones automáticas por cada contradicción CPE ──────────
            contradicciones_detectadas = resultado.get("contradicciones", [])
            if contradicciones_detectadas and not resultado.get("total_pendientes"):
                email_autor = obtener_email_autor_proyecto(id_proyecto)
                for contra in contradicciones_detectadas:
                    art_cpe = contra.get("articulo_constitucional", "")
                    guardar_correccion_proyecto(
                        id_proyecto=id_proyecto,
                        tipo_corrector="SENADO_NORMATIVA",
                        agente_origen="AGENTE_VERIFICADOR_CONSTITUCIONAL",
                        articulo_afectado=contra.get("articulo_proyecto", ""),
                        texto_original=contra.get("cita_proyecto", ""),
                        motivo=contra.get("fundamento", ""),
                        referencia_cpe=art_cpe,
                        sesion_id=sesion_id,
                    )
                    if email_autor:
                        guardar_correccion_proyecto(
                            id_proyecto=id_proyecto,
                            tipo_corrector="AUTOR_PROYECTO",
                            agente_origen="AGENTE_VERIFICADOR_CONSTITUCIONAL",
                            corrector_email=email_autor,
                            articulo_afectado=contra.get("articulo_proyecto", ""),
                            texto_original=contra.get("cita_proyecto", ""),
                            motivo=contra.get("fundamento", ""),
                            referencia_cpe=art_cpe,
                            sesion_id=sesion_id,
                        )
                logger.info(
                    f"[VerificadorCPE] {len(contradicciones_detectadas)} corrección(es) "
                    f"guardadas en sistema.correcciones_proyecto para proyecto {id_proyecto}"
                )

        duracion_ms = int((time.time() - t0) * 1000)
        if resultado.get("total_pendientes"):
            marcar_error(
                task_id, "Auditoría pendiente de revisión por fallos del proveedor LLM"
            )
        else:
            marcar_completado(
                task_id,
                resultado={"valido": resultado["valido"]},
                duracion_ms=duracion_ms,
            )
        resumen_ej = resultado.get("resumen_ejecutivo", {})
        registrar = logger.warning if resultado.get("total_pendientes") else logger.info
        registrar(
            f"[VerificadorCPE] Estado={resultado.get('estado')}, pendientes={resultado.get('total_pendientes', 0)}, valido={resultado['valido']}, "
            f"riesgo={resumen_ej.get('nivel_riesgo','?')}, "
            f"confianza={resumen_ej.get('score_confianza','?')}% [{duracion_ms}ms]"
        )
        resultado["task_id_constitucional"] = task_id
        resultado["duracion_ms"] = duracion_ms
        return resultado

    except Exception as e:
        duracion_ms = int((time.time() - t0) * 1000)
        marcar_error(task_id, str(e))
        logger.error(f"Error en VerificadorConstitucional: {e}")
        return {
            "resultado_final": "ERROR",
            "valido": False,
            "confianza": 0,
            "severidad_maxima": "ninguna",
            "num_contradicciones": 0,
            "contradicciones": [],
            "articulos_a_favor": [],
            "articulos_consultados": [],
            "requieren_analisis_fondo": [],
            "resumen_ejecutivo": {
                "nivel_riesgo": "DESCONOCIDO",
                "score_confianza": 0,
                "score_cobertura_cpe_pct": 0.0,
                "recomendaciones_globales": [
                    "⚠️ Error durante el análisis. Verificar manualmente."
                ],
            },
            "task_id_constitucional": task_id,
            "duracion_ms": duracion_ms,
            "error": str(e),
        }

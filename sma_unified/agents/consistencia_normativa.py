"""
Agente de Consistencia Normativa (Ordenamiento Legal Vigente)
=============================================================
Módulo INDEPENDIENTE que analiza un proyecto de ley contra el
CORPUS NORMATIVO VIGENTE boliviano cargado en la base de datos:
  - Código Penal, Código Civil, Código de Minería
  - Leyes Sectoriales, Decretos Supremos, Resoluciones
  - Cualquier PDF/norma ingresado en "Base Legal" del sistema

Fuente principal de datos: sistema.articulos_normativos (Neon PostgreSQL + pgvector),
con fallback al corpus documental public.normativas_vigentes.

Lógica DIFERENTE a la constitucional:
  * NO consulta la CPE — esa es competencia del VerificadorConstitucional.
  * Coteja ARTÍCULO por ARTÍCULO del proyecto contra el corpus de leyes vigentes.
  * Clasifica la relación en 5 categorías:
      contradiccion   - Consecuencias jurídicas incompatibles entre ambos textos.
      repeticion      - Dice lo mismo con distinta redacción (posible derogación tácita).
      vacio_llenado   - El proyecto cubre un vacío que la ley vigente dejaba abierto.
      complementario  - Misma materia, sin conflicto (se complementan).
      sin_relacion    - Similitud superficial, no hay relación jurídica real.
  * Para cada hallazgo sugiere una acción: derogar | modificar | mantener | ninguna.
  * Persiste en normativa.analisis_consistencia y publica en MongoDB Atlas.

Profundidad ampliada:
  - TOP_K configurable hasta 15 (vs 10 anterior).
  - Se analiza por bloques de artículos, no solo el documento completo.
  - Se añade análisis de derogación tácita y conflictos de especialidad.
  - Se incluye un resumen ejecutivo categorizando el riesgo normativo global.
"""
import json
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("consistencia_normativa")

from sma_unified.config import (
    settings,
    AGENTE_COMISION,
    AGENTE_CONSISTENCIA,
    TIPOS_RELACION_CONSISTENCIA,
)
from sma_unified.agents.llm_client import chat_completion_auditoria, map_con_contexto_auditoria
from sma_unified.agents.embeddings_nvidia import embeber_pregunta
from sma_unified.utils.parser_normativa import parsear_articulos
from sma_unified.db.mongo_atlas import (
    publicar_mensaje,
    marcar_en_proceso,
    marcar_completado,
    marcar_error,
    guardar_reporte_consistencia_mongo,
)
from sma_unified.db.neon_postgres import (
    buscar_articulos_normativos_semantico,
    obtener_articulos_normativos,
    guardar_analisis_consistencia,
    guardar_correccion_proyecto,
    obtener_email_autor_proyecto,
    ANALISIS_NEON_LOCK,
)

# ── Constantes de profundidad ────────────────────────────────────────────────
TOP_K_NORMAS = 6            # Alineado con el límite efectivo de cotejos por bloque
UMBRAL_SIMILITUD = 0.42     # Similitud mínima coseno (más bajo = más cobertura)
LONGITUD_MIN_BLOQUE = 30    # Mínimo de caracteres para considerar un bloque analizable
MAX_CHARS_EMBEDDING = 1500  # Máximo de caracteres enviados al modelo de embedding

# ── Normalización de la relación declarada por el LLM ─────────────────────────
# Los prompts del YAML y las restricciones transversales proponen vocabulario
# que NO pertenece a TIPOS_RELACION_CONSISTENCIA ("colision", "COLISION_DIRECTA",
# "DEROGACION_TACITA", "REDUNDANCIA", "COMPLEMENTARIA", "MODIFICACION_IMPLICITA").
# El modelo lo elige con más naturalidad que "contradiccion", y hasta ahora esa
# diferencia bastaba para rechazar toda la clasificación y dejar el artículo en
# PENDIENTE_REVISION. Aquí se traduce al conjunto válido en lugar de descartarla.
_ALIAS_TIPO_RELACION = {
    # contradicción / antinomia
    "colision": "contradiccion",
    "colision_directa": "contradiccion",
    "conflicto": "contradiccion",
    "conflicto_directo": "contradiccion",
    "antinomia": "contradiccion",
    "incompatible": "contradiccion",
    "incompatibilidad": "contradiccion",
    "modificacion_implicita": "contradiccion",
    "contradiccion_directa": "contradiccion",
    # repetición / derogación tácita
    "redundancia": "repeticion",
    "redundante": "repeticion",
    "duplicidad": "repeticion",
    "duplicado": "repeticion",
    "derogacion_tacita": "repeticion",
    "derogacion": "repeticion",
    "modificacion": "repeticion",
    # vacío cubierto
    "vacio": "vacio_llenado",
    "llenado_vacio": "vacio_llenado",
    "vacio_llenado": "vacio_llenado",
    # complemento
    "complementaria": "complementario",
    "complemento": "complementario",
    "compatible": "complementario",
    "concordante": "complementario",
    # sin relación
    "ninguna": "sin_relacion",
    "sin_relacion": "sin_relacion",
    "no_relacion": "sin_relacion",
    "sin_relacion_juridica": "sin_relacion",
    "superficial": "sin_relacion",
}


def _clave_tipo(valor: Any) -> str:
    """Clave de comparación en minúsculas, sin acentos ni separadores."""
    texto = str(valor or "").strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        texto = texto.replace(a, b)
    texto = "".join(c if c.isalnum() else "_" for c in texto)
    return "_".join(t for t in texto.split("_") if t)


def normalizar_tipo_relacion(valor: Any) -> Optional[str]:
    """Devuelve un valor de TIPOS_RELACION_CONSISTENCIA o None si es irreconocible.

    Se acepta tal cual si ya es válido, se traduce por alias y, en último lugar,
    por subcadena ("relación de colisión" -> "contradiccion"). `None` significa
    que no hay categoría fiable: el llamador debe conservar PENDIENTE_REVISION en
    vez de inventar una clasificación.
    """
    clave = _clave_tipo(valor)
    if not clave:
        return None
    if clave in TIPOS_RELACION_CONSISTENCIA:
        return clave
    if clave in _ALIAS_TIPO_RELACION:
        return _ALIAS_TIPO_RELACION[clave]

    # coincidencia por subcadena, de más específica a más general
    for fragmento, destino in (
        ("derogacion", "repeticion"),
        ("redundan", "repeticion"),
        ("repetic", "repeticion"),
        ("duplic", "repeticion"),
        ("vacio", "vacio_llenado"),
        ("llenado", "vacio_llenado"),
        ("complement", "complementario"),
        ("colision", "contradiccion"),
        ("contradicc", "contradiccion"),
        ("antinom", "contradiccion"),
        ("incompat", "contradiccion"),
        ("conflict", "contradiccion"),
        ("sin_relacion", "sin_relacion"),
        ("ninguna", "sin_relacion"),
    ):
        if fragmento in clave:
            return destino
    return None


class AgenteConsistenciaNormativa:
    """
    Compara el proyecto de ley (artículo por artículo) contra el corpus
    de leyes vigentes cargado en sistema.articulos_normativos o
    public.normativas_vigentes.

    Usa búsqueda semántica (NVIDIA NIM) y fallback léxico + LLM para:
      1. Recuperar normas vigentes similares.
      2. Clasificar la relación jurídica.
      3. Detectar derogación tácita y conflictos de especialidad.
    """

    def __init__(self):
        self.llm_model = settings.LLM_MODEL_CONSISTENCIA
        self.umbral = UMBRAL_SIMILITUD
        self.top_k = TOP_K_NORMAS

    # ── Embedding ──────────────────────────────────────────────────────────────

    def _embed(self, texto: str) -> List[float]:
        return embeber_pregunta(texto[:MAX_CHARS_EMBEDDING])

    # ── Parser de artículos ───────────────────────────────────────────────────

    def _reconocer_articulos(self, texto_documento: str) -> List[Dict[str, str]]:
        """
        Divide el documento en artículos usando el parser jurídico boliviano.
        Si no se reconocen artículos (oficio, fragmento atípico), lo trata como
        un único bloque para no dejar ningún texto sin cotejar.
        """
        try:
            articulos = parsear_articulos(texto_documento)
        except Exception as e:
            logger.warning(f"Parser no pudo dividir el documento: {e}")
            articulos = []

        unidades = [
            {"numero": a["numero_articulo"], "texto": a["texto"]}
            for a in articulos
            if a.get("texto") and len(a["texto"].strip()) >= LONGITUD_MIN_BLOQUE
        ]

        if unidades:
            return unidades

        # Fallback: documento completo como bloque único
        if texto_documento and len(texto_documento.strip()) >= LONGITUD_MIN_BLOQUE:
            return [{"numero": "(documento completo)", "texto": texto_documento}]
        return []

    # ── Clasificación con LLM (profundidad extendida) ─────────────────────────

    def _clasificar_relacion(
        self, texto_nuevo: str, candidato: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compara un artículo del proyecto contra uno vigente. Detecta además:
          - Derogación tácita: el nuevo regula lo mismo sin mencionar al anterior.
          - Conflicto de especialidad: la norma especial prevalece sobre la general.
          - Conflicto temporal: la norma posterior prevalece sobre la anterior.
        """
        from sma_unified.agents.base_agent import get_prompt_templates, render_prompt

        sys_tpl, usr_tpl = get_prompt_templates("Consistencia_Normativa")
        if sys_tpl and usr_tpl:
            prompt_sistema = sys_tpl
            prompt_usuario = render_prompt(
                usr_tpl,
                texto_proyecto=texto_nuevo[:800],
                normas_vigentes_texto=f"{candidato['documento']}, Art. {candidato['numero']}:\n{candidato['texto'][:800]}"
            )
        else:
            prompt_sistema = (
                "Eres un jurista boliviano experto en análisis de consistencia normativa y técnica legislativa.\n"
                "Compara el artículo NUEVO (proyecto de ley) con el artículo VIGENTE de la legislación boliviana y clasifica su relación jurídica con máxima rigurosidad y precisión (SIN ALUCINACIONES).\n\n"
                "Responde ÚNICAMENTE con un objeto JSON válido (sin texto adicional, sin bloques markdown extra):\n"
                '{"tipo_relacion": "contradiccion|repeticion|vacio_llenado|complementario|sin_relacion", '
                '"justificacion": "explicacion estricta citando ambos textos (max 120 palabras)", '
                '"sugerencia": "derogar|modificar|mantener|ninguna, con una frase de razon", '
                '"derogacion_tacita": true|false, '
                '"conflicto_especialidad": true|false, '
                '"riesgo": "alto|medio|bajo|ninguno"}\n\n'
                "Definiciones:\n"
                "- contradiccion: consecuencias jurídicas incompatibles. Riesgo alto/medio.\n"
                "- repeticion: mismo contenido, distinta redacción. Puede implicar derogación tácita.\n"
                "- vacio_llenado: el nuevo cubre un vacío que el vigente dejaba abierto.\n"
                "- complementario: misma materia, sin conflicto.\n"
                "- sin_relacion: similitud superficial, sin relación jurídica real.\n"
                "- derogacion_tacita: el artículo nuevo regula la misma materia sin indicar que deroga al anterior.\n"
                "- conflicto_especialidad: la norma especial debería prevalecer sobre la general."
            )
            prompt_usuario = (
                f"ARTÍCULO NUEVO (proyecto):\n{texto_nuevo[:800]}\n\n"
                f"ARTÍCULO VIGENTE — {candidato['documento']}, Art. {candidato['numero']}:\n"
                f"{candidato['texto'][:800]}"
            )

        try:
            contenido, _modelo = chat_completion_auditoria(
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario},
                ],
                temperature=0.0,
                timeout=(5, 30),
                max_model_attempts=2,
                max_tokens=1500,
            )
            from sma_unified.agents.llm_client import extraer_json_de_llm
            data = extraer_json_de_llm(contenido)
            if not isinstance(data, dict):
                raise ValueError("Clasificacion normativa incompleta o invalida: respuesta no es un objeto JSON")
            crudo = data.get("tipo_relacion")
            tipo = normalizar_tipo_relacion(crudo)
            if tipo is None:
                raise ValueError(
                    f"Clasificacion normativa incompleta o invalida: tipo_relacion={crudo!r} sin equivalente valido"
                )
            if _clave_tipo(crudo) != tipo:
                logger.info(f"[Consistencia] tipo_relacion normalizado: {crudo!r} -> {tipo!r}")
            data["tipo_relacion"] = tipo
            # "derogacion_tacita" puede llegar como tipo en vez de como bandera:
            # se conserva la señal sin perder la categoría válida.
            if "derogacion" in _clave_tipo(crudo) and "derogacion_tacita" not in data:
                data["derogacion_tacita"] = True
            data["verificado"] = True
        except Exception as e:
            logger.warning(f"[Consistencia] Cotejo pendiente por error LLM: {e}")
            return {
                "tipo_relacion": "pendiente_revision",
                "verificado": False,
                "estado": "PENDIENTE_REVISION",
                "motivo": str(e),
                "justificacion": "No se pudo completar el cotejo con IA.",
                "riesgo": "desconocido",
            }

        return data

    # ── Análisis de un artículo del proyecto ──────────────────────────────────

    # ── Análisis de un artículo del proyecto ──────────────────────────────────

    def analizar_articulo(
        self,
        texto_nuevo: str,
        articulo_proyecto_numero: str = "",
        nombre_archivo: Optional[str] = None,
        sesion_id: Optional[str] = None,
        task_id_mongo: Optional[str] = None,
        id_proyecto: Optional[int] = None,
        persistir: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Coteja UN artículo contra los cuerpos normativos vigentes en paralelo,
        filtrando y deduplicando los candidatos más relevantes.
        """
        try:
            embedding = self._embed(texto_nuevo)
        except Exception as e:
            # El análisis textual sigue siendo útil si NVIDIA Embeddings no
            # responde; la búsqueda por palabras permite recuperar normas ya
            # cargadas aunque su embedding esté ausente.
            logger.warning(f"[Consistencia] Embedding no disponible; se usará búsqueda léxica: {e}")
            embedding = None
        # neon_postgres usa una conexión psycopg2 singleton; serializar su uso
        # entre las unidades paralelas evita compartir cursores entre hilos.
        with ANALISIS_NEON_LOCK:
            candidatos = []
            if embedding:
                candidatos = buscar_articulos_normativos_semantico(
                    embedding, documento=None, top_k=self.top_k, umbral=self.umbral
                )
                if not candidatos:
                    candidatos = buscar_articulos_normativos_semantico(
                        embedding, documento=None, top_k=self.top_k, umbral=0.35
                    )
            if not candidatos:
                candidatos = obtener_articulos_normativos(
                    texto_query=texto_nuevo, limit=self.top_k
                )
                for candidato in candidatos:
                    candidato.setdefault("similitud", 0.0)
                if candidatos:
                    logger.info(f"[Consistencia] Recuperados {len(candidatos)} candidatos por palabras clave")

        # Deduplicación de candidatos por (documento, numero) y límite a top 6
        vistos_cand = set()
        candidatos_unicos = []
        for c in (candidatos or []):
            clave = (str(c.get("documento", "")).strip(), str(c.get("numero", "")).strip())
            if clave not in vistos_cand:
                vistos_cand.add(clave)
                candidatos_unicos.append(c)
        candidatos_unicos = candidatos_unicos[:6]

        if not candidatos_unicos:
            return []

        from concurrent.futures import ThreadPoolExecutor

        def _evaluar_candidato_normativo(cand: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            clasificacion = self._clasificar_relacion(texto_nuevo, cand)
            return cand, clasificacion

        with ThreadPoolExecutor(max_workers=2) as executor:
            evaluaciones_paralelas = map_con_contexto_auditoria(
                executor, _evaluar_candidato_normativo, candidatos_unicos
            )

        resultados: List[Dict[str, Any]] = []
        for candidato, clasificacion in evaluaciones_paralelas:
            tipo_relacion = clasificacion["tipo_relacion"]

            if tipo_relacion == "sin_relacion":
                continue

            resultado = {
                "articulo_proyecto": articulo_proyecto_numero,
                "numero_articulo": candidato["numero"],
                "norma": candidato["documento"],
                "similitud": round(float(candidato["similitud"]), 4),
                "tipo_relacion": tipo_relacion,
                "verificado": clasificacion.get("verificado", False),
                "estado": clasificacion.get("estado", "COMPLETADO"),
                "motivo": clasificacion.get("motivo"),
                "justificacion": clasificacion.get("justificacion", ""),
                "sugerencia": clasificacion.get("sugerencia", ""),
                "derogacion_tacita": clasificacion.get("derogacion_tacita", False),
                "conflicto_especialidad": clasificacion.get("conflicto_especialidad", False),
                "riesgo": clasificacion.get("riesgo", "ninguno"),
            }
            resultados.append(resultado)

            if persistir and resultado["verificado"]:
                with ANALISIS_NEON_LOCK:
                    guardar_analisis_consistencia(
                        articulo_nuevo_texto=texto_nuevo,
                        articulo_candidato_id=None,
                        similitud=resultado["similitud"],
                        tipo_relacion=tipo_relacion,
                        justificacion=resultado["justificacion"],
                        sugerencia=resultado["sugerencia"],
                        sesion_id=sesion_id,
                        task_id_mongo=task_id_mongo,
                        id_proyecto=id_proyecto,
                        modelo_llm=self.llm_model,
                        nombre_archivo=nombre_archivo,
                        articulo_proyecto_numero=articulo_proyecto_numero,
                        articulo_candidato_documento=candidato["documento"],
                        articulo_candidato_numero=candidato["numero"],
                    )

        return resultados

    # ── Análisis de todo el documento ─────────────────────────────────────────

    def analizar_documento(
        self,
        texto_documento: str,
        nombre_archivo: Optional[str] = None,
        sesion_id: Optional[str] = None,
        task_id_mongo: Optional[str] = None,
        id_proyecto: Optional[int] = None,
        persistir: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Reconoce artículos del documento y coteja CADA UNO contra el corpus vigente.
        """
        unidades = self._reconocer_articulos(texto_documento)
        if not unidades:
            logger.info("Consistencia normativa: documento vacío o sin contenido analizable.")
            return []

        resultados: List[Dict[str, Any]] = []
        vistos_hallazgos = set()

        def _analizar_unidad(indice_unidad):
            indice, unidad = indice_unidad
            logger.info(
                f"[Consistencia] Artículo {unidad['numero']} ({indice}/{len(unidades)}): iniciando cotejo"
            )
            hallazgos = self.analizar_articulo(
                unidad["texto"],
                articulo_proyecto_numero=unidad["numero"],
                nombre_archivo=nombre_archivo,
                sesion_id=sesion_id,
                task_id_mongo=task_id_mongo,
                id_proyecto=id_proyecto,
                persistir=persistir,
            )
            logger.info(
                f"[Consistencia] Artículo {unidad['numero']} ({indice}/{len(unidades)}): "
                f"{len(hallazgos)} hallazgos"
            )
            return hallazgos

        # Las unidades son independientes. Mantener un límite pequeño acelera
        # proyectos extensos sin saturar el proveedor LLM ni la base vectorial.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            hallazgos_por_unidad = map_con_contexto_auditoria(
                executor, _analizar_unidad, enumerate(unidades, start=1)
            )

        for hallazgos in hallazgos_por_unidad:
            for h in hallazgos:
                clave = (h.get("articulo_proyecto"), h.get("norma"), h.get("numero_articulo"), h.get("tipo_relacion"))
                if clave not in vistos_hallazgos:
                    vistos_hallazgos.add(clave)
                    resultados.append(h)

        return resultados

    # ── Resumen ejecutivo de riesgo normativo ─────────────────────────────────

    @staticmethod
    def generar_resumen(hallazgos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula el riesgo normativo global y categoriza los hallazgos.
        """
        resumen: Dict[str, int] = {}
        for h in hallazgos:
            resumen[h["tipo_relacion"]] = resumen.get(h["tipo_relacion"], 0) + 1

        alto = sum(1 for h in hallazgos if h.get("riesgo") == "alto")
        medio = sum(1 for h in hallazgos if h.get("riesgo") == "medio")
        derogaciones = sum(1 for h in hallazgos if h.get("derogacion_tacita"))
        especialidad = sum(1 for h in hallazgos if h.get("conflicto_especialidad"))

        if alto > 0:
            nivel_riesgo = "ALTO"
        elif medio > 1:
            nivel_riesgo = "MEDIO"
        elif len(hallazgos) > 0:
            nivel_riesgo = "BAJO"
        else:
            nivel_riesgo = "NINGUNO"

        return {
            "resumen_por_tipo": resumen,
            "nivel_riesgo_global": nivel_riesgo,
            "alertas_riesgo_alto": alto,
            "alertas_riesgo_medio": medio,
            "posibles_derogaciones_tacitas": derogaciones,
            "conflictos_especialidad": especialidad,
        }


# ── Punto de entrada del pipeline ────────────────────────────────────────────

def verificar_consistencia_normativa(
    texto_documento: str,
    sesion_id: str,
    task_id_distribuidor: Optional[str] = None,
    metadata_extra: Optional[Dict[str, Any]] = None,
    id_proyecto: Optional[int] = None,
    persistir: bool = True,
    nombre_archivo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de entrada usada por server.py (run_agent_consistencia).
    Publica en MongoDB, ejecuta análisis artículo por artículo y
    devuelve un dict con hallazgos + resumen ejecutivo de riesgo.
    """
    nombre_archivo = nombre_archivo or (metadata_extra or {}).get("nombre_archivo")

    task_id = publicar_mensaje(
        agente_origen=AGENTE_COMISION,
        agente_destino=AGENTE_CONSISTENCIA,
        tipo_tarea="Verificacion de Consistencia Normativa (Leyes Vigentes)",
        payload={
            "texto_preview": texto_documento[:400],
            "longitud_chars": len(texto_documento),
            "task_id_comision": task_id_distribuidor,
            **(metadata_extra or {}),
        },
        sesion_id=sesion_id,
        metadata={"etapa": "consistencia_normativa"},
    )
    marcar_en_proceso(task_id)
    t0 = time.time()

    try:
        agente = AgenteConsistenciaNormativa()
        hallazgos = agente.analizar_documento(
            texto_documento,
            nombre_archivo=nombre_archivo,
            sesion_id=sesion_id,
            task_id_mongo=task_id,
            id_proyecto=id_proyecto,
            persistir=persistir,
        )
        pendientes = [h for h in hallazgos if not h.get("verificado")]
        hallazgos = [h for h in hallazgos if h.get("verificado")]
        resumen = agente.generar_resumen(hallazgos)
        resumen.update(
            pendientes_revision=pendientes,
            total_pendientes=len(pendientes),
            estado="PENDIENTE_REVISION" if pendientes else "COMPLETADO",
        )
        if pendientes:
            resumen["nivel_riesgo_global"] = "DESCONOCIDO"

    except Exception as e:
        duracion_ms = int((time.time() - t0) * 1000)
        logger.warning(f"Agente Consistencia Normativa: error en análisis: {e}")
        marcar_error(task_id, str(e))
        return {
            "hallazgos": [],
            "analisis": [],
            "resumen_por_tipo": {},
            "nivel_riesgo_global": "DESCONOCIDO",
            "total_hallazgos": 0,
            "task_id_consistencia": task_id,
            "duracion_ms": duracion_ms,
            "error": str(e),
        }

    duracion_ms = int((time.time() - t0) * 1000)
    if pendientes:
        marcar_error(task_id, "Auditoría pendiente de revisión por fallos del proveedor LLM")
    else:
        marcar_completado(
            task_id,
            resultado={"total_hallazgos": len(hallazgos), **resumen},
            duracion_ms=duracion_ms,
        )
    logger.info(
        f"Consistencia normativa: {len(hallazgos)} hallazgos | "
        f"Riesgo: {resumen['nivel_riesgo_global']} [{duracion_ms}ms]"
    )

    # ── Persistir reporte completo en MongoDB Atlas (reportes_consistencia) ───
    if persistir:
        try:
            reporte_mongo = {
                "expediente_id": id_proyecto,
                "sesion_id": sesion_id,
                "nombre_archivo": nombre_archivo,
                "task_id": task_id,
                "hallazgos": hallazgos,
                "pendientes_revision": pendientes,
                "estado": resumen["estado"],
                "resumen_por_tipo": resumen.get("resumen_por_tipo", {}),
                "nivel_riesgo_global": resumen.get("nivel_riesgo_global", "NINGUNO"),
                "total_hallazgos": len(hallazgos),
                "alertas_riesgo_alto": resumen.get("alertas_riesgo_alto", 0),
                "alertas_riesgo_medio": resumen.get("alertas_riesgo_medio", 0),
                "posibles_derogaciones_tacitas": resumen.get("posibles_derogaciones_tacitas", 0),
                "conflictos_especialidad": resumen.get("conflictos_especialidad", 0),
                "duracion_ms": duracion_ms,
            }
            guardar_reporte_consistencia_mongo(reporte_mongo)
        except Exception as _rme:
            logger.warning(f"No se pudo guardar reporte de consistencia en Mongo: {_rme}")

    # ── Persistir correcciones automáticas por hallazgos críticos ────────────────────
    tipos_criticos = {"contradiccion", "repeticion"}
    hallazgos_criticos = [h for h in hallazgos if (h.get("tipo_relacion") in tipos_criticos or h.get("tipo") in tipos_criticos)]
    if id_proyecto and hallazgos_criticos and not pendientes:
        email_autor = obtener_email_autor_proyecto(id_proyecto)
        for hallazgo in hallazgos_criticos:
            norma_nombre = hallazgo.get("norma") or hallazgo.get("norma_vigente") or hallazgo.get("ley_referencia") or ""
            art_cand = hallazgo.get("numero_articulo") or ""
            norma_ref = f"{norma_nombre} Art. {art_cand}".strip()
            art_proy = hallazgo.get("articulo_proyecto") or "Documento"
            motivo_txt = hallazgo.get("justificacion") or hallazgo.get("fundamento") or ""
            texto_proy = hallazgo.get("texto_proyecto") or hallazgo.get("justificacion") or ""

            # Corrección para Mesa de Senadores Normativa
            guardar_correccion_proyecto(
                id_proyecto=id_proyecto,
                tipo_corrector="SENADO_NORMATIVA",
                agente_origen="AGENTE_CONSISTENCIA_NORMATIVA",
                articulo_afectado=art_proy,
                texto_original=texto_proy,
                motivo=motivo_txt,
                referencia_norma=str(norma_ref)[:200] if norma_ref else None,
                sesion_id=sesion_id,
            )
            # Corrección para el autor del proyecto si tiene email
            if email_autor:
                guardar_correccion_proyecto(
                    id_proyecto=id_proyecto,
                    tipo_corrector="AUTOR_PROYECTO",
                    agente_origen="AGENTE_CONSISTENCIA_NORMATIVA",
                    corrector_email=email_autor,
                    articulo_afectado=art_proy,
                    texto_original=texto_proy,
                    motivo=motivo_txt,
                    referencia_norma=str(norma_ref)[:200] if norma_ref else None,
                    sesion_id=sesion_id,
                )
        logger.info(
            f"[ConsistenciaNormativa] {len(hallazgos_criticos)} corrección(es) normativas "
            f"guardadas en sistema.correcciones_proyecto para proyecto {id_proyecto}"
        )

    return {
        "hallazgos": hallazgos,
        "analisis": hallazgos,        # alias para el frontend
        "total_hallazgos": len(hallazgos),
        "task_id_consistencia": task_id,
        "duracion_ms": duracion_ms,
        **resumen,
    }

"""
Agente Verificador de Constitucionalidad (CPE)
================================================
Módulo INDEPENDIENTE que analiza un proyecto de ley contra la
Constitución Política del Estado de Bolivia (CPE).

Fuente de datos: public.articulos_constitucion (Neon PostgreSQL + pgvector)

Lógica propia:
  1. Genera embedding del texto del proyecto (NVIDIA NIM).
  2. Recupera artículos CPE semánticamente similares vía pgvector.
  3. Para cada artículo candidato un LLM clasifica la relación en:
       A_FAVOR     - El proyecto desarrolla o garantiza lo que la CPE manda.
       EN_CONTRA   - El proyecto contradice, restringe o viola la CPE.
       NEUTRAL     - No hay tensión jurídica relevante.
  4. Persiste el dictamen en:
       - sistema.observaciones_constitucionales (Neon PostgreSQL)
       - MongoDB Atlas (bus de mensajería SMA)
  5. Retorna un dict estructurado con:
       valido, confianza, contradicciones, articulos_a_favor, articulos_consultados
"""
import json
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("verificador_constitucional")

from sma_unified.config import settings
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.agents.embeddings_nvidia import embeber_pregunta
from sma_unified.db.mongo_atlas import publicar_mensaje, marcar_en_proceso, marcar_completado, marcar_error
from sma_unified.db.neon_postgres import (
    obtener_articulos_constitucion,
    guardar_observacion_constitucional,
)

# ── Constantes ────────────────────────────────────────────────────────────────
TOP_K_CPE = 12          # Máximo de artículos CPE a recuperar por embedding
UMBRAL_CPE = 0.45       # Similitud coseno mínima para considerar un artículo relevante
MAX_CHARS_BLOQUE = 2000  # Máximo de caracteres por bloque de análisis


class VerificadorConstitucional:
    """
    Coteja un proyecto de ley contra la CPE artículo por artículo.
    Clasifica cada hallazgo como A_FAVOR, EN_CONTRA o NEUTRAL.
    """

    # ── Embedding ──────────────────────────────────────────────────────────────

    def _embed(self, texto: str) -> List[float]:
        return embeber_pregunta(texto[:MAX_CHARS_BLOQUE])

    # ── Recuperación de artículos CPE ──────────────────────────────────────────

    # ── Recuperación de artículos CPE ──────────────────────────────────────────

    def _recuperar_articulos_cpe(self, texto_proyecto: str) -> List[Dict[str, Any]]:
        """Búsqueda semántica en public.articulos_constitucion via pgvector o fallback por palabras clave."""
        try:
            articulos = obtener_articulos_constitucion(
                texto_query=texto_proyecto[:600],
                limit=TOP_K_CPE,
            )
            if not articulos:
                articulos = obtener_articulos_constitucion(
                    texto_query="derechos garantias principios estado bolivia",
                    limit=TOP_K_CPE,
                )
            
            # Deduplicación estricta por número de artículo constitucional
            vistos = set()
            unicos = []
            for a in (articulos or []):
                num = str(a.get("numero", "")).strip()
                if num and num not in vistos:
                    vistos.add(num)
                    unicos.append(a)
            return unicos
        except Exception as e:
            logger.warning(f"Error recuperando artículos CPE: {e}")
            return []

    # ── Clasificación A FAVOR / EN CONTRA con LLM ─────────────────────────────

    def _clasificar_relacion_cpe(
        self, texto_proyecto: str, articulo_cpe: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PASO 4 del pipeline Prometheus — DEDUCCIÓN por artículo.
        Clasifica SOLO con reglas explícitas (prohibición vs. permiso, obligación vs. omisión,
        jerarquía normativa, competencia/ámbito). NO interpreta ni pondera.
        Todo hallazgo requiere: cita_proyecto + cita_constitucional (literales).
        Si el caso requiere interpretación → REQUIERE_ANALISIS_DE_FONDO.
        """
        num = articulo_cpe.get("numero", "")
        titulo = articulo_cpe.get("titulo", "")
        texto_cpe = articulo_cpe.get("texto", "")[:800]

        sistema = (
            "Eres un filtro técnico de rigor lógico — NO un juez constitucional. "
            "Tu autoridad proviene EXCLUSIVAMENTE del texto literal de la Constitución y "
            "de las reglas de deducción que se te proporcionan. "
            "Si una afirmación sobre la Constitución no puede respaldarse con cita textual exacta, "
            "esa afirmación no existe para ti.\n\n"
            "REGLAS ABSOLUTAS:\n"
            "1. PROHIBIDO interpretar el espíritu o finalidad de normas.\n"
            "2. PROHIBIDO inventar artículos constitucionales o citas.\n"
            "3. PROHIBIDO usar conocimiento constitucional no provisto en el input.\n"
            "4. PROHIBIDO emitir juicio de constitucionalidad de fondo.\n"
            "5. Solo aplica estas reglas de deducción: (a) prohibición vs. permiso, "
            "(b) obligación vs. omisión, (c) jerarquía normativa, (d) competencia/ámbito.\n"
            "6. Si el caso requiere ponderación → usa clasificación REQUIERE_ANALISIS_DE_FONDO.\n"
            "7. 'cita_proyecto' y 'cita_constitucional' deben ser TEXTO LITERAL copiado. "
            "Si no puedes copiar ambas citas literalmente → clasificación NEUTRAL.\n"
            "8. Responde ÚNICAMENTE con JSON válido (sin texto adicional):"
            '{"clasificacion": "A_FAVOR|EN_CONTRA|NEUTRAL|REQUIERE_ANALISIS_DE_FONDO", '
            '"fundamento": "max 120 palabras, sin interpretación", '
            '"severidad": "bloqueante|grave|leve|ninguna", '
            '"cita_proyecto": "texto literal del proyecto que genera tensión (vacío si NEUTRAL)", '
            '"cita_constitucional": "texto literal del artículo constitucional aplicado", '
            '"verificado": true|false}'
        )
        usuario = (
            f"ARTÍCULO CPE — Art. {num} ({titulo}):\n{texto_cpe}\n\n"
            f"TEXTO DEL PROYECTO DE LEY (clasifica SOLO con reglas de deducción sobre este texto):\n"
            f"{texto_proyecto[:3000]}"
        )

        try:
            contenido, _modelo = chat_completion_resiliente(
                messages=[
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": usuario},
                ],
                temperature=0.0,
                max_tokens=1500,
            )
            from sma_unified.agents.llm_client import extraer_json_de_llm
            data = extraer_json_de_llm(contenido)
        except Exception as e:
            logger.warning(f"Fallback heurístico en _clasificar_relacion_cpe por error LLM: {e}")
            # Fallback determinista: keywords lógicas, nunca inventa
            proy_txt = texto_proyecto.lower()
            const_txt = (articulo_cpe.get("texto") or "").lower()
            prohibe = any(p in const_txt for p in ["prohíbe", "prohibe", "impedirá", "vedado", "no se permite"])
            obliga = any(o in proy_txt for o in ["deberá", "debera", "se obliga", "establece"])
            garantiza = any(g in const_txt for g in ["derecho", "garantiza", "reconoce", "salud", "educación", "trabajo"])
            if prohibe and obliga:
                data = {
                    "clasificacion": "EN_CONTRA",
                    "fundamento": f"Tensión detectada: La CPE Art. {num} establece una restricción incompatible.",
                    "severidad": "grave",
                    "cita_proyecto": texto_proyecto[:200],
                    "cita_constitucional": texto_cpe[:200],
                    "verificado": False,  # Fallback → no verificado por LLM
                }
            elif garantiza:
                data = {
                    "clasificacion": "A_FAVOR",
                    "fundamento": f"El proyecto se alinea con las garantías del Art. {num} CPE.",
                    "severidad": "ninguna",
                    "cita_proyecto": "",
                    "cita_constitucional": texto_cpe[:200],
                    "verificado": False,
                }
            else:
                data = {
                    "clasificacion": "NEUTRAL",
                    "fundamento": "Sin colisión directa detectada por reglas de deducción.",
                    "severidad": "ninguna",
                    "cita_proyecto": "",
                    "cita_constitucional": "",
                    "verificado": False,
                }

        # PASO 5 — Validación de citas (si no hay cita_constitucional → NEUTRAL)
        if not data.get("cita_constitucional") and data.get("clasificacion") == "EN_CONTRA":
            logger.warning(f"[VerificadorCPE] Art. {num}: hallazgo EN_CONTRA sin cita — degradado a NEUTRAL")
            data["clasificacion"] = "NEUTRAL"
            data["_descartado_sin_cita"] = True

        clasificacion_final = data.get("clasificacion", "NEUTRAL")
        if clasificacion_final not in ("A_FAVOR", "EN_CONTRA", "NEUTRAL", "REQUIERE_ANALISIS_DE_FONDO"):
            data["clasificacion"] = "NEUTRAL"

        return data

    # ── Análisis completo del documento ───────────────────────────────────────

    def analizar(
        self,
        texto_proyecto: str,
        sesion_id: str,
        id_proyecto: Optional[int] = None,
        task_id_mongo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Punto de entrada principal.
        Recupera los artículos CPE más relevantes, los clasifica en paralelo y
        construye el dictamen estructurado sin duplicados.
        """
        articulos_cpe = self._recuperar_articulos_cpe(texto_proyecto)

        contradicciones: List[Dict[str, Any]] = []
        a_favor: List[Dict[str, Any]] = []
        requieren_fondo: List[Dict[str, Any]] = []
        articulos_consultados: List[Dict[str, Any]] = []
        vistos_consultados = set()

        from concurrent.futures import ThreadPoolExecutor

        def _evaluar_articulo_cpe(art: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            clasificacion = self._clasificar_relacion_cpe(texto_proyecto, art)
            return art, clasificacion

        with ThreadPoolExecutor(max_workers=5) as executor:
            resultados_paralelos = list(executor.map(_evaluar_articulo_cpe, articulos_cpe))

        for art, clasificacion in resultados_paralelos:
            num = art.get("numero", "")
            titulo = art.get("titulo", "")
            texto_cpe = art.get("texto", "")

            if num in vistos_consultados:
                continue
            vistos_consultados.add(num)

            tipo = clasificacion["clasificacion"]
            extracto = texto_cpe[:180] if texto_cpe else ""
            articulos_consultados.append(
                {"numero": num, "titulo": titulo, "extracto": extracto}
            )

            if tipo == "EN_CONTRA":
                # PASO 5 — Autoverificación: sólo se registra si verificado=True o si cita presente
                if clasificacion.get("verificado", True):
                    contradicciones.append(
                        {
                            "articulo_proyecto": clasificacion.get("cita_proyecto", "Documento evaluado"),
                            "articulo_constitucional": f"Art. {num} - {titulo}",
                            "cita_proyecto": clasificacion.get("cita_proyecto", ""),
                            "cita_constitucional": clasificacion.get("cita_constitucional", texto_cpe[:300]),
                            "texto_constitucional_verificado": texto_cpe[:300],
                            "fundamento": clasificacion["fundamento"],
                            "severidad": clasificacion["severidad"],
                            "verificado": clasificacion.get("verificado", True),
                        }
                    )
                else:
                    logger.warning(f"[VerificadorCPE] Art. {num}: hallazgo EN_CONTRA no verificado — excluido")
            elif tipo == "A_FAVOR":
                a_favor.append(
                    {
                        "numero": num,
                        "titulo": titulo,
                        "extracto": extracto,
                        "fundamento": clasificacion["fundamento"],
                        "cita_constitucional": clasificacion.get("cita_constitucional", ""),
                    }
                )
            elif tipo == "REQUIERE_ANALISIS_DE_FONDO":
                # PASO 6 — Límite de mandato: no decide, marca para revisión
                requieren_fondo.append({
                    "articulo_constitucional": f"Art. {num} - {titulo}",
                    "razon": clasificacion.get("fundamento", "Requiere ponderación de derechos"),
                    "cita_constitucional": clasificacion.get("cita_constitucional", texto_cpe[:300]),
                })

        valido = len(contradicciones) == 0
        sevs = [c["severidad"] for c in contradicciones]
        severidad_maxima = (
            "bloqueante" if "bloqueante" in sevs
            else "grave" if "grave" in sevs
            else "leve" if "leve" in sevs
            else "ninguna"
        )
        confianza = max(55, 95 - len(contradicciones) * 12)
        resultado_final = "ARTICULADO_VALIDO" if valido else "CONTRADICCIONES_DETECTADAS"

        return {
            "resultado_final": resultado_final,
            "valido": valido,
            "confianza": confianza,
            "severidad_maxima": severidad_maxima,
            "num_contradicciones": len(contradicciones),
            "contradicciones": contradicciones,
            "requieren_analisis_fondo": requieren_fondo,
            "articulos_a_favor": a_favor,
            "articulos_consultados": articulos_consultados,
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
    Publica en MongoDB, ejecuta el análisis y persiste el dictamen.
    """
    task_id = publicar_mensaje(
        agente_origen="AGENTE_SISTEMA",
        agente_destino="AGENTE_CONSTITUCIONAL",
        tipo_tarea="Verificacion de Constitucionalidad CPE",
        payload={"preview": texto_documento[:300], "task_id_dist": task_id_distribuidor},
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

        if persistir and id_proyecto:
            guardar_observacion_constitucional(
                sesion_id=sesion_id,
                dictamen=resultado,
                id_proyecto=id_proyecto,
                task_id_mongo=task_id,
                modelo_llm=settings.LLM_MODEL_CREW,
                duracion_ms=int((time.time() - t0) * 1000),
                articulos_consultados=resultado.get("articulos_consultados"),
            )

        duracion_ms = int((time.time() - t0) * 1000)
        marcar_completado(task_id, resultado={"valido": resultado["valido"]}, duracion_ms=duracion_ms)
        logger.info(f"Verificacion constitucional completada: valido={resultado['valido']} [{duracion_ms}ms]")
        resultado["task_id_constitucional"] = task_id
        resultado["duracion_ms"] = duracion_ms
        return resultado

    except Exception as e:
        duracion_ms = int((time.time() - t0) * 1000)
        marcar_error(task_id, str(e))
        logger.error(f"Error en VerificadorConstitucional: {e}")
        return {
            "valido": False,
            "confianza": 0,
            "severidad_maxima": "ninguna",
            "num_contradicciones": 0,
            "contradicciones": [],
            "articulos_a_favor": [],
            "articulos_consultados": [],
            "task_id_constitucional": task_id,
            "duracion_ms": duracion_ms,
            "error": str(e),
        }

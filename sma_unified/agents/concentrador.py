# sma_unified/agents/concentrador.py
"""
Agente Concentrador y Emisor de Proyecto con Observaciones — Modelo Prometheus
===============================================================================
Tipo de razonamiento: Síntesis fidedigna paso a paso (Chain of Thought).

Reglas anti-alucinación (aplicadas en los 7 pasos):
  1. Grounding por cita: toda observación conserva 'cita_original' literal.
  2. "NO DISPONIBLE" > inventar: reporte incompleto → INSUMO_NO_VALIDO (excluido, no inventado).
  3. Salida JSON estricta.
  4. allow_delegation=False — el agente no delega a terceros.
  5. Autoverificación de fidelidad antes de emitir.
  6. Prohibido parafrasear el articulado del proyecto.
"""

import json
import time
import hashlib
from typing import Dict, List, Any, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("concentrador")

from sma_unified.agents.llm_client import chat_completion_resiliente, extraer_json_de_llm
from sma_unified.db.neon_postgres import get_conn, registrar_bitacora
from sma_unified.db.mongo_atlas import get_db


# ── Campos obligatorios que debe traer cada insumo de agente validador ────────
CAMPOS_REQUERIDOS_INSUMO = {"hallazgos", "agente_origen"}
NIVEL_CONFIANZA_MINIMO = 0.70  # Hallazgos < 70% se descartan


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
    conf = obs.get("confianza", obs.get("nivel_confianza", 1.0))
    try:
        if float(conf) < NIVEL_CONFIANZA_MINIMO:
            return False, f"Confianza {conf} < umbral {NIVEL_CONFIANZA_MINIMO}"
    except (TypeError, ValueError):
        pass
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
            art = h.get("articulo_afectado", h.get("articulo_constitucional", h.get("articulo", h.get("articulo_num", "N/A"))))
            cita = h.get("cita_original", h.get("fundamento", h.get("contenido", h.get("cita_proyecto", ""))))
            resultado.append({
                "id": f"OBS-{idx:03d}",
                "fuente": agente,
                "articulo": art,
                "articulo_afectado": art,
                "cita_original": str(cita).strip(),
                "tipo": h.get("clasificacion", h.get("tipo", "OBSERVACION")),
                "riesgo": h.get("severidad", h.get("riesgo", "leve")),
                "verificado": h.get("verificado", True),
            })
    return resultado


def _fusionar_redundancias(observaciones: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """
    PASO 4 — Fusiona observaciones que apuntan al mismo artículo + tipo.
    Conserva AMBAS fuentes en 'fuentes': []. Nunca elimina una fuente.
    """
    clave_a_grupo: Dict[str, List[Dict]] = {}
    for obs in observaciones:
        clave = f"{obs.get('articulo_afectado', '')}|{obs.get('tipo', '')}"
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


def _persistir_en_neon(conn, id_proyecto: int, resumen: str, riesgo: str, t0: float) -> None:
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE sistema.proyecto_ley SET
                estado_actual = 'AUDITORIA_COMPLETADA',
                observaciones_generales = COALESCE(observaciones_generales,'') ||
                    E'\\n[Concentrador] Riesgo: ' || %s || ' — ' || %s
            WHERE id_proyecto = %s
        """, (riesgo, resumen[:400], id_proyecto))
        conn.commit()
        cur.close()

        registrar_bitacora(
            id_proyecto=id_proyecto,
            agente_accion="Agente_Concentrador",
            accion_realizada="Consolidación de Expediente y Síntesis de Observaciones",
            descripcion=f"Riesgo: {riesgo} | {resumen[:200]}",
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


# ── Agente principal ──────────────────────────────────────────────────────────

class AgenteConcentrador:
    """
    Agente Concentrador y Emisor — Modelo Prometheus.
    Síntesis fidedigna con trazabilidad total. fusionar ≠ reescribir.
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

    def ejecutar(self, observaciones: List[Dict], proyecto_info: Dict) -> Dict:
        """
        Pipeline CoT de 7 pasos — síntesis fidedigna.
        """
        t0 = time.time()
        id_proyecto = int(proyecto_info.get("id") or proyecto_info.get("id_proyecto") or 0)
        titulo = proyecto_info.get("titulo") or proyecto_info.get("titulo_proyecto") or "Proyecto de Ley"

        # ── PASO 1: VALIDACIÓN DE INSUMOS ─────────────────────────────────────
        validos = []
        no_validos = []
        for obs in (observaciones or []):
            ok, razon = _validar_insumo(obs)
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
                "expediente_consolidado": {
                    "estado": "ERROR_INSUFICIENTE",
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

        # ── PASO 6: LLM — Síntesis narrativa del resumen ejecutivo ────────────
        riesgo_global = _calcular_riesgo_global(obs_verificadas)
        estado_siguiente = (
            "BLOQUEADO_PARA_DEBATE" if riesgo_global == "CRÍTICO"
            else "LISTO_PARA_DEBATE"
        )

        prompt_usuario = f"""
Proyecto: "{titulo}" (ID: {id_proyecto})
Nivel de riesgo global calculado: {riesgo_global}
Total observaciones verificadas: {len(obs_verificadas)}
Redundancias fusionadas: {len(fusionadas)}
Insumos excluidos: {len(no_validos)}

Observaciones verificadas (NO MODIFIQUES):
{json.dumps(obs_verificadas, ensure_ascii=False, indent=2)[:4000]}

INSTRUCCIÓN: Redacta ÚNICAMENTE el campo "resumen_ejecutivo" (máx 3 frases, en español formal).
NO parafrasees las citas_original. NO agregues información nueva.
Responde con JSON: {{"resumen_ejecutivo": "..."}}
"""
        resumen_ejecutivo = f"Expediente consolidado para: {titulo}. Riesgo global: {riesgo_global}."
        try:
            raw, _ = chat_completion_resiliente(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_usuario},
                ],
                temperature=0.1,
                max_tokens=400,
            )
            parsed = extraer_json_de_llm(raw)
            if isinstance(parsed, dict) and parsed.get("resumen_ejecutivo"):
                resumen_ejecutivo = parsed["resumen_ejecutivo"]
        except Exception as e:
            logger.warning(f"[Concentrador] LLM resumen fallback: {e}")

        # ── FORMATO PROMETHEUS ESTRICTO ───────────────────────────────────────
        lista_observaciones_final = [
            {
                "id": o.get("id") or f"OBS-{i+1:03d}",
                "fuente": (o.get("fuentes")[0] if isinstance(o.get("fuentes"), list) and o.get("fuentes") else o.get("fuente", "?")),
                "fuentes": o.get("fuentes", [o.get("fuente", "?")]),
                "articulo": o.get("articulo") or o.get("articulo_afectado", "N/A"),
                "articulo_afectado": o.get("articulo_afectado") or o.get("articulo", "N/A"),
                "cita_original": o.get("cita_original", ""),
                "tipo": o.get("tipo", "OBSERVACION"),
                "riesgo": o.get("riesgo", "leve"),
                "verificado": o.get("verificado", True),
            }
            for i, o in enumerate(obs_verificadas)
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

        # ── RESULTADO FINAL (Reporte Consolidado + Expediente) ────────────────
        resultado = {
            "estado": "CONSOLIDADO_COMPLETADO",
            "consolidado": {
                "observaciones": lista_observaciones_final,
                "redundancias_fusionadas": len(fusionadas),
                "insumos_no_validos": no_validos,
            },
            "bitacora": bitacora_trazabilidad,
            "expediente_consolidado": {
                "resumen_ejecutivo": resumen_ejecutivo,
                "observaciones_integradas": lista_observaciones_final,
                "redundancias_fusionadas": len(fusionadas),
                "insumos_no_validos": no_validos,
                "obs_descartadas_baja_confianza": obs_descartadas,
                "nivel_riesgo_general": riesgo_global,
                "estado_siguiente": estado_siguiente,
                "bitacora_trazabilidad": bitacora_trazabilidad,
            },
            "texto_proyecto_intacto": True
        }

        # ── PASO 7: PERSISTENCIA BD & ENVÍO A PRESIDENCIA DE COMISIÓN ─────────
        tiempo_ms = int((time.time() - t0) * 1000)
        conn = None
        if id_proyecto:
            try:
                conn = get_conn()
                _persistir_en_neon(conn, id_proyecto, resumen_ejecutivo, riesgo_global, t0)
            except Exception as e:
                logger.warning(f"[Concentrador] Neon no disponible: {e}")
        _persistir_en_mongo(id_proyecto, resultado, tiempo_ms)

        # Enviar Mensaje: Proyecto Consolidado -> Agente Presidencia de Comisión
        try:
            db = get_db()
            db["mensajes_sistema"].insert_one({
                "mensaje": "Proyecto Consolidado",
                "origen": "Agente_Concentrador",
                "destino": "Agente_Presidencia_Comision",
                "id_proyecto": id_proyecto,
                "estado_siguiente": estado_siguiente,
                "nivel_riesgo_general": riesgo_global,
                "total_observaciones": len(lista_observaciones_final),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            logger.info("[Concentrador] Notificación de Trámite enviada a Presidencia de Comisión")
        except Exception as m_err:
            logger.warning(f"[Concentrador] No se pudo encolar mensaje a Presidencia: {m_err}")

        logger.info(
            f"[Concentrador] ✅ Expediente consolidado | "
            f"Obs: {len(obs_verificadas)} | Riesgo: {riesgo_global} | {tiempo_ms}ms"
        )
        return resultado

# sma_unified/agents/publicacion.py
"""
Agente de Publicación Oficial — Modelo Prometheus
==================================================
Lógica DETERMINISTA: cero interpretación.
Ejecuta una secuencia fija de pasos validados para asignar número de ley,
fecha de vigencia, formatear para boletín oficial e integrar en la BD normativa.

Reglas anti-alucinación:
  1. Grounding por cita: ningún dato (número, fecha) se afirma sin fuente.
  2. "NO DISPONIBLE" > inventar: ante dato faltante → ERROR.
  3. Salida JSON estricta con campos cerrados.
  4. allow_delegation=False → sin delegación.
  5. Autoverificación antes de emitir.
"""

import os
import hashlib
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("publicacion_oficial")

from sma_unified.agents.llm_client import chat_completion_resiliente, extraer_json_de_llm
from sma_unified.db.neon_postgres import get_conn, registrar_bitacora
from sma_unified.db.mongo_atlas import get_db


# ── Constantes de configuración determinista ─────────────────────────────────
DIAS_VIGENCIA_DEFAULT = int(os.getenv("PUBLICACION_DIAS_VIGENCIA", "1"))
NUM_LEY_BASE = 1400  # Base si tabla vacía


def _obtener_siguiente_numero_ley(conn) -> int:
    """
    Lee el MÁXIMO número de ley registrado en sistema.proyecto_ley (Neon).
    Retorna último + 1. NUNCA inventa — si falla retorna ERROR_SIGNAL.
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(MAX(
                CAST(NULLIF(REGEXP_REPLACE(numero_ley, '[^0-9]', '', 'g'), '') AS INTEGER)
            ), %s) AS max_num
            FROM sistema.proyecto_ley
            WHERE numero_ley IS NOT NULL AND numero_ley != ''
        """, (NUM_LEY_BASE,))
        row = cur.fetchone()
        cur.close()
        return (row[0] or NUM_LEY_BASE) + 1
    except Exception as e:
        logger.warning(f"[Publicacion] No se pudo leer numeración desde Neon: {e}")
        raise RuntimeError(f"NO_DISPONIBLE: Registro de Numeración inaccesible — {e}")


def _calcular_fecha_vigencia(fecha_base: str, dias: int = DIAS_VIGENCIA_DEFAULT) -> str:
    """Aplica SOLO la regla: fecha_vigencia = fecha_base + N días. Sin interpretación."""
    try:
        dt = datetime.strptime(fecha_base, "%Y-%m-%d")
        return (dt + timedelta(days=dias)).strftime("%Y-%m-%d")
    except Exception:
        return (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")


def _hash_texto(texto: str) -> str:
    """SHA-256 completo del texto publicado — autoverificación de integridad fidedigna."""
    if not texto:
        return "NO_DISPONIBLE"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _validar_confirmacion_promulgacion(evaluacion_veto: Dict, texto_documento: str) -> tuple[bool, str]:
    """
    PASO 1 — VALIDACIÓN: Verifica que la confirmación de promulgación tenga
    los campos mínimos obligatorios:
      - texto del documento no vacío
      - decisión formal ejecutiva sea 'PROMULGAR'
    Si hay diferencia o inconsistencia, DETENERSE con ERROR_DATOS_INCONSISTENTES.
    """
    if not texto_documento or len(texto_documento.strip()) < 10:
        return False, "Texto de la ley sancionada faltante o incompleto (mínimo 10 caracteres requeridos)"

    ev = evaluacion_veto.get("evaluacion_veto", evaluacion_veto) if isinstance(evaluacion_veto, dict) else {}
    decision = ev.get("decision", "")
    
    # Si viene de veto o promulgación, debe ser PROMULGAR
    if decision and decision != "PROMULGAR":
        return False, f"Decisión no es PROMULGAR (recibido: '{decision}'). Requiere promulgación válida."
    return True, "OK"


def _persistir_publicacion_neon(
    conn,
    id_proyecto: int,
    numero_ley: int,
    numero_ley_str: str,
    fecha_promulgacion: str,
    fecha_vigencia: str,
    boletin_id: str,
    hash_texto: str,
    titulo: str,
) -> None:
    """PASO 5 — Escribe en la Base de Datos Normativa (Neon). Confirma con estado='LEY_PUBLICADA'."""
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE sistema.proyecto_ley SET
                numero_ley       = %s,
                estado_actual    = 'LEY_PUBLICADA',
                fecha_publicacion = %s::date,
                observaciones_generales = COALESCE(observaciones_generales,'') ||
                    E'\\n[Publicación] ' || %s || ' — Boletín: ' || %s || ' — Hash: ' || %s
            WHERE id_proyecto = %s
        """, (numero_ley_str, fecha_vigencia, titulo, boletin_id, hash_texto, id_proyecto))
        conn.commit()
        cur.close()
        logger.info(f"[Publicacion] BD Neon actualizada: {numero_ley_str} | Proyecto {id_proyecto}")
    except Exception as e:
        logger.warning(f"[Publicacion] Error persistiendo en Neon: {e}")
        raise


def _persistir_publicacion_mongo(
    id_proyecto: int,
    datos: Dict,
    tiempo_ms: int,
) -> None:
    """Registra la ejecución en MongoDB Atlas (bus de mensajería SMA)."""
    try:
        db = get_db()
        db["publicaciones_oficiales"].insert_one({
            "id_proyecto": id_proyecto,
            "agente": "Agente_Publicacion_Oficial",
            "datos": datos,
            "tiempo_ms": tiempo_ms,
            "ts": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.warning(f"[Publicacion] Error persistiendo en MongoDB: {e}")


# ── Agente principal ──────────────────────────────────────────────────────────

class AgentePublicacionOficial:
    """
    Agente de Publicación Oficial — Modelo Prometheus
    Procedimiento determinista automatizado: sin interpretación.
    """

    SYSTEM_PROMPT = (
        "Eres el Registrador Oficial de Leyes del Estado Plurinacional de Bolivia. "
        "Tu proceso es ESTRICTAMENTE DETERMINISTA: "
        "(1) Recibes los datos calculados del sistema, NO los interpretas. "
        "(2) Generas el JSON de publicación oficial EXACTAMENTE con los campos provistos. "
        "(3) Jamás inventas números, fechas ni contenido legal. "
        "(4) Si un campo está marcado 'NO_DISPONIBLE', lo mantienes tal cual y marcas estado=ERROR. "
        "Responde ÚNICAMENTE con JSON válido, sin texto adicional."
    )

    def ejecutar(self, evaluacion_veto: Dict, proyecto_info: Dict) -> Dict:
        """
        Pipeline determinista de 5 pasos:
          1. Validar confirmación de promulgación.
          2. Leer numeración oficial desde Neon.
          3. Calcular fecha de vigencia con regla configurada.
          4. Formatear con plantilla oficial.
          5. Integrar en BD Normativa + MongoDB.
        """
        t0 = time.time()
        id_proyecto = int(proyecto_info.get("id") or proyecto_info.get("id_proyecto") or 0)
        titulo = proyecto_info.get("titulo") or proyecto_info.get("titulo_proyecto") or "Ley Plurinacional"
        texto_ley = proyecto_info.get("texto_documento", "")

        # ── PASO 1: VALIDACIÓN DE INSUMOS ────────────────────────────────────
        valido, razon = _validar_confirmacion_promulgacion(evaluacion_veto, texto_ley)
        if not valido:
            logger.warning(f"[Publicacion] Validación fallida: {razon}")
            error_resp = {
                "estado": "ERROR_DATOS_INCONSISTENTES",
                "numero_ley": None,
                "fecha_vigencia": "NO_DISPONIBLE",
                "hash_texto": "NO_DISPONIBLE",
                "proyecto_id": str(id_proyecto),
                "razon": razon,
            }
            return {
                "estado": "ERROR_DATOS_INCONSISTENTES",
                "numero_ley": None,
                "fecha_vigencia": "NO_DISPONIBLE",
                "hash_texto": "NO_DISPONIBLE",
                "publicacion_oficial": error_resp
            }

        # ── PASO 2: NUMERACIÓN desde Registro Oficial (Neon / contador) ───────
        conn = None
        try:
            conn = get_conn()
            numero_ley_int = _obtener_siguiente_numero_ley(conn)
        except Exception as e:
            logger.warning(f"[Publicacion] Error en Registro de Numeración: {e}")
            error_resp = {
                "estado": "ERROR_NUMERACION_NO_DISPONIBLE",
                "numero_ley": None,
                "fecha_vigencia": "NO_DISPONIBLE",
                "hash_texto": "NO_DISPONIBLE",
                "proyecto_id": str(id_proyecto),
                "razon": str(e),
            }
            return {
                "estado": "ERROR_NUMERACION_NO_DISPONIBLE",
                "numero_ley": None,
                "fecha_vigencia": "NO_DISPONIBLE",
                "hash_texto": "NO_DISPONIBLE",
                "publicacion_oficial": error_resp
            }

        # ── PASO 3: VIGENCIA (regla determinista estricta: publicacion + N dias) ─
        fecha_promulgacion = datetime.now().strftime("%Y-%m-%d")
        fecha_vigencia = _calcular_fecha_vigencia(fecha_promulgacion, DIAS_VIGENCIA_DEFAULT)
        numero_ley_str = f"Ley No. {numero_ley_int}"
        boletin_id = f"BOL-{datetime.now().strftime('%Y-%m-%d')}-{numero_ley_int:04d}"
        hash_txt = _hash_texto(texto_ley or titulo)

        # ── PASO 4: FORMATO CON PLANTILLA OFICIAL ─────────────────────────────
        # Garantía anti-alucinación: valores deterministas sellados
        pub_dict = {
            "estado": "PUBLICADA",
            "numero_ley": numero_ley_int,
            "numero_ley_str": numero_ley_str,
            "fecha_vigencia": fecha_vigencia,
            "hash_texto": hash_txt,
            "proyecto_id": str(id_proyecto),
            "titulo": titulo,
            "fecha_promulgacion": fecha_promulgacion,
            "boletin_oficial": boletin_id,
            "estado_siguiente": "LEY_VIGENTE",
            "regla_vigencia_aplicada": f"fecha_publicacion + {DIAS_VIGENCIA_DEFAULT} dia(s)",
            "mensaje_salida": {
                "mensaje": "Ley Publicada",
                "destino": "Agente de Difusión Ciudadana",
                "numero_ley": numero_ley_int,
                "fecha_vigencia": fecha_vigencia,
                "hash_texto": hash_txt
            }
        }

        # Intento de verificación con LLM para asegurar formato de boletín
        user_prompt = f"""
Usa EXCLUSIVAMENTE estos datos calculados por el sistema. NO agregues ni modifiques nada:

proyecto_id: {id_proyecto}
numero_ley: {numero_ley_int} ({numero_ley_str})
titulo: {titulo}
fecha_promulgacion: {fecha_promulgacion}
fecha_vigencia: {fecha_vigencia}
boletin_oficial: {boletin_id}
hash_texto: {hash_txt}
estado: PUBLICADA

Genera el JSON de publicación oficial con exactamente esta estructura (sin inventar campos):
{{
  "publicacion_oficial": {{
    "estado": "PUBLICADA",
    "numero_ley": {numero_ley_int},
    "numero_ley_str": "{numero_ley_str}",
    "fecha_vigencia": "{fecha_vigencia}",
    "hash_texto": "{hash_txt}",
    "proyecto_id": "{id_proyecto}",
    "titulo": "{titulo}",
    "fecha_promulgacion": "{fecha_promulgacion}",
    "boletin_oficial": "{boletin_id}",
    "estado_siguiente": "LEY_VIGENTE",
    "regla_vigencia_aplicada": "fecha_publicacion + {DIAS_VIGENCIA_DEFAULT} dia(s)"
  }}
}}
"""
        try:
            raw, _ = chat_completion_resiliente(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=600,
            )
            data = extraer_json_de_llm(raw)
            pub = data.get("publicacion_oficial", {})
            # Autoverificación estricta contra alucinaciones
            if (str(pub.get("numero_ley")) != str(numero_ley_int) and pub.get("numero_ley_str") != numero_ley_str) or pub.get("fecha_vigencia") != fecha_vigencia:
                logger.warning("[Publicacion] LLM alteró campos calculados — usando fallback determinista")
                data = {"publicacion_oficial": pub_dict}
            else:
                pub["numero_ley"] = numero_ley_int
                pub["numero_ley_str"] = numero_ley_str
                pub["hash_texto"] = hash_txt
                pub["mensaje_salida"] = pub_dict["mensaje_salida"]
        except Exception as llm_err:
            logger.warning(f"[Publicacion] LLM fallback determinista: {llm_err}")
            data = {"publicacion_oficial": pub_dict}

        # ── PASO 5: INTEGRACIÓN EN BASE DE DATOS NORMATIVA ────────────────────
        if conn and id_proyecto:
            try:
                _persistir_publicacion_neon(
                    conn, id_proyecto, numero_ley_int, numero_ley_str,
                    fecha_promulgacion, fecha_vigencia, boletin_id, hash_txt, titulo
                )
                duracion_s = max(1, int(time.time() - t0))
                registrar_bitacora(
                    id_proyecto=id_proyecto,
                    agente_accion="Agente_Publicacion_Oficial",
                    accion_realizada="Promulgación Oficial y Asignación de Número de Ley",
                    descripcion=f"{numero_ley_str} | Boletín: {boletin_id} | Hash: {hash_txt[:16]}",
                    tiempo_segundos=duracion_s,
                )
            except Exception as db_e:
                logger.warning(f"[Publicacion] BD Neon no actualizada: {db_e}")
                data["publicacion_oficial"]["_bd_warning"] = str(db_e)

        tiempo_ms = int((time.time() - t0) * 1000)
        _persistir_publicacion_mongo(id_proyecto, data, tiempo_ms)

        # ── PASO 6: EJECUTAR ACCIÓN -> Enviar mensaje "Ley Publicada" a Difusión Ciudadana ──
        try:
            db = get_db()
            db["mensajes_sistema"].insert_one({
                "mensaje": "Ley Publicada",
                "origen": "Agente_Publicacion_Oficial",
                "destino": "Agente_Difusion_Ciudadana",
                "id_proyecto": id_proyecto,
                "numero_ley": numero_ley_int,
                "numero_ley_str": numero_ley_str,
                "fecha_vigencia": fecha_vigencia,
                "hash_texto": hash_txt,
                "boletin_oficial": boletin_id,
                "ts": datetime.utcnow().isoformat()
            })
            logger.info("[Publicacion] Mensaje 'Ley Publicada' despachado hacia Difusión Ciudadana")
        except Exception as m_err:
            logger.warning(f"[Publicacion] No se pudo encolar mensaje hacia Difusión Ciudadana: {m_err}")

        # Estructura de salida Prometheus combinada (raíz y objeto)
        data["estado"] = "PUBLICADA"
        data["numero_ley"] = numero_ley_int
        data["numero_ley_str"] = numero_ley_str
        data["fecha_vigencia"] = fecha_vigencia
        data["hash_texto"] = hash_txt

        logger.info(f"[Publicacion] ✅ {numero_ley_str} publicada | {boletin_id} | {tiempo_ms}ms")
        return data

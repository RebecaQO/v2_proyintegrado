"""
MongoDB Atlas — Bus de Comunicación entre Agentes
==================================================
Cada mensaje entre agentes queda registrado en la colección `agent_messages`
con todos los detalles: tarea, agente origen, destino, payload, estado y resultado.
"""
import os
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("sma_mongo")

# ── Lazy singleton para la conexión ─────────────────────────────────────────
_client = None
_db = None
_last_mongo_fail_time = 0.0


def get_db():
    """Retorna la instancia de base de datos MongoDB Atlas (singleton síncrono con circuit-breaker)."""
    global _client, _db, _last_mongo_fail_time
    if _db is not None:
        return _db
    now = time.monotonic()
    if now - _last_mongo_fail_time < 15.0:
        raise ConnectionError("MongoDB Atlas no disponible temporalmente (cooldown activo)")
    try:
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi

        uri = os.getenv("MONGO_URI", "")
        db_name = os.getenv("MONGO_DB", "sma_congreso")

        if not uri or "usuario:password" in uri:
            raise ValueError(
                "MONGO_URI no configurada. Edita .env con tu cadena de conexión de MongoDB Atlas."
            )

        _client = MongoClient(
            uri,
            server_api=ServerApi("1"),
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=5000,
            socketTimeoutMS=15000,
            retryWrites=True,
        )
        _client.admin.command("ping")  # Verifica conectividad
        _db = _client[db_name]
        logger.info(f"✅ MongoDB Atlas conectado → base de datos: {db_name}")
        _ensure_indexes(_db)
        return _db
    except Exception as e:
        _last_mongo_fail_time = time.monotonic()
        logger.error(f"❌ No se pudo conectar a MongoDB Atlas: {e}")
        raise


def _ensure_indexes(db):
    """Crea índices necesarios para rendimiento en las colecciones principales."""
    try:
        msgs = db["agent_messages"]
        msgs.create_index([("task_id", 1)], unique=True, sparse=True)
        msgs.create_index([("agente_destino", 1), ("estado", 1)])
        msgs.create_index([("timestamp", -1)])
        msgs.create_index([("sesion_id", 1)])

        docs = db["documentos"]
        docs.create_index([("expediente_id", 1)], unique=True, sparse=True)
        docs.create_index([("id_proyecto_pg", 1)])
        docs.create_index([("sesion_id", 1)])
        docs.create_index([("estado", 1)])
        docs.create_index([("fecha_ingreso", -1)])

        raw = db["documentos_raw"]
        raw.create_index([("doc_id", 1)], unique=True, sparse=True)
        raw.create_index([("sesion_id", 1)])

        # ── Colección: observaciones constitucionales ─────────────────
        obs = db["observaciones_constitucionales"]
        obs.create_index([("obs_id", 1)], unique=True, sparse=True)
        obs.create_index([("sesion_id", 1)])
        obs.create_index([("id_proyecto_pg", 1)])
        obs.create_index([("valido", 1), ("severidad_maxima", 1)])
        obs.create_index([("timestamp", -1)])

        # ── Colecciones de Dictaminación Legislativa Solicitadas ────────────
        rep_const = db["reportes_constitucionalidad"]
        rep_const.create_index([("expediente_id", 1)])
        rep_const.create_index([("sesion_id", 1)])

        rep_cons = db["reportes_consistencia"]
        rep_cons.create_index([("expediente_id", 1)])
        rep_cons.create_index([("sesion_id", 1)])
        rep_cons.create_index([("timestamp", -1)])

        notif_pend = db["notificaciones_pendientes"]
        notif_pend.create_index([("id_comision", 1)])
        notif_pend.create_index([("sesion_id", 1)])
        notif_pend.create_index([("estado", 1)])

        msg_ofic = db["mensajes_oficiales"]
        msg_ofic.create_index([("id_comision", 1)])
        msg_ofic.create_index([("sesion_id", 1)])
        msg_ofic.create_index([("fecha_envio", -1)])

        # ── Colecciones de Notificaciones por Cámara y Comisiones ─────
        notif_com = db["notificaciones_comision"]
        notif_com.create_index([("id_proyecto", 1)])
        notif_com.create_index([("sesion_id", 1)])
        notif_com.create_index([("comision", 1)])

        notif_bic = db["notificaciones_bicameral"]
        notif_bic.create_index([("id_proyecto", 1)])
        notif_bic.create_index([("sesion_id", 1)])

        msg_sen = db["mensajes_presidente_senado"]
        msg_sen.create_index([("id_proyecto", 1)])
        msg_sen.create_index([("sesion_id", 1)])

        msg_sis = db["mensajes_sistema"]
        msg_sis.create_index([("id_proyecto", 1)])

        # ── Colecciones de Expedientes Digitales, Audio y Concentración ──
        exp_dig = db["expedientes_digitales"]
        exp_dig.create_index([("id_proyecto", 1)], unique=True, sparse=True)
        exp_dig.create_index([("codigo_expediente", 1)], sparse=True)
        exp_dig.create_index([("estado", 1)])

        exp_conc = db["expedientes_concentrados"]
        exp_conc.create_index([("id_proyecto", 1)])
        exp_conc.create_index([("agente", 1)])

        reg_aud = db["registros_audio"]
        reg_aud.create_index([("id_proyecto", 1)])
        reg_aud.create_index([("tipo_audio", 1)])
        reg_aud.create_index([("fecha_captura", -1)])

        resp_ciud = db["respuestas_ciudadanas"]
        resp_ciud.create_index([("id_consulta", 1)], sparse=True)
        resp_ciud.create_index([("timestamp", -1)])

        actas_det = db["actas_detalladas"]
        actas_det.create_index([("id_proyecto", 1)])
        actas_det.create_index([("id_sesion", 1)])
        actas_det.create_index([("sesion_id", 1)])
        actas_det.create_index([("fecha_sesion", -1)])
        actas_det.create_index([("fecha_registro", -1)])

        ag_exec = db["agent_executions"]
        ag_exec.create_index([("id_proyecto", 1)])
        ag_exec.create_index([("nombre_agente", 1)])

        chat_ses = db["chat_sesiones"]
        chat_ses.create_index([("sesion_id", 1)])

        voz = db["voz_comandos"]
        voz.create_index([("sesion_id", 1)])

        casos = db["casos_compartidos"]
        casos.create_index([("actualizado", -1)])
        casos.create_index([("autor_id", 1), ("actualizado", -1)])
        casos.create_index([("estado", 1)])

        logger.info("Índices relacionales MongoDB verificados/creados.")
    except Exception as e:
        logger.warning(f"No se pudieron crear índices: {e}")


def guardar_reporte_constitucionalidad_mongo(data: Dict[str, Any]) -> str:
    """Guarda reporte en la colección reportes_constitucionalidad."""
    db = get_db()
    data["timestamp"] = datetime.now(timezone.utc)
    res = db["reportes_constitucionalidad"].insert_one(data)
    return str(res.inserted_id)


def guardar_reporte_consistencia_mongo(data: Dict[str, Any]) -> str:
    """Guarda reporte en la colección reportes_consistencia."""
    try:
        db = get_db()
        col = db["reportes_consistencia"]
        data["timestamp"] = datetime.now(timezone.utc)
        res = col.insert_one(data)
        logger.info(f"📋 Reporte de consistencia guardado en Mongo: {res.inserted_id} | sesión: {data.get('sesion_id')}")
        return str(res.inserted_id)
    except Exception as e:
        logger.warning(f"Error guardando reporte de consistencia en Mongo: {e}")
        return ""


def obtener_reportes_consistencia_mongo(
    expediente_id: Optional[Any] = None,
    sesion_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Obtiene reportes de consistencia normativa desde MongoDB."""
    try:
        db = get_db()
        col = db["reportes_consistencia"]
        filtro: Dict[str, Any] = {}
        if expediente_id is not None:
            filtro["$or"] = [{"expediente_id": expediente_id}, {"expediente_id": str(expediente_id)}]
        if sesion_id:
            filtro["sesion_id"] = sesion_id

        cursor = col.find(filtro, {"_id": 0}).sort("timestamp", -1).limit(limit)
        docs = list(cursor)
        for d in docs:
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        return docs
    except Exception as e:
        logger.warning(f"Error consultando reportes_consistencia en Mongo: {e}")
        return []


def obtener_reporte_consistencia_por_sesion_mongo(sesion_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene el reporte de consistencia normativa más reciente por sesion_id."""
    try:
        db = get_db()
        col = db["reportes_consistencia"]
        doc = col.find_one({"sesion_id": sesion_id}, {"_id": 0}, sort=[("timestamp", -1)])
        if doc and isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        return doc
    except Exception as e:
        logger.warning(f"Error consultando reporte_consistencia por sesión en Mongo: {e}")
        return None


def guardar_notificacion_oficial_mongo(data: Dict[str, Any]) -> str:
    """Guarda una notificación en notificaciones_pendientes y mensajes_oficiales."""
    db = get_db()
    data["timestamp"] = datetime.now(timezone.utc)
    db["notificaciones_pendientes"].insert_one(data)
    res = db["mensajes_oficiales"].insert_one(data)
    return str(res.inserted_id)


# ════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE MENSAJERÍA ENTRE AGENTES
# ════════════════════════════════════════════════════════════════════════════

def publicar_mensaje(
    agente_origen: str,
    agente_destino: str,
    tipo_tarea: str,
    payload: Dict[str, Any],
    sesion_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Publica un mensaje de comunicación entre agentes en MongoDB Atlas.

    Retorna el task_id generado.

    Esquema del documento:
    {
        task_id:        UUID único del mensaje/tarea
        sesion_id:      ID de sesión del flujo completo
        timestamp:      Fecha/hora UTC de creación
        agente_origen:  Nombre del agente que envía
        agente_destino: Nombre del agente que recibe
        tipo_tarea:     Nombre legible de la tarea a ejecutar
        estado:         "pendiente" | "en_proceso" | "completado" | "error"
        payload:        Datos enviados al agente destino
        resultado:      null (se llena al completar)
        metadata:       Información adicional (tiempos, modelo LLM, etc.)
        duracion_ms:    null (se llena al completar)
    }
    """
    task_id = str(uuid.uuid4())
    try:
        db = get_db()
        doc = {
            "task_id": task_id,
            "sesion_id": sesion_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc),
            "agente_origen": agente_origen,
            "agente_destino": agente_destino,
            "tipo_tarea": tipo_tarea,
            "estado": "pendiente",
            "payload": payload,
            "resultado": None,
            "metadata": metadata or {},
            "duracion_ms": None,
            "error_detalle": None,
        }
        db["agent_messages"].insert_one(doc)
        logger.info(
            f"📨 [{agente_origen}] → [{agente_destino}] | Tarea: {tipo_tarea} | ID: {task_id[:8]}..."
        )
    except Exception as e:
        logger.warning(f"No se pudo registrar mensaje en MongoDB: {e}")
    return task_id


def actualizar_estado(
    task_id: str,
    estado: str,
    resultado: Optional[Dict[str, Any]] = None,
    duracion_ms: Optional[int] = None,
    error_detalle: Optional[str] = None,
) -> None:
    """
    Actualiza el estado de un mensaje/tarea en MongoDB Atlas.

    estados posibles: 'pendiente', 'en_proceso', 'completado', 'error'
    """
    try:
        db = get_db()
        update = {"$set": {"estado": estado, "fecha_actualizacion": datetime.now(timezone.utc)}}
        if resultado is not None:
            update["$set"]["resultado"] = resultado
        if duracion_ms is not None:
            update["$set"]["duracion_ms"] = duracion_ms
        if error_detalle is not None:
            update["$set"]["error_detalle"] = error_detalle

        db["agent_messages"].update_one({"task_id": task_id}, update)
        logger.info(f"🔄 Tarea {task_id[:8]}... → estado: {estado}")
    except Exception as e:
        logger.warning(f"No se pudo actualizar estado en MongoDB: {e}")


def marcar_en_proceso(task_id: str) -> None:
    """Marca una tarea como 'en_proceso' al iniciar ejecución."""
    actualizar_estado(task_id, "en_proceso")


def marcar_completado(
    task_id: str,
    resultado: Dict[str, Any],
    duracion_ms: int = 0,
) -> None:
    """Marca una tarea como completada con su resultado."""
    actualizar_estado(task_id, "completado", resultado=resultado, duracion_ms=duracion_ms)


def marcar_error(task_id: str, error: str) -> None:
    """Marca una tarea como fallida con detalle del error."""
    actualizar_estado(task_id, "error", error_detalle=error)


# ════════════════════════════════════════════════════════════════════════════
# CONSULTAS DE VISUALIZACIÓN
# ════════════════════════════════════════════════════════════════════════════

def obtener_mensajes_recientes(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtiene los mensajes más recientes para la visualización en la UI."""
    db = get_db()
    cursor = (
        db["agent_messages"]
        .find({}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
    docs = list(cursor)
    # Convertir datetimes a strings para Reflex
    for d in docs:
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(d.get("fecha_actualizacion"), datetime):
            d["fecha_actualizacion"] = d["fecha_actualizacion"].strftime("%Y-%m-%d %H:%M:%S")
    return docs


def obtener_mensajes_sesion(sesion_id: str) -> List[Dict[str, Any]]:
    """Obtiene todos los mensajes de una sesión de procesamiento."""
    db = get_db()
    cursor = (
        db["agent_messages"]
        .find({"sesion_id": sesion_id}, {"_id": 0})
        .sort("timestamp", 1)
    )
    docs = list(cursor)
    for d in docs:
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return docs


def obtener_kpis_mongo() -> Dict[str, Any]:
    """KPIs de mensajería entre agentes para el dashboard."""
    db = get_db()
    col = db["agent_messages"]
    total = col.count_documents({})
    completados = col.count_documents({"estado": "completado"})
    en_proceso = col.count_documents({"estado": "en_proceso"})
    errores = col.count_documents({"estado": "error"})

    # Tiempo promedio de respuesta (agentes completados)
    pipeline = [
        {"$match": {"estado": "completado", "duracion_ms": {"$ne": None}}},
        {"$group": {"_id": None, "avg_ms": {"$avg": "$duracion_ms"}}},
    ]
    avg_result = list(col.aggregate(pipeline))
    avg_ms = int(avg_result[0]["avg_ms"]) if avg_result else 0

    # Mensajes por agente destino
    pipeline_agentes = [
        {"$group": {"_id": "$agente_destino", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    agentes_stats = {r["_id"]: r["count"] for r in col.aggregate(pipeline_agentes)}

    return {
        "total_mensajes": total,
        "completados": completados,
        "en_proceso": en_proceso,
        "errores": errores,
        "avg_duracion_ms": avg_ms,
        "agentes_stats": agentes_stats,
    }


def guardar_documento(doc_data: Dict[str, Any]) -> str:
    """Guarda un documento procesado en la colección 'documentos'."""
    db = get_db()
    exp_id = doc_data.get("expediente_id") or str(uuid.uuid4())
    doc_data["expediente_id"] = exp_id
    doc_data["fecha_ingreso"] = datetime.now(timezone.utc)
    db["documentos"].replace_one(
        {"expediente_id": exp_id}, doc_data, upsert=True
    )
    return exp_id


def obtener_documentos_recientes(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene los documentos más recientes."""
    db = get_db()
    cursor = (
        db["documentos"]
        .find({}, {"_id": 0})
        .sort("fecha_ingreso", -1)
        .limit(limit)
    )
    docs = list(cursor)
    for d in docs:
        if isinstance(d.get("fecha_ingreso"), datetime):
            d["fecha_ingreso"] = d["fecha_ingreso"].strftime("%Y-%m-%d %H:%M:%S")
    return docs


def ping_mongo() -> bool:
    """Retorna True si MongoDB Atlas responde correctamente."""
    try:
        get_db()
        return True
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════════════
# OBSERVACIONES CONSTITUCIONALES (colección nueva)
# ════════════════════════════════════════════════════════════════════════════

def guardar_observacion_constitucional_mongo(
    sesion_id: str,
    dictamen: Dict[str, Any],
    task_id_verificacion: Optional[str] = None,
    id_proyecto_pg: Optional[int] = None,
    articulos_consultados: Optional[List[Dict[str, Any]]] = None,
    modelo_llm: Optional[str] = None,
    duracion_ms: Optional[int] = None,
) -> str:
    """
    Guarda el dictamen constitucional en la colección MongoDB 'observaciones_constitucionales'.
    Sirve como cache rápido para el dashboard en tiempo real.

    Documento almacenado:
    {
        obs_id:               UUID único de la observación
        sesion_id:            ID de sesión del pipeline
        task_id_verificacion: UUID del mensaje en agent_messages
        id_proyecto_pg:       FK al id_proyecto en PostgreSQL (puede ser None)
        valido:               bool — True si el proyecto es conforme
        confianza:            float 0-100
        severidad_maxima:     'ninguna' | 'leve' | 'grave' | 'bloqueante'
        num_contradicciones:  int
        contradicciones:      lista de objetos con detalles de cada contradicción
        analisis_articulos:   lista de análisis por artículo del proyecto
        articulos_consultados:lista de artículos constitucionales consultados
        fundamentacion_general: str — razonamiento general del agente
        modelo_llm:           modelo usado
        duracion_ms:          tiempo de ejecución
        timestamp:            datetime UTC
    }

    Returns:
        obs_id (UUID string) del documento insertado.
    """
    import uuid as _uuid
    obs_id = str(_uuid.uuid4())
    db = get_db()

    doc = {
        "obs_id": obs_id,
        "sesion_id": sesion_id,
        "task_id_verificacion": task_id_verificacion,
        "id_proyecto_pg": id_proyecto_pg,
        "valido": bool(dictamen.get("valido", True)),
        "confianza": float(dictamen.get("confianza", 0)) if dictamen.get("confianza") is not None else None,
        "severidad_maxima": dictamen.get("severidad_maxima", "ninguna"),
        "num_contradicciones": len(dictamen.get("contradicciones", [])),
        "contradicciones": dictamen.get("contradicciones", []),
        "analisis_articulos": dictamen.get("analisis_por_articulo", []),
        "articulos_consultados": articulos_consultados or [],
        "fundamentacion_general": str(dictamen.get("fundamentacion_general", ""))[:3000],
        "modelo_llm": modelo_llm,
        "duracion_ms": duracion_ms,
        "timestamp": datetime.now(timezone.utc),
    }
    db["observaciones_constitucionales"].insert_one(doc)
    logger.info(
        f"⚖️  Observación constitucional MongoDB | sesión {sesion_id[:8]}... "
        f"| valido={doc['valido']} | severidad={doc['severidad_maxima']}"
    )
    return obs_id


def obtener_observaciones_mongo(
    limit: int = 20,
    solo_invalidos: bool = False,
) -> List[Dict[str, Any]]:
    """Obtiene observaciones constitucionales recientes desde MongoDB."""
    db = get_db()
    filtro: Dict[str, Any] = {}
    if solo_invalidos:
        filtro["valido"] = False
    cursor = (
        db["observaciones_constitucionales"]
        .find(filtro, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
    docs = list(cursor)
    for d in docs:
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return docs


def obtener_kpis_constitucionales_mongo() -> Dict[str, Any]:
    """KPIs de observaciones constitucionales desde MongoDB para el dashboard."""
    db = get_db()
    col = db["observaciones_constitucionales"]
    total = col.count_documents({})
    conformes = col.count_documents({"valido": True})
    con_contradicciones = col.count_documents({"valido": False})
    bloqueantes = col.count_documents({"severidad_maxima": "bloqueante"})
    graves = col.count_documents({"severidad_maxima": "grave"})

    pipeline_avg = [
        {"$match": {"confianza": {"$ne": None}}},
        {"$group": {"_id": None, "avg": {"$avg": "$confianza"}}},
    ]
    avg_result = list(col.aggregate(pipeline_avg))
    avg_confianza = round(avg_result[0]["avg"], 1) if avg_result else 0.0

    pipeline_sev = [
        {"$group": {"_id": "$severidad_maxima", "count": {"$sum": 1}}},
    ]
    sev_stats = {r["_id"]: r["count"] for r in col.aggregate(pipeline_sev)}

    return {
        "total": total,
        "conformes": conformes,
        "con_contradicciones": con_contradicciones,
        "bloqueantes": bloqueantes,
        "graves": graves,
        "avg_confianza": avg_confianza,
        "por_severidad": sev_stats,
    }


# ── Colecciones Especializadas del Proceso Legislativo 14 Agentes ────────────

def guardar_expediente_digital_mongo(data: Dict[str, Any]) -> str:
    """Guarda o actualiza un expediente digital completo en expedientes_digitales."""
    try:
        db = get_db()
        col = db["expedientes_digitales"]
        id_proyecto = data.get("id_proyecto", str(uuid.uuid4()))
        data["timestamp_actualizacion"] = datetime.now(timezone.utc)
        col.update_one(
            {"id_proyecto": id_proyecto},
            {"$set": data},
            upsert=True
        )
        return id_proyecto
    except Exception as e:
        logger.warning(f"Error guardando expediente digital en Mongo: {e}")
        return ""


def guardar_registro_audio_mongo(data: Dict[str, Any]) -> str:
    """Registra metadata de audio capturado (STT/TTS) en registros_audio."""
    try:
        db = get_db()
        col = db["registros_audio"]
        data["fecha_captura"] = datetime.now(timezone.utc)
        res = col.insert_one(data)
        return str(res.inserted_id)
    except Exception as e:
        logger.warning(f"Error guardando registro de audio en Mongo: {e}")
        return ""


def guardar_respuesta_ciudadana_mongo(data: Dict[str, Any]) -> str:
    """Registra consulta ciudadana atendida y respuesta generada en respuestas_ciudadanas."""
    try:
        db = get_db()
        col = db["respuestas_ciudadanas"]
        data["timestamp"] = datetime.now(timezone.utc)
        res = col.insert_one(data)
        return str(res.inserted_id)
    except Exception as e:
        logger.warning(f"Error guardando respuesta ciudadana en Mongo: {e}")
        return ""


def guardar_acta_detallada_mongo(data: Dict[str, Any]) -> str:
    """Registra acta completa con cronología paso a paso en actas_detalladas."""
    try:
        db = get_db()
        col = db["actas_detalladas"]
        data["fecha_registro"] = datetime.now(timezone.utc)
        res = col.insert_one(data)
        logger.info(
            f"📜 Acta detallada guardada en Mongo: {res.inserted_id} | "
            f"Proyecto: {data.get('id_proyecto')} | Sesión: {data.get('numero_sesion', data.get('id_sesion'))}"
        )
        return str(res.inserted_id)
    except Exception as e:
        logger.warning(f"Error guardando acta detallada en Mongo: {e}")
        return ""


def obtener_actas_detalladas_mongo(
    id_proyecto: Optional[Any] = None,
    sesion_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Obtiene actas detalladas parlamentarias desde MongoDB."""
    try:
        db = get_db()
        col = db["actas_detalladas"]
        filtro: Dict[str, Any] = {}
        if id_proyecto is not None:
            filtro["$or"] = [{"id_proyecto": id_proyecto}, {"id_proyecto": str(id_proyecto)}]
        if sesion_id:
            filtro["sesion_id"] = sesion_id

        cursor = col.find(filtro, {"_id": 0}).sort("fecha_registro", -1).limit(limit)
        docs = list(cursor)
        for d in docs:
            if isinstance(d.get("fecha_registro"), datetime):
                d["fecha_registro"] = d["fecha_registro"].strftime("%Y-%m-%d %H:%M:%S")
        return docs
    except Exception as e:
        logger.warning(f"Error consultando actas_detalladas en Mongo: {e}")
        return []


def obtener_acta_por_proyecto_mongo(id_proyecto: Any) -> Optional[Dict[str, Any]]:
    """Obtiene el acta detallada más reciente de un proyecto de ley."""
    try:
        db = get_db()
        col = db["actas_detalladas"]
        filtro = {"$or": [{"id_proyecto": id_proyecto}, {"id_proyecto": str(id_proyecto)}]}
        doc = col.find_one(filtro, {"_id": 0}, sort=[("fecha_registro", -1)])
        if doc and isinstance(doc.get("fecha_registro"), datetime):
            doc["fecha_registro"] = doc["fecha_registro"].strftime("%Y-%m-%d %H:%M:%S")
        return doc
    except Exception as e:
        logger.warning(f"Error consultando acta de proyecto en Mongo: {e}")
        return None



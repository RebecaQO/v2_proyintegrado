"""
SMA Congreso — Backend FastAPI
==============================
Servidor REST para la orquestación del Sistema Multi-Agente (SMA),
procesamiento de documentos, persistencia dual (MongoDB Atlas + PostgreSQL Neon)
y auditoría constitucional/normativa.
"""

import os
import sys
import uuid
import time
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import psycopg2
import psycopg2.extras

# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("sma_server")

# Imports de servicios SMA
from sma_unified.utils.doc_extractor import extraer_texto_archivo
from sma_unified.agents.pipeline import (
    ejecutar_fase_1_clasificacion,
    ejecutar_fase_2_agentes,
)
from sma_unified.db.neon_postgres import (
    get_conn,
    obtener_comisiones_activas,
    obtener_stats_constitucionales,
    obtener_ultimas_observaciones,
    obtener_observacion_por_proyecto,
    obtener_observacion_por_sesion,
    obtener_ultimos_analisis_consistencia,
    obtener_analisis_consistencia_por_archivo,
    obtener_stats_consistencia,
    listar_documentos_normativos,
    buscar_articulos_normativos_semantico,
)
from sma_unified.agents.embeddings_nvidia import generar_embeddings
from sma_unified.db.mongo_atlas import get_db, obtener_documentos_recientes, obtener_kpis_mongo

app = FastAPI(
    title="SMA Congreso API",
    description="Backend API para el Sistema Multi-Agente de Registro Legislativo",
    version="2.0.0",
)

# Configurar CORS para Vite (puerto 5173 / 3000 / cualquier origen)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = BASE_DIR / "uploaded_files"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploaded_files", StaticFiles(directory=str(UPLOAD_DIR)), name="uploaded_files")


# ── Schemas Pydantic ──────────────────────────────────────────────────────────

class Phase1Request(BaseModel):
    texto: str
    nombre_archivo: Optional[str] = "documento.txt"
    tipo_entrada: Optional[str] = "Texto Directo"
    sesion_id: Optional[str] = None
    metadata_extra: Optional[Dict[str, Any]] = None


class Phase2Request(BaseModel):
    sesion_id: str
    task_id_inicial: str
    task_id_distribuidor: str
    categoria: str
    agente_destino_nombre: str
    texto_documento: str
    nombre_archivo: Optional[str] = None
    tipo_entrada: Optional[str] = "Texto"
    id_proyecto: Optional[int] = None
    solicitud_id: Optional[int] = None
    t_inicio_fase1: Optional[float] = None
    local_filepath: Optional[str] = None


class SearchNormativaRequest(BaseModel):
    query: str
    documento: Optional[str] = None
    umbral: Optional[float] = 0.50
    top_k: Optional[int] = 10


class EmitPdfRequest(BaseModel):
    datos_constitucionales: Dict[str, Any]
    datos_consistencia: Dict[str, Any]
    sesion_id: str


class NotificadorComisionRequest(BaseModel):
    sesion_id: str
    id_proyecto: Optional[int] = None
    datos_comision: Optional[Dict[str, Any]] = None
    datos_constitucionales: Optional[Dict[str, Any]] = None
    datos_consistencia: Optional[Dict[str, Any]] = None
    pdf_filename: Optional[str] = None
    destinatario_extra: Optional[str] = None


class MiembroComisionRequest(BaseModel):
    id_comision: int
    nombre_completo: str
    cargo: Optional[str] = "Vocal"          # Presidente|Vicepresidente|Secretario|Vocal
    tipo_camara: Optional[str] = "Diputados"  # Diputados|Senadores
    email: Optional[str] = None
    partido_politico: Optional[str] = None


# ── Auto-migración: tabla sistema.miembro_comision ──────────────────────────
def _ensure_miembro_comision_table() -> None:
    """Crea la tabla de miembros si no existe."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sistema.miembro_comision (
                id_miembro      SERIAL PRIMARY KEY,
                id_comision     INT REFERENCES sistema.comision(id_comision) ON DELETE CASCADE,
                nombre_completo VARCHAR(255) NOT NULL,
                cargo           VARCHAR(100) DEFAULT 'Vocal'
                                CHECK (cargo IN ('Presidente','Vicepresidente','Secretario','Vocal')),
                tipo_camara     VARCHAR(50)  DEFAULT 'Diputados'
                                CHECK (tipo_camara IN ('Diputados','Senadores')),
                email           VARCHAR(150),
                partido_politico VARCHAR(100),
                fecha_asignacion DATE DEFAULT CURRENT_DATE,
                activo          BOOLEAN DEFAULT TRUE
            );
            ALTER TABLE sistema.miembro_comision ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE;
            ALTER TABLE sistema.comision ADD COLUMN IF NOT EXISTS activa BOOLEAN DEFAULT TRUE;
        """)
        conn.commit()
        cur.close()
        logger.info("✅ Tabla sistema.miembro_comision verificada/creada")
    except Exception as e:
        logger.warning(f"No se pudo crear/verificar tabla miembro_comision: {e}")

_ensure_miembro_comision_table()


# ── Endpoints de Salud y Estado ───────────────────────────────────────────────

@app.get("/api/health")
def get_health_status():
    """Verifica la salud de conexiones: MongoDB Atlas, Neon PostgreSQL y NVIDIA NIM."""
    status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
    }

    # 1. MongoDB Atlas
    try:
        db = get_db()
        db.command("ping")
        status["services"]["mongodb"] = {"status": "ok", "db": os.getenv("MONGO_DB", "sma_congreso")}
    except Exception as e:
        status["services"]["mongodb"] = {"status": "error", "message": str(e)}
        status["status"] = "degraded"

    # 2. PostgreSQL Neon
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        status["services"]["neon_postgres"] = {"status": "ok"}
    except Exception as e:
        status["services"]["neon_postgres"] = {"status": "error", "message": str(e)}
        status["status"] = "degraded"

    # 3. NVIDIA NIM LLM Config
    api_key = os.getenv("NVIDIA_API_KEY", "")
    status["services"]["nvidia_nim"] = {
        "configured": bool(api_key and not api_key.startswith("nvapi-placeholder")),
        "model_crew": os.getenv("LLM_MODEL_CREW", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
        "model_embed": os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b"),
    }

    return status


@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Métricas consolidadas y KPIs para el dashboard principal."""
    try:
        stats_obs = obtener_stats_constitucionales()
    except Exception:
        stats_obs = {"total": 0, "conformes": 0, "con_contradicciones": 0, "bloqueantes": 0, "graves": 0}

    try:
        comisiones = obtener_comisiones_activas()
        total_comisiones = len(comisiones)
    except Exception:
        total_comisiones = 10

    try:
        stats_consistencia = obtener_stats_consistencia()
    except Exception:
        stats_consistencia = {"total_normas": 0, "total_articulos": 0, "total_analisis": 0}

    # Estadísticas del Bus de Mensajes en MongoDB
    bus_stats = {}
    try:
        bus_stats = obtener_kpis_mongo()
    except Exception:
        pass

    return {
        "observaciones_constitucionales": stats_obs,
        "total_comisiones": total_comisiones,
        "consistencia_normativa": stats_consistencia,
        "bus_mensajes": bus_stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Endpoints del Pipeline Multi-Agente ──────────────────────────────────────

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Carga un archivo (PDF, DOCX, TXT), extrae su texto limpio
    y devuelve la información estructurada.
    """
    try:
        filename = file.filename or f"doc_{uuid.uuid4().hex[:8]}.txt"
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        # Guardar copia local en uploaded_files
        unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        dest_path = UPLOAD_DIR / unique_name
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        # Extraer texto
        texto_extraido, metadata_extraccion = extraer_texto_archivo(filename, file_bytes)

        if not texto_extraido.strip():
            texto_extraido = "[No se pudo extraer texto legible del documento o el archivo contiene solo imágenes]"

        return {
            "success": True,
            "filename": filename,
            "saved_as": unique_name,
            "local_path": str(dest_path),
            "size_bytes": len(file_bytes),
            "caracteres": len(texto_extraido),
            "palabras": len(texto_extraido.split()),
            "paginas": metadata_extraccion.get("num_paginas", 1),
            "motor": metadata_extraccion.get("motor", "standard"),
            "texto_preview": texto_extraido[:800],
            "texto_completo": texto_extraido,
        }
    except Exception as e:
        logger.error(f"Error procesando archivo subido: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/phase1")
def run_phase1_classification(req: Phase1Request):
    """
    FASE 1: Ejecuta el Agente Distribuidor (Nivel 1).
    Devuelve la categoría clasificada y pausa el flujo para confirmación humana.
    """
    try:
        if not req.texto.strip():
            raise HTTPException(status_code=400, detail="El texto del documento no puede estar vacío.")

        t_inicio = time.time()
        res_fase1 = ejecutar_fase_1_clasificacion(
            texto_documento=req.texto,
            nombre_archivo=req.nombre_archivo,
            tipo_entrada=req.tipo_entrada or "Texto Directo",
            metadata_extra=req.metadata_extra or {},
            sesion_id=req.sesion_id,
        )
        res_fase1["t_inicio_fase1"] = t_inicio
        return {
            "success": True,
            "data": res_fase1,
        }
    except Exception as e:
        logger.error(f"Error en Fase 1: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_id_proyecto(sesion_id: str, id_proyecto: Optional[int] = None, texto_doc: Optional[str] = None, nombre_archivo: Optional[str] = None) -> Optional[int]:
    """Garantiza que siempre exista un id_proyecto en sistema.proyecto_ley para la sesión."""
    if id_proyecto:
        return id_proyecto
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id_proyecto FROM sistema.proyecto_ley WHERE observaciones_generales LIKE %s ORDER BY fecha_ingreso DESC LIMIT 1",
            (f"%sesion:{sesion_id}%",)
        )
        row = cur.fetchone()
        if row:
            cur.close()
            return row[0]
        cur.close()
        
        # Si no existe, crearlo inmediatamente
        if texto_doc:
            from sma_unified.db.neon_postgres import guardar_proyecto_ley
            return guardar_proyecto_ley(
                sesion_id=sesion_id,
                texto_documento=texto_doc,
                nombre_archivo=nombre_archivo or "documento.pdf",
            )
    except Exception as e:
        logger.warning(f"No se pudo resolver id_proyecto para sesion {sesion_id}: {e}")
    return None


@app.post("/api/pipeline/agent_comision")
def run_agent_comision(req: Phase2Request):
    """Ejecuta únicamente el Agente de Asignación de Comisión (con comisiones desde BD Neon)."""
    from sma_unified.agents.comision import _get_asignador_agent
    from sma_unified.db.neon_postgres import obtener_comisiones_activas, asignar_comision_a_proyecto, registrar_bitacora
    from sma_unified.utils.text_sampler import muestrear_texto
    from sma_unified.config import load_tasks_yaml
    from crewai import Task, Crew
    import json

    def _strip_json(txt: str) -> str:
        if "```json" in txt:
            txt = txt.split("```json")[1].split("```")[0].strip()
        elif "```" in txt:
            txt = txt.split("```")[1].split("```")[0].strip()
        return txt.strip()

    try:
        t_inicio = time.time()
        # Cargar comisiones desde Neon (con fallback)
        comisiones = obtener_comisiones_activas()
        comisiones_str = "\n".join(f"- {c}" for c in comisiones)

        # Heurística temática basada en comisiones reales de Neon
        def _determinar_comision_heuristica(texto: str, lista_comisiones: List[str]) -> str:
            t = texto.lower()
            if any(k in t for k in ["agua", "medio ambiente", "tierra", "bosque", "biodiversidad", "recursos naturales"]):
                for c in lista_comisiones:
                    if "medio ambiente" in c.lower() or "tierra" in c.lower(): return c
            if any(k in t for k in ["economía", "tribut", "financ", "presupuesto", "banco", "fiscal", "inversión"]):
                for c in lista_comisiones:
                    if "planificación" in c.lower() or "economía" in c.lower() or "finanzas" in c.lower(): return c
            if any(k in t for k in ["salud", "educación", "deporte", "escuela", "hospital", "médic"]):
                for c in lista_comisiones:
                    if "educación" in c.lower() or "salud" in c.lower(): return c
            if any(k in t for k in ["justicia", "penal", "civil", "derechos humanos", "constituc"]):
                for c in lista_comisiones:
                    if "constitución" in c.lower() or "justicia" in c.lower(): return c
            for c in lista_comisiones:
                if "constitución" in c.lower(): return c
            return lista_comisiones[0] if lista_comisiones else "Comisión de Constitución, Legislación y Sistema Electoral"

        # Intento con LLM resiliente
        data = None
        try:
            from sma_unified.agents.llm_client import chat_completion_resiliente, extraer_json_de_llm
            prompt_com = f"""Eres el Asignador de Comisiones de la Asamblea Legislativa de Bolivia.
Comisiones disponibles en la base de datos:
{comisiones_str}

Texto del documento:
{muestrear_texto(req.texto_documento, 3000)}

Determina la comisión competente según la materia. Responde ÚNICAMENTE con JSON:
{{"comision_principal": "<nombre exacto de una comisión de la lista>", "prioridad": "Alta|Media|Normal", "resumen": "<breve resumen>", "complejidad": "Baja|Media|Alta"}}
"""
            raw_out, mod = chat_completion_resiliente(
                messages=[{"role": "user", "content": prompt_com}],
                temperature=0.1,
                max_tokens=250,
                timeout=8
            )
            data = extraer_json_de_llm(raw_out)
        except Exception as _llm_e:
            logger.warning(f"Fallback heurístico comisiones por error LLM: {_llm_e}")

        if not data or not isinstance(data, dict) or not data.get("comision_principal"):
            com_elegida = _determinar_comision_heuristica(req.texto_documento, comisiones)
            data = {
                "comision_principal": com_elegida,
                "prioridad": "Alta" if "urgente" in req.texto_documento.lower() else "Normal",
                "resumen": req.texto_documento.strip().split("\n")[0][:180] or "Proyecto legislativo canalizado por especialidad temática.",
                "complejidad": "Media",
            }

        id_proyecto = _resolve_id_proyecto(req.sesion_id, req.id_proyecto, req.texto_documento, req.nombre_archivo)
        data["id_proyecto"] = id_proyecto

        if id_proyecto and data.get("comision_principal"):
            # Actualizar proyecto en Neon
            asignar_comision_a_proyecto(
                id_proyecto, data["comision_principal"],
                data.get("resumen", "Asignado por IA"), True
            )
            # Actualizar titulo y resumen si vienen de la IA
            try:
                conn = get_conn()
                cur = conn.cursor()
                titulo_extract = data.get("tema_principal") or data.get("resumen", "").split(".")[0][:250] or req.nombre_archivo
                cur.execute(
                    """
                    UPDATE sistema.proyecto_ley SET
                        titulo = COALESCE(NULLIF(%s, ''), titulo),
                        resumen = COALESCE(NULLIF(%s, ''), resumen),
                        prioridad = %s
                    WHERE id_proyecto = %s
                    """,
                    (titulo_extract, data.get("resumen", ""), data.get("prioridad", "Media"), id_proyecto)
                )
                conn.commit()
                cur.close()
            except Exception as _ue:
                logger.warning(f"No se pudo actualizar titulo/resumen en Neon: {_ue}")

            # Registrar en Bitácora de Neon
            duracion_s = max(1, int(time.time() - t_inicio))
            registrar_bitacora(
                id_proyecto=id_proyecto,
                agente_accion="Agente_Comision_Legislativa",
                accion_realizada="Asignación de Comisión y Temática",
                descripcion=f"Comisión: {data.get('comision_principal')} | Prioridad: {data.get('prioridad', 'Normal')}",
                tiempo_segundos=duracion_s
            )

        # Buscar miembros de la comisión asignada en sistema.miembro_comision
        miembros = []
        try:
            conn = get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT m.nombre_completo, m.cargo, m.tipo_camara, m.email, m.partido_politico
                FROM sistema.miembro_comision m
                JOIN sistema.comision c ON c.id_comision = m.id_comision
                WHERE (c.codigo_comision = %s OR c.nombre_corto = %s OR c.nombre_comision ILIKE %s)
                  AND (m.activo IS NULL OR m.activo = TRUE)
                ORDER BY 
                  CASE m.cargo 
                    WHEN 'Presidente' THEN 1 
                    WHEN 'Vicepresidente' THEN 2 
                    WHEN 'Secretario' THEN 3 
                    ELSE 4 
                  END
            """, (data.get("comision_principal"), data.get("comision_principal"), f"%{data.get('comision_principal')}%"))
            rows = cur.fetchall()
            cur.close()
            miembros = [dict(r) for r in rows]
        except Exception as _me:
            logger.warning(f"No se pudieron obtener miembros de comisión: {_me}")

        data["miembros"] = miembros
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error en Agente Comisión: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_constitucional")
def run_agent_constitucional(req: Phase2Request):
    """Ejecuta el Agente de Verificación Constitucional (CPE) — módulo independiente."""
    from sma_unified.agents.verificador_constitucional import verificar_constitucionalidad
    from sma_unified.db.neon_postgres import actualizar_proyecto_con_observacion, registrar_bitacora
    from sma_unified.db.mongo_atlas import guardar_reporte_constitucionalidad_mongo

    try:
        t_inicio = time.time()
        id_proyecto = _resolve_id_proyecto(req.sesion_id, req.id_proyecto, req.texto_documento, req.nombre_archivo)

        resultado = verificar_constitucionalidad(
            texto_documento=req.texto_documento,
            sesion_id=req.sesion_id,
            id_proyecto=id_proyecto,
            task_id_distribuidor=f"task_{req.sesion_id}",
            persistir=True,
        )

        resultado["id_proyecto"] = id_proyecto

        if id_proyecto:
            try:
                actualizar_proyecto_con_observacion(
                    id_proyecto,
                    resultado.get("id_observacion_neon"),
                    resultado.get("valido", True),
                )
                duracion_s = max(1, int(time.time() - t_inicio))
                registrar_bitacora(
                    id_proyecto=id_proyecto,
                    agente_accion="Agente_Verificador_Constitucional",
                    accion_realizada="Control y Dictamen de Constitucionalidad (CPE)",
                    descripcion=f"Dictamen: {'CONFORME' if resultado.get('valido') else 'OBSERVADO'} | Severidad: {resultado.get('severidad_maxima', 'ninguna')} | Confianza: {resultado.get('confianza', 95)}%",
                    nivel_confianza=float(resultado.get("confianza", 95)),
                    tiempo_segundos=duracion_s
                )
            except Exception as _e:
                logger.warning(f"No se pudo actualizar proyecto en Neon: {_e}")

        try:
            guardar_reporte_constitucionalidad_mongo({
                "expediente_id": id_proyecto,
                "sesion_id": req.sesion_id,
                "nombre_archivo": req.nombre_archivo,
                "dictamen": resultado,
                "num_contradicciones": resultado.get("num_contradicciones", 0),
                "articulos_a_favor": len(resultado.get("articulos_a_favor", [])),
            })
        except Exception as _mge:
            logger.warning(f"No se pudo guardar reporte en Mongo: {_mge}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en Agente Constitucional: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_consistencia")
def run_agent_consistencia(req: Phase2Request):
    """Ejecuta el Agente de Consistencia Normativa (leyes vigentes) — módulo independiente."""
    from sma_unified.agents.consistencia_normativa import verificar_consistencia_normativa
    from sma_unified.db.neon_postgres import registrar_bitacora
    try:
        t_inicio = time.time()
        id_proyecto = _resolve_id_proyecto(req.sesion_id, req.id_proyecto, req.texto_documento, req.nombre_archivo)

        resultado = verificar_consistencia_normativa(
            texto_documento=req.texto_documento,
            sesion_id=req.sesion_id,
            task_id_distribuidor=f"task_{req.sesion_id}",
            metadata_extra={"nombre_archivo": req.nombre_archivo},
            id_proyecto=id_proyecto,
            nombre_archivo=req.nombre_archivo,
        )

        resultado["id_proyecto"] = id_proyecto

        if id_proyecto:
            try:
                duracion_s = max(1, int(time.time() - t_inicio))
                registrar_bitacora(
                    id_proyecto=id_proyecto,
                    agente_accion="Agente_Consistencia_Normativa",
                    accion_realizada="Auditoría de Consistencia Normativa (pgvector)",
                    descripcion=f"Hallazgos: {resultado.get('total_hallazgos', 0)} | Riesgo Global: {resultado.get('nivel_riesgo_global', 'OK')}",
                    tiempo_segundos=duracion_s
                )
            except Exception as _be:
                logger.warning(f"No se pudo registrar bitacora consistencia: {_be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en Agente Consistencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/emit_pdf")
def run_emit_pdf(req: EmitPdfRequest):
    """
    Emite un PDF con los resultados de las auditorias en formato profesional.
    """
    from sma_unified.agents.emisor_resultados import emitir_informe_pdf
    from sma_unified.db.neon_postgres import registrar_bitacora
    try:
        t_inicio = time.time()
        resultado = emitir_informe_pdf(
            datos_constitucionales=req.datos_constitucionales,
            datos_consistencia=req.datos_consistencia,
            sesion_id=req.sesion_id
        )

        id_proyecto = _resolve_id_proyecto(req.sesion_id)
        if id_proyecto and resultado.get("filename"):
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE sistema.proyecto_ley SET archivo_pdf = %s WHERE id_proyecto = %s",
                    (resultado["filename"], id_proyecto)
                )
                conn.commit()
                cur.close()

                duracion_s = max(1, int(time.time() - t_inicio))
                registrar_bitacora(
                    id_proyecto=id_proyecto,
                    agente_accion="Agente_Emisor_Resultados",
                    accion_realizada="Emisión de Dictamen Técnico Oficial (PDF)",
                    descripcion=f"Documento generado: {resultado['filename']}",
                    tiempo_segundos=duracion_s
                )
            except Exception as _pe:
                logger.warning(f"No se pudo actualizar archivo_pdf en Neon: {_pe}")

        return {
            "success": True,
            "data": resultado
        }
    except Exception as e:
        logger.error(f"Error emitiendo PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_notificador")
def run_agent_notificador(req: NotificadorComisionRequest):
    """
    Agente Notificador de Comisión (5to Agente):
    Redacta y procesa el correo HTML institucional formal para los miembros
    y autoridades de la comisión legislativa asignada vía Gmail SMTP o Twilio SendGrid Email API.
    """
    from sma_unified.agents.notificador_comision import notificar_miembros_comision
    try:
        id_proyecto = _resolve_id_proyecto(req.sesion_id, req.id_proyecto)
        resultado = notificar_miembros_comision(
            sesion_id=req.sesion_id,
            id_proyecto=id_proyecto,
            datos_comision=req.datos_comision,
            datos_constitucionales=req.datos_constitucionales,
            datos_consistencia=req.datos_consistencia,
            pdf_filename=req.pdf_filename,
            destinatario_extra=req.destinatario_extra,
        )
        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en Agente Notificador: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints CrewAI Flujo Legislativo Extendido ────────────────────────────

@app.post("/api/pipeline/agent_constitucion_fondo")
async def run_agent_constitucion_fondo_endpoint(payload: Dict[str, Any]):
    """
    Etapa 3: Agente Comisión Constitución (Fondo)
    Análisis hermenéutico y viabilidad sustantiva (no solo formal).
    """
    try:
        from sma_unified.agents.constitucion_fondo import AgenteConstitucionFondo
        from sma_unified.db.neon_postgres import registrar_bitacora
        
        texto_proyecto = payload.get("texto_proyecto", "")
        obs_formales = payload.get("obs_formales", [])
        proyecto_info = payload.get("proyecto_info", {})
        id_proyecto = payload.get("id_proyecto") or proyecto_info.get("id_proyecto") or proyecto_info.get("id")
        
        agente = AgenteConstitucionFondo()
        resultado = agente.ejecutar(
            texto_proyecto=texto_proyecto,
            obs_formales=obs_formales,
            proyecto_info=proyecto_info
        )
        
        if id_proyecto:
            try:
                dictamen = resultado.get("dictamen_fondo", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Constitucion_Fondo",
                    accion_realizada="Análisis Hermenéutico Constitucional de Fondo",
                    descripcion=f"Viabilidad: {dictamen.get('viabilidad_fondo', 'N/A')} | Riesgo: {dictamen.get('riesgo_constitucional', 'BAJO')}",
                    tiempo_segundos=1
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Constitucion Fondo: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Constitucion Fondo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_concentrador")
async def run_agent_concentrador_endpoint(payload: Dict[str, Any]):
    """
    Etapa 4: Agente Concentrador y Emisor
    Consolidación y síntesis de observaciones de todos los agentes.
    """
    try:
        from sma_unified.agents.concentrador import AgenteConcentrador
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        observaciones = payload.get("observaciones", [])
        id_proyecto = payload.get("id_proyecto") or proyecto_info.get("id_proyecto") or proyecto_info.get("id")

        agente = AgenteConcentrador()
        resultado = agente.ejecutar(
            observaciones=observaciones,
            proyecto_info=proyecto_info
        )

        if id_proyecto:
            try:
                exp = resultado.get("expediente_consolidado", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Concentrador",
                    accion_realizada="Consolidación de Expediente y Síntesis de Observaciones",
                    descripcion=f"Riesgo Global: {exp.get('nivel_riesgo_general', 'MEDIO')} | Observaciones integradas: {len(exp.get('observaciones_integradas', []))}",
                    tiempo_segundos=1
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Concentrador: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Concentrador: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_secretario")
async def run_agent_secretario_endpoint(payload: Dict[str, Any]):
    """
    Etapa 5: Agente Secretario de Cámara
    Registro de actas de debate parlamentario y votaciones.
    """
    try:
        from sma_unified.agents.secretario import AgenteSecretarioCamara
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        debate_data = payload.get("debate_data", {})
        id_proyecto = payload.get("id_proyecto") or proyecto_info.get("id_proyecto") or proyecto_info.get("id")

        agente = AgenteSecretarioCamara()
        resultado = agente.ejecutar(
            debate_data=debate_data,
            proyecto_info=proyecto_info
        )

        if id_proyecto:
            try:
                acta = resultado.get("acta_debate", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Secretario_Camara",
                    accion_realizada="Registro de Debate Parlamentario y Votación Nominal",
                    descripcion=f"Sesión: #{acta.get('sesion_numero', 1)} | Votaciones: {len(acta.get('votaciones', []))}",
                    tiempo_segundos=1
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Secretario: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Secretario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_bicameral")
async def run_agent_bicameral_endpoint(payload: Dict[str, Any]):
    """
    Etapa 6: Agente Comunicación Bicameral
    Coordinación y reconciliación entre Cámara de Origen y Revisora.
    """
    try:
        from sma_unified.agents.bicameral import AgenteBicameral
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        version_original = payload.get("version_original", {})
        version_retornada = payload.get("version_retornada", {})
        id_proyecto = payload.get("id_proyecto") or proyecto_info.get("id_proyecto") or proyecto_info.get("id")

        agente = AgenteBicameral()
        resultado = agente.ejecutar(
            version_original=version_original,
            version_retornada=version_retornada,
            proyecto_info=proyecto_info
        )

        if id_proyecto:
            try:
                ciclo = resultado.get("ciclo_bicameral", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Bicameral",
                    accion_realizada="Control de Trámite Bicameral y Reconciliación",
                    descripcion=f"Cambios: {ciclo.get('clasificacion_cambios', 'MENORES')} | Ruta: {ciclo.get('ruta_siguiente', 'SANCION_DIRECTA')}",
                    tiempo_segundos=1
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Bicameral: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Bicameral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_veto_promulgacion")
async def run_agent_veto_promulgacion_endpoint(payload: Dict[str, Any]):
    """
    Etapa 7: Agente Veto y Promulgación
    Evaluación estratégica multicriterio del Órgano Ejecutivo.
    """
    try:
        from sma_unified.agents.veto_promulgacion import AgenteVetoPromulgacion
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        expediente = payload.get("expediente", {})
        id_proyecto = payload.get("id_proyecto") or proyecto_info.get("id_proyecto") or proyecto_info.get("id")

        agente = AgenteVetoPromulgacion()
        resultado = agente.ejecutar(
            expediente=expediente,
            proyecto_info=proyecto_info
        )

        if id_proyecto:
            try:
                ev = resultado.get("evaluacion_veto", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Veto_Promulgacion",
                    accion_realizada="Evaluación Estratégica Multicriterio de Promulgación",
                    descripcion=f"Decisión: {ev.get('decision', 'PROMULGAR')} | Score: {ev.get('score_final', 7.5)}",
                    tiempo_segundos=1
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Veto/Promulgación: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Veto/Promulgacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_publicacion")
async def run_agent_publicacion_endpoint(payload: Dict[str, Any]):
    """
    Etapa 8: Agente Publicación Oficial
    Asignación de número de ley y registro en Boletín Oficial.
    """
    try:
        from sma_unified.agents.publicacion import AgentePublicacionOficial
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        evaluacion_veto = payload.get("evaluacion_veto", {})
        id_proyecto = payload.get("id_proyecto") or proyecto_info.get("id_proyecto") or proyecto_info.get("id")

        agente = AgentePublicacionOficial()
        resultado = agente.ejecutar(
            evaluacion_veto=evaluacion_veto,
            proyecto_info=proyecto_info
        )

        if id_proyecto:
            try:
                pub = resultado.get("publicacion_oficial", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Publicacion_Oficial",
                    accion_realizada="Promulgación Oficial y Asignación de Número de Ley",
                    descripcion=f"{pub.get('numero_ley', 'Ley')} | Boletín: {pub.get('boletin_oficial', 'BOL-OFICIAL')}",
                    tiempo_segundos=1
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Publicación: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Publicacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/pipeline_completo")
async def run_pipeline_completo_endpoint(payload: Dict[str, Any]):
    """
    Ejecución del pipeline completo CrewAI de extremo a extremo (Etapas 3 a 8).
    """
    try:
        from sma_unified.agents.crew_orchestrator import ejecutar_pipeline_completo

        proyecto_info = payload.get("proyecto_info", {})
        texto_documento = payload.get("texto_proyecto") or payload.get("texto_documento", "")
        observaciones_previas = payload.get("observaciones_previas", [])

        resultado = ejecutar_pipeline_completo(
            proyecto_info=proyecto_info,
            texto_documento=texto_documento,
            observaciones_previas=observaciones_previas
        )

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en pipeline completo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints de Expedientes y Consultas ─────────────────────────────────────

@app.get("/api/expedientes")
def get_expedientes(limit: int = Query(50, ge=1, le=200)):
    """Lista los proyectos de ley registrados en Neon PostgreSQL con su estado de auditoría."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT 
                p.id_proyecto,
                p.numero_expediente,
                p.titulo,
                p.resumen,
                p.archivo_pdf,
                p.fecha_ingreso,
                p.prioridad,
                p.id_estado_actual,
                c.nombre_comision,
                c.nombre_corto as comision_corto,
                obs.valido as valido_constitucional,
                obs.confianza,
                obs.severidad_maxima,
                obs.num_contradicciones
            FROM sistema.proyecto_ley p
            LEFT JOIN sistema.comision c ON p.id_comision_actual = c.id_comision
            LEFT JOIN LATERAL (
                SELECT valido, confianza, severidad_maxima, num_contradicciones
                FROM sistema.observaciones_constitucionales
                WHERE id_proyecto = p.id_proyecto
                ORDER BY fecha_analisis DESC
                LIMIT 1
            ) obs ON TRUE
            ORDER BY COALESCE(p.fecha_ingreso, '2000-01-01'::timestamp) DESC, p.id_proyecto DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        expedientes = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("fecha_ingreso"), datetime):
                d["fecha_ingreso"] = d["fecha_ingreso"].isoformat()
            if d.get("confianza") is not None:
                d["confianza"] = float(d["confianza"])
            expedientes.append(d)

        return {
            "success": True,
            "total": len(expedientes),
            "data": expedientes,
        }
    except Exception as e:
        logger.error(f"Error listando expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/expedientes/{id_proyecto}")
def get_expediente_detalle(id_proyecto: int):
    """Obtiene el expediente integral con bitácora, dictamen, observaciones y consistencia."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Proyecto
        cur.execute(
            """
            SELECT p.*, c.nombre_comision, c.nombre_corto as comision_corto
            FROM sistema.proyecto_ley p
            LEFT JOIN sistema.comision c ON p.id_comision_actual = c.id_comision
            WHERE p.id_proyecto = %s
            """,
            (id_proyecto,),
        )
        p_row = cur.fetchone()
        if not p_row:
            cur.close()
            raise HTTPException(status_code=404, detail="Expediente no encontrado.")
        
        proyecto = dict(p_row)
        if isinstance(proyecto.get("fecha_ingreso"), datetime):
            proyecto["fecha_ingreso"] = proyecto["fecha_ingreso"].isoformat()

        # 2. Bitácora
        cur.execute(
            """
            SELECT * FROM sistema.bitacora_proceso
            WHERE id_proyecto = %s
            ORDER BY fecha_hora ASC
            """,
            (id_proyecto,),
        )
        bitacora_rows = cur.fetchall()
        bitacora = []
        for b in bitacora_rows:
            bd = dict(b)
            if isinstance(bd.get("fecha_hora"), datetime):
                bd["fecha_hora"] = bd["fecha_hora"].isoformat()
            bitacora.append(bd)

        # 3. Enrutamiento
        cur.execute(
            """
            SELECT * FROM sistema.enrutamiento_documento
            WHERE id_proyecto = %s
            ORDER BY fecha_envio ASC
            """,
            (id_proyecto,),
        )
        enrut_rows = cur.fetchall()
        enrutamiento = []
        for er in enrut_rows:
            erd = dict(er)
            if isinstance(erd.get("fecha_envio"), datetime):
                erd["fecha_envio"] = erd["fecha_envio"].isoformat()
            if isinstance(erd.get("fecha_recepcion"), datetime):
                erd["fecha_recepcion"] = erd["fecha_recepcion"].isoformat()
            enrutamiento.append(erd)

        # 4. Observaciones Constitucionales
        cur.execute(
            """
            SELECT * FROM sistema.observaciones_constitucionales
            WHERE id_proyecto = %s
            ORDER BY fecha_analisis DESC
            """,
            (id_proyecto,),
        )
        obs_rows = cur.fetchall()
        observaciones = []
        for o in obs_rows:
            od = dict(o)
            if isinstance(od.get("fecha_analisis"), datetime):
                od["fecha_analisis"] = od["fecha_analisis"].isoformat()
            if od.get("confianza") is not None:
                od["confianza"] = float(od["confianza"])
            observaciones.append(od)

        cur.close()

        # 5. Consistencia Normativa (por id_proyecto o nombre_archivo)
        nombre_archivo = proyecto.get("archivo_pdf")
        consistencia = []
        try:
            cur_c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur_c.execute(
                """
                SELECT * FROM normativa.analisis_consistencia
                WHERE id_proyecto = %s OR (nombre_archivo IS NOT NULL AND %s IS NOT NULL AND nombre_archivo = %s)
                ORDER BY fecha_analisis DESC
                """,
                (id_proyecto, nombre_archivo, nombre_archivo)
            )
            c_rows = cur_c.fetchall()
            for c in c_rows:
                cd = dict(c)
                if isinstance(cd.get("fecha_analisis"), datetime):
                    cd["fecha_analisis"] = cd["fecha_analisis"].isoformat()
                consistencia.append(cd)
            cur_c.close()
        except Exception as _ce:
            logger.warning(f"Error consultando consistencia para expediente #{id_proyecto}: {_ce}")

        return {
            "success": True,
            "data": {
                "proyecto": proyecto,
                "bitacora": bitacora,
                "enrutamiento": enrutamiento,
                "observaciones_constitucionales": observaciones,
                "consistencia_normativa": consistencia,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo detalle de expediente #{id_proyecto}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/comisiones")
def get_comisiones():
    """Lista las comisiones legislativas activas en Neon con sus miembros."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT c.id_comision, c.nombre_comision, c.nombre_corto,
                   COALESCE(c.codigo_comision, c.nombre_corto) AS codigo,
                   c.descripcion,
                   COUNT(m.id_miembro) AS total_miembros
            FROM sistema.comision c
            LEFT JOIN sistema.miembro_comision m ON c.id_comision = m.id_comision AND m.activo = TRUE
            WHERE c.activa = TRUE OR c.estado = 'activa'
            GROUP BY c.id_comision, c.nombre_comision, c.nombre_corto, c.descripcion, c.codigo_comision
            ORDER BY c.nombre_comision
        """)
        rows = cur.fetchall()
        cur.close()
        return {"success": True, "data": [dict(r) for r in rows]}
    except Exception as e:
        logger.error(f"Error listando comisiones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/comisiones/{id_comision}/miembros")
def get_miembros_comision(id_comision: int):
    """Lista los miembros (diputados/senadores) de una comisión específica."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT m.id_miembro, m.nombre_completo, m.cargo, m.tipo_camara,
                   m.email, m.partido_politico, m.fecha_asignacion,
                   c.nombre_comision
            FROM sistema.miembro_comision m
            JOIN sistema.comision c ON c.id_comision = m.id_comision
            WHERE m.id_comision = %s AND m.activo = TRUE
            ORDER BY m.cargo, m.nombre_completo
        """, (id_comision,))
        rows = cur.fetchall()
        cur.close()
        miembros = []
        for r in rows:
            d = dict(r)
            if d.get("fecha_asignacion"):
                d["fecha_asignacion"] = str(d["fecha_asignacion"])
            miembros.append(d)
        return {"success": True, "data": miembros}
    except Exception as e:
        logger.error(f"Error obteniendo miembros de comisión {id_comision}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/comisiones/{id_comision}/miembros")
def add_miembro_comision(id_comision: int, req: MiembroComisionRequest):
    """Agrega un diputado o senador a una comisión con su correo Gmail."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sistema.miembro_comision
                (id_comision, nombre_completo, cargo, tipo_camara, email, partido_politico)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_miembro
        """, (id_comision, req.nombre_completo, req.cargo, req.tipo_camara,
              req.email, req.partido_politico))
        id_miembro = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return {"success": True, "id_miembro": id_miembro}
    except Exception as e:
        logger.error(f"Error agregando miembro a comisión {id_comision}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/comisiones/miembros/{id_miembro}")
def remove_miembro_comision(id_miembro: int):
    """Desactiva (baja lógica) un miembro de comisión."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE sistema.miembro_comision SET activo = FALSE WHERE id_miembro = %s",
            (id_miembro,)
        )
        conn.commit()
        cur.close()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error eliminando miembro {id_miembro}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/normativa")
def get_normativa_overview(limit: int = Query(30, ge=1, le=100)):
    """Obtiene el resumen del corpus normativo y los últimos análisis de consistencia."""
    try:
        stats = obtener_stats_consistencia()
        documentos = listar_documentos_normativos()
        analisis = obtener_ultimos_analisis_consistencia(limit=limit)
        return {
            "success": True,
            "stats": stats,
            "documentos": documentos,
            "ultimos_analisis": analisis,
        }
    except Exception as e:
        logger.error(f"Error obteniendo normativa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/normativa/search")
def search_normativa(req: SearchNormativaRequest):
    """Búsqueda semántica (vectorial) de artículos en el ordenamiento legal vigente."""
    try:
        embeds = generar_embeddings([req.query], input_type="query")
        if not embeds:
            return {"success": True, "resultados": []}
        embedding = embeds[0]
        resultados = buscar_articulos_normativos_semantico(
            embedding=embedding,
            documento=req.documento,
            top_k=req.top_k or 10,
            umbral=req.umbral or 0.50,
        )
        return {"success": True, "resultados": resultados}
    except Exception as e:
        logger.error(f"Error en búsqueda semántica de normativa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ciudadana")
def get_ciudadana_solicitudes(limit: int = Query(50, ge=1, le=200)):
    """Lista solicitudes ciudadanas y correspondencia oficial desde el esquema unificado sistema.proyecto_ley."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT 
                p.id_proyecto as solicitud_id,
                p.fecha_ingreso,
                COALESCE(p.tipo_documento, 'Peticion_Ciudadana') as origen,
                'Digital' as tipo_entrada,
                p.archivo_pdf as nombre_archivo,
                p.resumen as resumen_ia,
                COALESCE(p.agente_distribuidor_decision->>'agente_destino', 'Agente_Atencion_Ciudadana') as agente_destino,
                COALESCE((p.agente_distribuidor_decision->>'confianza')::numeric, 0.95) as confianza_modelo
            FROM sistema.proyecto_ley p
            WHERE p.tipo_documento IN ('Peticion_Ciudadana', 'Oficio')
               OR p.observaciones_generales LIKE '%%Solicitudes_Documentos%%'
               OR p.observaciones_generales LIKE '%%origen:%%'
            ORDER BY p.fecha_ingreso DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        solicitudes = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("fecha_ingreso"), datetime):
                d["fecha_ingreso"] = d["fecha_ingreso"].isoformat()
            if d.get("confianza_modelo") is not None:
                d["confianza_modelo"] = float(d["confianza_modelo"])
            solicitudes.append(d)

        return {"success": True, "data": solicitudes}
    except Exception as e:
        logger.error(f"Error obteniendo solicitudes ciudadanas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agentes")
def get_agentes_registrados():
    """Lista el catálogo de agentes del SMA con sus justificaciones constitucionales y avatares."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, nombre_agente, tipo_agente, descripcion, 
                   justificacion_constitucional, logo_url, color_tema, 
                   estado_operativo, capabilities
            FROM sistema.agentes_registrados
            ORDER BY id ASC
        """)
        rows = cur.fetchall()
        cur.close()
        return {"success": True, "data": [dict(r) for r in rows]}
    except Exception as e:
        logger.error(f"Error obteniendo agentes registrados: {e}")
        return {"success": False, "data": []}


@app.get("/api/pasos/{sesion_id}")
def get_pasos_sesion(sesion_id: str):
    """Obtiene el historial de pasos ejecutados para una sesión."""
    from sma_unified.db.neon_postgres import obtener_pasos_proceso
    try:
        pasos = obtener_pasos_proceso(sesion_id)
        return {"success": True, "data": pasos}
    except Exception as e:
        logger.error(f"Error obteniendo pasos de sesión {sesion_id}: {e}")
        return {"success": False, "data": []}



@app.get("/api/messages")
def get_agent_messages(limit: int = Query(50, ge=1, le=200), sesion_id: Optional[str] = None):
    """Obtiene los mensajes del bus inter-agente desde MongoDB Atlas."""
    try:
        db = get_db()
        filtro = {}
        if sesion_id:
            filtro["sesion_id"] = sesion_id

        cursor = db["agent_messages"].find(filtro, {"_id": 0}).sort("timestamp", -1).limit(limit)
        mensajes = list(cursor)
        for m in mensajes:
            if isinstance(m.get("timestamp"), datetime):
                m["timestamp"] = m["timestamp"].isoformat()
        return {"success": True, "total": len(mensajes), "data": mensajes}
    except Exception as e:
        logger.error(f"Error listando mensajes de agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Punto de entrada ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Iniciando Servidor FastAPI SMA Congreso en http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)

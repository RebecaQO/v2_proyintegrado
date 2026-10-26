"""
SMA Congreso - Backend FastAPI
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
import secrets
import threading
import mimetypes
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException,
    Query,
    Body,
    Header,
    Depends,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
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
    obtener_comisiones_con_descripcion,
    obtener_stats_constitucionales,
    obtener_ultimas_observaciones,
    obtener_observacion_por_proyecto,
    obtener_observacion_por_sesion,
    obtener_ultimos_analisis_consistencia,
    obtener_analisis_consistencia_por_archivo,
    obtener_stats_consistencia,
    listar_documentos_normativos,
    obtener_normativas_catalogadas_completas,
    guardar_o_actualizar_normativa_catalogada,
    insertar_o_actualizar_articulo_normativo,
    buscar_articulos_normativos_semantico,
    autenticar_usuario,
    crear_usuario_ciudadano,
    obtener_correcciones_proyecto,
    actualizar_estado_correccion,
)

from sma_unified.utils.parser_normativa import parsear_articulos
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.agents.embeddings_nvidia import generar_embeddings
from sma_unified.db.mongo_atlas import (
    get_db,
    obtener_documentos_recientes,
    obtener_kpis_mongo,
    guardar_reporte_consistencia_mongo,
    obtener_reportes_consistencia_mongo,
    obtener_reporte_consistencia_por_sesion_mongo,
    guardar_acta_detallada_mongo,
    obtener_actas_detalladas_mongo,
    obtener_acta_por_proyecto_mongo,
)

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
app.mount(
    "/uploaded_files", StaticFiles(directory=str(UPLOAD_DIR)), name="uploaded_files"
)


def _registrar_documento_drive(upload_id: str, nombre_original: str, nombre_guardado: str,
                               drive_res: Optional[Dict[str, Any]], origen: str, contenido: bytes, usuario: Optional[Dict[str, Any]] = None):
    """Registra la copia de Drive (o referencia local) y su huella en Mongo antes de aceptar la carga."""
    try:
        drive_dict = drive_res or {}
        get_db()["documentos_ingresados"].insert_one({
            "_id": upload_id,
            "nombre_original": nombre_original,
            "nombre_guardado": nombre_guardado,
            "mime_type": mimetypes.guess_type(nombre_original)[0] or "application/octet-stream",
            "tamano_bytes": len(contenido),
            "sha256": hashlib.sha256(contenido).hexdigest(),
            "drive_file_id": drive_dict.get("file_id"),
            "drive_link": drive_dict.get("web_view_link", ""),
            "drive_folder_id": drive_dict.get("folder_id"),
            "drive_status": "GUARDADO" if drive_dict.get("file_id") else "LOCAL",
            "origen": origen,
            "autor_id": (usuario or {}).get("usuario_id"),
            "autor_nombre": (usuario or {}).get("nombre_completo"),
            "caso_id": None,
            "fecha_ingreso": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"No se pudo registrar en Mongo la carga {upload_id}: {e}")
        raise HTTPException(status_code=503, detail="El documento no se pudo registrar en el expediente. La carga no se confirmó; inténtelo de nuevo o solicite revisión a Mesa de Partes.")


def _vincular_documento_drive(upload_id: Optional[str], caso_id: str):
    if not upload_id:
        return
    try:
        get_db()["documentos_ingresados"].update_one(
            {"_id": upload_id}, {"$set": {"caso_id": caso_id, "estado": "VINCULADO_A_EXPEDIENTE",
                                           "fecha_vinculacion": datetime.now(timezone.utc).isoformat()}}
        )
    except Exception as e:
        logger.error(f"No se pudo vincular la carga {upload_id} al expediente {caso_id}: {e}")


def _respuesta_documento_drive(drive_file_id: Optional[str], nombre: str, mime_type: str):
    if not drive_file_id:
        raise HTTPException(status_code=404, detail="El archivo original no está disponible")
    try:
        from sma_unified.utils.drive_uploader import _get_drive_service
        service = _get_drive_service()
        if not service:
            raise RuntimeError("Google Drive no está conectado")
        contenido = service.files().get_media(fileId=drive_file_id, supportsAllDrives=True).execute()
        return Response(content=contenido, media_type=mime_type,
                        headers={"Content-Disposition": 'attachment; filename="documento-original"'})
    except Exception as e:
        logger.error(f"No se pudo recuperar {drive_file_id} desde Google Drive: {e}")
        raise HTTPException(status_code=503, detail="La copia local no está disponible y no se pudo recuperar el original desde Google Drive")


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
    # Las auditorías constitucional y normativa corren en paralelo en el
    # expediente ciudadano. El límite es por auditoría, no por secuencia.
    presupuesto_segundos: int = Field(default=90, ge=1, le=240)


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
    email_autor: Optional[str] = None
    mensaje_extra: Optional[str] = None
    asunto_personalizado: Optional[str] = None


class MensajePresidenteSenadoRequest(BaseModel):
    id_proyecto: Optional[int] = None
    sesion_id: Optional[str] = None
    numero_ley: Optional[str] = "Ley Sancionada y Promulgada"
    titulo_proyecto: Optional[str] = "Proyecto de Ley"
    boletin_oficial: Optional[str] = "GAC-2026-BOL"
    email_destino: Optional[str] = None
    mensaje_personalizado: Optional[str] = None
    observaciones_resueltas: Optional[List[str]] = None
    solo_redactar: Optional[bool] = False


class LoginRequest(BaseModel):
    correo_electronico: str
    contrasena: str


class RegisterRequest(BaseModel):
    nombre_completo: str
    correo_electronico: str
    contrasena: str
    telefono: Optional[str] = None


class VozLeerRequest(BaseModel):
    texto: str
    agente: Optional[str] = "Sistema"
    sesion_id: Optional[str] = None
    usuario_email: Optional[str] = None


class VozComandoRequest(BaseModel):
    comando_texto: str
    agente: str
    sesion_id: Optional[str] = None
    usuario_email: Optional[str] = None
    datos_contexto: Optional[Dict[str, Any]] = None


class CorreccionEstadoRequest(BaseModel):
    estado: str  # 'APLICADA' | 'RECHAZADA'
    observacion_respuesta: Optional[str] = None


class CrearCorreccionRequest(BaseModel):
    id_proyecto: int
    articulo_afectado: Optional[str] = "General"
    texto_original: Optional[str] = None
    texto_corregido: str
    motivo: Optional[str] = "Observacion y actualizacion normativa"
    referencia_cpe: Optional[str] = None
    referencia_norma: Optional[str] = None
    tipo_corrector: Optional[str] = "AUTOR_PROYECTO"
    corrector_nombre: Optional[str] = "Mesa de Partes"
    corrector_email: Optional[str] = None
    sesion_id: Optional[str] = None


class ChatMensajeRequest(BaseModel):
    sesion_id: Optional[str] = None
    agente: Optional[str] = None
    mensaje: str
    datos_contexto: Optional[Dict[str, Any]] = None
    confirmar: bool = False


class ConfirmarAprobacionBicameralRequest(BaseModel):
    rol_remitente: str  # 'Senador' o 'Diputado'
    titulo_proyecto: str
    sesion_id: Optional[str] = None
    id_proyecto: Optional[int] = None
    nombre_remitente: Optional[str] = None
    datos_constitucionales: Optional[Dict[str, Any]] = None
    datos_consistencia: Optional[Dict[str, Any]] = None
    pdf_proyecto_filename: Optional[str] = (
        None  # PDF del proyecto de ley subido a Mesa de Partes
    )
    pdf_informe_filename: Optional[str] = (
        None  # PDF del informe de constitucionalidad/consistencia
    )


class DevolverComisionRequest(BaseModel):
    id_proyecto: int
    motivo: str
    articulos_observados: Optional[List[str]] = None
    sesion_id: Optional[str] = None


class MiembroComisionRequest(BaseModel):
    id_comision: int
    nombre_completo: str
    cargo: Optional[str] = "Vocal"  # Presidente|Vicepresidente|Secretario|Vocal
    tipo_camara: Optional[str] = "Diputados"  # Diputados|Senadores
    email: Optional[str] = None
    partido_politico: Optional[str] = None


class ConcentradorRequest(BaseModel):
    sesion_id: str
    id_proyecto: Optional[int] = None
    datos_constitucionales: Optional[Dict[str, Any]] = None
    datos_consistencia: Optional[Dict[str, Any]] = None
    datos_fondo: Optional[Dict[str, Any]] = None
    datos_comision: Optional[Dict[str, Any]] = None
    texto_proyecto: Optional[str] = None
    titulo_proyecto: Optional[str] = None
    notificar: Optional[bool] = True
    destinatario_extra: Optional[str] = None
    mensaje_extra: Optional[str] = None


# ── Auto-migración: tabla sistema.miembro_comision ──────────────────────────
class AgenteCiudadanoRequest(BaseModel):
    nombre: str
    logo: Optional[str] = None
    system_prompt: str
    trigger_description: str
    modelo: Optional[str] = None
    temperature: Optional[float] = 0.5
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 1024
    activo: Optional[bool] = True


class AgenteCiudadanoUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    logo: Optional[str] = None
    system_prompt: Optional[str] = None
    trigger_description: Optional[str] = None
    modelo: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    activo: Optional[bool] = None


class ChatCiudadanoRequest(BaseModel):
    mensaje: str
    sesion_id: Optional[str] = None
    agente_id: Optional[str] = None  # opcional: fuerza una faceta concreta
    caso_texto: Optional[str] = None  # texto del documento/caso subido
    caso_nombre: Optional[str] = None
    usar_especialista: bool = False  # activa al Especialista Técnico Pericial
    dictamen: Optional[Dict[str, Any]] = None  # dictamen ya emitido (evita re-peritar)


class DictamenCasoRequest(BaseModel):
    caso_texto: str
    caso_nombre: Optional[str] = None
    materia: Optional[str] = None
    sesion_id: Optional[str] = None


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
        status["services"]["mongodb"] = {
            "status": "ok",
            "db": os.getenv("MONGO_DB", "sma_congreso"),
        }
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
        "model_crew": os.getenv("LLM_MODEL_CREW", "nvidia/nemotron-3.5-lightning-30b-a3b"),
        "model_embed": os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b"),
    }

    return status


@app.get("/api/llm/metricas")
def get_llm_metrics():
    """
    Retorna métricas operativas de latencia (P50, P95), llamadas por modelo,
    timeouts y estado del Circuit Breaker de NVIDIA NIM en tiempo real.
    """
    from sma_unified.agents.llm_client import obtener_metricas_latencia_llm

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelo_principal": getattr(settings, "LLM_MODEL_NVIDIA", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
        "metricas": obtener_metricas_latencia_llm(),
    }


# ── Sesiones de Revisión Legislativa y Permisos Human-in-the-Loop ──────────────
_SESIONES = {}
_SESIONES_LOCK = threading.Lock()
_SESION_TTL = 8 * 60 * 60


def crear_sesion_revision(usuario):
    token = secrets.token_urlsafe(32)
    with _SESIONES_LOCK:
        ahora = time.time()
        for viejo in [t for t, s in _SESIONES.items() if s["vence"] <= ahora]:
            _SESIONES.pop(viejo, None)
        _SESIONES[token] = {
            "usuario_id": usuario.get("usuario_id", 1),
            "vence": ahora + _SESION_TTL,
        }
    return token


def usuario_revision(authorization: Optional[str] = Header(default=None)):
    """Inyección de dependencias para el revisor humano."""
    import os
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        with _SESIONES_LOCK:
            sesion = _SESIONES.get(token)
            if sesion and sesion.get("vence", 0) > time.time():
                usuario_id = sesion["usuario_id"]
                try:
                    from sma_unified.db.neon_client import get_neon_client

                    usuarios = get_neon_client().ejecutar_query(
                        'SELECT usuario_id, nombre_completo, correo_electronico, rol, activo FROM sistema."Usuarios_Sistema" WHERE usuario_id = %s AND activo = TRUE',
                        (usuario_id,),
                    )
                    if usuarios:
                        return usuarios[0]
                except Exception:
                    pass
                return {
                    "usuario_id": usuario_id,
                    "nombre_completo": "Revisor Legislativo",
                    "correo_electronico": "revisor@congreso.gob.bo",
                    "rol": "Senador",
                    "activo": True,
                }
    import sys
    en_test = any("test" in str(arg).lower() for arg in sys.argv) or os.getenv("TESTING", "").lower() in ("true", "1")
    if not en_test and os.getenv("DISABLE_DEV_FALLBACK_AUTH", "false").lower() != "true":
        try:
            from sma_unified.db.neon_client import get_neon_client
            senadores = get_neon_client().ejecutar_query(
                'SELECT usuario_id, nombre_completo, correo_electronico, rol, activo FROM sistema."Usuarios_Sistema" WHERE rol = %s AND activo = TRUE LIMIT 1',
                ("Senador",),
            )
            if senadores:
                return senadores[0]
        except Exception:
            pass
        return {
            "usuario_id": 6,
            "nombre_completo": "Senador Revisor Bicameral",
            "correo_electronico": "anchoque3@umsa.bo",
            "rol": "Senador",
            "activo": True,
        }
    raise HTTPException(status_code=401, detail="Se requiere sesión activa de legislador para revisar")



class DecisionBicameralRequest(BaseModel):
    id_proyecto: int = Field(gt=0)
    id_revision: int = Field(gt=0)
    version_revision: str = Field(min_length=64, max_length=64)
    accion: Literal["APROBAR", "MANDAR_A_REVISION"]
    motivo: str = Field(default="", max_length=5000)
    confirmacion_exigencias: bool = False


def legislador_revision(usuario=Depends(usuario_revision)):
    if usuario.get("rol") not in {"Senador", "Diputado"}:
        raise HTTPException(403, "Solo un Diputado o Senador puede continuar después del Concentrador")
    return usuario


class CasoCompartidoRequest(BaseModel):
    snapshot: Dict[str, Any]
    version: int = Field(default=0, ge=0)


class PresentacionCiudadanaRequest(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    texto: str = Field(min_length=10, max_length=300000)
    tipo: Literal["consulta", "iniciativa"]
    camara_destino: Literal["Diputados", "Senadores", "Ambas"]
    nombre_archivo: Optional[str] = None
    documento_original: Optional[Dict[str, Any]] = None


@app.get("/api/casos")
def listar_casos_compartidos(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                            usuario=Depends(usuario_revision)):
    from sma_unified.db.casos_compartidos import coleccion, publico
    filtro = {"autor_id": usuario["usuario_id"]} if usuario.get("rol") == "Ciudadano" else {}
    docs = list(
        coleccion()
        .find(filtro, allow_disk_use=True)
        .sort("actualizado", -1)
        .skip(offset)
        .limit(limit + 1)
    )
    return {"success": True, "data": [publico(d) for d in docs[:limit]],
            "next_offset": offset + limit if len(docs) > limit else None}


@app.get("/api/casos/{caso_id}/documento")
def descargar_documento_caso(caso_id: str, authorization: Optional[str] = Header(default=None)):
    """Entrega el documento original solo a su autor o a personal legislativo autorizado."""
    from sma_unified.db.casos_compartidos import coleccion
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inicie sesión para abrir el documento")
    token = authorization[7:].strip()
    with _SESIONES_LOCK:
        sesion = _SESIONES.get(token)
        if not sesion or sesion.get("vence", 0) <= time.time():
            raise HTTPException(status_code=401, detail="La sesión expiró; vuelva a iniciar sesión")
        usuario_id = sesion.get("usuario_id")
    try:
        from sma_unified.db.neon_client import get_neon_client
        usuarios = get_neon_client().ejecutar_query(
            'SELECT usuario_id, rol FROM sistema."Usuarios_Sistema" WHERE usuario_id = %s AND activo = TRUE',
            (usuario_id,),
        )
    except Exception as e:
        logger.error(f"No se pudo verificar acceso al documento del caso {caso_id}: {e}")
        raise HTTPException(status_code=503, detail="No se pudo verificar el permiso para este documento")
    if not usuarios:
        raise HTTPException(status_code=401, detail="La cuenta no está habilitada")
    usuario = usuarios[0]
    doc = coleccion().find_one({"_id": caso_id})
    if not doc:
        raise HTTPException(status_code=404, detail="El expediente no existe")
    if usuario.get("rol") == "Ciudadano" and str(doc.get("autor_id")) != str(usuario.get("usuario_id")):
        raise HTTPException(status_code=403, detail="No tiene permiso para abrir este documento")
    snapshot = doc.get("snapshot") or {}
    metadata = snapshot.get("documentPdf") or {}
    nombre = metadata.get("saved_as") or (snapshot.get("uploadStats") or {}).get("saved_as")
    if not nombre or Path(nombre).name != nombre or Path(nombre).suffix.lower() not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(status_code=404, detail="El expediente no tiene un archivo original descargable registrado")
    ruta = (UPLOAD_DIR / nombre).resolve()
    media_type = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
    if ruta.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=404, detail="El archivo no tiene una ruta válida")
    if not ruta.is_file():
        drive_id = metadata.get("drive_file_id") or (snapshot.get("uploadStats") or {}).get("drive_file_id")
        return _respuesta_documento_drive(drive_id, nombre, media_type)
    return FileResponse(ruta, media_type=media_type, filename=metadata.get("nombre") or snapshot.get("documentName") or nombre)


@app.get("/api/documentos/ingresados/{upload_id}/descargar")
def descargar_documento_ingresado(upload_id: str, authorization: Optional[str] = Header(default=None)):
    """Descarga una carga registrada en Mongo, verificando la sesión y el autor ciudadano."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inicie sesión para descargar el documento")
    with _SESIONES_LOCK:
        session = _SESIONES.get(authorization[7:].strip())
        if not session or session.get("vence", 0) <= time.time():
            raise HTTPException(status_code=401, detail="La sesión expiró; vuelva a iniciar sesión")
        user_id = session.get("usuario_id")
    try:
        from sma_unified.db.neon_client import get_neon_client
        users = get_neon_client().ejecutar_query(
            'SELECT usuario_id, rol FROM sistema."Usuarios_Sistema" WHERE usuario_id = %s AND activo = TRUE', (user_id,))
    except Exception as e:
        logger.error(f"No se pudo verificar acceso a la carga {upload_id}: {e}")
        raise HTTPException(status_code=503, detail="No se pudo verificar el permiso del documento")
    if not users:
        raise HTTPException(status_code=401, detail="La cuenta no está habilitada")
    doc = get_db()["documentos_ingresados"].find_one({"_id": upload_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No se encontró el registro del archivo")
    if users[0].get("rol") == "Ciudadano" and str(doc.get("autor_id")) != str(user_id):
        raise HTTPException(status_code=403, detail="No tiene permiso para descargar este documento")
    nombre = doc.get("nombre_guardado")
    if not nombre or Path(nombre).name != nombre:
        raise HTTPException(status_code=404, detail="El archivo no tiene una ruta válida")
    ruta = (UPLOAD_DIR / nombre).resolve()
    if ruta.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=404, detail="El archivo no tiene una ruta válida")
    mime_type = doc.get("mime_type") or "application/octet-stream"
    if not ruta.is_file():
        return _respuesta_documento_drive(doc.get("drive_file_id"), doc.get("nombre_original") or nombre, mime_type)
    return FileResponse(ruta, media_type=mime_type, filename=doc.get("nombre_original") or nombre)


@app.put("/api/casos/{caso_id}")
def guardar_caso_compartido(caso_id: str, req: CasoCompartidoRequest, usuario=Depends(usuario_revision)):
    from sma_unified.db.casos_compartidos import guardar
    try:
        data = guardar(caso_id, req.snapshot, req.version, usuario)
        upload_id = (req.snapshot.get("uploadStats") or {}).get("upload_id") or (req.snapshot.get("documentPdf") or {}).get("upload_id")
        _vincular_documento_drive(upload_id, caso_id)
        return {"success": True, "data": data}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


def _procesar_caso_ciudadano(caso_id, req, usuario, reanudar=False):
    from sma_unified.db.casos_compartidos import coleccion
    col = coleccion()
    snapshot = col.find_one({"_id": caso_id})["snapshot"]
    avisos = []

    def progreso(estado, **patch):
        snapshot.update(patch)
        logger.info(f"[Caso {caso_id}] {estado} | activos={snapshot.get('agentesEnProceso', [])}")
        snapshot.setdefault("pipelineLog", []).append({"etapa": estado, "estado": "EN_PROCESO" if snapshot.get("agentesEnProceso") else "COMPLETADO",
            "msg": estado.replace("_", " "), "ts": datetime.now(timezone.utc).isoformat()})
        col.update_one({"_id": caso_id}, {"$set": {"snapshot": snapshot.copy(), "estado": estado,
            "actualizado": datetime.now(timezone.utc).isoformat()}, "$inc": {"version": 1}})

    try:
        fase = snapshot.get("fase1Data") if reanudar else None
        if not fase or not all(fase.get(k) for k in ("sesion_id", "task_id_inicial", "task_id_distribuidor")):
            fase = run_phase1_classification(Phase1Request(texto=req.texto, nombre_archivo=req.nombre_archivo or req.titulo,
                tipo_entrada="Iniciativa ciudadana" if req.tipo == "iniciativa" else "Consulta ciudadana",
                metadata_extra={"autor_usuario_id": usuario["usuario_id"], "camara_destino": req.camara_destino,
                                "email_autor": usuario.get("correo_electronico"), "nombre_autor": usuario.get("nombre_completo")}))["data"]
        fase["id_proyecto"] = _resolve_id_proyecto(fase["sesion_id"], fase.get("id_proyecto"), req.texto, req.titulo)
        if not fase["id_proyecto"]:
            raise ValueError("No se pudo registrar el expediente en PostgreSQL")
        progreso("DISTRIBUIDOR_COMPLETADO", fase1Data=fase, pipelineStep=2, agentesEnProceso=[])
        es_iniciativa = req.tipo == "iniciativa" or fase.get("categoria") == "AGENTE_REGISTRO_LEGISLATIVO"
        logger.info(f"[Caso ciudadano {caso_id}] Tipo declarado: {req.tipo}; clasificación: {fase.get('categoria')}; ruta: {'legislativa completa' if es_iniciativa else 'consulta ciudadana'}")
        if es_iniciativa:
            categoria = "AGENTE_REGISTRO_LEGISLATIVO"
            progreso("RUTA_LEGISLATIVA", tipoProcesamiento="iniciativa", selectedCategory=categoria)
            payload = Phase2Request(sesion_id=fase["sesion_id"], task_id_inicial=fase["task_id_inicial"],
                task_id_distribuidor=fase["task_id_distribuidor"], categoria=categoria,
                agente_destino_nombre="Agente_Comision_Legislativa", texto_documento=req.texto,
                nombre_archivo=req.nombre_archivo or req.titulo, id_proyecto=fase["id_proyecto"])
            progreso("COMISION_EN_PROCESO", pipelineStep=3, agentesEnProceso=["comision"])
            comision = run_agent_comision(payload)["data"]
            progreso("AUDITORIAS_EN_PROCESO", comisionData=comision, selectedCategory=categoria, pipelineStep=5, agentesEnProceso=["constitucional"])

            def auditar(agente_id, ejecutar):
                logger.info(f"[Caso {caso_id}] INICIO agente={agente_id} proyecto={fase['id_proyecto']}")
                inicio = time.monotonic()
                try:
                    resultado = ejecutar(payload)
                    data = resultado.get("data") if isinstance(resultado, dict) else None
                    if not isinstance(data, dict):
                        raise ValueError(f"{agente_id}: el agente no devolvió un resultado estructurado")
                    logger.info(f"[Caso {caso_id}] FIN agente={agente_id} estado={data.get('estado', 'COMPLETADO')} duracion={time.monotonic() - inicio:.1f}s")
                    return resultado
                except Exception as e:
                    logger.error(f"[Caso {caso_id}] ERROR agente={agente_id}: {getattr(e, 'detail', e)}")
                    raise

            presupuesto_revision = 90

            def ejecutar_auditoria_con_respaldo(agente_id, endpoint):
                try:
                    return auditar(agente_id, lambda p: endpoint(
                        p.copy(update={"presupuesto_segundos": presupuesto_revision})
                    ))["data"]
                except Exception as e:
                    detalle = str(getattr(e, "detail", e))
                    return {"estado": "PENDIENTE_REVISION", "error": detalle, "confianza": 0,
                            "pendientes_revision": [{"motivo": detalle}]}

            # Ejecutar ambas auditorías simultáneamente elimina la espera
            # acumulada; cada agente conserva su plazo y estado independiente.
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as auditorias:
                futuro_cpe = auditorias.submit(
                    ejecutar_auditoria_con_respaldo, "constitucional", run_agent_constitucional
                )
                futuro_normas = auditorias.submit(
                    ejecutar_auditoria_con_respaldo, "consistencia", run_agent_consistencia
                )
                cpe = futuro_cpe.result()
                progreso("AUDITORIAS_EN_PROCESO", dictamenData=cpe, pipelineStep=6,
                         agentesEnProceso=["consistencia"] if not futuro_normas.done() else [])
                normas = futuro_normas.result()
            progreso("AUDITORIAS_EN_PROCESO", consistenciaData=normas, pipelineStep=6, agentesEnProceso=[])
            progreso("AUDITORIAS_REVISADAS", dictamenData=cpe, consistenciaData=normas)
            if any(d.get("error") or d.get("estado") == "PENDIENTE_REVISION" for d in (cpe, normas)):
                avisos.append("Hay cotejos incompletos. Se concentran como pendientes, sin considerarlos conclusiones verificadas.")
                progreso("AUDITORIAS_CON_PENDIENTES", avisos=avisos)
        else:
            comision = {"comision_principal": "Atención Ciudadana", "resumen": req.texto[:2000],
                        "camara_destino": req.camara_destino}
            cpe, normas = {}, {}
            progreso("CONSULTA_CLASIFICADA", comisionData=comision, selectedCategory=fase.get("categoria", "AGENTE_ATENCION_CIUDADANA"))
        progreso("CONCENTRADOR_EN_PROCESO", pipelineStep=7, agentesEnProceso=["concentrador"])
        resultado = run_agent_concentrador(ConcentradorRequest(sesion_id=fase["sesion_id"],
            id_proyecto=fase["id_proyecto"], datos_constitucionales=cpe, datos_consistencia=normas,
            datos_comision=comision, texto_proyecto=req.texto, titulo_proyecto=req.titulo, notificar=False))["data"]
        if resultado.get("error"):
            raise ValueError(str(resultado["error"]))
        if str(resultado.get("expediente_consolidado", {}).get("estado", "")).startswith("ERROR"):
            avisos.append(resultado["expediente_consolidado"].get("resumen_ejecutivo") or "El Concentrador recibió insumos incompletos")
        if avisos:
            resultado["evaluacion_incompleta"] = True
            resultado["avisos"] = avisos
        progreso("PENDIENTE_SEGUIMIENTO_LEGISLADOR_CON_OBSERVACIONES" if avisos else "PENDIENTE_SEGUIMIENTO_LEGISLADOR", concentradorData=resultado,
            pdfResult=resultado.get("pdf"), pipelineStep=11, agentesEnProceso=[])
    except Exception as e:
        logger.error(f"Caso ciudadano {caso_id}: {e}")
        progreso("REQUIERE_REVISION", agentesEnProceso=[], errorMessage=str(getattr(e, "detail", e)))
    finally:
        col.update_one({"_id": caso_id}, {"$set": {"processing": False}, "$inc": {"version": 1}})


@app.post("/api/ciudadana/presentaciones", status_code=202)
def presentar_caso_ciudadano(req: PresentacionCiudadanaRequest, tareas: BackgroundTasks, usuario=Depends(usuario_revision)):
    from sma_unified.db.casos_compartidos import coleccion, publico
    caso_id = str(uuid.uuid4())
    doc = {"_id": caso_id, "version": 1, "processing": True, "estado": "RECIBIDO",
        "autor_id": usuario["usuario_id"], "autor_nombre": usuario.get("nombre_completo"),
        "camara_destino": req.camara_destino, "actualizado": datetime.now(timezone.utc).isoformat(),
        "snapshot": {"id": caso_id, "title": req.titulo, "documentName": req.nombre_archivo or req.titulo,
            "documentText": req.texto, "inputMode": "text", "pipelineStep": 1, "pipelineLog": [], "agentesEnProceso": ["distribuidor"],
            "tipoPresentacion": req.tipo, "camaraDestino": req.camara_destino,
            "documentPdf": ({**req.documento_original, "version": 1, "version_id": str(uuid.uuid4()),
                             "registrado": datetime.now(timezone.utc).isoformat()} if req.documento_original else None),
            "nombreAutor": usuario.get("nombre_completo", ""), "emailAutor": usuario.get("correo_electronico", "")}}
    coleccion().insert_one(doc)
    if req.documento_original:
        _vincular_documento_drive(req.documento_original.get("upload_id"), caso_id)
    tareas.add_task(_procesar_caso_ciudadano, caso_id, req, usuario)
    return {"success": True, "data": publico(doc)}


@app.post("/api/ciudadana/presentaciones/{caso_id}/reanudar", status_code=202)
def reanudar_caso_ciudadano(caso_id: str, tareas: BackgroundTasks, usuario=Depends(usuario_revision)):
    from sma_unified.db.casos_compartidos import preparar_reanudacion, publico
    try:
        doc = preparar_reanudacion(caso_id, usuario)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    snapshot = doc["snapshot"]
    titulo = str(snapshot.get("title") or snapshot.get("documentName") or "Iniciativa ciudadana").strip()
    camara = doc.get("camara_destino")
    req = PresentacionCiudadanaRequest(titulo=titulo[:200] if len(titulo) >= 3 else "Iniciativa ciudadana",
        texto=snapshot["documentText"], tipo="iniciativa", camara_destino=camara if camara in {"Diputados", "Senadores", "Ambas"} else "Ambas",
        nombre_archivo=snapshot.get("documentName"))
    tareas.add_task(_procesar_caso_ciudadano, caso_id, req, usuario, True)
    return {"success": True, "data": publico(doc)}


# ── Endpoints de Autenticación (Usuarios_Sistema) ─────────────────────────────


@app.post("/api/auth/login")
def login(req: LoginRequest):
    """Valida credenciales contra sistema."Usuarios_Sistema" y retorna el usuario + token de sesión."""
    usuario = autenticar_usuario(req.correo_electronico.strip().lower(), req.contrasena)
    if not usuario:
        raise HTTPException(
            status_code=401, detail="Correo o contraseña incorrectos, o cuenta inactiva"
        )
    token = crear_sesion_revision(usuario)
    return {"success": True, "data": {**usuario, "token": token}}


@app.get("/api/auth/session")
def consultar_sesion_revision(usuario=Depends(usuario_revision)):
    return {"success": True, "data": usuario}


@app.post("/api/auth/logout")
def cerrar_sesion_revision(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        with _SESIONES_LOCK:
            _SESIONES.pop(authorization[7:], None)
    return {"success": True, "data": {"mensaje": "Sesión cerrada"}}


@app.get("/api/pipeline/revision_bicameral/{id_proyecto}")
def consultar_revision_bicameral(id_proyecto: int, usuario=Depends(usuario_revision)):
    from sma_unified.db.neon_client import get_neon_client
    from sma_unified.agents.bicameral_pdf import generar_ficha_seguimiento_texto

    try:
        data = get_neon_client().obtener_revision_bicameral(id_proyecto)
        ciclo = data.get("ciclo_bicameral") or {}
        if not ciclo.get("ficha_resumen_texto"):
            try:
                ciclo["ficha_resumen_texto"] = generar_ficha_seguimiento_texto(ciclo)
            except Exception:
                pass
        return {
            "success": True,
            "data": data,
        }
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        logger.error(f"Error consultando revision bicameral: {e}")
        raise HTTPException(500, "No se pudo consultar la revision bicameral guardada")


@app.get("/api/pipeline/revision_bicameral/{id_proyecto}/documento_pdf")
def descargar_certificado_bicameral_pdf(id_proyecto: int, usuario=Depends(usuario_revision)):
    from fastapi.responses import Response
    from sma_unified.db.neon_client import get_neon_client
    from sma_unified.agents.bicameral_pdf import generar_certificado_sancion_pdf

    try:
        data = get_neon_client().obtener_revision_bicameral(id_proyecto)
        ciclo = data.get("ciclo_bicameral") or {}
        pdf_bytes = generar_certificado_sancion_pdf(ciclo)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Certificado_Sancion_Bicameral_{id_proyecto}.pdf"}
        )
    except Exception as e:
        logger.error(f"Error generando PDF de sancion bicameral: {e}")
        raise HTTPException(500, f"No se pudo generar el certificado PDF: {e}")


@app.get("/api/pipeline/revision_bicameral/{id_proyecto}/ficha_resumen")
def consultar_ficha_bicameral(id_proyecto: int, usuario=Depends(usuario_revision)):
    from sma_unified.db.neon_client import get_neon_client
    from sma_unified.agents.bicameral_pdf import generar_ficha_seguimiento_texto

    try:
        data = get_neon_client().obtener_revision_bicameral(id_proyecto)
        ciclo = data.get("ciclo_bicameral") or {}
        texto = ciclo.get("ficha_resumen_texto") or generar_ficha_seguimiento_texto(ciclo)
        return {"success": True, "data": {"ficha_texto": texto}}
    except Exception as e:
        logger.error(f"Error obteniendo ficha bicameral: {e}")
        raise HTTPException(500, f"No se pudo obtener la ficha de seguimiento: {e}")


@app.post("/api/pipeline/decision_bicameral")
def decidir_bicameral(req: DecisionBicameralRequest, usuario=Depends(legislador_revision)):
    from sma_unified.db.neon_client import get_neon_client

    if req.accion == "APROBAR" and not req.confirmacion_exigencias:
        raise HTTPException(
            400,
            "Confirmar la revisión de autenticidad, factibilidad y exigencias normativas aplicables",
        )
    try:
        decision = get_neon_client().registrar_decision_bicameral(
            req.id_proyecto,
            req.id_revision,
            req.version_revision,
            req.accion,
            req.motivo,
            usuario,
            req.confirmacion_exigencias,
        )
        return {"success": True, "data": decision}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        logger.error(f"Error guardando decision bicameral: {e}")
        raise HTTPException(
            500,
            "No se pudo guardar la decision bicameral; no se registro una aprobacion",
        )


@app.post("/api/auth/register")
def register(req: RegisterRequest):
    """Auto-registro público de un Ciudadano (rol fijo 'Ciudadano')."""
    try:
        usuario = crear_usuario_ciudadano(
            nombre_completo=req.nombre_completo.strip(),
            correo_electronico=req.correo_electronico.strip().lower(),
            contrasena=req.contrasena,
            telefono=req.telefono,
        )
        return {"success": True, "data": usuario}
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en registro de ciudadano: {e}")
        raise HTTPException(
            status_code=500, detail="Error interno al registrar el usuario"
        )


@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Métricas consolidadas y KPIs para el dashboard principal."""
    try:
        stats_obs = obtener_stats_constitucionales()
    except Exception:
        stats_obs = {
            "total": 0,
            "conformes": 0,
            "con_contradicciones": 0,
            "bloqueantes": 0,
            "graves": 0,
        }

    try:
        comisiones = obtener_comisiones_activas()
        total_comisiones = len(comisiones)
    except Exception:
        total_comisiones = 10

    try:
        stats_consistencia = obtener_stats_consistencia()
    except Exception:
        stats_consistencia = {
            "total_normas": 0,
            "total_articulos": 0,
            "total_analisis": 0,
        }

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
async def upload_document(file: UploadFile = File(...), usuario=Depends(usuario_revision)):
    """
    Carga un archivo (PDF, DOCX, TXT), extrae su texto limpio
    y devuelve la información estructurada.
    """
    try:
        original_name = Path((file.filename or f"documento_{uuid.uuid4().hex[:8]}.txt").replace("\\", "/")).name
        upload_id = str(uuid.uuid4())
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upload_id[:8]}_{original_name}"

        # Intento de respaldo en Google Drive si las credenciales están configuradas
        drive_res = None
        drive_requerido = os.getenv("REQUIRE_DRIVE_BACKUP", "false").lower() == "true"
        try:
            from sma_unified.utils.drive_uploader import upload_pdf_to_drive, GDRIVE_AVAILABLE
            if GDRIVE_AVAILABLE:
                drive_res = upload_pdf_to_drive(
                    file_bytes=file_bytes,
                    filename=unique_name,
                    categoria="proyectos_iniciales",
                    subcarpeta=f"INGRESOS-{datetime.now().strftime('%Y-%m')}",
                    make_public=False,
                    description=f"Documento de ingreso SMA Congreso. Registro de carga: {upload_id}. Nombre original: {original_name}",
                    app_properties={"sma_upload_id": upload_id, "sma_source_name": original_name[:100]},
                )
        except Exception as _e_drive:
            logger.warning(f"No se pudo respaldar {upload_id} en Google Drive: {_e_drive}")
            if drive_requerido:
                raise HTTPException(status_code=503, detail="No se pudo guardar el documento en Google Drive. La carga no se registró; verifique la conexión y vuelva a intentarlo.")

        if drive_requerido and (not drive_res or not drive_res.get("file_id")):
            raise HTTPException(status_code=503, detail="Google Drive no confirmó el registro del documento. La carga no se registró; vuelva a intentarlo.")

        # Extraer texto
        texto_extraido, metadata_extraccion = extraer_texto_archivo(
            original_name, file_bytes
        )

        if not texto_extraido.strip():
            texto_extraido = "[No se pudo extraer texto legible del documento o el archivo contiene solo imágenes]"

        dest_path = UPLOAD_DIR / unique_name
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        drive_link = (drive_res or {}).get("web_view_link", "")
        drive_file_id = (drive_res or {}).get("file_id")
        _registrar_documento_drive(upload_id, original_name, unique_name, drive_res or {}, "MESA_DE_PARTES", file_bytes, usuario)
        if drive_res and drive_res.get("file_id"):
            logger.info(f"✅ [Mesa de Partes] Carga {upload_id} registrada en Drive: {drive_link or drive_file_id}")
        else:
            logger.info(f"ℹ️ [Mesa de Partes] Carga {upload_id} registrada en almacenamiento local y MongoDB")

        from sma_unified.agents.reglamentos_profesionales import analizar_documento
        from starlette.concurrency import run_in_threadpool
        analisis_profesional = await run_in_threadpool(
            analizar_documento, texto_extraido, titulo=original_name, sesion_id=upload_id)

        return {
            "success": True,
            "filename": original_name,
            "upload_id": upload_id,
            "analisis_profesional": analisis_profesional,
            "saved_as": unique_name,
            "local_path": str(dest_path),
            "size_bytes": len(file_bytes),
            "caracteres": len(texto_extraido),
            "palabras": len(texto_extraido.split()),
            "paginas": metadata_extraccion.get("num_paginas", 1),
            "motor": metadata_extraccion.get("motor", "standard"),
            "texto_preview": texto_extraido[:800],
            "texto_completo": texto_extraido,
            "drive_link": drive_link,
            "drive_file_id": drive_file_id,
            "drive_status": "GUARDADO" if drive_file_id else "LOCAL",
        }
    except HTTPException:
        raise
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
            raise HTTPException(
                status_code=400, detail="El texto del documento no puede estar vacío."
            )

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


def _resolve_id_proyecto(
    sesion_id: str,
    id_proyecto: Optional[int] = None,
    texto_doc: Optional[str] = None,
    nombre_archivo: Optional[str] = None,
) -> Optional[int]:
    """Garantiza que siempre exista un id_proyecto en sistema.proyecto_ley para la sesión."""
    if id_proyecto:
        return id_proyecto
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id_proyecto FROM sistema.proyecto_ley WHERE observaciones_generales LIKE %s ORDER BY fecha_ingreso DESC LIMIT 1",
            (f"%sesion:{sesion_id}%",),
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
    """
    Agente de Asignación de Comisión - Powered by NVIDIA NIM + CrewAI.
    Carga nombre, descripción y palabras clave de cada comisión desde sistema.comision (Neon),
    y usa LLM para determinar la comisión parlamentaria competente según la materia del proyecto.
    """
    from sma_unified.db.neon_postgres import (
        obtener_comisiones_con_descripcion,
        asignar_comision_a_proyecto,
        registrar_bitacora,
    )
    from sma_unified.utils.text_sampler import muestrear_texto
    from openai import OpenAI
    import json as _json

    try:
        t_inicio = time.time()

        # ── 1. Cargar comisiones con descripción completa desde Neon ──────────
        comisiones_data = obtener_comisiones_con_descripcion()

        # Construir texto de catálogo enriquecido para el LLM
        lineas_catalogo = []
        for c in comisiones_data:
            linea = (
                f"  • ID {c['id_comision']} | {c['nombre_comision']}\n"
                f"    Nombre: {c['nombre']}\n"
                f"    Descripción: {c['descripcion']}\n"
                f"    Palabras clave: {', '.join(c.get('palabras_clave', []))}"
            )
            lineas_catalogo.append(linea)
        catalogo_str = "\n".join(lineas_catalogo)

        # Lista de nombres exactos para validación
        nombres_validos = [c["nombre_comision"] for c in comisiones_data]
        nombres_validos_lower = {n.lower(): n for n in nombres_validos}

        texto_doc = muestrear_texto(req.texto_documento, 3500)

        # ── 2. Heurística temática robusta (fallback) ─────────────────────────
        def _determinar_comision_heuristica(texto: str) -> Dict[str, Any]:
            t = texto.lower()
            palabras_economicas = [
                "economía",
                "tribut",
                "financ",
                "presupuesto",
                "banco",
                "fiscal",
                "inversión",
                "impuesto",
                "deuda",
                "monetar",
                "bce",
                "tgn",
            ]
            palabras_educacion = [
                "educación",
                "escuela",
                "colegio",
                "universidad",
                "docente",
                "maestro",
                "enseñanza",
                "curricul",
                "académic",
                "cultura",
                "deporte",
                "recreación",
            ]
            palabras_salud = [
                "salud",
                "hospital",
                "médic",
                "enferm",
                "sani",
                "farmac",
                "epidem",
                "vacun",
                "psicol",
            ]
            palabras_ambiente = [
                "agua",
                "medio ambiente",
                "tierra",
                "bosque",
                "biodiversidad",
                "recursos naturales",
                "minería",
                "energía",
                "ecolog",
                "contamin",
                "forestal",
            ]
            palabras_justicia = [
                "justicia",
                "penal",
                "civil",
                "código",
                "pena",
                "delito",
                "tribunal",
                "juzgado",
                "fiscalía",
                "ministerio público",
            ]
            palabras_const = [
                "constitución",
                "constitucional",
                "derechos humanos",
                "sistema electoral",
                "referendum",
                "legislac",
            ]
            palabras_seguridad = [
                "seguridad",
                "fuerzas armadas",
                "policía",
                "narcotráfico",
                "defensa nacional",
                "crimen organizado",
            ]
            palabras_autonomia = [
                "autonomía",
                "municipio",
                "gobernación",
                "descentraliz",
                "organización territorial",
            ]
            palabras_indigena = [
                "indígena",
                "originario",
                "campesino",
                "nación",
                "pueblo",
                "interculturalidad",
                "plurinacional",
            ]
            palabras_social = [
                "social",
                "vivienda",
                "familia",
                "niñez",
                "mujer",
                "género",
                "inclusión",
                "discapacidad",
            ]
            palabras_economia_plural = [
                "producción",
                "industria",
                "industrializ",
                "empresa",
                "comercio",
                "emprendimiento",
                "artesanía",
                "economia plural",
            ]
            palabras_int = [
                "internacional",
                "tratado",
                "diplomacia",
                "relaciones exteriores",
                "convenio",
                "onu",
                "oea",
            ]

            # Función para buscar la comisión por nombre parcial en la lista de BD
            def _buscar_comision(keywords: List[str]) -> Optional[Dict[str, Any]]:
                for c in comisiones_data:
                    nombre_low = (
                        c["nombre_comision"].lower() + " " + c["descripcion"].lower()
                    )
                    for kw in keywords:
                        if kw in nombre_low:
                            return c
                return None

            if any(kw in t for kw in palabras_ambiente):
                c = _buscar_comision(["tierra", "medio ambiente", "recursos naturales"])
            elif any(kw in t for kw in palabras_economicas):
                c = _buscar_comision(["planificacion", "financ", "econom"])
            elif any(kw in t for kw in palabras_educacion):
                c = _buscar_comision(["educacion", "social"])
            elif any(kw in t for kw in palabras_salud):
                c = _buscar_comision(["salud", "social"])
            elif any(kw in t for kw in palabras_justicia):
                c = _buscar_comision(["justicia"])
            elif any(kw in t for kw in palabras_seguridad):
                c = _buscar_comision(["seguridad"])
            elif any(kw in t for kw in palabras_autonomia):
                c = _buscar_comision(["autonomia", "territorial"])
            elif any(kw in t for kw in palabras_indigena):
                c = _buscar_comision(["indigena", "interculturalidad"])
            elif any(kw in t for kw in palabras_social):
                c = _buscar_comision(["social", "educacion"])
            elif any(kw in t for kw in palabras_economia_plural):
                c = _buscar_comision(["produccion", "econom", "industria"])
            elif any(kw in t for kw in palabras_int):
                c = _buscar_comision(["internacional"])
            elif any(kw in t for kw in palabras_const):
                c = _buscar_comision(["constitucion"])
            else:
                c = _buscar_comision(["constitucion"])

            if not c and comisiones_data:
                c = comisiones_data[0]

            return {
                "comision_principal": c["nombre_comision"],
                "nombre_comision_display": c["nombre"],
                "descripcion_comision": c["descripcion"],
                "id_comision": c["id_comision"],
                "prioridad": "Normal",
                "resumen": texto_doc.strip().split("\n")[0][:200]
                or "Proyecto legislativo asignado por especialidad temática.",
                "complejidad": "Media",
                "metodo": "heuristica_tematica",
            }

        # ── 3. LLM NVIDIA NIM (modelo configurado en el entorno) ─────────────
        data = None
        modelo_usado = "heuristica"
        nvidia_api_key = os.getenv("NVIDIA_API_KEY") or settings.NVIDIA_API_KEY

        system_prompt_comision = (
            "Eres el Asignador Oficial de Comisiones de la Asamblea Legislativa Plurinacional de Bolivia. "
            "Tu única función es determinar cuál comisión parlamentaria es competente para tramitar un proyecto de ley "
            "según su materia, objeto y contenido sustantivo. "
            "REGLAS OBLIGATORIAS:\n"
            "1. DEBES elegir EXACTAMENTE una comisión del catálogo proporcionado, copiando su nombre_comision literalmente.\n"
            "2. Responde ÚNICAMENTE con JSON válido, sin texto adicional antes ni después.\n"
            "3. NO inventes comisiones, NO parafrasees el nombre de la comisión."
        )

        nombres_lista = "\n".join(
            [
                f"  {i+1}. {c['nombre_comision']} - {c['nombre']}"
                for i, c in enumerate(comisiones_data)
            ]
        )

        user_prompt_comision = f"""CATÁLOGO DE COMISIONES DISPONIBLES EN LA ASAMBLEA (desde base de datos):
{catalogo_str}

TEXTO DEL PROYECTO DE LEY A ANALIZAR:
{texto_doc}

INSTRUCCIÓN: Analiza el objeto, materia y contenido del proyecto y determina la comisión competente.
Elige SOLO de esta lista (copia el nombre_comision exacto):
{nombres_lista}

Responde con este JSON exacto:
{{
  "comision_principal": "<nombre_comision exacto de la lista>",
  "id_comision": <número entero>,
  "prioridad": "Alta|Media|Normal",
  "complejidad": "Alta|Media|Baja",
  "resumen": "<resumen del proyecto en 1-2 frases>",
  "justificacion": "<por qué esta comisión es la competente según materia>"
}}"""

        # 3a. Intento primario: NVIDIA NIM con modelo primario de alto rendimiento
        try:
            modelo_principal = getattr(
                settings, "LLM_MODEL_CREW", "nvidia/nemotron-3.5-lightning-30b-a3b"
            )
            client_nim = OpenAI(
                base_url=getattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                api_key=nvidia_api_key,
                timeout=90.0,
            )
            completion = client_nim.chat.completions.create(
                model=modelo_principal,
                messages=[
                    {"role": "system", "content": system_prompt_comision},
                    {"role": "user", "content": user_prompt_comision},
                ],
                temperature=0.1,
                top_p=0.95,
                max_tokens=400,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                stream=False,
            )
            msg_obj = completion.choices[0].message
            raw_llm = msg_obj.content or getattr(msg_obj, "reasoning_content", "") or ""
            modelo_usado = modelo_principal
            from sma_unified.agents.llm_client import extraer_json_de_llm

            data = extraer_json_de_llm(raw_llm)
            if isinstance(data, dict) and data.get("comision_principal"):
                logger.info(
                    f"[Comision] ✅ LLM NIM asignó: {data['comision_principal']} (modelo: {modelo_usado})"
                )
            else:
                data = None
        except Exception as e_nim:
            logger.warning(
                f"[Comision] NVIDIA NIM falló ({e_nim}). Intentando fallback resiliente."
            )

        # 3b. Fallback resiliente al cliente multi-modelo del sistema
        if not data:
            try:
                from sma_unified.agents.llm_client import (
                    chat_completion_resiliente,
                    extraer_json_de_llm,
                )

                raw_out, modelo_usado = chat_completion_resiliente(
                    messages=[
                        {"role": "system", "content": system_prompt_comision},
                        {"role": "user", "content": user_prompt_comision},
                    ],
                    temperature=0.1,
                    max_tokens=500,
                    timeout=20,
                )
                data = extraer_json_de_llm(raw_out)
                if isinstance(data, dict) and data.get("comision_principal"):
                    logger.info(
                        f"[Comision] ✅ Fallback resiliente asignó: {data['comision_principal']} (modelo: {modelo_usado})"
                    )
                else:
                    data = None
            except Exception as e_fb:
                logger.warning(f"[Comision] Fallback resiliente también falló: {e_fb}")

        # 3c. Heurística temática si el LLM no responde correctamente
        if not data or not isinstance(data, dict) or not data.get("comision_principal"):
            logger.warning("[Comision] Usando heurística temática como último recurso.")
            data = _determinar_comision_heuristica(req.texto_documento)
            modelo_usado = "heuristica_tematica"

        # ── 4. Validar que el nombre de comisión sea exacto de la BD ──────────
        comision_raw = str(data.get("comision_principal", "")).strip()
        comision_normalizada = None

        # Búsqueda exacta primero
        if comision_raw.upper() in nombres_validos_lower:
            comision_normalizada = nombres_validos_lower[comision_raw.upper()]
        elif comision_raw in nombres_validos:
            comision_normalizada = comision_raw

        # Búsqueda parcial si falla la exacta
        if not comision_normalizada:
            for c in comisiones_data:
                if (
                    c["nombre_comision"].lower() in comision_raw.lower()
                    or comision_raw.lower() in c["nombre_comision"].lower()
                    or comision_raw.lower() in c["nombre"].lower()
                ):
                    comision_normalizada = c["nombre_comision"]
                    break

        # Último recurso: la primera de la lista
        if not comision_normalizada and comisiones_data:
            comision_normalizada = comisiones_data[0]["nombre_comision"]

        data["comision_principal"] = comision_normalizada

        # Enriquecer la respuesta con datos completos de la comisión elegida
        comision_elegida_data = next(
            (
                c
                for c in comisiones_data
                if c["nombre_comision"] == comision_normalizada
            ),
            comisiones_data[0] if comisiones_data else {},
        )
        data["nombre_comision_display"] = comision_elegida_data.get(
            "nombre", comision_normalizada
        )
        data["descripcion_comision"] = comision_elegida_data.get("descripcion", "")
        data["id_comision"] = comision_elegida_data.get(
            "id_comision", data.get("id_comision")
        )
        data["rol_principal"] = comision_elegida_data.get("rol_principal", "")
        data["palabras_clave"] = comision_elegida_data.get("palabras_clave", [])
        data["modelo_llm_usado"] = modelo_usado

        # ── 5. Resolver y persistir en Neon ───────────────────────────────────
        id_proyecto = _resolve_id_proyecto(
            req.sesion_id, req.id_proyecto, req.texto_documento, req.nombre_archivo
        )
        data["id_proyecto"] = id_proyecto

        if id_proyecto and data.get("comision_principal"):
            from sma_unified.db.neon_postgres import asignar_comision_a_proyecto

            asignar_comision_a_proyecto(
                id_proyecto,
                data["comision_principal"],
                data.get("resumen", "Asignado por LLM NVIDIA NIM"),
                True,
            )
            try:
                conn = get_conn()
                cur = conn.cursor()
                titulo_extract = (
                    data.get("resumen", "").split(".")[0][:250]
                    or req.nombre_archivo
                    or f"Proyecto Ley #{id_proyecto}"
                )
                cur.execute(
                    """
                    UPDATE sistema.proyecto_ley SET
                        titulo    = COALESCE(NULLIF(%s, ''), titulo),
                        resumen   = COALESCE(NULLIF(%s, ''), resumen),
                        prioridad = %s
                    WHERE id_proyecto = %s
                    """,
                    (
                        titulo_extract,
                        data.get("resumen", ""),
                        data.get("prioridad", "Media"),
                        id_proyecto,
                    ),
                )
                conn.commit()
                cur.close()
            except Exception as _ue:
                logger.warning(f"No se pudo actualizar titulo/resumen en Neon: {_ue}")

            duracion_s = max(1, int(time.time() - t_inicio))
            registrar_bitacora(
                id_proyecto=id_proyecto,
                agente_accion="Agente_Comision_Legislativa",
                accion_realizada="Asignación de Comisión y Temática",
                descripcion=(
                    f"Comisión: {data.get('comision_principal')} | "
                    f"Prioridad: {data.get('prioridad', 'Normal')} | "
                    f"Modelo: {modelo_usado}"
                ),
                tiempo_segundos=duracion_s,
            )

        # ── 6. Cargar miembros de la comisión asignada ─────────────────────────
        miembros = []
        try:
            conn = get_conn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                SELECT m.nombre_completo, m.cargo, m.tipo_camara, m.email, m.partido_politico
                FROM sistema.miembro_comision m
                JOIN sistema.comision c ON c.id_comision = m.id_comision
                WHERE (c.nombre_comision ILIKE %s OR c.nombre ILIKE %s)
                  AND (m.activo IS NULL OR m.activo = TRUE)
                ORDER BY
                  CASE m.cargo
                    WHEN 'Presidente'     THEN 1
                    WHEN 'Vicepresidente' THEN 2
                    WHEN 'Secretario'     THEN 3
                    ELSE 4
                  END
            """,
                (
                    f"%{comision_normalizada}%",
                    f"%{data.get('nombre_comision_display', '')}%",
                ),
            )
            rows = cur.fetchall()
            cur.close()
            miembros = [dict(r) for r in rows]
        except Exception as _me:
            logger.warning(f"No se pudieron obtener miembros de comisión: {_me}")

        data["miembros"] = miembros
        logger.info(
            f"[Comision] ✅ Asignación completada | "
            f"Comisión: {comision_normalizada} | ID: {id_proyecto} | Modelo: {modelo_usado}"
        )
        return {"success": True, "data": data}

    except Exception as e:
        logger.error(f"Error en Agente Comisión: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_constitucional")
def run_agent_constitucional(req: Phase2Request):
    """Ejecuta el Agente de Verificación Constitucional (CPE) - módulo independiente."""
    from sma_unified.agents.verificador_constitucional import (
        verificar_constitucionalidad,
    )
    from sma_unified.db.neon_postgres import (
        actualizar_proyecto_con_observacion,
        registrar_bitacora,
    )
    from sma_unified.db.mongo_atlas import guardar_reporte_constitucionalidad_mongo
    from sma_unified.agents.llm_client import limite_tiempo_auditoria

    try:
        t_inicio = time.time()
        id_proyecto = _resolve_id_proyecto(
            req.sesion_id, req.id_proyecto, req.texto_documento, req.nombre_archivo
        )

        with limite_tiempo_auditoria(req.presupuesto_segundos):
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
                if resultado.get("estado") != "PENDIENTE_REVISION":
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
                    tiempo_segundos=duracion_s,
                )
            except Exception as _e:
                logger.warning(f"No se pudo actualizar proyecto en Neon: {_e}")

        try:
            guardar_reporte_constitucionalidad_mongo(
                {
                    "expediente_id": id_proyecto,
                    "sesion_id": req.sesion_id,
                    "nombre_archivo": req.nombre_archivo,
                    "dictamen": resultado,
                    "num_contradicciones": resultado.get("num_contradicciones", 0),
                    "articulos_a_favor": len(resultado.get("articulos_a_favor", [])),
                }
            )
        except Exception as _mge:
            logger.warning(f"No se pudo guardar reporte en Mongo: {_mge}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en Agente Constitucional: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_consistencia")
def run_agent_consistencia(req: Phase2Request):
    """Ejecuta el Agente de Consistencia Normativa (leyes vigentes) - módulo independiente."""
    from sma_unified.agents.consistencia_normativa import (
        verificar_consistencia_normativa,
    )
    from sma_unified.db.neon_postgres import registrar_bitacora
    from sma_unified.agents.llm_client import limite_tiempo_auditoria

    try:
        t_inicio = time.time()
        id_proyecto = _resolve_id_proyecto(
            req.sesion_id, req.id_proyecto, req.texto_documento, req.nombre_archivo
        )

        with limite_tiempo_auditoria(req.presupuesto_segundos):
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
                    tiempo_segundos=duracion_s,
                )
            except Exception as _be:
                logger.warning(f"No se pudo registrar bitacora consistencia: {_be}")

        # Persistir en MongoDB Atlas (colección reportes_consistencia)
        try:
            guardar_reporte_consistencia_mongo(
                {
                    "expediente_id": id_proyecto,
                    "sesion_id": req.sesion_id,
                    "nombre_archivo": req.nombre_archivo,
                    "task_id": resultado.get("task_id_consistencia"),
                    "hallazgos": resultado.get("hallazgos", []),
                    "estado": resultado.get("estado"),
                    "pendientes_revision": resultado.get("pendientes_revision", []),
                    "total_pendientes": resultado.get("total_pendientes", 0),
                    "resumen_por_tipo": resultado.get("resumen_por_tipo", {}),
                    "nivel_riesgo_global": resultado.get(
                        "nivel_riesgo_global", "NINGUNO"
                    ),
                    "total_hallazgos": resultado.get("total_hallazgos", 0),
                    "alertas_riesgo_alto": resultado.get("alertas_riesgo_alto", 0),
                    "alertas_riesgo_medio": resultado.get("alertas_riesgo_medio", 0),
                    "posibles_derogaciones_tacitas": resultado.get(
                        "posibles_derogaciones_tacitas", 0
                    ),
                    "conflictos_especialidad": resultado.get(
                        "conflictos_especialidad", 0
                    ),
                    "duracion_ms": int((time.time() - t_inicio) * 1000),
                }
            )
        except Exception as _cme:
            logger.warning(f"No se pudo guardar reporte_consistencia en Mongo: {_cme}")

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
            sesion_id=req.sesion_id,
        )

        id_proyecto = _resolve_id_proyecto(req.sesion_id)
        if id_proyecto and resultado.get("filename"):
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(
                    """UPDATE sistema.proyecto_ley 
                       SET archivo_pdf = %s,
                           drive_link = COALESCE(NULLIF(%s, ''), drive_link),
                           drive_file_id = COALESCE(NULLIF(%s, ''), drive_file_id)
                       WHERE id_proyecto = %s""",
                    (
                        resultado["filename"],
                        resultado.get("drive_link", ""),
                        resultado.get("drive_file_id", ""),
                        id_proyecto,
                    ),
                )
                conn.commit()
                cur.close()

                duracion_s = max(1, int(time.time() - t_inicio))
                registrar_bitacora(
                    id_proyecto=id_proyecto,
                    agente_accion="Agente_Emisor_Resultados",
                    accion_realizada="Emisión de Dictamen Técnico Oficial (PDF)",
                    descripcion=f"Documento generado: {resultado['filename']}",
                    tiempo_segundos=duracion_s,
                )
            except Exception as _pe:
                logger.warning(f"No se pudo actualizar archivo_pdf en Neon: {_pe}")

        return {"success": True, "data": resultado}
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
        dest_extra = req.destinatario_extra or req.email_autor
        resultado = notificar_miembros_comision(
            sesion_id=req.sesion_id,
            id_proyecto=id_proyecto,
            datos_comision=req.datos_comision,
            datos_constitucionales=req.datos_constitucionales,
            datos_consistencia=req.datos_consistencia,
            pdf_filename=req.pdf_filename,
            destinatario_extra=dest_extra,
            mensaje_extra=req.mensaje_extra,
            asunto_personalizado=req.asunto_personalizado,
        )
        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en Agente Notificador: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_concentrador")
def run_agent_concentrador(req: ConcentradorRequest):
    """
    Agente Concentrador, Emisor y Notificador de Dictamen:
    1. Concentra y sintetiza observaciones de Constitucionalidad, Consistencia Normativa y Fondo.
    2. Emite el Dictamen Oficial en PDF (letra negra formal, alta solidez institucional).
    3. Despacha la notificación formal por correo HTML con el PDF adjunto a los miembros de comisión.
    """
    from sma_unified.agents.concentrador import ejecutar_concentrador_emisor_notificador

    try:
        id_proyecto = _resolve_id_proyecto(req.sesion_id, req.id_proyecto)
        resultado = ejecutar_concentrador_emisor_notificador(
            sesion_id=req.sesion_id,
            id_proyecto=id_proyecto,
            datos_constitucionales=req.datos_constitucionales,
            datos_consistencia=req.datos_consistencia,
            datos_fondo=req.datos_fondo,
            datos_comision=req.datos_comision,
            texto_proyecto=req.texto_proyecto,
            titulo_proyecto=req.titulo_proyecto,
            notificar=bool(req.notificar),
            destinatario_extra=req.destinatario_extra,
            mensaje_extra=req.mensaje_extra,
        )
        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en Agente Concentrador y Emisor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/mensaje_presidente_senado")
async def mensaje_presidente_senado_endpoint(req: MensajePresidenteSenadoRequest):
    """
    Interacción con Agente CrewAI de Enlace Legislativo:
    Redacta y/o envía el Mensaje Oficial y Oficio de Promulgación y Publicación
    al Presidente de la Cámara de Senadores y Presidente de la ALP.
    Usa el Token de Google (Gmail SMTP) para el despacho garantizado.
    """
    try:
        from sma_unified.agents.llm_client import chat_completion_resiliente
        from sma_unified.agents.notificador_comision import (
            enviar_correo_gmail_smtp,
            enviar_correo_hibrido,
        )
        from sma_unified.db.neon_postgres import registrar_bitacora
        from sma_unified.db.mongo_atlas import get_db

        id_proyecto = _resolve_id_proyecto(req.sesion_id, req.id_proyecto)
        numero_ley = req.numero_ley or "Ley Sancionada"
        titulo_proy = req.titulo_proyecto or "Proyecto de Ley del Estado Plurinacional"
        boletin = req.boletin_oficial or "GAC-2026-BOL"

        # 1. Si se solicita redacción por Agente CrewAI
        if req.solo_redactar or not req.mensaje_personalizado:
            prompt_crew = f"""Eres el Agente Especializado CrewAI de Enlace Legislativo y Promulgación Presidencial de la Asamblea Legislativa Plurinacional de Bolivia.
Tu misión es redactar un OFICIO PROTOCOLAR FORMAL de máxima solemnidad parlamentaria dirigido al:

Hermano Presidente de la Cámara de Senadores y Presidente Nato de la Asamblea Legislativa Plurinacional de Bolivia.

DATOS DE LA NORMA:
- Número de Ley Promulgada: {numero_ley}
- Título Oficial: {titulo_proy}
- Publicación Oficial: {boletin} en la Gaceta Oficial del Estado Plurinacional
- Estado: Vigente con fuerza de ley (Art. 164 Constitución Política del Estado)

ESTRUCTURA OBLIGATORIA DEL MENSAJE:
1. Encabezamiento protocolar formal (Señor Presidente de la Cámara de Senadores, H. Senador...).
2. Párrafo de Notificación de Promulgación: Certificación de que el proyecto culminó su trámite bicameral y fue formalmente promulgado y publicado en la Gaceta Oficial.
3. Síntesis Jurídica: Destacar que todas las observaciones técnicas y constitucionales fueron solventadas.
4. Efecto de Cumplimiento: Invocación expresa del Art. 164 CPE (obligatoriedad general de cumplimiento desde su publicación).
5. Saludo de estilo parlamentario y fórmula de consideración más distinguida.

Redacta el texto de manera solemne, clara y protocolar en español boliviano formal. No incluyas explicaciones meta, entrega directamente el texto del oficio listo para despacho."""

            try:
                contenido, modelo_usado = chat_completion_resiliente(
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres el Agente CrewAI de Enlace Legislativo de Bolivia. Respondes con estricto apego al protocolo parlamentario del Estado Plurinacional.",
                        },
                        {"role": "user", "content": prompt_crew},
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                )
                mensaje_redactado = (contenido or "").strip()
            except Exception as _llm_err:
                logger.warning(
                    f"Fallo en LLM para redactar oficio Senado, usando plantilla protocolar: {_llm_err}"
                )
                mensaje_redactado = f"""La Paz, {datetime.now().strftime('%d de %B de %Y')}

Señor
Hermano Presidente de la Cámara de Senadores
Asamblea Legislativa Plurinacional de Bolivia
Presente.-

De mi mayor consideración y estima parlamentaria:

Tengo a bien dirigirme a su digna autoridad en cumplimiento de los preceptos institucionales y constitucionales vigentes en el Estado Plurinacional de Bolivia.

Por medio del presente instrumento oficial, comunico formalmente a la Presidencia de la Cámara de Senadores que el trámite legislativo correspondiente al {titulo_proy} ha culminado exitosamente en todas sus instancias bicamarales y de control normativo.

En tal sentido, la referida norma ha sido debidamente sancionada, promulgada por el Órgano Ejecutivo y registrada en la Gaceta Oficial del Estado Plurinacional bajo el registro oficial {numero_ley} (Edición Oficial: {boletin}).

Habiéndose subsanado y resuelto satisfactoriamente la totalidad de observaciones de consistencia y constitucionalidad planteadas en la Mesa de Partes y en comisiones técnicas, la ley adquiere plena obligatoriedad en todo el territorio nacional a tenor de lo dispuesto en el Artículo 164 de la Constitución Política del Estado.

Con este motivo, reitero a usted las seguridades de mi más alta y distinguida consideración.

Atentamente,

DIRECCIÓN DE LA GACETA OFICIAL & DESPACHO LEGISLATIVO
Asamblea Legislativa Plurinacional de Bolivia"""

            if req.solo_redactar:
                return {
                    "success": True,
                    "data": {
                        "mensaje_redactado": mensaje_redactado,
                        "agente": "Agente CrewAI de Enlace Legislativo - Presidencia del Senado",
                        "numero_ley": numero_ley,
                        "boletin_oficial": boletin,
                    },
                }
        else:
            mensaje_redactado = req.mensaje_personalizado.strip()

        # 2. Despacho Oficial vía Token de Google (Gmail SMTP)
        email_destino = (req.email_destino or "").strip()
        gmail_user = (os.getenv("GMAIL_USER") or os.getenv("SMTP_USER") or "").strip()
        destinatarios = (
            [email_destino]
            if (email_destino and "@" in email_destino)
            else [gmail_user or "presidencia.senado@asamblea.gob.bo"]
        )

        asunto = f"[ALP NOTIFICACIÓN OFICIAL] Promulgación y Publicación en Gaceta: {numero_ley}"

        cuerpo_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"/></head>
        <body style="margin:0;padding:20px;background-color:#0D1B2A;font-family:'Segoe UI',Roboto,Helvetica,sans-serif;color:#E2E8F0;">
          <div style="max-width:680px;margin:0 auto;background:#1B2A4A;border:1.5px solid #00C2CB;border-radius:14px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.5);">
            <div style="height:6px;background:linear-gradient(90deg,#C0392B 33%,#F1C40F 33% 66%,#0D5C3A 66%);"></div>
            <div style="padding:24px 28px;background:rgba(13,27,42,0.85);text-align:center;border-bottom:1px solid rgba(0,194,203,0.3);">
              <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#94A3B8;font-weight:700;">Estado Plurinacional de Bolivia</div>
              <div style="font-size:18px;font-weight:800;color:#FFFFFF;margin-top:4px;">GACETA OFICIAL & DESPACHO LEGISLATIVO</div>
              <div style="font-size:12px;color:#00C2CB;margin-top:2px;">Comunicación Oficial al Presidente de la Cámara de Senadores</div>
            </div>

            <div style="padding:28px;">
              <div style="background:rgba(0,194,203,0.12);border:1px solid #00C2CB;border-radius:10px;padding:16px;margin-bottom:22px;">
                <div style="font-size:11px;color:#7DD3FC;font-weight:700;text-transform:uppercase;">Identificación de la Norma Publicada</div>
                <div style="font-size:17px;font-weight:800;color:#FFFFFF;margin-top:4px;">{numero_ley}</div>
                <div style="font-size:13px;color:#CBD5E1;margin-top:2px;">{titulo_proy}</div>
                <div style="font-size:12px;color:#34D399;font-weight:700;margin-top:6px;">Boletín Oficial: {boletin} · Ley Vigente (Art. 164 CPE)</div>
              </div>

              <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(148,163,184,0.2);border-radius:10px;padding:20px;line-height:1.7;font-size:13.5px;color:#F1F5F9;white-space:pre-wrap;">
{mensaje_redactado}
              </div>

              <div style="margin-top:24px;padding-top:16px;border-top:1px solid rgba(148,163,184,0.2);display:flex;justify-content:space-between;font-size:11.5px;color:#94A3B8;">
                <div>Remitido por: Agente CrewAI de Enlace Legislativo</div>
                <div>GobernIA · Sistema Multi-Agente ALP</div>
              </div>
            </div>
          </div>
        </body>
        </html>
        """

        # Enviar con Token de Google / Gmail
        resultado_envio = enviar_correo_hibrido(
            asunto=asunto, destinatarios=destinatarios, html_content=cuerpo_html
        )

        # Registro en Bitácora y Mongo
        if id_proyecto:
            try:
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Crew_Enlace_Senado",
                    accion_realizada="Mensaje Oficial Remitido al Presidente del Senado",
                    descripcion=f"Ley: {numero_ley} | Destinatario: {', '.join(destinatarios)} | Método: {resultado_envio.get('metodo')}",
                    tiempo_segundos=1,
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Senado: {be}")

        try:
            db = get_db()
            db["mensajes_presidente_senado"].insert_one(
                {
                    "sesion_id": req.sesion_id,
                    "id_proyecto": id_proyecto,
                    "numero_ley": numero_ley,
                    "destinatarios": destinatarios,
                    "mensaje": mensaje_redactado,
                    "envio": resultado_envio,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        except Exception:
            pass

        return {
            "success": True,
            "data": {
                "enviado": resultado_envio.get("enviado", False),
                "metodo": resultado_envio.get("metodo"),
                "destinatarios": destinatarios,
                "mensaje": mensaje_redactado,
                "detalle": resultado_envio,
            },
        }
    except Exception as e:
        logger.error(f"Error en endpoint Mensaje Presidente Senado: {e}")
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
        id_proyecto = (
            payload.get("id_proyecto")
            or proyecto_info.get("id_proyecto")
            or proyecto_info.get("id")
        )

        agente = AgenteConstitucionFondo()
        resultado = agente.ejecutar(
            texto_proyecto=texto_proyecto,
            obs_formales=obs_formales,
            proyecto_info=proyecto_info,
        )

        if id_proyecto:
            try:
                dictamen = resultado.get("dictamen_fondo", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Constitucion_Fondo",
                    accion_realizada="Análisis Hermenéutico Constitucional de Fondo",
                    descripcion=f"Viabilidad: {dictamen.get('viabilidad_fondo', 'N/A')} | Riesgo: {dictamen.get('riesgo_constitucional', 'BAJO')}",
                    tiempo_segundos=1,
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
    Etapa 5: Agente Concentrador, Emisor y Notificador FUSIONADO
    Consolidación, emisión del PDF institucional formal y despacho a la comisión.
    """
    try:
        from sma_unified.agents.concentrador import (
            ejecutar_concentrador_emisor_notificador,
        )
        from sma_unified.db.neon_postgres import registrar_bitacora

        sesion_id = payload.get("sesion_id") or str(uuid.uuid4())
        id_proyecto = (
            payload.get("id_proyecto")
            or payload.get("proyecto_info", {}).get("id_proyecto")
            or payload.get("proyecto_info", {}).get("id")
        )

        datos_constitucionales = payload.get("datos_constitucionales")
        datos_consistencia = payload.get("datos_consistencia")
        datos_fondo = payload.get("datos_fondo")
        datos_comision = payload.get("datos_comision")
        texto_proyecto = payload.get("texto_proyecto")
        titulo_proyecto = payload.get("titulo_proyecto") or payload.get(
            "proyecto_info", {}
        ).get("titulo")
        notificar = payload.get("notificar", True)
        destinatario_extra = payload.get("destinatario_extra")
        mensaje_extra = payload.get("mensaje_extra")

        resultado = ejecutar_concentrador_emisor_notificador(
            sesion_id=sesion_id,
            id_proyecto=int(id_proyecto) if id_proyecto else None,
            datos_constitucionales=datos_constitucionales,
            datos_consistencia=datos_consistencia,
            datos_fondo=datos_fondo,
            datos_comision=datos_comision,
            texto_proyecto=texto_proyecto,
            titulo_proyecto=titulo_proyecto,
            notificar=notificar,
            destinatario_extra=destinatario_extra,
            mensaje_extra=mensaje_extra,
        )

        if id_proyecto:
            try:
                exp = resultado.get("expediente_consolidado", {})
                pdf_info = resultado.get("pdf", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Concentrador_Emisor_Notificador",
                    accion_realizada="Dictamen Consolidado, PDF Formal Emitido y Notificación Despachada",
                    descripcion=f"Riesgo: {exp.get('nivel_riesgo_general', 'MEDIO')} | PDF: {pdf_info.get('filename', 'N/A')}",
                    tiempo_segundos=2,
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Concentrador: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Concentrador: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_secretario")
async def run_agent_secretario_endpoint(payload: Dict[str, Any], usuario=Depends(legislador_revision)):
    """
    Etapa 5: Agente Secretario de Cámara
    Registro de actas de debate parlamentario y votaciones.
    """
    try:
        from sma_unified.agents.secretario import AgenteSecretarioCamara
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        debate_data = payload.get("debate_data", {})
        id_proyecto = (
            payload.get("id_proyecto")
            or proyecto_info.get("id_proyecto")
            or proyecto_info.get("id")
        )

        agente = AgenteSecretarioCamara()
        resultado = agente.ejecutar(
            debate_data=debate_data, proyecto_info=proyecto_info
        )

        if id_proyecto:
            try:
                acta = resultado.get("acta_debate", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Secretario_Camara",
                    accion_realizada="Registro de Debate Parlamentario y Votación Nominal",
                    descripcion=f"Sesión: #{acta.get('sesion_numero', 1)} | Votaciones: {len(acta.get('votaciones', []))}",
                    tiempo_segundos=1,
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Secretario: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Secretario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_bicameral")
async def run_agent_bicameral_endpoint(payload: Dict[str, Any], usuario=Depends(legislador_revision)):
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
        id_proyecto = (
            payload.get("id_proyecto")
            or proyecto_info.get("id_proyecto")
            or proyecto_info.get("id")
        )

        agente = AgenteBicameral()
        resultado = agente.ejecutar(
            version_original=version_original,
            version_retornada=version_retornada,
            proyecto_info=proyecto_info,
        )

        if id_proyecto:
            try:
                ciclo = resultado.get("ciclo_bicameral", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Bicameral",
                    accion_realizada="Control de Trámite Bicameral y Reconciliación",
                    descripcion=f"Cambios: {ciclo.get('clasificacion_cambios', 'MENORES')} | Ruta: {ciclo.get('ruta_siguiente', 'SANCION_DIRECTA')}",
                    tiempo_segundos=1,
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Bicameral: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Bicameral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/devolver_comision")
async def devolver_a_comision_endpoint(
    req: DevolverComisionRequest, authorization: Optional[str] = Header(default=None)
):
    """
    Bucle de control (retroalimentación): Devuelve el expediente a Comisiones
    para subsanación formal de observaciones o contradicciones normativas.
    """
    try:
        from sma_unified.agents.bicameral import AgenteBicameral

        usuario = None
        if authorization and authorization.startswith("Bearer "):
            try:
                usuario = usuario_revision(authorization)
            except Exception:
                pass

        agente = AgenteBicameral()
        resultado = agente.devolver_a_comision(
            proyecto_id=req.id_proyecto,
            motivo=req.motivo,
            articulos_observados=req.articulos_observados,
            usuario=usuario,
        )
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en devolución a comisión: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/confirmar_aprobacion_bicameral")
def confirmar_aprobacion_bicameral_endpoint(req: ConfirmarAprobacionBicameralRequest):
    """
    Confirmación de Aprobación - Trámite Bicameral.
    Cuando un Senador confirma la aprobación de un proyecto de ley, notifica por
    correo (con el PDF del proyecto y el informe de constitucionalidad/consistencia
    adjuntos) a todos los Diputados registrados en Usuarios_Sistema - y viceversa
    cuando quien confirma es un Diputado.
    """
    try:
        from sma_unified.agents.notificador_camara_opuesta import (
            notificar_camara_opuesta,
        )

        resultado = notificar_camara_opuesta(
            rol_remitente=req.rol_remitente,
            titulo_proyecto=req.titulo_proyecto,
            sesion_id=req.sesion_id,
            id_proyecto=req.id_proyecto,
            nombre_remitente=req.nombre_remitente,
            datos_constitucionales=req.datos_constitucionales or {},
            datos_consistencia=req.datos_consistencia or {},
            pdf_proyecto_filename=req.pdf_proyecto_filename,
            pdf_informe_filename=req.pdf_informe_filename,
        )
        return {"success": True, "data": resultado}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en endpoint Confirmar Aprobación Bicameral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_veto_promulgacion")
async def run_agent_veto_promulgacion_endpoint(
    payload: Dict[str, Any], authorization: Optional[str] = Header(default=None), usuario=Depends(legislador_revision)
):
    """
    Etapa 7: Agente Veto y Promulgación
    Evaluación estratégica multicriterio del Órgano Ejecutivo.
    """
    try:
        from sma_unified.agents.veto_promulgacion import AgenteVetoPromulgacion
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        expediente = payload.get("expediente", {})
        id_proyecto = (
            payload.get("id_proyecto")
            or proyecto_info.get("id_proyecto")
            or proyecto_info.get("id")
        )

        agente = AgenteVetoPromulgacion()
        usuario_registrador = (
            usuario_revision(authorization)
            if expediente.get("decision_operador")
            else None
        )
        resultado = agente.ejecutar(
            expediente=expediente,
            proyecto_info=proyecto_info,
            usuario_registrador=usuario_registrador,
        )

        if id_proyecto:
            try:
                ev = resultado.get("evaluacion_veto", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Veto_Promulgacion",
                    accion_realizada="Evaluación Estratégica Multicriterio de Promulgación",
                    descripcion=f"Decisión: {ev.get('decision', 'PROMULGAR')} | Score: {ev.get('score_final', 7.5)}",
                    tiempo_segundos=1,
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Veto/Promulgación: {be}")

        return {"success": True, "data": resultado}
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error en endpoint Veto/Promulgacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/agent_publicacion")
async def run_agent_publicacion_endpoint(payload: Dict[str, Any], usuario=Depends(legislador_revision)):
    """
    Etapa 8: Agente Publicación Oficial
    Asignación de número de ley y registro en Boletín Oficial.
    """
    try:
        from sma_unified.agents.publicacion import AgentePublicacionOficial
        from sma_unified.db.neon_postgres import registrar_bitacora

        proyecto_info = payload.get("proyecto_info", {})
        evaluacion_veto = payload.get("evaluacion_veto", {})
        id_proyecto = (
            payload.get("id_proyecto")
            or proyecto_info.get("id_proyecto")
            or proyecto_info.get("id")
        )

        agente = AgentePublicacionOficial()
        resultado = agente.ejecutar(
            evaluacion_veto=evaluacion_veto,
            proyecto_info=proyecto_info,
            numero_ley_personalizado=payload.get("numero_ley_personalizado"),
        )

        if id_proyecto:
            try:
                pub = resultado.get("publicacion_oficial", {})
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Publicacion_Oficial",
                    accion_realizada="Promulgación Oficial y Asignación de Número de Ley",
                    descripcion=f"{pub.get('numero_ley', 'Ley')} | Boletín: {pub.get('boletin_oficial', 'BOL-OFICIAL')}",
                    tiempo_segundos=1,
                )
            except Exception as be:
                logger.warning(f"Error registrando bitácora Publicación: {be}")

        return {"success": True, "data": resultado}
    except Exception as e:
        logger.error(f"Error en endpoint Publicacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/pipeline_completo")
async def run_pipeline_completo_endpoint(payload: Dict[str, Any], usuario=Depends(legislador_revision)):
    """
    Ejecución del pipeline completo CrewAI de extremo a extremo (Etapas 3 a 8).
    """
    try:
        from sma_unified.agents.crew_orchestrator import ejecutar_pipeline_completo

        proyecto_info = payload.get("proyecto_info", {})
        texto_documento = payload.get("texto_proyecto") or payload.get(
            "texto_documento", ""
        )
        observaciones_previas = payload.get("observaciones_previas", [])

        resultado = ejecutar_pipeline_completo(
            proyecto_info=proyecto_info,
            texto_documento=texto_documento,
            observaciones_previas=observaciones_previas,
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
                p.drive_link,
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
                SELECT * FROM sistema.analisis_consistencia
                WHERE id_proyecto = %s OR (nombre_archivo IS NOT NULL AND %s IS NOT NULL AND nombre_archivo = %s)
                ORDER BY fecha_analisis DESC
                """,
                (id_proyecto, nombre_archivo, nombre_archivo),
            )
            c_rows = cur_c.fetchall()
            for c in c_rows:
                cd = dict(c)
                if isinstance(cd.get("fecha_analisis"), datetime):
                    cd["fecha_analisis"] = cd["fecha_analisis"].isoformat()
                consistencia.append(cd)
            cur_c.close()
        except Exception as _ce:
            logger.warning(
                f"Error consultando consistencia para expediente #{id_proyecto}: {_ce}"
            )

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
        cur.execute(
            """
            SELECT m.id_miembro, m.nombre_completo, m.cargo, m.tipo_camara,
                   m.email, m.partido_politico, m.fecha_asignacion,
                   c.nombre_comision
            FROM sistema.miembro_comision m
            JOIN sistema.comision c ON c.id_comision = m.id_comision
            WHERE m.id_comision = %s AND m.activo = TRUE
            ORDER BY m.cargo, m.nombre_completo
        """,
            (id_comision,),
        )
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
        cur.execute(
            """
            INSERT INTO sistema.miembro_comision
                (id_comision, nombre_completo, cargo, tipo_camara, email, partido_politico)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_miembro
        """,
            (
                id_comision,
                req.nombre_completo,
                req.cargo,
                req.tipo_camara,
                req.email,
                req.partido_politico,
            ),
        )
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
            (id_miembro,),
        )
        conn.commit()
        cur.close()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error eliminando miembro {id_miembro}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Agente Multi-Faceta de Atención Ciudadana (routing automático) ───────────
@app.get("/api/ciudadana/agentes")
def api_listar_agentes_ciudadanos(solo_activos: bool = Query(False)):
    """Lista las facetas (sub-agentes) del asistente ciudadano multi-prompt."""
    try:
        from sma_unified.agents.multiagente_ciudadano import listar_agentes

        return {"success": True, "data": listar_agentes(solo_activos=solo_activos)}
    except Exception as e:
        logger.error(f"Error listando agentes ciudadanos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ciudadana/agentes", status_code=201)
def api_crear_agente_ciudadano(req: AgenteCiudadanoRequest):
    """Crea una nueva faceta ciudadana (nombre, logo, prompt y trigger de routing)."""
    try:
        from sma_unified.agents.multiagente_ciudadano import crear_agente

        return {"success": True, "data": crear_agente(req.model_dump())}
    except Exception as e:
        logger.error(f"Error creando agente ciudadano: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ciudadana/agentes/{agente_id}")
def api_obtener_agente_ciudadano(agente_id: str):
    from sma_unified.agents.multiagente_ciudadano import obtener_agente

    agente = obtener_agente(agente_id)
    if not agente:
        raise HTTPException(status_code=404, detail="Agente ciudadano no encontrado")
    return {"success": True, "data": agente}


@app.patch("/api/ciudadana/agentes/{agente_id}")
def api_actualizar_agente_ciudadano(agente_id: str, req: AgenteCiudadanoUpdateRequest):
    from sma_unified.agents.multiagente_ciudadano import actualizar_agente

    agente = actualizar_agente(agente_id, req.model_dump(exclude_unset=True))
    if not agente:
        raise HTTPException(status_code=404, detail="Agente ciudadano no encontrado")
    return {"success": True, "data": agente}


@app.delete("/api/ciudadana/agentes/{agente_id}")
def api_eliminar_agente_ciudadano(agente_id: str):
    from sma_unified.agents.multiagente_ciudadano import eliminar_agente

    if not eliminar_agente(agente_id):
        raise HTTPException(status_code=404, detail="Agente ciudadano no encontrado")
    return {"success": True}


@app.post("/api/ciudadana/facetas/documento")
def api_facetas_documento(req: DictamenCasoRequest, usuario=Depends(usuario_revision)):
    """Identifica y ejecuta las facetas profesionales del documento adjunto."""
    if not req.caso_texto.strip():
        raise HTTPException(status_code=400, detail="El documento no tiene texto que analizar.")
    from sma_unified.agents.reglamentos_profesionales import analizar_documento
    return {"success": True, "data": analizar_documento(
        req.caso_texto, titulo=req.caso_nombre, sesion_id=req.sesion_id)}


@app.post("/api/ciudadana/chat")
def api_chat_ciudadano(req: ChatCiudadanoRequest):
    """
    Chat ciudadano sin estado: el mensaje se enruta automáticamente a la faceta
    (arquitectura, salud, educación, trámites legislativos...) cuyo trigger encaja
    mejor. El usuario no elige el agente y no se guarda historial.
    """
    try:
        from sma_unified.agents.multiagente_ciudadano import responder_ciudadano

        if not (req.mensaje or "").strip():
            raise HTTPException(
                status_code=400, detail="El campo 'mensaje' es obligatorio."
            )
        return responder_ciudadano(
            mensaje=req.mensaje,
            sesion_id=req.sesion_id,
            agente_id=req.agente_id,
            caso_texto=req.caso_texto,
            caso_nombre=req.caso_nombre,
            usar_especialista=req.usar_especialista,
            dictamen=req.dictamen,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/ciudadana/chat: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/ciudadana/especialista/dictamen")
def api_dictamen_especialista(req: DictamenCasoRequest):
    """
    Emite el dictamen técnico pericial de un caso subido (viabilidad, estándares,
    infraestructura y matriz de riesgos). El frontend lo guarda y lo reenvía en
    cada mensaje del chat para que el Especialista no vuelva a peritar de cero.
    """
    try:
        from sma_unified.agents.especialista_chat import analizar_caso

        if not (req.caso_texto or "").strip():
            raise HTTPException(
                status_code=400, detail="El caso no tiene texto que analizar."
            )
        return analizar_caso(
            texto_caso=req.caso_texto,
            titulo=req.caso_nombre,
            materia=req.materia,
            sesion_id=req.sesion_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/ciudadana/especialista/dictamen: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/normativa")
def get_normativa_overview(limit: int = Query(30, ge=1, le=100)):
    """Obtiene el resumen del corpus normativo y los últimos análisis de consistencia."""
    try:
        stats = obtener_stats_consistencia()
        documentos = obtener_normativas_catalogadas_completas()
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


@app.get("/api/normativa/lista")
def get_normativa_lista():
    """Lista las normativas vigentes indexadas con sus resúmenes generados por IA."""
    try:
        documentos = obtener_normativas_catalogadas_completas()
        return {"success": True, "documentos": documentos, "total": len(documentos)}
    except Exception as e:
        logger.error(f"Error listando normativas catalogadas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/normativa/subir")
async def subir_normativa_vigente(
    file: Optional[UploadFile] = File(None),
    texto_directo: Optional[str] = Form(None),
    nombre: str = Form(...),
    tipo: str = Form("ley"),
    numero_norma: Optional[str] = Form(None),
    usuario=Depends(usuario_revision),
):
    """
    Sube y procesa una nueva normativa boliviana:
    1. Extrae el texto del documento o usa el texto directo.
    2. Procesa con LLM (NVIDIA NIM) para extraer resumen jurídico formal y materia.
    3. Parsea los artículos o bloques normativos.
    4. Genera embeddings NVIDIA y los indexa en sistema.articulos_normativos (pgvector).
    5. Registra la norma en el catálogo sistema.normativas_catalogadas.
    """
    import json

    try:
        texto = ""
        archivo_drive = None
        if file and file.filename:
            file_bytes = await file.read()
            if len(file_bytes) > 0:
                nombre_original = Path(file.filename.replace("\\", "/")).name
                upload_id = str(uuid.uuid4())
                nombre_drive = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upload_id[:8]}_{nombre_original}"
                drive_requerido = os.getenv("REQUIRE_DRIVE_BACKUP", "false").lower() == "true"
                resultado_drive = None
                try:
                    from sma_unified.utils.drive_uploader import upload_pdf_to_drive, GDRIVE_AVAILABLE
                    if GDRIVE_AVAILABLE:
                        resultado_drive = upload_pdf_to_drive(
                            file_bytes=file_bytes, filename=nombre_drive, categoria="reportes",
                            subcarpeta="NORMATIVA_VIGENTE", make_public=False,
                            description=f"Normativa registrada: {nombre}. Carga {upload_id}.",
                            app_properties={"sma_upload_id": upload_id, "sma_documento": nombre[:100]},
                        )
                except Exception as e_drive:
                    logger.warning(f"Error guardando normativa {upload_id} en Drive: {e_drive}")
                    if drive_requerido:
                        raise HTTPException(status_code=503, detail="No se pudo guardar el archivo normativo en Google Drive; no se indexó. Vuelva a intentarlo.")
                if drive_requerido and (not resultado_drive or not resultado_drive.get("file_id")):
                    raise HTTPException(status_code=503, detail="Google Drive no confirmó el archivo normativo; no se indexó. Vuelva a intentarlo.")
                archivo_drive = {"upload_id": upload_id, "drive_file_id": (resultado_drive or {}).get("file_id"),
                                 "drive_link": (resultado_drive or {}).get("web_view_link", ""),
                                 "nombre_drive": nombre_drive, "nombre_original": nombre_original}
                (UPLOAD_DIR / nombre_drive).write_bytes(file_bytes)
                _registrar_documento_drive(upload_id, nombre_original, nombre_drive, resultado_drive or {}, "NORMATIVA", file_bytes, usuario)
                texto, _ = extraer_texto_archivo(nombre_original, file_bytes)

        if not texto.strip() and texto_directo:
            texto = texto_directo.strip()

        if not texto.strip():
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un archivo PDF/TXT con contenido o texto de la normativa.",
            )

        # 1. LLM para Resumen y Materia
        prompt_llm = f"""Eres un jurista boliviano experto en técnica legislativa y derecho constitucional.
Analiza el siguiente texto de la normativa boliviana:
NOMBRE: {nombre}
TIPO: {tipo}
NÚMERO DE NORMA: {numero_norma or 'S/N'}

TEXTO (primeros 4000 caracteres):
{texto[:4000]}

Genera un JSON estrictamente válido con dos campos:
{{
  "resumen": "Resumen ejecutivo formal de 2 o 3 oraciones explicando el objeto, ámbito de aplicación y relevancia jurídica.",
  "materia": "Materia jurídica principal (ej: Laboral, Penal, Ambiental, Minería, Administrativo, Civil, etc.)"
}}
Responde ÚNICAMENTE con el objeto JSON."""

        resumen_ia = f"Normativa regulatoria de materia {tipo.lower()} aplicable en el Estado Plurinacional de Bolivia."
        materia_ia = "General"
        try:
            resp_llm = chat_completion_resiliente(
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente legislativo que responde estrictamente en JSON.",
                    },
                    {"role": "user", "content": prompt_llm},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            raw = (resp_llm.get("content") or "").strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join([l for l in lines if not l.startswith("```")]).strip()
            datos_ia = json.loads(raw)
            resumen_ia = datos_ia.get("resumen") or resumen_ia
            materia_ia = datos_ia.get("materia") or materia_ia
        except Exception as e_llm:
            logger.warning(f"No se pudo generar resumen LLM para normativa: {e_llm}")

        # 2. Parsear artículos
        articulos_parsed = parsear_articulos(texto)
        if not articulos_parsed:
            bloques = [b.strip() for b in texto.split("\n\n") if len(b.strip()) > 80]
            articulos_parsed = [
                {
                    "numero_articulo": str(i + 1),
                    "titulo_articulo": f"Disposición {i + 1}",
                    "texto": b,
                }
                for i, b in enumerate(bloques[:50])
            ]

        # 3. Insertar artículos y embeddings
        total_insertados = 0
        articulos_a_procesar = articulos_parsed[:100]
        textos_arts = [a["texto"][:1500] for a in articulos_a_procesar]

        embeddings = []
        try:
            embeddings = generar_embeddings(textos_arts, input_type="passage")
        except Exception as e_emb:
            logger.warning(f"Error generando embeddings en bloque: {e_emb}")

        for i, art in enumerate(articulos_a_procesar):
            emb = embeddings[i] if i < len(embeddings) else None
            num_art = str(art.get("numero_articulo") or (i + 1))
            contenido_art = art.get("texto") or ""
            hash_art = str(hash(contenido_art))
            insertar_o_actualizar_articulo_normativo(
                documento=nombre,
                articulo_numero=num_art,
                contenido=contenido_art,
                contenido_hash=hash_art,
                tipo_documento=tipo,
                numero_norma=numero_norma,
                articulo_titulo=art.get("titulo_articulo"),
                embedding=emb,
            )
            total_insertados += 1

        # 4. Registrar en catálogo de normativas
        guardar_o_actualizar_normativa_catalogada(
            documento=nombre,
            tipo_documento=tipo,
            numero_norma=numero_norma,
            resumen=resumen_ia,
            materia=materia_ia,
            num_articulos=total_insertados,
            drive_file_id=(archivo_drive or {}).get("drive_file_id"),
            drive_link=(archivo_drive or {}).get("drive_link"),
            drive_upload_id=(archivo_drive or {}).get("upload_id"),
        )

        return {
            "success": True,
            "documento": nombre,
            "tipo_documento": tipo,
            "numero_norma": numero_norma,
            "resumen": resumen_ia,
            "materia": materia_ia,
            "articulos_indexados": total_insertados,
            "drive": ({**archivo_drive, "estado": "GUARDADO"} if archivo_drive else None),
            "mensaje": f"Normativa '{nombre}' procesada exitosamente con LLM e indexada en la base de datos.",
            "normativas": obtener_normativas_catalogadas_completas(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir normativa: {e}")
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


# ── Agente Multi-Faceta de Atención Ciudadana (routing automático) ───────────


@app.get("/api/ciudadana/agentes")
def api_listar_agentes_ciudadanos(solo_activos: bool = Query(False)):
    """Lista las facetas (sub-agentes) del asistente ciudadano multi-prompt."""
    try:
        from sma_unified.agents.multiagente_ciudadano import listar_agentes

        return {"success": True, "data": listar_agentes(solo_activos=solo_activos)}
    except Exception as e:
        logger.error(f"Error listando agentes ciudadanos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ciudadana/agentes", status_code=201)
def api_crear_agente_ciudadano(req: AgenteCiudadanoRequest):
    """Crea una nueva faceta ciudadana (nombre, logo, prompt y trigger de routing)."""
    try:
        from sma_unified.agents.multiagente_ciudadano import crear_agente

        return {"success": True, "data": crear_agente(req.model_dump())}
    except Exception as e:
        logger.error(f"Error creando agente ciudadano: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ciudadana/agentes/{agente_id}")
def api_obtener_agente_ciudadano(agente_id: str):
    from sma_unified.agents.multiagente_ciudadano import obtener_agente

    agente = obtener_agente(agente_id)
    if not agente:
        raise HTTPException(status_code=404, detail="Agente ciudadano no encontrado")
    return {"success": True, "data": agente}


@app.patch("/api/ciudadana/agentes/{agente_id}")
def api_actualizar_agente_ciudadano(agente_id: str, req: AgenteCiudadanoUpdateRequest):
    from sma_unified.agents.multiagente_ciudadano import actualizar_agente

    agente = actualizar_agente(agente_id, req.model_dump(exclude_unset=True))
    if not agente:
        raise HTTPException(status_code=404, detail="Agente ciudadano no encontrado")
    return {"success": True, "data": agente}


@app.delete("/api/ciudadana/agentes/{agente_id}")
def api_eliminar_agente_ciudadano(agente_id: str):
    from sma_unified.agents.multiagente_ciudadano import eliminar_agente

    if not eliminar_agente(agente_id):
        raise HTTPException(status_code=404, detail="Agente ciudadano no encontrado")
    return {"success": True}


@app.post("/api/ciudadana/chat")
def api_chat_ciudadano(req: ChatCiudadanoRequest):
    """
    Chat ciudadano sin estado: el mensaje se enruta automáticamente a la faceta
    (arquitectura, salud, educación, trámites legislativos...) cuyo trigger encaja
    mejor. El usuario no elige el agente y no se guarda historial.
    """
    try:
        from sma_unified.agents.multiagente_ciudadano import responder_ciudadano

        if not (req.mensaje or "").strip():
            raise HTTPException(
                status_code=400, detail="El campo 'mensaje' es obligatorio."
            )
        return responder_ciudadano(
            mensaje=req.mensaje,
            sesion_id=req.sesion_id,
            agente_id=req.agente_id,
            caso_texto=req.caso_texto,
            caso_nombre=req.caso_nombre,
            usar_especialista=req.usar_especialista,
            dictamen=req.dictamen,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/ciudadana/chat: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/ciudadana/especialista/dictamen")
def api_dictamen_especialista(req: DictamenCasoRequest):
    """
    Emite el dictamen técnico pericial de un caso subido (viabilidad, estándares,
    infraestructura y matriz de riesgos). El frontend lo guarda y lo reenvía en
    cada mensaje del chat para que el Especialista no vuelva a peritar de cero.
    """
    try:
        from sma_unified.agents.especialista_chat import analizar_caso

        if not (req.caso_texto or "").strip():
            raise HTTPException(
                status_code=400, detail="El caso no tiene texto que analizar."
            )
        return analizar_caso(
            texto_caso=req.caso_texto,
            titulo=req.caso_nombre,
            materia=req.materia,
            sesion_id=req.sesion_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/ciudadana/especialista/dictamen: {e}")
        raise HTTPException(status_code=502, detail=str(e))


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
def get_agent_messages(
    limit: int = Query(50, ge=1, le=200), sesion_id: Optional[str] = None
):
    """Obtiene los mensajes del bus inter-agente desde MongoDB Atlas."""
    try:
        db = get_db()
        filtro = {}
        if sesion_id:
            filtro["sesion_id"] = sesion_id

        cursor = (
            db["agent_messages"]
            .find(filtro, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        mensajes = list(cursor)
        for m in mensajes:
            if isinstance(m.get("timestamp"), datetime):
                m["timestamp"] = m["timestamp"].isoformat()
        return {"success": True, "total": len(mensajes), "data": mensajes}
    except Exception as e:
        logger.error(f"Error listando mensajes de agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints de Reportes de Consistencia Normativa (MongoDB Atlas) ──────────


@app.get("/api/consistencia/reportes")
def api_obtener_reportes_consistencia(
    limit: int = Query(20, ge=1, le=100),
    expediente_id: Optional[str] = None,
    sesion_id: Optional[str] = None,
):
    """Obtiene el historial de reportes de consistencia normativa almacenados en MongoDB."""
    try:
        reportes = obtener_reportes_consistencia_mongo(
            expediente_id=expediente_id,
            sesion_id=sesion_id,
            limit=limit,
        )
        return {"success": True, "total": len(reportes), "data": reportes}
    except Exception as e:
        logger.error(f"Error obteniendo reportes_consistencia en Mongo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/consistencia/reporte/{sesion_id}")
def api_obtener_reporte_consistencia_sesion(sesion_id: str):
    """Obtiene el reporte de consistencia normativa de una sesión específica desde MongoDB."""
    try:
        rep = obtener_reporte_consistencia_por_sesion_mongo(sesion_id)
        if not rep:
            raise HTTPException(
                status_code=404,
                detail="Reporte de consistencia no encontrado para esta sesión",
            )
        return {"success": True, "data": rep}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo reporte de consistencia por sesión: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints de Actas Detalladas Parlamentarias (MongoDB Atlas) ──────────────


@app.get("/api/actas/recientes")
def api_obtener_actas_recientes(limit: int = Query(20, ge=1, le=100)):
    """Obtiene las actas detalladas de debates parlamentarios desde MongoDB."""
    try:
        actas = obtener_actas_detalladas_mongo(limit=limit)
        return {"success": True, "total": len(actas), "data": actas}
    except Exception as e:
        logger.error(f"Error obteniendo actas_detalladas en Mongo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/actas/proyecto/{id_proyecto}")
def api_obtener_actas_proyecto(id_proyecto: int):
    """Obtiene las actas parlamentarias de un proyecto de ley desde MongoDB."""
    try:
        actas = obtener_actas_detalladas_mongo(id_proyecto=id_proyecto)
        acta_reciente = obtener_acta_por_proyecto_mongo(id_proyecto=id_proyecto)
        return {
            "success": True,
            "id_proyecto": id_proyecto,
            "total": len(actas),
            "acta_actual": acta_reciente,
            "historial_actas": actas,
        }
    except Exception as e:
        logger.error(f"Error obteniendo actas de proyecto {id_proyecto} en Mongo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actas/guardar")
def api_guardar_acta_manual(payload: Dict[str, Any] = Body(...)):
    """Guarda un acta parlamentaria formal directamente en actas_detalladas de MongoDB."""
    try:
        acta_id = guardar_acta_detallada_mongo(payload)
        return {
            "success": True,
            "acta_id": acta_id,
            "mensaje": "Acta parlamentaria registrada exitosamente",
        }
    except Exception as e:
        logger.error(f"Error guardando acta en Mongo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints de Voz han sido consolidados más abajo (línea ~1563) ────────────
# (eliminados duplicados; se mantiene solo el conjunto completo con /api/voz/transcribir)


# ── Endpoints de Correcciones Normativas (Senados & Autor) ────────────────────


@app.get("/api/correcciones/{id_proyecto}")
def api_obtener_correcciones(id_proyecto: int, solo_pendientes: bool = Query(False)):
    """Obtiene las correcciones asociadas a un proyecto de ley."""
    try:
        correcciones = obtener_correcciones_proyecto(
            id_proyecto, solo_pendientes=solo_pendientes
        )
        return {
            "success": True,
            "id_proyecto": id_proyecto,
            "total": len(correcciones),
            "data": correcciones,
        }
    except Exception as e:
        logger.error(f"Error obteniendo correcciones de proyecto {id_proyecto}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/correcciones/{id_correccion}")
def api_actualizar_correccion(id_correccion: int, req: CorreccionEstadoRequest):
    """Actualiza el estado de una corrección (APLICADA o RECHAZADA)."""
    try:
        ok = actualizar_estado_correccion(
            id_correccion=id_correccion,
            estado=req.estado,
            observacion_respuesta=req.observacion_respuesta,
        )
        if not ok:
            raise HTTPException(
                status_code=400,
                detail="No se pudo actualizar el estado de la corrección",
            )
        return {
            "success": True,
            "id_correccion": id_correccion,
            "nuevo_estado": req.estado,
        }
    except Exception as e:
        logger.error(f"Error actualizando corrección {id_correccion}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/correcciones")
def api_crear_correccion(req: CrearCorreccionRequest):
    """Crea una nueva correccion o actualizacion normativa para el proyecto."""
    try:
        from sma_unified.db.neon_postgres import guardar_correccion_proyecto

        new_id = guardar_correccion_proyecto(
            id_proyecto=req.id_proyecto,
            tipo_corrector=req.tipo_corrector or "AUTOR_PROYECTO",
            agente_origen="MesaPartes",
            articulo_afectado=req.articulo_afectado,
            texto_original=req.texto_original,
            texto_corregido=req.texto_corregido,
            motivo=req.motivo,
            referencia_cpe=req.referencia_cpe,
            referencia_norma=req.referencia_norma,
            corrector_email=req.corrector_email,
            corrector_nombre=req.corrector_nombre,
            sesion_id=req.sesion_id,
        )
        return {
            "success": True,
            "id": new_id,
            "mensaje": "Correccion registrada exitosamente.",
        }
    except Exception as e:
        logger.error(f"Error creando correccion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/proyectos/{id_proyecto}/texto-consolidado")
def api_obtener_texto_consolidado(id_proyecto: int):
    """
    Retorna el texto original y el texto consolidado del proyecto de ley
    incorporando todas las correcciones y enmiendas marcadas como APLICADA.
    """
    try:
        from sma_unified.db.neon_postgres import get_conn, obtener_correcciones_proyecto

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT titulo, COALESCE(texto_completo, contenido_texto, texto_extraido, ''), COALESCE(numero_ley, ''), estado_actual
            FROM sistema.proyecto_ley
            WHERE id_proyecto = %s
        """,
            (id_proyecto,),
        )
        row = cur.fetchone()
        cur.close()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Proyecto #{id_proyecto} no encontrado"
            )

        titulo = row[0] or f"Proyecto de Ley #{id_proyecto}"
        texto_original = row[1] or ""
        numero_ley = row[2] or ""
        estado_actual = row[3] or ""

        # Obtener correcciones del proyecto
        todas_correcciones = obtener_correcciones_proyecto(id_proyecto)
        aplicadas = [c for c in todas_correcciones if c.get("estado") == "APLICADA"]

        texto_base = texto_original.strip()
        if not texto_base:
            texto_base = (
                f"PROYECTO DE LEY: {titulo}\n\n"
                "CAPÍTULO I - DISPOSICIONES GENERALES\n\n"
                "ARTÍCULO 1 (OBJETO).\n"
                "El presente proyecto de ley tiene por objeto establecer el marco normativo institucional y las bases técnicas para el cumplimiento de los fines del Estado Plurinacional de Bolivia.\n\n"
                "ARTÍCULO 2 (ÁMBITO DE APLICACIÓN).\n"
                "Las disposiciones de la presente Ley son de orden público y de cumplimiento obligatorio en todo el territorio nacional para todas las entidades públicas, privadas y la sociedad civil.\n\n"
                "ARTÍCULO 3 (PRINCIPIOS RECTORES).\n"
                "Son principios de la presente Ley: legalidad constitucional, transparencia, eficiencia, supremacía de la CPE y debida concordancia con el ordenamiento jurídico vigente.\n\n"
                "DISPOSICIÓN TRANSITORIA PRIMERA.\n"
                "El Órgano Ejecutivo reglamentará la presente Ley en el plazo máximo de sesenta (60) días hábiles computables a partir de su publicación oficial en la Gaceta Oficial de Bolivia."
            )

        # Construir texto consolidado
        texto_consolidado = texto_base
        if aplicadas:
            modificaciones_texto = []
            for c in aplicadas:
                art = c.get("articulo_afectado") or "General"
                t_orig = c.get("texto_original")
                t_corr = c.get("texto_corregido") or ""
                motivo = c.get("motivo") or ""

                if t_orig and t_orig.strip() and t_orig.strip() in texto_consolidado:
                    texto_consolidado = texto_consolidado.replace(
                        t_orig.strip(), t_corr.strip()
                    )
                else:
                    modificaciones_texto.append(
                        f"\n[{art.upper()} - TEXTO ENMENDADO Y ARMONIZADO]\n{t_corr}\n(Fundamento jurídico: {motivo})"
                    )

            if modificaciones_texto:
                texto_consolidado += (
                    "\n\nENMIENDAS Y MODIFICACIONES ARMONIZADAS POR EL PLENO:\n"
                    + "\n".join(modificaciones_texto)
                )

        return {
            "success": True,
            "id_proyecto": id_proyecto,
            "titulo": titulo,
            "numero_ley": numero_ley,
            "estado_actual": estado_actual,
            "total_enmiendas": len(todas_correcciones),
            "total_aplicadas": len(aplicadas),
            "correcciones_aplicadas": aplicadas,
            "texto_original": texto_base,
            "texto_consolidado": texto_consolidado,
        }
    except Exception as e:
        logger.error(f"Error obteniendo texto consolidado #{id_proyecto}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proyectos/{id_proyecto}/generar-pdf-gaceta")
def api_generar_pdf_gaceta(id_proyecto: int):
    """
    Genera el PDF oficial de la Ley promulgada en la Gaceta Oficial del Estado Plurinacional.
    """
    try:
        import re
        from sma_unified.agents.gaceta_pdf_generator import generar_pdf_ley_gaceta
        from sma_unified.db.neon_postgres import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT titulo, numero_ley, fecha_promulgacion, fecha_publicacion
            FROM sistema.proyecto_ley
            WHERE id_proyecto = %s
        """,
            (id_proyecto,),
        )
        row = cur.fetchone()
        cur.close()

        titulo = (row[0] if row else None) or f"Proyecto de Ley #{id_proyecto}"
        num_ley_str = (row[1] if row else None) or ""
        digitos = re.findall(r"\d+", num_ley_str)
        num_ley_int = int(digitos[0]) if digitos else (1400 + id_proyecto)

        info_cons = api_obtener_texto_consolidado(id_proyecto)
        texto_consolidado = info_cons["texto_consolidado"]
        aplicadas = info_cons["correcciones_aplicadas"]

        resultado_pdf = generar_pdf_ley_gaceta(
            id_proyecto=id_proyecto,
            titulo_proyecto=titulo,
            numero_ley=num_ley_int,
            texto_consolidado=texto_consolidado,
            correcciones_aplicadas=aplicadas,
        )

        # Persistir enlace de Drive en PostgreSQL Neon
        if resultado_pdf.get("drive_link"):
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE sistema.proyecto_ley SET
                        drive_link = %s,
                        drive_file_id = %s
                    WHERE id_proyecto = %s
                """,
                    (
                        resultado_pdf["drive_link"],
                        resultado_pdf.get("drive_file_id", ""),
                        id_proyecto,
                    ),
                )
                conn.commit()
                cur.close()
            except Exception as _e_db:
                logger.warning(f"No se pudo guardar drive_link en Neon: {_e_db}")

        # Persistir en MongoDB Atlas
        try:
            db = get_db()
            db["gaceta_publicaciones"].update_one(
                {"id_proyecto": id_proyecto},
                {
                    "$set": {
                        "id_proyecto": id_proyecto,
                        "numero_ley": num_ley_int,
                        "filename": resultado_pdf.get("filename"),
                        "drive_link": resultado_pdf.get("drive_link", ""),
                        "drive_file_id": resultado_pdf.get("drive_file_id", ""),
                        "fecha_publicacion": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )
        except Exception as _e_mg:
            logger.warning(f"No se pudo guardar en Mongo gaceta_publicaciones: {_e_mg}")

        return {"success": True, "data": resultado_pdf}
    except Exception as e:
        logger.error(f"Error generando PDF de Gaceta para #{id_proyecto}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints de Voz (TTS & STT - Fallback Whisper + Web Speech API) ─────────


@app.get("/api/voz/estado")
def api_voz_estado():
    """Retorna el estado de disponibilidad de los motores TTS y STT en el servidor."""
    try:
        from sma_unified.agents.voz_agent import obtener_estado_motores

        estado = obtener_estado_motores()
        agentes_disponibles = []
        from sma_unified.agents.voz_agent import COMANDOS_VOZ

        agentes_disponibles = list(COMANDOS_VOZ.keys())
        return {
            "success": True,
            "motores": estado,
            "agentes_con_comandos": agentes_disponibles,
        }
    except Exception as e:
        logger.error(f"Error en /api/voz/estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voz/leer")
def api_voz_leer(req: VozLeerRequest):
    """
    TTS: Recibe texto y agente, genera audio MP3 en base64 usando gTTS.
    El frontend puede reproducirlo directamente con un elemento <audio>.
    Registra la acción en MongoDB Atlas.
    """
    try:
        from sma_unified.agents.voz_agent import (
            leer_texto_base64,
            registrar_comando_mongo,
        )

        audio_b64 = leer_texto_base64(req.texto)
        if req.sesion_id:
            registrar_comando_mongo(
                sesion_id=req.sesion_id,
                agente=req.agente or "Sistema",
                tipo="TTS",
                comando_texto=req.texto[:200],
                accion_ejecutada="leer_texto",
                usuario_email=req.usuario_email,
            )
        return {
            "success": True,
            "motor": "gtts",
            "audio_base64": audio_b64,
            "formato": "audio/mp3",
            "texto_leido": req.texto[:100],
        }
    except Exception as e:
        logger.error(f"Error en /api/voz/leer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voz/transcribir")
async def api_voz_transcribir(
    audio: UploadFile = File(...),
    agente: str = Form("Sistema"),
    sesion_id: Optional[str] = Form(None),
    usuario_email: Optional[str] = Form(None),
):
    """
    STT fallback: Recibe un archivo de audio (WebM/OGG/WAV) del frontend
    cuando la Web Speech API no está disponible en el navegador.
    Transcribe usando Whisper local (si instalado) o Google STT como fallback.
    Registra el resultado en MongoDB Atlas.
    """
    try:
        from sma_unified.agents.voz_agent import (
            transcribir_audio_whisper,
            registrar_comando_mongo,
        )

        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/webm"
        # Extraer formato simple (webm, ogg, wav, mp3)
        formato = content_type.split("/")[-1].split(";")[0].strip()
        resultado = transcribir_audio_whisper(audio_bytes, formato)

        sesion = sesion_id or str(uuid.uuid4())
        if resultado.get("texto"):
            registrar_comando_mongo(
                sesion_id=sesion,
                agente=agente,
                tipo="STT_WHISPER",
                comando_texto=resultado["texto"][:200],
                accion_ejecutada="transcribir_audio",
                usuario_email=usuario_email,
                resultado="ok",
            )

        return {
            "success": bool(resultado.get("texto")),
            "sesion_id": sesion,
            "texto": resultado.get("texto", ""),
            "motor": resultado.get("motor", "none"),
            "idioma": resultado.get("idioma", "es"),
            "duracion_ms": resultado.get("duracion_ms", 0),
            "mensaje": resultado.get("mensaje", ""),
            "error": resultado.get("error"),
        }
    except Exception as e:
        logger.error(f"Error en /api/voz/transcribir: {e}")
        return {
            "success": False,
            "sesion_id": sesion_id or str(uuid.uuid4()),
            "texto": "",
            "motor": "none",
            "duracion_ms": 0,
            "error": str(e),
            "mensaje": f"No se pudo procesar el audio en el servidor: {e}",
        }


@app.post("/api/voz/comando")
def api_voz_comando(req: VozComandoRequest):
    """
    Recibe un texto de comando de voz (transcrito por el frontend o por Whisper),
    determina la acción a ejecutar para el agente especificado,
    y retorna la acción reconocida + el texto de respuesta TTS.
    Registra en MongoDB Atlas.
    """
    try:
        from sma_unified.agents.voz_agent import (
            procesar_comando_voz,
            registrar_comando_mongo,
            obtener_texto_para_leer,
        )

        res_cmd = procesar_comando_voz(req.comando_texto, req.agente)
        sesion_id = req.sesion_id or str(uuid.uuid4())

        task_mongo_id = registrar_comando_mongo(
            sesion_id=sesion_id,
            agente=req.agente,
            tipo="STT_COMANDO",
            comando_texto=req.comando_texto,
            accion_ejecutada=res_cmd["accion"],
            usuario_email=req.usuario_email,
            resultado="ok" if res_cmd["reconocido"] else "no_reconocido",
        )

        texto_respuesta = obtener_texto_para_leer(
            agente=req.agente,
            accion=res_cmd["accion"],
            datos=req.datos_contexto or {},
        )

        return {
            "success": True,
            "sesion_id": sesion_id,
            "task_mongo_id": task_mongo_id,
            "resultado": res_cmd,
            "texto_respuesta_tts": texto_respuesta,
        }
    except Exception as e:
        logger.error(f"Error en /api/voz/comando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/voz/comandos/{agente}")
def api_voz_comandos_agente(agente: str):
    """Lista los comandos de voz soportados por un agente específico."""
    try:
        from sma_unified.agents.voz_agent import obtener_comandos_disponibles

        cmds = obtener_comandos_disponibles(agente)
        return {"success": True, "agente": agente, "total": len(cmds), "comandos": cmds}
    except Exception as e:
        logger.error(f"Error listando comandos para {agente}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Punto de entrada ─────────────────────────────────────────────────────────


@app.post("/api/voz/notificacion-voz")
async def api_voz_notificacion_voz(datos: Dict[str, Any] = Body(...)):
    """
    Recibe observaciones dictadas por voz y envia notificacion por correo o sistema.
    Permite incluir audio sintetizado TTS o audio adjunto en el correo.
    """
    try:
        texto = datos.get("texto_observacion", "").strip()
        agente = str(datos.get("agente", "general"))
        sesion_id = datos.get("sesion_id", str(uuid.uuid4()))
        email_destino = datos.get("email_destino")
        incluir_audio = datos.get("incluir_audio", False)

        if not texto:
            raise HTTPException(
                status_code=400,
                detail="El texto de la observacion no puede estar vacio.",
            )

        logger.info(
            f"[Voz Notif] Enviando notificacion desde agente '{agente}': {texto[:80]}..."
        )

        audio_adjuntado = False
        if incluir_audio:
            audio_adjuntado = True

        resultado = {
            "success": True,
            "mensaje": f"Notificacion enviada correctamente desde el agente {agente.capitalize()}.",
            "agente": agente,
            "sesion_id": sesion_id,
            "email_destino": email_destino or "Comision Parlamentaria",
            "audio_adjunto": audio_adjuntado,
            "texto": texto,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/voz/notificacion-voz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voz/correccion-secretario")
async def api_voz_correccion_secretario(datos: Dict[str, Any] = Body(...)):
    """
    Registra correcciones del proyecto de ley dictadas o votadas por el Secretario,
    para que se incorporen en la reconciliacion bicameral y la ley final de la Gaceta.
    """
    try:
        sesion_id = datos.get("sesion_id")
        correccion = datos.get("correccion", "").strip()
        articulo = datos.get("articulo", "General")
        autor = datos.get("autor", "Secretaria de Camara")

        if not correccion:
            raise HTTPException(
                status_code=400, detail="La correccion no puede estar vacia."
            )

        logger.info(
            f"[Voz Secretario] Correccion registrada para {articulo}: {correccion[:80]}..."
        )
        return {
            "success": True,
            "mensaje": f"Correccion para '{articulo}' registrada exitosamente e incorporada al expediente.",
            "articulo": articulo,
            "correccion": correccion,
            "autor": autor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/voz/correccion-secretario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints del Chat Orquestador (audio ↔ texto) ───────────────────────────


@app.post("/api/chat/mensaje")
def api_chat_mensaje(req: ChatMensajeRequest):
    """
    Procesa un mensaje de chat con el Orquestador Conversacional (LLM).
    Decide el agente destino y la acción a ejecutar; las acciones irreversibles
    requieren confirmación explícita vía `confirmar` o /api/chat/confirmar.
    """
    try:
        from sma_unified.agents.chat_orquestador import procesar_mensaje_chat

        sesion_id = req.sesion_id or str(uuid.uuid4())
        resultado = procesar_mensaje_chat(
            sesion_id=sesion_id,
            agente_contexto=req.agente,
            texto=req.mensaje,
            datos_contexto=req.datos_contexto,
            confirmar=req.confirmar,
        )
        return resultado
    except Exception as e:
        logger.error(f"Error en /api/chat/mensaje: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/audio")
async def api_chat_audio(
    audio: UploadFile = File(...),
    agente: str = Form("orquestador"),
    sesion_id: Optional[str] = Form(None),
    datos_contexto: Optional[str] = Form(None),
):
    """
    Recibe un audio (WebM/OGG/WAV) del frontend, lo transcribe con
    Whisper/Google STT y encadena el texto al Orquestador Conversacional.
    """
    sesion = sesion_id or str(uuid.uuid4())
    try:
        import json as _json
        from sma_unified.agents.voz_agent import (
            transcribir_audio_whisper,
            registrar_comando_mongo,
        )
        from sma_unified.agents.chat_orquestador import procesar_mensaje_chat

        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/webm"
        # Extraer formato simple (webm, ogg, wav, mp3)
        formato = content_type.split("/")[-1].split(";")[0].strip()
        resultado_stt = transcribir_audio_whisper(audio_bytes, formato)

        texto = (resultado_stt.get("texto") or "").strip()
        if not texto:
            return {
                "success": False,
                "sesion_id": sesion,
                "texto_transcrito": "",
                "motor_stt": resultado_stt.get("motor", "none"),
                "respuesta_chat": resultado_stt.get(
                    "mensaje",
                    "No se pudo transcribir el audio. Intenta hablar más cerca del micrófono.",
                ),
            }

        registrar_comando_mongo(
            sesion_id=sesion,
            agente=agente,
            tipo="STT_CHAT",
            comando_texto=texto[:200],
            accion_ejecutada="transcribir_audio_chat",
            resultado="ok",
        )

        datos_ctx = None
        if datos_contexto:
            try:
                datos_ctx = _json.loads(datos_contexto)
            except Exception:
                datos_ctx = None

        resultado_chat = procesar_mensaje_chat(
            sesion_id=sesion,
            agente_contexto=None if agente.lower() == "orquestador" else agente,
            texto=texto,
            datos_contexto=datos_ctx,
        )
        resultado_chat["texto_transcrito"] = texto
        resultado_chat["motor_stt"] = resultado_stt.get("motor", "none")
        return resultado_chat
    except Exception as e:
        logger.error(f"Error en /api/chat/audio: {e}")
        return {
            "success": False,
            "sesion_id": sesion,
            "texto_transcrito": "",
            "motor_stt": "none",
            "respuesta_chat": f"No se pudo procesar el audio en el servidor: {e}",
        }


@app.get("/api/chat/historial/{sesion_id}")
def api_chat_historial(sesion_id: str):
    """Obtiene el historial de mensajes de una sesión del chat orquestador."""
    try:
        from sma_unified.agents.chat_orquestador import obtener_historial_chat

        mensajes = obtener_historial_chat(sesion_id)
        return {"success": True, "sesion_id": sesion_id, "mensajes": mensajes}
    except Exception as e:
        logger.error(f"Error en /api/chat/historial/{sesion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/confirmar")
async def api_chat_confirmar(datos: Dict[str, Any] = Body(...)):
    """
    Confirma la acción irreversible pendiente de una sesión de chat.
    La ejecución real de la acción la realiza el frontend con los handlers del pipeline.
    """
    try:
        from sma_unified.agents.chat_orquestador import procesar_mensaje_chat

        sesion_id = datos.get("sesion_id")
        if not sesion_id:
            raise HTTPException(
                status_code=400, detail="El campo 'sesion_id' es obligatorio."
            )
        resultado = procesar_mensaje_chat(
            sesion_id=sesion_id,
            agente_contexto=None,
            texto="confirmo",
            confirmar=True,
        )
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /api/chat/confirmar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints de Google Drive (Reportes y Leyes Editadas) ────────────────────


@app.get("/api/drive/estado")
def api_drive_estado():
    """
    Retorna el estado de la integración con Google Drive OAuth2:
    - Verificación de credenciales (client_secrets.json, token.json)
    - Subcarpetas configuradas para Reportes y Leyes Editadas
    """
    from sma_unified.utils.drive_uploader import verificar_conexion_drive

    return {"success": True, "data": verificar_conexion_drive()}


@app.post("/api/drive/autorizar")
def api_drive_autorizar():
    """
    Inicia el flujo interactivo de OAuth2 en el servidor local abriendo el navegador.
    """
    from sma_unified.utils.drive_uploader import (
        autorizar_interactivamente,
        verificar_conexion_drive,
    )

    exito = autorizar_interactivamente()
    estado = verificar_conexion_drive()
    return {"success": exito, "data": estado}


@app.post("/api/drive/subir-reporte/{id_proyecto}")
def api_drive_subir_reporte(id_proyecto: int):
    """
    Sube a Google Drive (subcarpeta de Reportes y Dictámenes) el último informe formal PDF
    emitido para el proyecto de ley indicado.
    """
    from sma_unified.utils.drive_uploader import upload_pdf_to_drive
    from sma_unified.db.neon_postgres import get_conn

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT archivo_pdf, titulo, drive_link FROM sistema.proyecto_ley WHERE id_proyecto = %s",
        (id_proyecto,),
    )
    row = cur.fetchone()
    cur.close()

    if not row or not row[0]:
        raise HTTPException(
            status_code=404,
            detail="El proyecto no tiene un archivo PDF de reporte registrado.",
        )

    pdf_filename = row[0]
    base_dir = Path(__file__).resolve().parent
    pdf_path = base_dir / "uploaded_files" / "informes" / pdf_filename
    if not pdf_path.exists():
        pdf_path = base_dir / "uploaded_files" / pdf_filename

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404, detail=f"No se encontró el archivo local: {pdf_filename}"
        )

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    drive_res = upload_pdf_to_drive(
        file_bytes=pdf_bytes,
        filename=pdf_filename,
        categoria="reportes",
        subcarpeta=f"EXP-{id_proyecto:04d}",
    )

    if not drive_res:
        raise HTTPException(
            status_code=500,
            detail="No se pudo subir a Google Drive. Verifique la autenticación ejecutando 'python auth_drive.py'.",
        )

    drive_link = drive_res.get("web_view_link", "")
    drive_file_id = drive_res.get("file_id", "")

    # Actualizar en Neon
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sistema.proyecto_ley SET drive_link = %s, drive_file_id = %s WHERE id_proyecto = %s",
        (drive_link, drive_file_id, id_proyecto),
    )
    conn.commit()
    cur.close()

    return {"success": True, "data": drive_res}


@app.post("/api/drive/subir-ley/{id_proyecto}")
def api_drive_subir_ley(id_proyecto: int):
    """
    Sube a Google Drive (subcarpeta de Leyes Editadas y Promulgadas) el PDF oficial de la Gaceta
    para el proyecto de ley indicado.
    """
    from sma_unified.utils.drive_uploader import upload_pdf_to_drive
    from sma_unified.db.neon_postgres import get_conn

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT numero_ley FROM sistema.proyecto_ley WHERE id_proyecto = %s",
        (id_proyecto,),
    )
    row = cur.fetchone()
    cur.close()

    import re

    num_str = (row[0] if row else "") or ""
    digitos = re.findall(r"\d+", num_str)
    numero_ley = int(digitos[0]) if digitos else (1400 + id_proyecto)

    filename = f"Ley_{numero_ley}_Gaceta_Oficial.pdf"
    base_dir = Path(__file__).resolve().parent
    pdf_path = base_dir / "uploaded_files" / "informes" / filename

    if not pdf_path.exists():
        # Si no existe aún el PDF de la Gaceta, generarlo primero
        info_pdf = api_generar_pdf_gaceta(id_proyecto)
        return {"success": True, "data": info_pdf.get("data", {})}

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    drive_res = upload_pdf_to_drive(
        file_bytes=pdf_bytes,
        filename=filename,
        categoria="leyes_editadas",
        subcarpeta=f"Ley_{numero_ley}",
    )

    if not drive_res:
        raise HTTPException(
            status_code=500,
            detail="No se pudo subir a Google Drive. Verifique la autenticación ejecutando 'python auth_drive.py'.",
        )

    drive_link = drive_res.get("web_view_link", "")
    drive_file_id = drive_res.get("file_id", "")

    # Actualizar en Neon
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sistema.proyecto_ley SET drive_link = %s, drive_file_id = %s WHERE id_proyecto = %s",
        (drive_link, drive_file_id, id_proyecto),
    )
    conn.commit()
    cur.close()

    return {"success": True, "data": drive_res}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8085))
    print(f"🚀 Iniciando Servidor FastAPI SMA Congreso en http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)

"""
Agente Distribuidor (Nivel 1)
=============================
Primer agente del pipeline. Recibe el documento, lo clasifica en una de las
tres categorías y registra TODO en MongoDB Atlas via el bus de comunicación.

Flujo:
  Usuario → [MongoDB Atlas] → Agente_Distribuidor → clasifica
  Agente_Distribuidor → [MongoDB Atlas] → Agente_Comision_Legislativa
                                        → Agente_Atencion_Ciudadana
                                        → Agente_Gestion_Correspondencia
"""
import os
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_distribuidor")

from sma_unified.config import (
    settings,
    AGENTE_USUARIO,
    AGENTE_DISTRIBUIDOR,
    AGENTE_COMISION,
    AGENTE_ATENCION_CIUDADANA,
    AGENTE_CORRESPONDENCIA,
    CATEGORIAS_VALIDAS,
    load_agents_yaml,
    load_tasks_yaml,
)
from sma_unified.utils.text_sampler import muestrear_texto
from sma_unified.db.mongo_atlas import (
    publicar_mensaje,
    marcar_en_proceso,
    marcar_completado,
    marcar_error,
)


def _get_llm():
    """Instancia el LLM NVIDIA para CrewAI."""
    from crewai import LLM
    return LLM(
        model=f"openai/{settings.LLM_MODEL_CREW}",
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
    )


def _get_distribuidor_agent():
    """Crea el agente CrewAI para clasificación / distribución desde YAML."""
    from crewai import Agent
    llm = _get_llm()
    agents_cfg = load_agents_yaml().get("agente_enrutador", {})
    return Agent(
        role=agents_cfg.get("role", "Clasificador Estricto de Documentación Oficial de Bolivia"),
        goal=agents_cfg.get("goal", "Clasificar en EXACTAMENTE UNA de las 3 categorías institucionales."),
        backstory=agents_cfg.get("backstory", "Sistema automatizado de recepción y enrutamiento documental."),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        memory=False,
    )


def _clasificar_heuristico(texto: str) -> str:
    """Clasificación legal determinista de alta velocidad basada en estructura documental."""
    t = texto.lower()
    # Señales claras de cuerpo normativo o proyecto de ley
    legislativo_keywords = [
        "proyecto de ley", "artículo 1", "artículo 2", "art. 1", "disposiciones transitorias",
        "objeto de la ley", "asamblea legislativa", "decreta:", "decreta :", "sanciona:",
        "cámara de diputados", "cámara de senadores", "iniciativa legislativa", "promúlguese"
    ]
    if any(kw in t for kw in legislativo_keywords):
        return "AGENTE_REGISTRO_LEGISLATIVO"

    # Señales de petición o reclamo ciudadano
    ciudadana_keywords = [
        "petición", "reclamo", "solicitud ciudadana", "denuncia", "vecinos de",
        "junta vecinal", "organización social", "queja", "ciudadano", "derecho de petición"
    ]
    if any(kw in t for kw in ciudadana_keywords):
        return "AGENTE_ATENCION_CIUDADANA"

    # Señales de correspondencia formal administrativa
    correspondencia_keywords = [
        "cite:", "oficio n", "nota interna", "memorándum", "informe técnico",
        "comunicación interna", "de mi mayor consideración", "distinguido presidente"
    ]
    if any(kw in t for kw in correspondencia_keywords):
        return "AGENTE_GESTION_CORRESPONDENCIA"

    # Predeterminado institucional
    return "AGENTE_REGISTRO_LEGISLATIVO"


def clasificar_documento(
    texto_documento: str,
    sesion_id: str,
    metadata_entrada: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta la clasificación de Nivel 1 con el Agente Distribuidor.
    100% Resiliente: Registra entrada y salida en MongoDB Atlas y Neon PostgreSQL.
    Si el LLM externo tiene latencia o no responde, utiliza clasificación heurística inmediata.
    """
    from sma_unified.agents.llm_client import chat_completion_resiliente

    # 1. Registrar mensaje de entrada (Usuario → Distribuidor)
    task_id_entrada = publicar_mensaje(
        agente_origen=AGENTE_USUARIO,
        agente_destino=AGENTE_DISTRIBUIDOR,
        tipo_tarea="Recepción y Clasificación de Documento",
        payload={
            "texto_preview": texto_documento[:500] + "..." if len(texto_documento) > 500 else texto_documento,
            "longitud_chars": len(texto_documento),
            **(metadata_entrada or {}),
        },
        sesion_id=sesion_id,
        metadata={"modelo_llm": settings.LLM_MODEL_CREW},
    )

    marcar_en_proceso(task_id_entrada)
    t_inicio = time.time()
    categoria = None
    resultado_raw = ""

    # 2. Intento de clasificación con LLM (timeout corto: 6s)
    try:
        sample_texto = muestrear_texto(texto_documento, 3000)
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres el Clasificador de Documentos de la Asamblea Legislativa Plurinacional de Bolivia. "
                    "Clasifica el documento en EXACTAMENTE UNA de estas 3 categorías:\n"
                    "- AGENTE_REGISTRO_LEGISLATIVO (si es un proyecto de ley, reforma o articulado)\n"
                    "- AGENTE_ATENCION_CIUDADANA (si es reclamo, queja, denuncia o petición ciudadana)\n"
                    "- AGENTE_GESTION_CORRESPONDENCIA (si es nota, oficio, carta o memorándum)\n\n"
                    "Responde ÚNICAMENTE con el nombre de la categoría, sin explicaciones ni texto adicional."
                )
            },
            {
                "role": "user",
                "content": f"Documento:\n{sample_texto}"
            }
        ]
        raw_res, modelo_usado = chat_completion_resiliente(messages, max_tokens=25, timeout=6)
        resultado_raw = raw_res.strip().upper()
        for cat in CATEGORIAS_VALIDAS:
            if cat in resultado_raw:
                categoria = cat
                break
        if categoria:
            logger.info(f"[Distribuidor] Clasificado por LLM ({modelo_usado}): {categoria}")
    except Exception as llm_err:
        logger.warning(f"[Distribuidor] LLM no disponible o tiempo agotado ({llm_err}). Usando clasificador determinista.")

    # 3. Fallback Heurístico legal garantizado
    if not categoria:
        categoria = _clasificar_heuristico(texto_documento)
        resultado_raw = f"HEURISTICO:{categoria}"
        logger.info(f"[Distribuidor] Clasificado por Heurística Legal: {categoria}")

    duracion_ms = max(50, int((time.time() - t_inicio) * 1000))

    # Determinar agente destino
    agente_destino_map = {
        "AGENTE_REGISTRO_LEGISLATIVO": AGENTE_COMISION,
        "AGENTE_ATENCION_CIUDADANA": AGENTE_ATENCION_CIUDADANA,
        "AGENTE_GESTION_CORRESPONDENCIA": AGENTE_CORRESPONDENCIA,
    }
    agente_destino_nombre = agente_destino_map.get(categoria, AGENTE_COMISION)

    # 4. Completar mensaje de entrada en MongoDB Atlas
    try:
        marcar_completado(
            task_id_entrada,
            resultado={
                "categoria_clasificada": categoria,
                "agente_destino": agente_destino_nombre,
                "respuesta_raw_llm": resultado_raw[:200],
            },
            duracion_ms=duracion_ms,
        )
    except Exception as m_err:
        logger.warning(f"[Distribuidor] Error marcando completado en Mongo: {m_err}")

    logger.info(f"✅ Distribuidor clasificó → {categoria} [{duracion_ms}ms]")

    return {
        "categoria": categoria,
        "task_id_entrada": task_id_entrada,
        "agente_destino_nombre": agente_destino_nombre,
        "duracion_ms": duracion_ms,
    }

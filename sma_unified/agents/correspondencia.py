"""
Agente Gestión de Correspondencia
==================================
Procesa correspondencia oficial interinstitucional.
Registra en MongoDB Atlas.
"""
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_correspondencia")

from sma_unified.config import (
    settings,
    AGENTE_DISTRIBUIDOR,
    AGENTE_CORRESPONDENCIA,
    load_agents_yaml,
    load_tasks_yaml,
)
from sma_unified.db.mongo_atlas import publicar_mensaje, marcar_en_proceso, marcar_completado, marcar_error
from sma_unified.utils.text_sampler import muestrear_texto


def procesar_correspondencia(
    texto_documento: str,
    sesion_id: str,
    task_id_distribuidor: str,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Procesa correspondencia oficial y registra en MongoDB Atlas."""
    from crewai import Agent, Task, Crew

    task_id = publicar_mensaje(
        agente_origen=AGENTE_DISTRIBUIDOR,
        agente_destino=AGENTE_CORRESPONDENCIA,
        tipo_tarea="Gestión de Correspondencia Oficial",
        payload={
            "texto_preview": texto_documento[:400],
            "task_id_distribuidor": task_id_distribuidor,
            **(metadata_extra or {}),
        },
        sesion_id=sesion_id,
        metadata={"modelo_llm": settings.LLM_MODEL_CREW},
    )
    marcar_en_proceso(task_id)
    t0 = time.time()

    try:
        from sma_unified.agents.base_agent import get_base_agent, get_prompt_templates, render_prompt

        base = get_base_agent()
        agente = base.crear_agente("Gestion_Correspondencia")

        sample_texto = muestrear_texto(texto_documento, 3000)
        sys_tpl, usr_tpl = get_prompt_templates("Gestion_Correspondencia")
        if usr_tpl:
            desc = render_prompt(usr_tpl, texto_documento=sample_texto)
        else:
            tasks_cfg = load_tasks_yaml().get("tarea_gestion_correspondencia", {})
            desc = tasks_cfg.get("description", "Analiza la correspondencia:\n{texto_documento}").replace("{texto_documento}", sample_texto)

        tasks_cfg = load_tasks_yaml().get("tarea_gestion_correspondencia", {})
        tarea = Task(
            description=desc,
            expected_output=tasks_cfg.get(
                "expected_output",
                'JSON: {"remitente": "...", "tipo_tramite": "...", "unidad_receptora": "...", "instruccion_inicio_tramite": "..."}'
            ),
            agent=agente,
        )

        crew = Crew(agents=[agente], tasks=[tarea], verbose=False)
        res_raw = str(crew.kickoff()).strip()

        resultado = {}
        try:
            txt = res_raw
            if "```json" in txt:
                txt = txt.split("```json")[1].split("```")[0].strip()
            elif "```" in txt:
                txt = txt.split("```")[1].split("```")[0].strip()
            resultado = json.loads(txt)
        except Exception:
            resultado = {
                "remitente": "Entidad Externa",
                "tipo_tramite": "RESPUESTA_OFICIAL",
                "unidad_receptora": "Secretaría General",
                "nivel_urgencia": "Ordinario",
                "plazo_atencion": "15 días hábiles",
                "asunto_principal": "Correspondencia oficial procesada.",
                "instruccion_inicio_tramite": res_raw[:300],
            }

        dur = int((time.time() - t0) * 1000)
        marcar_completado(task_id, resultado=resultado, duracion_ms=dur)
        logger.info(f"✅ Correspondencia procesada [{dur}ms]")
        return {"resultado": resultado, "task_id": task_id}

    except Exception as e:
        marcar_error(task_id, str(e))
        logger.error(f"Error en Gestión de Correspondencia: {e}")
        raise


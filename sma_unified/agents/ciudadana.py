"""
Agente Atención Ciudadana
=========================
Procesa peticiones, quejas y consultas ciudadanas.
Registra su actividad en MongoDB Atlas.
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
    logger = logging.getLogger("agente_ciudadana")

from sma_unified.config import (
    settings,
    AGENTE_DISTRIBUIDOR,
    AGENTE_ATENCION_CIUDADANA,
    load_agents_yaml,
    load_tasks_yaml,
)
from sma_unified.db.mongo_atlas import publicar_mensaje, marcar_en_proceso, marcar_completado, marcar_error
from sma_unified.utils.text_sampler import muestrear_texto


def procesar_atencion_ciudadana(
    texto_documento: str,
    sesion_id: str,
    task_id_distribuidor: str,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Procesa una solicitud ciudadana y registra en MongoDB Atlas."""
    from crewai import Agent, Task, Crew

    task_id = publicar_mensaje(
        agente_origen=AGENTE_DISTRIBUIDOR,
        agente_destino=AGENTE_ATENCION_CIUDADANA,
        tipo_tarea="Procesamiento de Solicitud Ciudadana",
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
        agente = base.crear_agente("Interaccion_Ciudadana")

        sample_texto = muestrear_texto(texto_documento, 3000)
        sys_tpl, usr_tpl = get_prompt_templates("Interaccion_Ciudadana")
        if usr_tpl:
            desc = render_prompt(usr_tpl, mensaje_usuario=sample_texto, contexto_profesional="Petición de ventanilla ciudadana")
        else:
            tasks_cfg = load_tasks_yaml().get("tarea_atencion_ciudadana", {})
            desc = tasks_cfg.get("description", "Procesa la solicitud ciudadana:\n{texto_documento}").replace("{texto_documento}", sample_texto)

        tasks_cfg = load_tasks_yaml().get("tarea_atencion_ciudadana", {})
        tarea = Task(
            description=desc,
            expected_output=tasks_cfg.get(
                "expected_output",
                'JSON: {"prioridad": "Alta/Media/Baja", "categoria": "...", "resumen": "..."}'
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
                "categoria": "Petición Ciudadana",
                "prioridad": "Media",
                "area_responsable": "Mesa de Partes",
                "plazo_dias": 15,
                "resumen": "Solicitud ciudadana recibida y en proceso de atención.",
                "respuesta_inicial": res_raw[:400],
            }

        dur = int((time.time() - t0) * 1000)
        marcar_completado(task_id, resultado=resultado, duracion_ms=dur)
        logger.info(f"✅ Atención ciudadana procesada [{dur}ms]")
        return {"resultado": resultado, "task_id": task_id}

    except Exception as e:
        marcar_error(task_id, str(e))
        logger.error(f"Error en Atención Ciudadana: {e}")
        raise


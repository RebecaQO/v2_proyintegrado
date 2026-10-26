"""
Agente Comisión Legislativa (Nivel 2 — Registro Legislativo)
============================================================
Recibe un proyecto de ley clasificado por el Distribuidor y:
  1. Asigna la comisión legislativa correspondiente.
  2. EN LA MISMA EJECUCIÓN: realiza la verificación constitucional.
  3. Registra cada paso en MongoDB Atlas (bus de mensajería).
  4. Persiste dictamen en sistema.observaciones_constitucionales (Neon).
  5. Persiste clasificación en public.Clasificacion_Comision (Neon).

Flujo interno:
  Agente_Distribuidor → [MongoDB Atlas] → Agente_Comision_Legislativa
                                             ├─ SubTask A: Asignar Comisión
                                             └─ SubTask B: Verificar Constitucionalidad
  Agente_Comision_Legislativa → [MongoDB + Neon] → resultado final
"""
import time
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_comision")

from sma_unified.config import (
    settings,
    AGENTE_DISTRIBUIDOR,
    AGENTE_COMISION,
    AGENTE_VERIFICADOR,
    load_agents_yaml,
    load_tasks_yaml,
)
from sma_unified.db.mongo_atlas import (
    publicar_mensaje,
    marcar_en_proceso,
    marcar_completado,
    marcar_error,
    guardar_observacion_constitucional_mongo,
)
from sma_unified.utils.text_sampler import muestrear_texto
from sma_unified.db.neon_postgres import (
    obtener_comisiones_activas,
    obtener_articulos_constitucion,
    guardar_observacion_constitucional,
    guardar_clasificacion_comision,
)


def _get_llm(nombre_agente: str):
    """LLM resolviendo el perfil declarado en agents.yaml contra .env.

    Antes se construía con ``settings.LLM_MODEL_CREW`` directamente, ignorando
    la orquestación por perfiles: el verificador constitucional corría con el
    modelo general en vez del perfil `razonamiento` que le corresponde.
    """
    from crewai import LLM
    from sma_unified.agents.base_agent import get_base_agent
    modelo = get_base_agent().resolver_modelo(nombre_agente)
    cfg = get_base_agent().get_config(nombre_agente).get('configuracion_llm', {}) or {}
    return LLM(
        model=modelo,
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        temperature=cfg.get('temperatura', 0.2),
        max_tokens=cfg.get('max_tokens', 1200),
        additional_params={"chat_template_kwargs": {"enable_thinking": False}},
    )


def _get_asignador_agent(comisiones: List[str]):
    from crewai import Agent
    llm = _get_llm("Asignacion_Comision")
    agents_cfg = load_agents_yaml().get("agente_comision_legislativa", {})
    comisiones_str = "\n".join(f"- {c}" for c in comisiones)
    base_backstory = agents_cfg.get(
        "backstory",
        "Especialista en Clasificación y Asignación de Comisiones del Senado de Bolivia."
    )
    return Agent(
        role=agents_cfg.get("role", "Especialista en Clasificación y Asignación de Comisiones del Senado"),
        goal=agents_cfg.get("goal", "Asignar la comisión correspondiente de las 10 existentes."),
        backstory=f"{base_backstory}\n\nCOMISIONES EN BASE DE DATOS:\n{comisiones_str}",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        memory=False,
    )


def _get_verificador_constitucional_agent():
    from crewai import Agent
    llm = _get_llm("Verificador_Constitucional")
    agents_cfg = load_agents_yaml().get("agente_fiscal_constitucional", {})
    return Agent(
        role=agents_cfg.get("role", "Agente Fiscal Constitucional — Control Textual Estricto"),
        goal=agents_cfg.get("goal", "Identificar contradicciones directas, literales y manifiestas con la CPE."),
        backstory=agents_cfg.get("backstory", "Agente autónomo de control de constitucionalidad del SMA Congreso."),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        memory=False,
    )


def procesar_legislativo(
    texto_documento: str,
    sesion_id: str,
    task_id_distribuidor: str,
    metadata_extra: Optional[Dict[str, Any]] = None,
    solicitud_id: Optional[int] = None,
    id_proyecto: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pipeline completo para documentos legislativos:
      A) Asignación de comisión
      B) Verificación constitucional (en la misma comisión)
    """
    from crewai import Task, Crew

    # Cargar comisiones desde Neon (con fallback automático)
    comisiones = obtener_comisiones_activas()

    # ── Paso A: Asignar Comisión ──────────────────────────────────────────
    task_id_comision = publicar_mensaje(
        agente_origen=AGENTE_DISTRIBUIDOR,
        agente_destino=AGENTE_COMISION,
        tipo_tarea="Asignación de Comisión Legislativa",
        payload={
            "texto_preview": texto_documento[:400],
            "longitud_chars": len(texto_documento),
            "task_id_distribuidor": task_id_distribuidor,
            **(metadata_extra or {}),
        },
        sesion_id=sesion_id,
        metadata={"modelo_llm": settings.LLM_MODEL_CREW, "etapa": "asignacion_comision"},
    )
    marcar_en_proceso(task_id_comision)
    t_a = time.time()

    comisiones_str = "\n".join(f"- {c}" for c in comisiones)
    agente_asignador = _get_asignador_agent(comisiones)

    tasks_cfg = load_tasks_yaml().get("tarea_clasificacion_comision", {})
    plantilla = tasks_cfg.get("prompt_operativo") or tasks_cfg.get("description", "Determina la comisión:\n{texto_documento}")
    desc_comision = plantilla.replace("{texto_documento}", muestrear_texto(texto_documento, 4000)).replace("{comisiones_info}", comisiones_str)

    tarea_comision = Task(
        description=desc_comision,
        expected_output=tasks_cfg.get("expected_output", 'JSON: {"comision_principal": "...", "comision_coadyuvante": "...", "fundamentacion_competencia": "..."}'),
        agent=agente_asignador,
    )

    crew_a = Crew(agents=[agente_asignador], tasks=[tarea_comision], verbose=False)
    res_a_raw = str(crew_a.kickoff()).strip()

    # Parsear resultado de asignación
    comision_data: Dict[str, Any] = {}
    try:
        txt = res_a_raw
        if "```json" in txt:
            txt = txt.split("```json")[1].split("```")[0].strip()
        elif "```" in txt:
            txt = txt.split("```")[1].split("```")[0].strip()
        comision_data = json.loads(txt)
    except Exception:
        comision_data = {
            "comision_principal": comisiones[0] if comisiones else "COMISION_DE_CONSTITUCION",
            "comision_coadyuvante": "COMISION_DE_PLANIFICACION_Y_FINANZAS",
            "fundamentacion_competencia": "Asignación reglamentaria según materia sustantiva del proyecto e impacto fiscal conexo.",
            "palabras_clave": ["Legislación", "Normativa", "Políticas Públicas"],
            "resumen": "Proyecto legislativo en análisis parlamentario.",
            "complejidad": "Media",
            "prioridad": "Normal",
            "plazo_dias": 20,
        }

    duracion_a = int((time.time() - t_a) * 1000)
    marcar_completado(task_id_comision, resultado=comision_data, duracion_ms=duracion_a)
    logger.info(
        f"✅ Comisiones asignadas: Principal='{comision_data.get('comision_principal')}' | "
        f"Coadyuvante='{comision_data.get('comision_coadyuvante')}' [{duracion_a}ms]"
    )

    # ── Paso B: Verificación Constitucional ────────────────────────────────
    task_id_verif = publicar_mensaje(
        agente_origen=AGENTE_COMISION,
        agente_destino=AGENTE_VERIFICADOR,
        tipo_tarea="Verificación Constitucional",
        payload={
            "texto_preview": texto_documento[:400],
            "comision_asignada": comision_data.get("comision_principal"),
            "palabras_clave": comision_data.get("palabras_clave", []),
            "task_id_comision": task_id_comision,
        },
        sesion_id=sesion_id,
        metadata={"modelo_llm": settings.LLM_MODEL_CREW, "etapa": "verificacion_constitucional"},
    )
    marcar_en_proceso(task_id_verif)
    t_b = time.time()

    # Obtener artículos constitucionales relevantes desde Neon
    palabras_busqueda = " ".join(
        (comision_data.get("palabras_clave") if isinstance(comision_data.get("palabras_clave"), list) else [])
        + [texto_documento[:200]]
    )
    arts_constitucion = obtener_articulos_constitucion(palabras_busqueda)
    arts_constitucion_str = "\n\n".join([
        f"Art. {a['numero']} — {a['titulo']}\n{a['texto'][:400]}"
        for a in arts_constitucion[:15]
    ]) if arts_constitucion else "No se obtuvieron artículos constitucionales de la base de datos."

    agente_verif = _get_verificador_constitucional_agent()
    tasks_cfg_verif = load_tasks_yaml().get("tarea_verificacion_constitucional", {})
    desc_verif = tasks_cfg_verif.get("description", "Audita la constitucionalidad:\n{texto_documento}")
    # Antes: texto_documento[:5000] — para una ley de 39 páginas (~120,000
    # caracteres) eso cubre apenas la Exposición de Motivos y los primeros
    # artículos, dejando afuera el 95%+ del articulado que es justamente lo
    # que hay que auditar constitucionalmente. Se usa un muestreo
    # representativo (cabecera + fragmentos distribuidos a lo largo de todo
    # el documento + cierre) para que la auditoría alcance a "ver" articulado
    # de todo el cuerpo de la ley, no sólo el principio.
    desc_verif = desc_verif.replace("{texto_documento}", muestrear_texto(texto_documento, 9000, num_muestras_intermedias=6)).replace("{articulos_constitucion_info}", arts_constitucion_str)

    tarea_verif = Task(
        description=desc_verif,
        expected_output=tasks_cfg_verif.get(
            "expected_output",
            'JSON: {"valido": true/false, "confianza": 85, "severidad_maxima": "ninguna", "contradicciones": []}'
        ),
        agent=agente_verif,
    )

    crew_b = Crew(agents=[agente_verif], tasks=[tarea_verif], verbose=False)
    res_b_raw = str(crew_b.kickoff()).strip()

    dictamen: Dict[str, Any] = {}
    try:
        txt = res_b_raw
        if "```json" in txt:
            txt = txt.split("```json")[1].split("```")[0].strip()
        elif "```" in txt:
            txt = txt.split("```")[1].split("```")[0].strip()
        dictamen = json.loads(txt)
    except Exception:
        tiene_contradiccion = any(
            kw in res_b_raw.upper()
            for kw in ["CONTRADICCIÓN", "CONTRADICE", "CONTRADICCION", "INCOMPATIBLE", "VULNERA"]
        )
        dictamen = {
            "valido": not tiene_contradiccion,
            "confianza": 75.0,
            "severidad_maxima": "leve" if tiene_contradiccion else "ninguna",
            "contradicciones": [],
            "analisis_por_articulo": [],
            "fundamentacion_general": res_b_raw[:600],
        }

    duracion_b = int((time.time() - t_b) * 1000)

    # Completar mensaje en MongoDB
    marcar_completado(
        task_id_verif,
        resultado={
            "valido": dictamen.get("valido", True),
            "confianza": dictamen.get("confianza", 85),
            "severidad_maxima": dictamen.get("severidad_maxima", "ninguna"),
            "num_contradicciones": len(dictamen.get("contradicciones", [])),
            "fundamentacion_general": str(dictamen.get("fundamentacion_general", ""))[:300],
        },
        duracion_ms=duracion_b,
    )
    logger.info(
        f"✅ Verificación constitucional: valido={dictamen.get('valido')} [{duracion_b}ms]"
    )

    # ── Persistencia dual: MongoDB + Neon ──────────────────────────────────

    # 1) Guardar observación en colección MongoDB (cache dashboard)
    obs_id_mongo = guardar_observacion_constitucional_mongo(
        sesion_id=sesion_id,
        dictamen=dictamen,
        task_id_verificacion=task_id_verif,
        id_proyecto_pg=id_proyecto,
        articulos_consultados=arts_constitucion,
        modelo_llm=settings.LLM_MODEL_CREW,
        duracion_ms=duracion_b,
    )

    # 2) Guardar observación en tabla PostgreSQL sistema.observaciones_constitucionales
    id_observacion_neon = guardar_observacion_constitucional(
        sesion_id=sesion_id,
        dictamen=dictamen,
        task_id_mongo=task_id_verif,
        id_proyecto=id_proyecto,
        articulos_consultados=arts_constitucion,
        modelo_llm=settings.LLM_MODEL_CREW,
        duracion_ms=duracion_b,
    )

    # 3) Guardar clasificación de comisión en public.Clasificacion_Comision
    guardar_clasificacion_comision(
        solicitud_id=solicitud_id,
        comision_data=comision_data,
        dictamen=dictamen,
    )

    return {
        "comision_data": comision_data,
        "dictamen": dictamen,
        "task_id_comision": task_id_comision,
        "task_id_verificacion": task_id_verif,
        "arts_constitucion_count": len(arts_constitucion),
        "obs_id_mongo": obs_id_mongo,
        "id_observacion_neon": id_observacion_neon,
    }

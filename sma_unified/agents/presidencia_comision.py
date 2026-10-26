# sma_unified/agents/presidencia_comision.py

from typing import Dict, List, Any, Optional
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_postgres import guardar_sesion_debate_db
from sma_unified.db.mongo_atlas import guardar_acta_detallada_mongo

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_presidencia_comision")


class AgentePresidenciaComision:
    """Agente Presidencia de Comisión (Nivel 2) - Planificación del debate, orden del día y cronograma."""

    def __init__(self, base_agent: Optional[BaseAgenteLegislativo] = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Presidencia_Comision')

    def crear_tarea(self, texto_proyecto: str, proyecto_info: Dict[str, Any]) -> Task:
        """Crear tarea CrewAI de planificación de comisión."""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Presidencia_Comision")
        if usr_tpl:
            prompt = self.base.render_template(
                usr_tpl,
                titulo=proyecto_info.get('titulo', 'Proyecto de Ley'),
                proyecto_id=proyecto_info.get('id', 'N/A'),
                comision_asignada=proyecto_info.get('comision_asignada', 'Comisión de Constitución y Legislación'),
                texto_proyecto=texto_proyecto[:1500] if texto_proyecto else 'Texto no disponible'
            )
        else:
            prompt = f"""
        Elabora el plan de trabajo y Orden del Día para la Comisión Legislativa competente.
        PROYECTO: ID={proyecto_info.get('id', 'N/A')}, Titulo={proyecto_info.get('titulo', 'N/A')}
        Establece orden del día detallado, tiempos de exposición, peritos a convocar y cronograma.
        Responde estrictamente en JSON con la clave plan_comision.
        """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con Orden del Día, especialistas convocados y cronograma"
        )

    def ejecutar(self, texto_proyecto: str, proyecto_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la planificación parlamentaria de comisión con resiliencia."""
        t0 = time.time()
        proyecto_id = proyecto_info.get('id') or proyecto_info.get('id_proyecto') or 1
        titulo = proyecto_info.get('titulo', 'Proyecto de Ley')
        comision = proyecto_info.get('comision_asignada', 'Comisión de Constitución y Legislación')

        sys_tpl, usr_tpl = self.base.get_prompt_templates("Presidencia_Comision")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                titulo=titulo,
                proyecto_id=proyecto_id,
                comision_asignada=comision,
                texto_proyecto=texto_proyecto[:1500] if texto_proyecto else 'Texto no disponible'
            )
        else:
            system_prompt = (
                "Eres la Presidencia de la Comisión Legislativa de la Asamblea Legislativa Plurinacional de Bolivia. "
                "Conforme al Reglamento Camaral y el Art. 156 de la CPE, organizas el debate parlamentario: "
                "confeccionas el Orden del Día, convocas peritos y proyectas el calendario legislativo. "
                "Responde ÚNICAMENTE con JSON válido."
            )

            user_prompt = f"""
        Proyecto de Ley: {titulo} (ID: {proyecto_id})
        Comisión Responsable: {comision}

        Texto del proyecto (resumen):
        {texto_proyecto[:1500] if texto_proyecto else 'Texto no disponible'}

        Genera el plan de trabajo de la comisión en este formato JSON:
        {{
          "plan_comision": {{
            "proyecto_id": "{proyecto_id}",
            "comision_nombre": "{comision}",
            "orden_del_dia": [
              {{
                "numero": 1,
                "punto": "Lectura del proyecto y antecedentes por Secretaría",
                "tiempo_estimado_minutos": 20,
                "responsable": "Secretario de Comisión"
              }},
              {{
                "numero": 2,
                "punto": "Exposición de motivos por el proponente o proyectista",
                "tiempo_estimado_minutos": 30,
                "responsable": "Proponente de la Ley"
              }},
              {{
                "numero": 3,
                "punto": "Audiencia con peritos técnicos y organizaciones sociales",
                "tiempo_estimado_minutos": 45,
                "responsable": "Especialistas convocados"
              }},
              {{
                "numero": 4,
                "punto": "Debate artículo por artículo y votación del informe en comisión",
                "tiempo_estimado_minutos": 60,
                "responsable": "Pleno de la Comisión"
              }}
            ],
            "especialistas_convocados": [
              "Delegado de la Procuraduría General del Estado",
              "Perito técnico en la materia del proyecto",
              "Representantes de organizaciones sociales afines"
            ],
            "cronograma_estimado_dias": 15,
            "plan_de_audiencias": "Audiencia pública el día 5 de tratamiento; plazo de enmiendas hasta el día 10.",
            "instrucciones_a_secretaria": "Distribuir copias del proyecto a los 13 miembros de la comisión.",
            "duracion_ms": 0
          }}
        }}
        """

        try:
            raw_res, modelo = chat_completion_resiliente(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            cleaned = raw_res.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"Fallback en AgentePresidenciaComision: {e}")
            data = {
                "plan_comision": {
                    "proyecto_id": str(proyecto_id),
                    "comision_nombre": comision,
                    "orden_del_dia": [
                        {"numero": 1, "punto": "Lectura general", "tiempo_estimado_minutos": 30, "responsable": "Secretario"},
                        {"numero": 2, "punto": "Debate y votación en comisión", "tiempo_estimado_minutos": 60, "responsable": "Comisión"}
                    ],
                    "especialistas_convocados": ["Asesores técnicos de comisión"],
                    "cronograma_estimado_dias": 15,
                    "plan_de_audiencias": "Tratamiento ordinario en comisión",
                    "instrucciones_a_secretaria": "Notificar a miembros de comisión",
                    "duracion_ms": 0
                }
            }

        plan_obj = data.get("plan_comision", {})
        plan_obj["duracion_ms"] = int((time.time() - t0) * 1000)

        # Persistir sesión preparatoria en PostgreSQL si id_proyecto es válido
        if isinstance(proyecto_id, int) or (isinstance(proyecto_id, str) and proyecto_id.isdigit()):
            try:
                guardar_sesion_debate_db(
                    camara="COMISION",
                    comision_nombre=comision,
                    id_proyecto=int(proyecto_id),
                    numero_sesion="SES-COM-01",
                    total_asistentes=13,
                    orden_del_dia=plan_obj.get("orden_del_dia", []),
                    resumen_debate=f"Apertura de tratamiento en {comision}. Cronograma estimado: {plan_obj.get('cronograma_estimado_dias', 15)} días.",
                    acta_completa=json.dumps(plan_obj, ensure_ascii=False, indent=2)
                )
            except Exception as ep:
                logger.warning(f"No se pudo registrar sesión de comisión en Neon: {ep}")

            try:
                guardar_acta_detallada_mongo({
                    "id_proyecto": int(proyecto_id),
                    "sesion_id": proyecto_info.get("sesion_id") if isinstance(proyecto_info, dict) else None,
                    "id_sesion": 1,
                    "numero_sesion": "SES-COM-01",
                    "camara": "COMISION",
                    "comision_nombre": comision,
                    "fecha_sesion": time.strftime("%Y-%m-%d"),
                    "total_asistentes": 13,
                    "orden_del_dia": plan_obj.get("orden_del_dia", []),
                    "resumen_debate": f"Apertura de tratamiento en {comision}.",
                    "acta_debate": plan_obj,
                    "duracion_ms": plan_obj.get("duracion_ms", 0),
                })
            except Exception as em:
                logger.warning(f"No se pudo guardar acta de comisión en Mongo: {em}")

        return data

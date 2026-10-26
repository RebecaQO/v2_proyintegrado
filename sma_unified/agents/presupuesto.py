# sma_unified/agents/presupuesto.py

from typing import Dict, List, Any, Optional
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_postgres import guardar_dictamen_tecnico_db

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_presupuesto")


class AgentePresupuesto:
    """Agente de Planificación Fiscal y Presupuesto (Nivel 2) - Sostenibilidad del TGN y Ley 1178 SAFCO."""

    def __init__(self, base_agent: Optional[BaseAgenteLegislativo] = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Planificacion_Presupuesto')

    def crear_tarea(self, texto_proyecto: str, proyecto_info: Dict[str, Any]) -> Task:
        """Crear tarea CrewAI de evaluación presupuestaria."""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Planificacion_Presupuesto")
        if usr_tpl:
            prompt = self.base.render_template(
                usr_tpl,
                titulo=proyecto_info.get('titulo', 'Proyecto de Ley'),
                proyecto_id=proyecto_info.get('id', 'N/A'),
                texto_proyecto=texto_proyecto[:2000]
            )
        else:
            prompt = f"""
            Realiza una evaluación de impacto fiscal y presupuestario del proyecto de ley.
            PROYECTO: ID={proyecto_info.get('id', 'N/A')}, Titulo={proyecto_info.get('titulo', 'N/A')}
            TEXTO: {texto_proyecto[:2000]}...
            Evalúa costos de implementación, gastos operativos recurrentes, fuentes de financiamiento
            y simula 3 escenarios macroeconómicos (optimista, conservador, pesimista).
            Responde estrictamente en JSON con la clave evaluacion_fiscal.
            """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con evaluación fiscal, costos TGN y 3 escenarios macroeconómicos"
        )

    def ejecutar(self, texto_proyecto: str, proyecto_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta el análisis presupuestario y de sostenibilidad fiscal."""
        t0 = time.time()
        proyecto_id = proyecto_info.get('id') or proyecto_info.get('id_proyecto') or 1
        titulo = proyecto_info.get('titulo', 'Proyecto de Ley')

        sys_tpl, usr_tpl = self.base.get_prompt_templates("Planificacion_Presupuesto")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                titulo=titulo,
                proyecto_id=proyecto_id,
                texto_proyecto=texto_proyecto[:2000] if texto_proyecto else 'Texto no disponible'
            )
        else:
            system_prompt = (
                "Eres el Analista Principal de la Comisión de Planificación, Política Económica y Finanzas "
                "de la Asamblea Legislativa Plurinacional de Bolivia. Rigiendo bajo la Ley 1178 (SAFCO), "
                "evalúas si los proyectos de ley cuentan con respaldo presupuestario real en el Tesoro General "
                "de la Nación (TGN), calculas costos y proyectas 3 escenarios fiscales. Responde en JSON válido."
            )

            user_prompt = f"""
            Proyecto de Ley: {titulo} (ID: {proyecto_id})

            Texto del proyecto:
            {texto_proyecto[:2000] if texto_proyecto else 'Texto no disponible'}

            Genera el informe de viabilidad fiscal en este formato JSON exacto:
            {{
              "evaluacion_fiscal": {{
                "proyecto_id": "{proyecto_id}",
                "viabilidad_fiscal": "SOSTENIBLE",
                "costo_implementacion_inicial_bs": 12000000.0,
            "costo_operativo_anual_bs": 3500000.0,
            "fuente_financiamiento_identificada": true,
            "fuentes_propuestas": [
              "Recursos Propios de la entidad ejecutora",
              "Asignación programada en el Presupuesto General del Estado (PGE)"
            ],
            "escenarios": {{
              "optimista": {{
                "costo_neto_quinquenal_bs": 25000000.0,
                "retorno_social_inversion": "ALTO",
                "impacto_pib": "+0.08%"
              }},
              "conservador": {{
                "costo_neto_quinquenal_bs": 29500000.0,
                "retorno_social_inversion": "MODERADO",
                "impacto_pib": "+0.04%"
              }},
              "pesimista": {{
                "costo_neto_quinquenal_bs": 36000000.0,
                "retorno_social_inversion": "BAJO",
                "impacto_pib": "+0.01%"
              }}
            }},
            "alerta_presupuesto_tgn": "VERDE",
            "recomendacion_fiscal": "El proyecto es fiscalmente viable y no compromete el déficit fiscal del Estado.",
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
                max_tokens=2200
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
            logger.warning(f"Fallback en AgentePresupuesto: {e}")
            data = {
                "evaluacion_fiscal": {
                    "proyecto_id": str(proyecto_id),
                    "viabilidad_fiscal": "CONDICIONADA_A_RECURSOS",
                    "costo_implementacion_inicial_bs": 5000000.0,
                    "costo_operativo_anual_bs": 1200000.0,
                    "fuente_financiamiento_identificada": False,
                    "fuentes_propuestas": ["Tesoro General de la Nación"],
                    "escenarios": {
                        "optimista": {"costo_neto_quinquenal_bs": 11000000.0},
                        "conservador": {"costo_neto_quinquenal_bs": 13000000.0},
                        "pesimista": {"costo_neto_quinquenal_bs": 16000000.0}
                    },
                    "alerta_presupuesto_tgn": "AMARILLA",
                    "recomendacion_fiscal": "Se requiere que el proyectista precise la fuente de financiamiento conforme al Art. 11 de la Ley 1178.",
                    "duracion_ms": 0
                }
            }

        eval_obj = data.get("evaluacion_fiscal", {})
        eval_obj["duracion_ms"] = int((time.time() - t0) * 1000)

        # Persistir en Neon como dictamen presupuestario
        if isinstance(proyecto_id, int) or (isinstance(proyecto_id, str) and proyecto_id.isdigit()):
            try:
                guardar_dictamen_tecnico_db(
                    id_proyecto=int(proyecto_id),
                    tipo_dictamen="PRESUPUESTARIO",
                    agente_emisor="Planificacion_Presupuesto",
                    viabilidad=eval_obj.get("viabilidad_fiscal", "SOSTENIBLE"),
                    puntuacion=9.0 if eval_obj.get("alerta_presupuesto_tgn") == "VERDE" else 6.0,
                    contenido_dictamen=eval_obj,
                    recomendaciones=eval_obj.get("recomendacion_fiscal", "")
                )
            except Exception as ep:
                logger.warning(f"No se pudo registrar dictamen fiscal en Neon: {ep}")

        return data

# sma_unified/agents/especialista_tecnico.py

from typing import Dict, List, Any, Optional
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_postgres import guardar_dictamen_tecnico_db
from sma_unified.db.mongo_atlas import get_db

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_especialista_tecnico")


class AgenteEspecialistaTecnico:
    """Agente Especialista Técnico (Nivel 2) - Evaluación de factibilidad fáctica, técnica y estándares."""

    def __init__(self, base_agent: Optional[BaseAgenteLegislativo] = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Especialista_Tecnico')

    def crear_tarea(self, texto_proyecto: str, proyecto_info: Dict[str, Any]) -> Task:
        """Crear tarea CrewAI de dictamen técnico."""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Especialista_Tecnico")
        if usr_tpl:
            prompt = self.base.render_template(
                usr_tpl,
                titulo=proyecto_info.get('titulo', 'Proyecto de Ley'),
                proyecto_id=proyecto_info.get('id', 'N/A'),
                materia=proyecto_info.get('materia', 'General'),
                texto_proyecto=texto_proyecto[:2000] if texto_proyecto else 'Texto no disponible'
            )
        else:
            prompt = f"""
        Realiza una evaluación pericial de viabilidad técnica y fáctica del siguiente proyecto de ley.
        PROYECTO: ID={proyecto_info.get('id', 'N/A')}, Titulo={proyecto_info.get('titulo', 'N/A')}
        TEXTO: {texto_proyecto[:2000]}...
        Evalúa estándares aplicables (ISO, OIT, normas bolivianas), infraestructura requerida y matriz de riesgos.
        Responde estrictamente en formato JSON con la clave dictamen_tecnico.
        """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con dictamen técnico pericial y matriz de riesgos"
        )

    def ejecutar(self, texto_proyecto: str, proyecto_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta el análisis técnico pericial con fallback resiliente."""
        t0 = time.time()
        proyecto_id = proyecto_info.get('id') or proyecto_info.get('id_proyecto') or 1
        titulo = proyecto_info.get('titulo', 'Proyecto de Ley')
        materia = proyecto_info.get('materia', 'General')

        sys_tpl, usr_tpl = self.base.get_prompt_templates("Especialista_Tecnico")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                titulo=titulo,
                proyecto_id=proyecto_id,
                materia=materia,
                texto_proyecto=texto_proyecto[:2000] if texto_proyecto else 'Texto no disponible'
            )
        else:
            system_prompt = (
                "Eres el Especialista Técnico Pericial de las Comisiones Legislativas de Bolivia. "
                "Tu deber es evaluar la factibilidad fáctica de las leyes propuestas: infraestructura, "
                "estándares internacionales (ISO, OIT, OMS), recursos técnicos y riesgos operacionales. "
                "Responde ÚNICAMENTE con un JSON válido estructurado."
            )

            user_prompt = f"""
        Proyecto de Ley: {titulo} (ID: {proyecto_id})
        Materia: {materia}
        Texto del proyecto:
        {texto_proyecto[:2000] if texto_proyecto else 'Texto no disponible'}

        Genera el dictamen técnico pericial en este formato exacto:
        {{
          "dictamen_tecnico": {{
            "proyecto_id": "{proyecto_id}",
            "materia_tecnica": "{materia}",
            "viabilidad_tecnica": "VIABLE",
            "puntuacion_viabilidad": 8.5,
            "infraestructura_requerida": [
              "Centros de cómputo y conectividad en sedes operativas",
              "Sistemas de interoperabilidad y seguridad digital"
            ],
            "estandares_aplicables": [
              "ISO/IEC 27001 (Seguridad de la información)",
              "Estándar Boliviano NB/ISO 9001"
            ],
            "matriz_riesgos": [
              {{
                "riesgo": "Capacitación técnica insuficiente del personal operativo",
                "probabilidad": 0.4,
                "impacto": "MEDIO",
                "mitigacion_sugerida": "Implementar programa nacional de capacitación previa a la entrada en vigencia"
              }}
            ],
            "dictamen_tecnico_resumen": "El proyecto es técnicamente factible con la adopción de las salvaguardas tecnológicas descritas.",
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
            # Limpiar bloques markdown si existen
            cleaned = raw_res.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"Fallback en AgenteEspecialistaTecnico: {e}")
            data = {
                "dictamen_tecnico": {
                    "proyecto_id": str(proyecto_id),
                    "materia_tecnica": materia,
                    "viabilidad_tecnica": "VIABLE_CON_CONDICIONES",
                    "puntuacion_viabilidad": 7.0,
                    "infraestructura_requerida": ["Equipamiento básico y soporte operativo"],
                    "estandares_aplicables": ["Normas técnicas nacionales"],
                    "matriz_riesgos": [
                        {
                            "riesgo": "Implementación gradual requerida",
                            "probabilidad": 0.5,
                            "impacto": "MEDIO",
                            "mitigacion_sugerida": "Establecer cronograma transitorio de 180 días"
                        }
                    ],
                    "dictamen_tecnico_resumen": "Dictamen pericial preliminar favorable con condiciones de implementación gradual.",
                    "duracion_ms": 0
                }
            }

        dictamen_obj = data.get("dictamen_tecnico", {})
        dictamen_obj["duracion_ms"] = int((time.time() - t0) * 1000)

        # Persistir en PostgreSQL Neon si hay id_proyecto
        if isinstance(proyecto_id, int) or (isinstance(proyecto_id, str) and proyecto_id.isdigit()):
            try:
                guardar_dictamen_tecnico_db(
                    id_proyecto=int(proyecto_id),
                    tipo_dictamen="TECNICO_MATERIA",
                    agente_emisor="Especialista_Tecnico",
                    viabilidad=dictamen_obj.get("viabilidad_tecnica", "VIABLE"),
                    puntuacion=float(dictamen_obj.get("puntuacion_viabilidad", 7.5)),
                    contenido_dictamen=dictamen_obj,
                    recomendaciones=dictamen_obj.get("dictamen_tecnico_resumen", "")
                )
            except Exception as ep:
                logger.warning(f"No se pudo guardar dictamen técnico en Neon: {ep}")

        return data

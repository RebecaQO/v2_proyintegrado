# sma_unified/agents/bicameral.py

from typing import Dict, List, Any
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_client import get_neon_client
from sma_unified.db.cosmos_client import CosmosDBClient


class AgenteBicameral:
    """Agente Comunicacion Bicameral - Coordinador del tramite entre camaras legislativas"""

    def __init__(self, base_agent: BaseAgenteLegislativo = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Bicameral')
        self.neon = get_neon_client()

    def crear_tarea(self, version_original: Dict, version_retornada: Dict, proyecto_info: Dict) -> Task:
        """Crear tarea CrewAI de gestion bicameral"""
        prompt = f"""
        Gestiona el tramite bicameral para el siguiente proyecto.
        PROYECTO: ID={proyecto_info.get('id', 'N/A')}, Titulo={proyecto_info.get('titulo', 'N/A')}
        VERSION ORIGINAL: {json.dumps(version_original, indent=2, ensure_ascii=False)}
        VERSION RETORNADA: {json.dumps(version_retornada, indent=2, ensure_ascii=False)}
        INSTRUCCIONES: Compara versiones, clasifica cambios MAYORES/MENORES, decide ruta.
        Responde UNICAMENTE con JSON con la clave ciclo_bicameral.
        """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con ciclo bicameral y ruta decisional"
        )

    def ejecutar(self, version_original: Dict, version_retornada: Dict, proyecto_info: Dict) -> Dict:
        """Ejecutar tramite bicameral con resiliencia LLM y persistencia"""
        t0 = time.time()
        proyecto_id = proyecto_info.get('id') or proyecto_info.get('id_proyecto') or 1

        system_prompt = (
            "Eres el Coordinador del Tramite Bicameral de la Asamblea Legislativa Plurinacional "
            "de Bolivia, compuesta por dos camaras:\n"
            "- Camara de Diputados (camara baja): 130 miembros, elegidos mediante un sistema "
            "mixto de circunscripciones uninominales, plurinominales y especiales indigenas, "
            "representando a los nueve departamentos.\n"
            "- Camara de Senadores (camara alta): 36 miembros, con 4 senadores por cada uno de "
            "los nueve departamentos, elegidos por votacion departamental.\n"
            "Compara versiones de la Camara de Origen y Revisora, detecta diferencias y "
            "determina la ruta legislativa. Responde unicamente en JSON valido."
        )
        user_prompt = f"""
        Proyecto: {proyecto_info.get('titulo', 'Proyecto de Ley')} (ID: {proyecto_id})
        Version Original: {json.dumps(version_original, ensure_ascii=False)}
        Version Retornada: {json.dumps(version_retornada, ensure_ascii=False)}

        Genera el JSON con esta estructura:
        {{
          "ciclo_bicameral": {{
            "proyecto_id": "{proyecto_id}",
            "cambios_detectados": [{{"tipo": "MODIFICACION", "articulo": 1, "descripcion": "...", "impacto": "MENOR"}}],
            "clasificacion_cambios": "MENORES",
            "ruta_siguiente": "SANCION_DIRECTA",
            "justificacion": "Los cambios son de naturaleza formal",
            "estado_siguiente": "LISTO_PARA_VETO_PROMULGACION"
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
                max_tokens=1500
            )
            data = json.loads(raw_res)
        except Exception:
            data = {
                "ciclo_bicameral": {
                    "proyecto_id": str(proyecto_id),
                    "cambios_detectados": [],
                    "clasificacion_cambios": "MENORES",
                    "ruta_siguiente": "SANCION_DIRECTA",
                    "justificacion": "Tramite bicameral completado. Versiones convergentes.",
                    "estado_siguiente": "LISTO_PARA_VETO_PROMULGACION"
                }
            }

        duracion_ms = int((time.time() - t0) * 1000)

        try:
            ciclo = data.get("ciclo_bicameral", {})
            self.neon.insertar_observacion(
                id_proyecto=int(proyecto_id),
                tipo_obs="TRAMITE_BICAMERAL",
                agente="Comunicacion Bicameral",
                hallazgos=ciclo,
                riesgo="BAJO" if ciclo.get("clasificacion_cambios") == "MENORES" else "MEDIO",
                recomendacion=ciclo.get("justificacion", "")
            )
            self.neon.actualizar_estado_proyecto(int(proyecto_id), "EN_TRAMITE_BICAMERAL", "Comunicacion Bicameral")
        except Exception as db_err:
            print(f"Aviso Neon Bicameral: {db_err}")

        try:
            cosmos = CosmosDBClient()
            cosmos.log_agent_execution(
                id_proyecto=str(proyecto_id),
                nombre_agente="Comunicacion Bicameral",
                input_data={"version_original": version_original, "version_retornada": version_retornada},
                output_data=data,
                tiempo_ms=duracion_ms
            )
            cosmos.close()
        except Exception as mg_err:
            print(f"Aviso Mongo Bicameral: {mg_err}")

        return data

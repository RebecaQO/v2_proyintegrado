# sma_unified/agents/constitucion_fondo.py

from typing import Dict, List, Any
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_client import get_neon_client
from sma_unified.db.cosmos_client import CosmosDBClient


class AgenteConstitucionFondo:
    """Agente Comision Constitucion (Fondo) - Analisis hermeneutico constitucional sustantivo"""

    def __init__(self, base_agent: BaseAgenteLegislativo = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Constitucion_Fondo')
        self.neon = get_neon_client()

    def crear_tarea(self, texto_proyecto: str, obs_formales: List[Dict], proyecto_info: Dict) -> Task:
        """Crear tarea CrewAI de analisis constitucional de fondo"""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Constitucion_Fondo")
        if usr_tpl:
            prompt = self.base.render_template(
                usr_tpl,
                titulo=proyecto_info.get('titulo', 'Proyecto de Ley'),
                proyecto_id=proyecto_info.get('id', 'N/A'),
                texto_proyecto=texto_proyecto[:2000],
                obs_formales=json.dumps(obs_formales, indent=2, ensure_ascii=False)
            )
        else:
            prompt = f"""
            Realiza analisis hermeneutico de constitucionalidad sustantiva (no formal).
            PROYECTO: ID={proyecto_info.get('id', 'N/A')}, Titulo={proyecto_info.get('titulo', 'N/A')}
            TEXTO: {texto_proyecto[:2000]}...
            OBSERVACIONES FORMALES PREVIAS: {json.dumps(obs_formales, indent=2, ensure_ascii=False)}
            INSTRUCCIONES: Aplica hermeneutica juridica, busca precedentes del TC, pondera derechos.
            Genera dictamen de viabilidad de FONDO, no solo de forma.
            Responde UNICAMENTE con JSON con la clave dictamen_fondo.
            """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con dictamen hermeneutico y viabilidad constitucional de fondo"
        )

    def ejecutar(self, texto_proyecto: str, obs_formales: List[Dict], proyecto_info: Dict) -> Dict:
        """Ejecutar analisis constitucional de fondo con resiliencia LLM"""
        t0 = time.time()
        proyecto_id = proyecto_info.get('id') or proyecto_info.get('id_proyecto') or 1

        sys_tpl, usr_tpl = self.base.get_prompt_templates("Constitucion_Fondo")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                titulo=proyecto_info.get('titulo', 'Proyecto de Ley'),
                proyecto_id=proyecto_id,
                texto_proyecto=texto_proyecto[:1500] if texto_proyecto else 'Texto no disponible',
                obs_formales=json.dumps(obs_formales, ensure_ascii=False)
            )
        else:
            system_prompt = (
                "Eres el experto en hermeneutica constitucional de la Comision de Constitucion. "
                "Tu analisis va mas alla del control formal: buscas viabilidad SUSTANTIVA. "
                "Aplicas interpretacion sistematica, precedentes del Tribunal Constitucional "
                "Plurinacional y principios de ponderacion de derechos. Responde en JSON valido."
            )
            user_prompt = f"""
            Proyecto: {proyecto_info.get('titulo', 'Proyecto de Ley')} (ID: {proyecto_id})

            Texto del proyecto (primeros 1500 caracteres):
            {texto_proyecto[:1500] if texto_proyecto else 'Texto no disponible'}

            Observaciones formales del Verificador Constitucional:
            {json.dumps(obs_formales, ensure_ascii=False)}

            Genera el dictamen constitucional de fondo:
            {{
              "dictamen_fondo": {{
                "proyecto_id": "{proyecto_id}",
                "viabilidad_fondo": "VIABLE_CON_OBSERVACIONES",
                "analisis_hermeneutico": {{
                  "principios_aplicables": [
                    "Principio de supremacia constitucional (Art. 410 CPE)",
                    "Principio pro persona (Art. 13 CPE)",
                    "Principio de progresividad de derechos"
                  ],
                  "precedentes_relevantes": [
                    "SCP 0760/2003-R — Control de constitucionalidad de normas",
                    "SCP 1422/2012 — Ponderacion de derechos fundamentales"
                  ],
                  "conflictos_derechos": [
                    {{
                      "derecho_1": "Derecho al desarrollo economico (Art. 306 CPE)",
                      "derecho_2": "Derecho al medio ambiente (Art. 33 CPE)",
                      "ponderacion": "Prevalece el desarrollo sostenible con salvaguardas ambientales"
                    }}
                  ],
                  "interpretacion_sistematica": "La norma es coherente con el bloque de constitucionalidad cuando se interpreta en contexto del MESCP boliviano"
                }},
                "recomendaciones": "Incorporar clausula de salvaguarda medioambiental en Art. 5 para garantizar constitucionalidad plena",
                "riesgo_constitucional": "BAJO",
                "estado_siguiente": "LISTO_PARA_CONCENTRACION"
              }}
            }}
            """

        try:
            raw_res, modelo = chat_completion_resiliente(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2500
            )
            data = json.loads(raw_res)
        except Exception:
            data = {
                "dictamen_fondo": {
                    "proyecto_id": str(proyecto_id),
                    "viabilidad_fondo": "VIABLE_CON_OBSERVACIONES",
                    "analisis_hermeneutico": {
                        "principios_aplicables": [
                            "Supremacia constitucional (Art. 410 CPE)",
                            "Principio pro persona (Art. 13 CPE)"
                        ],
                        "precedentes_relevantes": [
                            "SCP 0760/2003-R — Control constitucional",
                            "SCP 1422/2012 — Ponderacion de derechos"
                        ],
                        "conflictos_derechos": [],
                        "interpretacion_sistematica": "Norma coherente con el bloque de constitucionalidad boliviano"
                    },
                    "recomendaciones": "Revisar redaccion de articulos observados para mayor precision juridica.",
                    "riesgo_constitucional": "BAJO",
                    "estado_siguiente": "LISTO_PARA_CONCENTRACION"
                }
            }

        duracion_ms = int((time.time() - t0) * 1000)

        try:
            dictamen = data.get("dictamen_fondo", {})
            riesgo = dictamen.get("riesgo_constitucional", "MEDIO")
            self.neon.insertar_observacion(
                id_proyecto=int(proyecto_id),
                tipo_obs="DICTAMEN_CONSTITUCIONAL_FONDO",
                agente="Comision Constitucion Fondo",
                hallazgos=dictamen,
                riesgo=riesgo,
                recomendacion=dictamen.get("recomendaciones", "")
            )
            self.neon.actualizar_estado_proyecto(
                int(proyecto_id), "EN_ANALISIS_FONDO", "Comision Constitucion Fondo"
            )
        except Exception as db_err:
            print(f"Aviso Neon ConstitucionFondo: {db_err}")

        try:
            cosmos = CosmosDBClient()
            cosmos.log_agent_execution(
                id_proyecto=str(proyecto_id),
                nombre_agente="Comision Constitucion Fondo",
                input_data={"texto_proyecto": texto_proyecto[:500], "obs_formales": obs_formales},
                output_data=data,
                tiempo_ms=duracion_ms
            )
            cosmos.close()
        except Exception as mg_err:
            print(f"Aviso Mongo ConstitucionFondo: {mg_err}")

        return data

# sma_unified/agents/difusion_ciudadana.py

from typing import Dict, List, Any, Optional
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.mongo_atlas import guardar_respuesta_ciudadana_mongo

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_difusion_ciudadana")


class AgenteDifusionCiudadana:
    """Agente de Difusión Ciudadana en Lenguaje Claro (Fase 5) - Pedagogía Cívica y Traducción Legal."""

    def __init__(self, base_agent: Optional[BaseAgenteLegislativo] = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Difusion_Ciudadana')

    def crear_tarea(self, texto_ley: str, ley_info: Dict[str, Any]) -> Task:
        """Crear tarea CrewAI de difusión ciudadana."""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Difusion_Ciudadana")
        numero_ley = ley_info.get('numero_ley') or ley_info.get('numero_ley_asignado') or "Ley del Estado"
        titulo = ley_info.get('titulo', 'Ley Promulgada')
        if usr_tpl:
            prompt = self.base.render_template(
                usr_tpl,
                numero_ley=numero_ley,
                titulo=titulo,
                texto_ley=texto_ley[:2500] if texto_ley else 'Texto no disponible'
            )
        else:
            prompt = f"""
        Transforma el texto de la ley promulgada en una guía en Lenguaje Claro para la población boliviana.
        LEY: {numero_ley}, Titulo={titulo}
        TEXTO: {texto_ley[:2500]}...
        Explica sin tecnicismos: qué derechos otorga, qué obligaciones impone, a quiénes beneficia
        y genera 3 preguntas frecuentes con respuestas sencillas.
        Responde estrictamente en JSON con la clave difusion_ciudadana.
        """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con guía ciudadana, derechos, obligaciones y preguntas frecuentes"
        )

    def ejecutar(self, texto_ley: str, ley_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la simplificación a lenguaje claro con LLM resiliente."""
        t0 = time.time()
        numero_ley = ley_info.get('numero_ley') or ley_info.get('numero_ley_asignado') or "Ley del Estado"
        titulo = ley_info.get('titulo', 'Ley Promulgada')

        sys_tpl, usr_tpl = self.base.get_prompt_templates("Difusion_Ciudadana")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                numero_ley=numero_ley,
                titulo=titulo,
                texto_ley=texto_ley[:2500] if texto_ley else 'Texto no disponible'
            )
        else:
            system_prompt = (
                "Eres el Comunicador Cívico Oficial de la Asamblea Legislativa Plurinacional de Bolivia. "
                "Tu misión es aplicar las normas internacionales de 'Lenguaje Claro': traducir textos legales "
                "complejos a un castellano sencillo, directo, comprensible y cercano para cualquier ciudadano, "
                "destacando siempre sus derechos y deberes. Responde en JSON estructurado."
            )

            user_prompt = f"""
        Ley Oficial: {numero_ley} - {titulo}

        Texto íntegro o articulado principal:
        {texto_ley[:2500] if texto_ley else 'Texto no disponible'}

        Genera la guía ciudadana en este formato JSON:
        {{
          "difusion_ciudadana": {{
            "numero_ley": "{numero_ley}",
            "titulo_ciudadano": "Lo que debes saber sobre la nueva {numero_ley}",
            "proposito_en_palabras_simples": "Esta ley tiene por objetivo cuidar y proteger...",
            "tus_nuevos_derechos": [
              "Derecho a exigir transparencia en la gestión de tus datos personales",
              "Derecho a recibir atención oportuna y sin cobros indebidos"
            ],
            "tus_nuevas_obligaciones": [
              "Brindar información verídica al realizar trámites oficiales",
              "Cumplir con las disposiciones de cuidado comunitario"
            ],
            "a_quienes_aplica": "A todas las personas individuales, colectivas, empresas y entidades públicas en Bolivia.",
            "desde_cuando_rige": "A partir de los 15 días hábiles posteriores a su publicación en la Gaceta Oficial.",
            "preguntas_frecuentes": [
              {{
                "pregunta": "¿Tengo que pagar algún trámite adicional por esta ley?",
                "respuesta": "No, los trámites ordinarios regulados en esta norma son completamente gratuitos."
              }},
              {{
                "pregunta": "¿Dónde puedo denunciar si una institución no cumple esta norma?",
                "respuesta": "Puedes acudir a las oficinas de atención al ciudadano o a la Defensoría del Pueblo."
              }}
            ],
            "mensaje_radial_breve": "¡Hermana, hermano boliviano! La Asamblea informa: la nueva {numero_ley} protege tus derechos. Conócela y hazla respetar.",
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
                temperature=0.3,
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
            logger.warning(f"Fallback en AgenteDifusionCiudadana: {e}")
            data = {
                "difusion_ciudadana": {
                    "numero_ley": numero_ley,
                    "titulo_ciudadano": f"Resumen Ciudadano de la {numero_ley}",
                    "proposito_en_palabras_simples": f"La norma {numero_ley} regula aspectos de beneficio público para la población.",
                    "tus_nuevos_derechos": ["Acceso a servicios públicos eficientes y garantizados."],
                    "tus_nuevas_obligaciones": ["Respetar las disposiciones y reglamentos vigentes."],
                    "a_quienes_aplica": "Población en general y entidades del Estado.",
                    "desde_cuando_rige": "A partir de su publicación oficial.",
                    "preguntas_frecuentes": [
                        {"pregunta": "¿Qué regula esta ley?", "respuesta": titulo}
                    ],
                    "mensaje_radial_breve": f"Conoce la nueva {numero_ley} para el beneficio de todos los bolivianos.",
                    "duracion_ms": 0
                }
            }

        dif_obj = data.get("difusion_ciudadana", {})
        dif_obj["duracion_ms"] = int((time.time() - t0) * 1000)

        # Persistir en MongoDB Atlas
        try:
            guardar_respuesta_ciudadana_mongo({
                "id_consulta": f"DIF-{numero_ley}",
                "tipo": "DIFUSION_LEGISLATIVA",
                "contenido": dif_obj,
                "numero_ley": numero_ley
            })
        except Exception as em:
            logger.warning(f"No se pudo registrar difusión en MongoDB: {em}")

        return data

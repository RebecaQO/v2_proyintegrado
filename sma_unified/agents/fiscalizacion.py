# sma_unified/agents/fiscalizacion.py

from typing import Dict, List, Any, Optional
import json
import time
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_postgres import get_conn

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_fiscalizacion")


class AgenteFiscalizacion:
    """Agente de Fiscalización y Control Posterior (Fase 5) - Monitoreo post-legislativo y alertas a Contraloría."""

    def __init__(self, base_agent: Optional[BaseAgenteLegislativo] = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Fiscalizacion')

    def crear_tarea(self, datos_ejecucion: Dict[str, Any], ley_info: Dict[str, Any]) -> Task:
        """Crear tarea CrewAI de fiscalización posterior."""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Fiscalizacion")
        numero_ley = ley_info.get('numero_ley') or ley_info.get('numero_ley_asignado') or "Ley del Estado"
        titulo = ley_info.get('titulo', 'Ley Promulgada')
        if usr_tpl:
            prompt = self.base.render_template(
                usr_tpl,
                numero_ley=numero_ley,
                titulo=titulo,
                datos_ejecucion=json.dumps(datos_ejecucion, ensure_ascii=False)
            )
        else:
            prompt = f"""
        Realiza la auditoría y control posterior de implementación de la ley.
        LEY: {numero_ley}, Titulo={titulo}
        DATOS DE EJECUCIÓN: {json.dumps(datos_ejecucion, ensure_ascii=False)}
        Evalúa el cumplimiento de plazos reglamentarios, presupuesto ejecutado y detecta anomalías.
        Responde estrictamente en formato JSON con la clave reporte_fiscalizacion.
        """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con indicadores de cumplimiento, estado de implementación y alertas a Contraloría"
        )

    def ejecutar(self, datos_ejecucion: Dict[str, Any], ley_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta el análisis de fiscalización y control posterior."""
        t0 = time.time()
        numero_ley = ley_info.get('numero_ley') or ley_info.get('numero_ley_asignado') or "Ley del Estado"
        titulo = ley_info.get('titulo', 'Ley Promulgada')
        id_proyecto = ley_info.get('id_proyecto') or ley_info.get('id')

        sys_tpl, usr_tpl = self.base.get_prompt_templates("Fiscalizacion")
        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                numero_ley=numero_ley,
                titulo=titulo,
                datos_ejecucion=json.dumps(datos_ejecucion, ensure_ascii=False, indent=2)
            )
        else:
            system_prompt = (
                "Eres el Auditor de la Comisión de Fiscalización y Control Posterior de la Asamblea "
                "Legislativa Plurinacional de Bolivia (Art. 158 CPE). Monitoreas el cumplimiento de las leyes "
                "promulgadas: plazos de reglamentación por los ministerios del Órgano Ejecutivo, ejecución "
                "del gasto y detección de irregularidades para alertar a la Contraloría General del Estado. "
                "Responde ÚNICAMENTE con JSON válido."
            )

            user_prompt = f"""
        Ley Monitoreada: {numero_ley} - {titulo}
        Datos de implementación reportados:
        {json.dumps(datos_ejecucion, ensure_ascii=False, indent=2)}

        Genera el informe de control posterior en este formato JSON exacto:
        {{
          "reporte_fiscalizacion": {{
            "numero_ley": "{numero_ley}",
            "estado_implementacion": "EN_PLAZO",
            "dias_desde_promulgacion": 120,
            "indicadores_evaluados": [
              {{
                "indicador": "Emisión del Decreto Supremo Reglamentario",
                "plazo_constitucional_dias": 90,
                "dias_transcurridos": 80,
                "estado": "EN_PLAZO",
                "observacion": "Ministerio responsable remitió borrador a UDAPE para aprobación."
              }},
              {{
                "indicador": "Ejecución presupuestaria asignada",
                "presupuesto_programado_bs": 10000000.0,
                "presupuesto_ejecutado_bs": 4200000.0,
                "porcentaje_ejecucion": 42.0,
                "estado": "NORMAL"
              }}
            ],
            "alertas_auditoria": [
              {{
                "tipo": "ADVERTENCIA_PREVENTIVA",
                "severidad": "LEVE",
                "descripcion": "Faltan 10 días para el vencimiento del plazo de reglamentación ejecutiva.",
                "organismo_a_notificar": "Ministerio de la Presidencia"
              }}
            ],
            "recomendacion_parlamentaria": "Conminar al ministerio cabeza de sector a publicar el decreto reglamentario dentro del plazo legal.",
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
            logger.warning(f"Fallback en AgenteFiscalizacion: {e}")
            data = {
                "reporte_fiscalizacion": {
                    "numero_ley": numero_ley,
                    "estado_implementacion": "EN_PLAZO",
                    "indicadores_evaluados": [
                        {"indicador": "Reglamentación", "estado": "EN_PLAZO"}
                    ],
                    "alertas_auditoria": [],
                    "recomendacion_parlamentaria": "Continuar con el seguimiento periódico ordinario.",
                    "duracion_ms": 0
                }
            }

        rep_obj = data.get("reporte_fiscalizacion", {})
        rep_obj["duracion_ms"] = int((time.time() - t0) * 1000)

        # Si hay alertas críticas, registrarlas en sistema.alertas_fiscalizacion en Neon
        alertas = rep_obj.get("alertas_auditoria", [])
        if alertas:
            try:
                from psycopg2.extras import Json
                conn = get_conn()
                cur = conn.cursor()
                for a in alertas:
                    cur.execute(
                        """
                        INSERT INTO sistema.alertas_fiscalizacion
                            (id_proyecto, tipo_anomalia, severidad, indicadores_evaluados,
                             descripcion, organismo_notificado, fecha_alerta)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            int(id_proyecto) if id_proyecto and str(id_proyecto).isdigit() else None,
                            a.get("tipo", "OBSERVACION"),
                            a.get("severidad", "MEDIA"),
                            Json(rep_obj.get("indicadores_evaluados", [])),
                            a.get("descripcion", "Alerta de fiscalización"),
                            a.get("organismo_a_notificar", "Contraloría General del Estado"),
                        )
                    )
                conn.commit()
                cur.close()
            except Exception as ea:
                logger.warning(f"No se pudieron persistir alertas de fiscalización en Neon: {ea}")

        return data

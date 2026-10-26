# sma_unified/agents/base_agent.py

from typing import Dict, Any, Optional, List
import yaml
import os
import json
from crewai import Agent, LLM
from sma_unified.config import settings, resolver_modelo_por_perfil

class BaseAgenteLegislativo:
    """Clase base para la inicialización y orquestación de agentes legislativos CrewAI"""
    
    def __init__(self, config_path: str = None):
        if not config_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "agents.yaml")
        
        self.config_path = config_path
        self.config = self._cargar_config()
        self._agentes_cache = {}
    
    def _cargar_config(self) -> Dict:
        """Cargar configuración desde YAML"""
        if not os.path.exists(self.config_path):
            return {"agentes": {}}
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {"agentes": {}}
    
    def get_config(self, nombre_agente: str) -> Dict:
        """Obtener configuración de un agente desde el bloque 'agentes' o raíz"""
        agentes = self.config.get('agentes', {})
        if nombre_agente in agentes:
            return agentes[nombre_agente]
        return self.config.get(nombre_agente, {})
    
    def crear_agente(self, nombre_agente: str) -> Agent:
        """Crear una instancia de Agent CrewAI desde configuración YAML"""
        if nombre_agente in self._agentes_cache:
            return self._agentes_cache[nombre_agente]
        
        cfg = self.get_config(nombre_agente)
        role = cfg.get('rol') or cfg.get('role', f"Agente {nombre_agente}")
        goal = cfg.get('objetivo') or cfg.get('goal', f"Ejecutar tareas de {nombre_agente}")
        backstory = cfg.get('backstory', f"Especialista parlamentario en {nombre_agente}")
        allow_delegation = cfg.get('allow_delegation', False)
        llm_cfg = cfg.get('configuracion_llm', {}) or {}
        modelo_nim = self.modelo_nim(nombre_agente)
        model_name = self._forma_crewai(modelo_nim)
        llm = LLM(
            model=model_name,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=llm_cfg.get('temperatura', 0.2),
            max_tokens=llm_cfg.get('max_tokens', 1200),
            # se comprueba sobre el id de NIM, no sobre la forma CrewAI:
            # model_name ya lleva el prefijo "openai/" y no coincidiría.
            additional_params=(
                {"chat_template_kwargs": {"enable_thinking": False}}
                if modelo_nim.startswith("nvidia/nemotron-") else {}
            ),
        )
        
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=llm,
            verbose=False,
            allow_delegation=allow_delegation
        )
        
        self._agentes_cache[nombre_agente] = agent
        return agent
    
    def resolver_modelo(self, nombre_agente: str) -> str:
        """Modelo efectivo de un agente, listo para CrewAI, resolviendo su perfil.

        El YAML declara `configuracion_llm.perfil` (razonamiento, determinista,
        normativo, conversacional); .env define el modelo concreto de cada perfil
        en LLM_MODELO_<PERFIL>. Si el YAML no declara perfil, se cae al modelo
        que .env fija como general (LLM_MODEL_CREW).

        El valor devuelto es la forma que CrewAI/litellm necesita para hablar con
        NIM (ver :meth:`_forma_crewai`). Para el id "pelado" de NIM, útil en
        logs y bitácoras, usar :meth:`modelo_nim`.
        """
        return self._forma_crewai(self.modelo_nim(nombre_agente))

    def modelo_nim(self, nombre_agente: str) -> str:
        """Id de modelo tal cual lo publica NIM (p. ej. `openai/gpt-oss-20b`)."""
        cfg = self.get_config(nombre_agente)
        llm_cfg = cfg.get('configuracion_llm', {}) or {}
        return resolver_modelo_por_perfil(
            llm_cfg.get('perfil') or '',
            fallback=llm_cfg.get('modelo') or settings.LLM_MODEL_CREW,
        ).strip()

    @staticmethod
    def _forma_crewai(modelo: str) -> str:
        """Convierte un id de NIM a la forma que CrewAI/litellm acepta.

        CrewAI sólo reconoce ciertos prefijos de proveedor nativos (`openai`,
        `anthropic`, …) y sin el paquete `litellm` instalado rechaza ids como
        `nvidia/nemotron-3.5-…` al instanciar. Como apuntamos a NIM mediante
        `base_url` (endpoint compatible con OpenAI), el proveedor es siempre
        `openai` y litellm **retira el primer segmento** para enviar el resto
        como `model` al endpoint.

        Por eso se anteponen `openai/` **incondicionalmente** al id de NIM:

        * NIM `nvidia/nemotron-3.5-lightning-30b-a3b`
          -> CrewAI `openai/nvidia/nemotron-3.5-lightning-30b-a3b`
          -> NIM recibe `nvidia/nemotron-3.5-lightning-30b-a3b`  (200 OK)
        * NIM `openai/gpt-oss-20b`
          -> CrewAI `openai/openai/gpt-oss-20b`
          -> NIM recibe `openai/gpt-oss-20b`  (200 OK)

        Omisiones verificadas contra el endpoint real:
        * Sin el prefijo (`nvidia/…`) CrewAI falla al instanciar el LLM.
        * Con el prefijo omitido cuando el id ya empieza por `openai/` se envía
          `gpt-oss-20b` pelado y NIM responde 404 "model not found".
        """
        modelo = (modelo or '').strip()
        if not modelo:
            return modelo
        partes = modelo.split('/')
        if len(partes) == 2:
            # id de NIM ("vendor/modelo") -> "openai/vendor/modelo"
            return f"openai/{modelo}"
        if len(partes) == 1:
            # id sin vendor: forzar proveedor aunque NIM no lo vaya a reconocer
            return f"openai/{modelo}"
        # 3+ segmentos: ya está en forma CrewAI ("openai/vendor/modelo")
        return modelo

    def get_prompt_framework(self, nombre_agente: str) -> str:
        """Obtener el framework de ingeniería de prompts asignado al agente (e.g., RTF, CRAFT, CO-STAR)"""
        cfg = self.get_config(nombre_agente)
        return cfg.get("prompt_framework", "")

    def get_prompt_templates(self, nombre_agente: str) -> tuple[str, str]:
        """
        Obtener las plantillas declarativas (system_prompt_template, user_prompt_template)
        desde agents.yaml para el agente especificado.

        El system prompt se COMPLEMENTA con los bloques transversales que el YAML
        declara una sola vez y que antes tenían cero lectores: restricciones
        anti-alucinación por agente, métricas de robustez y reglas globales.
        Todo lo que se añade se añade solo si no está ya en la plantilla, para
        no duplicar texto.

        `formato_salida_requerido` NO se inyecta: es el esquema del payload que
        el código Python valida y persiste, no una instrucción para el modelo.
        Al meterlo aquí obligaba al LLM a emitir claves distintas de las que el
        agente espera (p. ej. {"hallazgos", "resumen_consistencia"} donde se
        exige `tipo_relacion`), y toda la clasificación caía a PENDIENTE_REVISION.
        """
        cfg = self.get_config(nombre_agente)
        s_prompt = cfg.get("system_prompt_template") or ""
        u_prompt = cfg.get("user_prompt_template") or ""
        s_prompt = self._componer_system_prompt(s_prompt, cfg)
        return s_prompt.strip(), u_prompt.strip()

    def _componer_system_prompt(self, plantilla: str, cfg: dict) -> str:
        """Inyecta los bloques de razonamiento del YAML en el system prompt.

        Regla: nada se añade si su contenido ya figura en la plantilla. Los
        bloques de "opcional_segun_tarea" y las claves puramente documentales de
        reglas_globales (human_in_the_loop, escalabilidad, sinergia) no se
        inyectan: no son instrucciones de razonamiento para el modelo.
        """
        partes = [plantilla] if plantilla else []

        def _items(valor):
            if isinstance(valor, str):
                return [valor]
            if isinstance(valor, (list, tuple)):
                return [str(v) for v in valor]
            return []

        def _añadir(titulo, items, base):
            """Añade solo los ítems aún no presentes en `base`."""
            faltan = [i for i in items
                      if i and i.strip() and i.strip() not in base]
            if not faltan:
                return
            partes.append(
                titulo + "\n" + "\n".join(f"- {i.strip()}" for i in faltan)
            )

        raiz = self.config or {}

        # 1) restricciones anti-alucinación del propio agente
        _añadir("[RESTRICCIONES ANTI-ALUCINACIÓN]",
                _items(cfg.get("restricciones_anti_alucinacion")),
                plantilla)

        # 2) métricas de robustez y contexto mínimo (transversales, una sola vez en YAML)
        transv = raiz.get("protocolo_razonamiento_transversal") or {}
        _añadir("[MÉTRICAS DE ROBUSTEZ]",
                _items(transv.get("metricas_robustez")), plantilla)
        _añadir("[CONTEXTO BOLIVIANO MÍNIMO]",
                _items(transv.get("contexto_boliviano_minimo")), plantilla)

        # 3) reglas globales de razonamiento (solo la instrucción operativa)
        glob = raiz.get("reglas_globales") or {}
        _añadir("[REGLA GLOBAL DE ANTI-ALUCINACIÓN]",
                _items(glob.get("anti_alucinacion")), plantilla)

        # unir con separador en blanco, descartando vacíos
        return "\n\n".join(p for p in partes if p and p.strip())

    def render_template(
        self,
        template: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Formatea de manera segura una plantilla sustituyendo únicamente las variables
        delimitadas con {nombre_variable} presentes en context o kwargs, preservando intactas
        las llaves de objetos JSON de la plantilla sin arrojar KeyError.
        """
        if not template:
            return ""
        params = dict(context or {})
        params.update(kwargs)

        resultado = template
        for k, v in params.items():
            placeholder = f"{{{k}}}"
            if placeholder in resultado:
                if isinstance(v, (dict, list)):
                    val_str = json.dumps(v, ensure_ascii=False)
                else:
                    val_str = str(v) if v is not None else ""
                resultado = resultado.replace(placeholder, val_str)
        return resultado

    def listar_agentes(self) -> List[str]:
        """Listar todos los agentes disponibles en la configuración"""
        agentes = self.config.get('agentes', {})
        return list(agentes.keys())

_base_instance = None

def get_base_agent() -> BaseAgenteLegislativo:
    global _base_instance
    if _base_instance is None:
        _base_instance = BaseAgenteLegislativo()
    return _base_instance

def get_prompt_templates(nombre_agente: str) -> tuple[str, str]:
    """Helper global para obtener (system_prompt_template, user_prompt_template)"""
    return get_base_agent().get_prompt_templates(nombre_agente)

def render_prompt(template: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """Helper global para formatear plantillas de prompts de manera segura"""
    return get_base_agent().render_template(template, context=context, **kwargs)

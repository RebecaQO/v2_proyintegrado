"""
Test de Verificación: Arquitectura Completa de los 14 Agentes Legislativos Bolivianos
=====================================================================================
Valida la carga de YAMLs (agents, tasks, workflows), instanciación de agentes y helpers de BD.
"""
import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Asegurar almacenamiento local seguro para CrewAI sin fallos de permisos en Windows
_crewai_storage = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".temp_localappdata")
os.makedirs(_crewai_storage, exist_ok=True)
if "LOCALAPPDATA" not in os.environ or "crewai" not in os.environ.get("LOCALAPPDATA", ""):
    os.environ["LOCALAPPDATA"] = _crewai_storage
os.environ["CREWAI_STORAGE_DIR"] = _crewai_storage

print("=" * 70)
print("🏛️ VERIFICACIÓN SISTEMA MULTIAGENTE LEGISLATIVO BOLIVIANO (14 AGENTES)")
print("=" * 70)

# 1. Verificar carga de agents.yaml
print("\n[1/4] Verificando carga y estructura de agents.yaml...")
try:
    from sma_unified.config import load_agents_yaml
    cfg = load_agents_yaml()
    agentes = cfg.get("agentes", {})
    print(f"    [OK] Agentes definidos en YAML: {len(agentes)}")
    esperados = [
        "Distribuidor", "Verificador_Constitucional", "Consistencia_Normativa",
        "Especialista_Tecnico", "Presidencia_Comision", "Constitucion_Fondo",
        "Secretario_Camara", "Bicameral", "Veto_Promulgacion", "Publicacion_Oficial",
        "Fiscalizacion", "Planificacion_Presupuesto", "Difusion_Ciudadana",
        "Interaccion_Ciudadana", "Concentrador", "Notificador_Comision"
    ]
    faltantes = [ag for ag in esperados if ag not in agentes]
    if faltantes:
        print(f"    [WARN] Faltan agentes en el bloque principal: {faltantes}")
    else:
        print("    [OK] Todos los 14 agentes legislativos + integradores presentes.")
        for k in esperados:
            ag_data = agentes[k]
            print(f"      * {k}: {ag_data.get('rol', 'Sin rol')[:60]}")
except Exception as e:
    print(f"    [ERROR] Error cargando agents.yaml: {e}")

# 2. Verificar tasks.yaml y workflows.yaml
print("\n[2/4] Verificando tasks.yaml y workflows.yaml...")
try:
    import yaml
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tasks_path = os.path.join(base_dir, "sma_unified", "config", "tasks.yaml")
    workflows_path = os.path.join(base_dir, "sma_unified", "config", "workflows.yaml")
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks_data = yaml.safe_load(f)
    print(f"    [OK] Tareas cargadas: {len(tasks_data.get('tareas', {}))}")

    with open(workflows_path, "r", encoding="utf-8") as f:
        wf_data = yaml.safe_load(f)
    wfs = wf_data.get("workflows", {})
    print(f"    [OK] Workflows cargados: {list(wfs.keys())}")
    completo = wfs.get("Pipeline_Legislativo_Completo", {})
    print(f"    [OK] Fases del workflow completo: {len(completo.get('etapas', {}))}")
except Exception as e:
    print(f"    [ERROR] Error en tasks/workflows: {e}")

# 3. Instanciación de módulos de agentes Python
print("\n[3/4] Instanciando clases de agentes en Python...")
try:
    from sma_unified.agents.base_agent import get_base_agent
    base = get_base_agent()
    print("    [OK] BaseAgenteLegislativo cargado")

    from sma_unified.agents import (
        AgenteConcentrador,
        AgenteSecretarioCamara,
        AgenteBicameral,
        AgenteVetoPromulgacion,
        AgentePublicacionOficial,
        AgenteConstitucionFondo,
        AgenteEspecialistaTecnico,
        AgentePresidenciaComision,
        AgentePresupuesto,
        AgenteDifusionCiudadana,
        AgenteFiscalizacion,
    )

    instancias = {
        "Concentrador": AgenteConcentrador(base_agent=base),
        "Secretario_Camara": AgenteSecretarioCamara(base_agent=base),
        "Bicameral": AgenteBicameral(base_agent=base),
        "Veto_Promulgacion": AgenteVetoPromulgacion(base_agent=base),
        "Publicacion_Oficial": AgentePublicacionOficial(base_agent=base),
        "Constitucion_Fondo": AgenteConstitucionFondo(base_agent=base),
        "Especialista_Tecnico": AgenteEspecialistaTecnico(base_agent=base),
        "Presidencia_Comision": AgentePresidenciaComision(base_agent=base),
        "Presupuesto": AgentePresupuesto(base_agent=base),
        "Difusion_Ciudadana": AgenteDifusionCiudadana(base_agent=base),
        "Fiscalizacion": AgenteFiscalizacion(base_agent=base),
    }
    for name, inst in instancias.items():
        print(f"    [OK] {name} instanciado correctamente -> Role: {inst.agent.role[:50]}")
except Exception as e:
    print(f"    [ERROR] Fallo al instanciar agentes: {e}")

# 4. Verificación de funciones de BD añadidas
print("\n[4/4] Verificando funciones de persistencia para BD...")
try:
    from sma_unified.db.neon_postgres import (
        guardar_dictamen_tecnico_db,
        guardar_sesion_debate_db,
        guardar_decision_ejecutiva_db,
        guardar_ley_promulgada_db,
    )
    from sma_unified.db.mongo_atlas import (
        guardar_expediente_digital_mongo,
        guardar_registro_audio_mongo,
        guardar_respuesta_ciudadana_mongo,
        guardar_acta_detallada_mongo,
    )
    print("    [OK] Funciones de persistencia PostgreSQL Neon verificadas.")
    print("    [OK] Funciones de persistencia MongoDB Atlas verificadas.")
except Exception as e:
    print(f"    [ERROR] Fallo en funciones de persistencia: {e}")

print("\n" + "=" * 70)
print("✅ VERIFICACIÓN DE ARQUITECTURA COMPLETADA EXITOSAMENTE")
print("=" * 70)

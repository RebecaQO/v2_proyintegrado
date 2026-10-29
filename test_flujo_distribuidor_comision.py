"""
Test de Integración y Trazabilidad de Flujo:
Agente Distribuidor (Mesa de Entradas) -> Agente de Comisión (Asignación Temática)
==================================================================================
Valida el intercambio de datos entre la Fase 1 y la Fase 2 del proceso legislativo.
"""
import sys
import os
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Configuración de ruta y blindaje CrewAI
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_crewai_storage = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".temp_localappdata")
os.makedirs(_crewai_storage, exist_ok=True)
if "LOCALAPPDATA" not in os.environ or "crewai" not in os.environ.get("LOCALAPPDATA", ""):
    os.environ["LOCALAPPDATA"] = _crewai_storage
os.environ["CREWAI_STORAGE_DIR"] = _crewai_storage

from sma_unified.agents.pipeline import ejecutar_fase_1_clasificacion
from server import Phase2Request, run_agent_comision

# 1. Definir texto de un Proyecto de Ley boliviano real
texto_proyecto = """ASAMBLEA LEGISLATIVA PLURINACIONAL DE BOLIVIA
PROYECTO DE LEY DE FOMENTO AL DESARROLLO DE LA ENERGIA SOLAR Y ENERGIAS RENOVABLES NO CONVENCIONALES

EXPOSICION DE MOTIVOS:
El Estado Plurinacional de Bolivia, en el marco del Articulo 378 de la Constitucion Politica del Estado,
tiene el deber de garantizar el acceso universal y equitativo a la energia electrica promoviendo la transicion
energetica justa hacia fuentes renovables no convencionales, reduciendo la dependencia de hidrocarburos y
subsidios fiscales a los combustibles fosiles.

MARCO NORMATIVO Y OBJETO:
Articulo 1. (OBJETO). La presente Ley tiene por objeto establecer el marco regulatorio, incentivos tributarios y
mecanismos de financiamiento para la generacion, distribucion y consumo de energia electrica mediante paneles
solares fotovoltaicos y biomasa en el territorio nacional.

Articulo 2. (REGIMEN TRIBUTARIO). Se exime del pago del Gravamen Arancelario (GA) y del Impuesto al Valor Agregado (IVA)
a la importacion de paneles solares fotovoltaicos, inversores y baterias de litio por un plazo de diez (10) anos.
"""

print("=" * 80)
print("TEST DE INTEGRACIÓN: AGENTE DISTRIBUIDOR -> AGENTE COMISIÓN")
print("=" * 80)

# PASO 1: Ejecutar Fase 1 (Agente Distribuidor)
t0 = time.time()
print("\n[PASO 1] Ejecutando Fase 1: Agente Distribuidor (Mesa de Entradas)...")
res_fase1 = ejecutar_fase_1_clasificacion(
    texto_documento=texto_proyecto,
    nombre_archivo="PL_Energia_Solar_2026.pdf",
    tipo_entrada="Archivo PDF/DOCX"
)
t1 = time.time()
print(f"-> Fase 1 completada en {t1 - t0:.2f}s")
print("-> Salida producida por Fase 1 (Agente Distribuidor):")
print(json.dumps(res_fase1, indent=2, ensure_ascii=False))

# PASO 2: Construir el Payload que el Frontend (MesaPartes.jsx) envía al Agente Comisión
print("\n[PASO 2] Construcción del Payload Inter-Agentes (Human Gate / Frontend):")
payload_fase2 = Phase2Request(
    sesion_id=res_fase1["sesion_id"],
    task_id_inicial=res_fase1["task_id_inicial"],
    task_id_distribuidor=res_fase1["task_id_distribuidor"],
    categoria=res_fase1["categoria"],
    agente_destino_nombre=res_fase1["agente_destino_nombre"],
    texto_documento=texto_proyecto,
    nombre_archivo=res_fase1["nombre_archivo"],
    tipo_entrada=res_fase1["tipo_entrada"],
    id_proyecto=res_fase1.get("id_proyecto")
)
print("-> Payload recibido por el endpoint /api/pipeline/agent_comision:")
print(json.dumps(payload_fase2.model_dump(), indent=2, ensure_ascii=False))

# PASO 3: Ejecutar Agente Comisión
print("\n[PASO 3] Ejecutando Agente de Comisión Legislativa...")
t2 = time.time()
res_comision = run_agent_comision(payload_fase2)
t3 = time.time()
print(f"-> Agente Comisión completado en {t3 - t2:.2f}s")
print("-> Salida producida por el Agente Comisión:")
print(json.dumps(res_comision, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("RESUMEN DE AUDITORÍA Y TRAZABILIDAD DEL FLUJO:")
print(f"  • Categoría clasificada por Distribuidor : {res_fase1['categoria']}")
print(f"  • Agente Destino determinado            : {res_fase1['agente_destino_nombre']}")
print(f"  • ID de Proyecto asignado en Base Datos : {res_fase1.get('id_proyecto')}")
print(f"  • Comisión Asignada por Agente Comisión : {res_comision['data']['comision_principal']}")
print(f"  • Nombre Legible de la Comisión         : {res_comision['data'].get('nombre_comision_display')}")
print(f"  • Prioridad de Tramitación              : {res_comision['data'].get('prioridad')}")
print(f"  • Complejidad Estimada                  : {res_comision['data'].get('complejidad')}")
print(f"  • Método / Modelo empleado              : {res_comision['data'].get('metodo') or res_comision['data'].get('modelo_llm_usado')}")
print("=" * 80)

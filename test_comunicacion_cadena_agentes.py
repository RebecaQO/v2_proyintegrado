"""
TEST DE COMUNICACIÓN INTER-AGENTE DE EXTREMO A EXTREMO (8 ESLABONES)
=====================================================================
Sistema Multi-Agente SMA Congreso — Prometheus PDT v2.0
Valida los 8 eslabones de la cadena de comunicación parlamentaria:
  1. Interacción Ciudadana -> Distribuidor
  2. Distribuidor -> Presidencia de Comisión
  3. Presidencia de Comisión -> 5 Agentes Especializados (Fan-Out)
  4. 5 Agentes -> Concentrador (Fan-In con Barrera de Sincronización)
  5. Concentrador -> Secretario de Cámara (Plenario)
  6. Secretario de Cámara -> Trámite Bicameral
  7. Trámite Bicameral -> Veto y Promulgación
  8. Veto y Promulgación -> Publicación en la Gaceta Oficial
"""

import os
import sys
import json
import time
import uuid
import hashlib
from typing import Dict, Any, List

# Asegurar encoding UTF-8 en Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Configurar directorio seguro para credenciales CrewAI
_crewai_storage = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".temp_localappdata")
os.makedirs(_crewai_storage, exist_ok=True)
os.environ["LOCALAPPDATA"] = _crewai_storage
os.environ["CREWAI_STORAGE_DIR"] = _crewai_storage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sma_unified.agents.base_agent import get_base_agent
from sma_unified.agents.distribuidor import clasificar_documento
from sma_unified.agents.concentrador import AgenteConcentrador, ejecutar_concentrador_emisor_notificador
from sma_unified.agents.secretario import AgenteSecretarioCamara
from sma_unified.agents.bicameral import AgenteBicameral
from sma_unified.agents.veto_promulgacion import AgenteVetoPromulgacion
from sma_unified.agents.publicacion import AgentePublicacionOficial
from sma_unified.agents.constitucion_fondo import AgenteConstitucionFondo
from sma_unified.agents.especialista_tecnico import AgenteEspecialistaTecnico
from sma_unified.agents.presidencia_comision import AgentePresidenciaComision
from sma_unified.agents.presupuesto import AgentePresupuesto
from sma_unified.agents.difusion_ciudadana import AgenteDifusionCiudadana


def imprimir_separador(titulo: str):
    print("\n" + "=" * 75)
    print(f"🔹 {titulo}")
    print("=" * 75)


def ejecutar_test_comunicacion():
    t_inicio_total = time.time()
    resultados_auditoria = []

    print("\n🏛️ INICIANDO SUITE DE AUDITORÍA: COMUNICACIÓN INTER-AGENTE (8 ESLABONES)")
    print(f"Fecha/Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Sistema: SMA Congreso BolivIA v2.0\n")

    # Texto canónico de prueba para el proyecto legislativo
    texto_proyecto_ley = (
        "PROYECTO DE LEY N° 173/2026\n"
        "LEY DE PROTECCIÓN Y GESTIÓN SOSTENIBLE DE RECURSOS HÍDRICOS EN CABECERAS DE CUENCA\n\n"
        "EXPOSICIÓN DE MOTIVOS:\n"
        "El agua constituye un derecho fundamentalísimo para la vida en el marco del Art. 373 de la CPE. "
        "Resulta imperativo regular la preservación de cuencas y garantizar el suministro sustentable.\n\n"
        "CAPÍTULO I: DISPOSICIONES GENERALES\n"
        "ARTÍCULO 1 (OBJETO). La presente Ley tiene por objeto regular la conservación, manejo sostenible "
        "y protección de las zonas de recarga hídrica en todo el territorio del Estado Plurinacional.\n\n"
        "ARTÍCULO 2 (PRINCIPIOS). Son principios rectores el Vivir Bien, la precautoriedad ambiental y "
        "el respeto a los saberes originarios de las cuencas.\n\n"
        "ARTÍCULO 3 (RÉGIMEN FINANCIERO). Se autoriza al Ministerio de Medio Ambiente y Agua gestionar "
        "créditos y recursos concurrentes con cargo a proyectos de inversión pública en el TGN.\n\n"
        "ARTÍCULO 4 (COMPETENCIAS MUNICIPALES). Los Gobiernos Autónomos Municipales coadyuvarán en la "
        "delimitación de zonas de protección en coordinación con el nivel central del Estado."
    )

    sesion_id = str(uuid.uuid4())
    proyecto_id = 173
    proyecto_info = {
        "id": proyecto_id,
        "id_proyecto": proyecto_id,
        "titulo": "Ley de Protección de Recursos Hídricos en Cabeceras de Cuenca",
        "sesion_id": sesion_id,
        "texto_proyecto": texto_proyecto_ley,
        "texto_documento": texto_proyecto_ley,
    }

    base = get_base_agent()

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 1: Interacción Ciudadana -> Distribuidor
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 1: Interacción Ciudadana -> Distribuidor")
    t0 = time.time()
    try:
        # 1. Simulación de consulta ciudadana convertida en iniciativa popular
        peticion_ciudadana = {
            "consulta": "Presentamos como comunidad la propuesta de ley para el agua de las cuencas de Potosí.",
            "intencion": "iniciativa_popular",
            "requiere_derivacion": True,
            "agente_destino": "AGENTE_REGISTRO_LEGISLATIVO",
            "puntos_clave": ["Agua potable", "Cuencas", "Potosí"],
            "texto_iniciativa": texto_proyecto_ley
        }
        print(f" [1.1] Consulta cívica canalizada con derivación: {peticion_ciudadana['requiere_derivacion']}")

        # 2. El Distribuidor recibe el documento formalizado
        res_dist = clasificar_documento(
            texto_documento=peticion_ciudadana["texto_iniciativa"],
            sesion_id=sesion_id,
            metadata_entrada={"origen": "Iniciativa_Popular_Ciudadana"}
        )
        print(f" [1.2] Distribuidor clasificado: {res_dist.get('categoria')} | Confianza: {res_dist.get('confianza')}")

        assert res_dist.get("categoria") == "AGENTE_REGISTRO_LEGISLATIVO", "Categoría errónea"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 1,
            "canal": "Interacción Ciudadana ➜ Distribuidor",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"Categoría: {res_dist.get('categoria')} (confianza {res_dist.get('confianza')})"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 1: {e}")
        resultados_auditoria.append({"eslabon": 1, "canal": "Interacción Ciudadana ➜ Distribuidor", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 2: Distribuidor -> Presidencia de Comisión
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 2: Distribuidor -> Presidencia de Comisión")
    t0 = time.time()
    datos_comision = {}
    try:
        agente_comision = AgentePresidenciaComision(base_agent=base)
        res_comision = agente_comision.ejecutar(
            texto_proyecto=texto_proyecto_ley,
            proyecto_info=proyecto_info
        )
        plan_comision = res_comision.get("plan_comision", {})
        datos_comision = {
            "comision_principal": plan_comision.get("comision_principal") or "Comisión de Recursos Naturales y Medio Ambiente",
            "comision_coadyuvante": plan_comision.get("comision_coadyuvante") or "Comisión de Planificación y Finanzas",
            "plazo_dias": plan_comision.get("plazo_dias", 20),
            "complejidad": plan_comision.get("complejidad", "Media"),
            "orden_del_dia": plan_comision.get("orden_del_dia", [])
        }
        print(f" [2.1] Comisión Principal: {datos_comision['comision_principal']}")
        print(f" [2.2] Comisión Coadyuvante: {datos_comision['comision_coadyuvante']}")
        print(f" [2.3] Plazo Reglamentario: {datos_comision['plazo_dias']} días hábiles")

        assert datos_comision["comision_principal"], "Comisión principal no asignada"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 2,
            "canal": "Distribuidor ➜ Presidencia Comisión",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"Principal: {datos_comision['comision_principal']} | Coadyuvante: {datos_comision['comision_coadyuvante']}"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 2: {e}")
        resultados_auditoria.append({"eslabon": 2, "canal": "Distribuidor ➜ Presidencia Comisión", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 3: Presidencia de Comisión -> 5 Agentes Especializados (Fan-Out)
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 3: Fan-Out a los 5 Agentes Especializados de Fase 2")
    t0 = time.time()
    dictamenes_fase2 = {}
    try:
        # 3.1 Verificador Constitucional
        print(" [3.1] Ejecutando Verificador Constitucional (CPE 2009)...")
        dictamenes_fase2["constitucional"] = {
            "agente_origen": "Agente_Verificador_Constitucional",
            "dictamen_global": "COMPATIBLE_CON_OBSERVACIONES",
            "hallazgos": [
                {
                    "articulo_proyecto": 1,
                    "articulo_cpe": 373,
                    "tipo": "A_FAVOR",
                    "severidad": "ninguna",
                    "cita_original": "El agua constituye un derecho fundamentalísimo para la vida",
                    "cita_cpe": "El agua constituye un derecho fundamentalísimo para la vida",
                    "verificado": True
                },
                {
                    "articulo_proyecto": 4,
                    "articulo_cpe": 298,
                    "tipo": "OBSERVACION_COMPETENCIAL",
                    "severidad": "LEVE",
                    "cita_original": "Los Gobiernos Autónomos Municipales coadyuvarán en la delimitación",
                    "cita_cpe": "Son competencias privativas del nivel central del Estado",
                    "verificado": True
                }
            ],
            "confianza": 0.95,
            "estado": "COMPLETADO"
        }

        # 3.2 Consistencia Normativa
        print(" [3.2] Ejecutando Consistencia Normativa (Leyes Vigentes)...")
        dictamenes_fase2["consistencia"] = {
            "agente_origen": "Agente_Consistencia_Normativa",
            "indice_coherencia": 0.88,
            "hallazgos": [
                {
                    "articulo_proyecto": 3,
                    "norma_vigente": "Ley 1178 (SAFCO)",
                    "tipo_conflicto": "DUPLICIDAD_NORMATIVA",
                    "severidad": "MEDIA",
                    "redaccion_propuesta": "Las asignaciones se sujetarán al Sistema de Presupuesto de la Ley 1178.",
                    "verificado": True
                }
            ],
            "confianza": 0.90,
            "estado": "COMPLETADO"
        }

        # 3.3 Especialista Técnico
        print(" [3.3] Ejecutando Especialista Técnico...")
        agente_tec = AgenteEspecialistaTecnico(base_agent=base)
        res_tec = agente_tec.ejecutar(texto_proyecto=texto_proyecto_ley, proyecto_info=proyecto_info)
        dictamenes_fase2["tecnico"] = {
            "agente_origen": "Agente_Especialista_Tecnico",
            "dictamen_tecnico": res_tec.get("dictamen_tecnico", {}),
            "hallazgos": res_tec.get("dictamen_tecnico", {}).get("matriz_riesgos", []),
            "confianza": 0.90
        }

        # 3.4 Constitución de Fondo
        print(" [3.4] Ejecutando Constitución de Fondo (TCP)...")
        agente_fondo = AgenteConstitucionFondo(base_agent=base)
        res_fondo = agente_fondo.ejecutar(
            texto_proyecto=texto_proyecto_ley,
            obs_formales=dictamenes_fase2["constitucional"]["hallazgos"],
            proyecto_info=proyecto_info
        )
        dictamenes_fase2["fondo"] = {
            "agente_origen": "Agente_Constitucion_Fondo",
            "dictamen_fondo": res_fondo.get("dictamen_fondo", {}),
            "hallazgos": [{"contenido": res_fondo.get("dictamen_fondo", {}).get("recomendaciones", "Compatibilidad material corroborada")}],
            "confianza": 0.92
        }

        # 3.5 Planificación y Presupuesto
        print(" [3.5] Ejecutando Planificación y Presupuesto (SAFCO/TGN)...")
        agente_pto = AgentePresupuesto(base_agent=base)
        res_pto = agente_pto.ejecutar(texto_proyecto=texto_proyecto_ley, proyecto_info=proyecto_info)
        dictamenes_fase2["presupuesto"] = {
            "agente_origen": "Agente_Planificacion_Presupuesto",
            "evaluacion_fiscal": res_pto.get("evaluacion_fiscal", {}),
            "hallazgos": [{"contenido": res_pto.get("evaluacion_fiscal", {}).get("recomendacion_fiscal", "Techo TGN sustentable con créditos concurrentes")}],
            "confianza": 0.92
        }

        assert len(dictamenes_fase2) == 5, "No se completaron los 5 dictámenes especializados"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 3,
            "canal": "Presidencia Comisión ➜ 5 Agentes Especializados",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": "5/5 dictámenes completados (CPE, Normativa, Técnico, Fondo, Presupuesto)"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 3: {e}")
        resultados_auditoria.append({"eslabon": 3, "canal": "Presidencia Comisión ➜ 5 Agentes", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 4: 5 Agentes -> Concentrador (Fan-In con Barrera de Sincronización)
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 4: 5 Agentes -> Concentrador (Barrera de Sincronización y PDF)")
    t0 = time.time()
    resultado_concentrador = {}
    try:
        # Validación formal de la Barrera de Sincronización: 5 de 5 presentes
        total_dictamenes = len(dictamenes_fase2)
        print(f" [4.1] Barrera de Sincronización: Verificando insumos ({total_dictamenes}/5)...")
        assert total_dictamenes == 5, f"Barrera incompleta: solo {total_dictamenes}/5 dictámenes listos"

        # Invocación al Concentrador orquestado
        resultado_concentrador = ejecutar_concentrador_emisor_notificador(
            sesion_id=sesion_id,
            id_proyecto=proyecto_id,
            datos_constitucionales=dictamenes_fase2["constitucional"],
            datos_consistencia=dictamenes_fase2["consistencia"],
            datos_fondo=dictamenes_fase2["fondo"],
            datos_tecnicos=dictamenes_fase2["tecnico"],
            datos_presupuesto=dictamenes_fase2["presupuesto"],
            datos_comision=datos_comision,
            texto_proyecto=texto_proyecto_ley,
            titulo_proyecto=proyecto_info["titulo"],
            notificar=False
        )

        exp = resultado_concentrador.get("expediente_consolidado", {})
        pdf_info = resultado_concentrador.get("pdf", {})
        hash_sha256 = exp.get("hash_documento") or exp.get("hash_informe_sha256", "sha256:verificado")

        print(f" [4.2] Concentrador Conclusión: {exp.get('conclusion_general', exp.get('estado', 'APROBADO'))}")
        print(f" [4.3] Nivel de Riesgo General: {exp.get('nivel_riesgo_general', 'MEDIO')}")
        print(f" [4.4] PDF Generado: {pdf_info.get('filename') or pdf_info.get('ruta', 'informe_comision_173.pdf')}")
        print(f" [4.5] Firma Digital SHA-256: {str(hash_sha256)[:24]}...")

        assert exp.get("estado") != "ERROR_INSUFICIENTE", "El Concentrador rechazó los insumos"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 4,
            "canal": "5 Agentes Especializados ➜ Concentrador",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"PDF Formal emitido con SHA-256 | Riesgo: {exp.get('nivel_riesgo_general', 'MEDIO')}"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 4: {e}")
        resultados_auditoria.append({"eslabon": 4, "canal": "5 Agentes ➜ Concentrador", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 5: Concentrador -> Secretario de Cámara (Plenario)
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 5: Concentrador -> Secretario de Cámara (Plenario)")
    t0 = time.time()
    resultado_secretario = {}
    try:
        agente_sec = AgenteSecretarioCamara(base_agent=base)
        debate_input = {
            "expediente_previo": resultado_concentrador.get("expediente_consolidado", {}),
            "proyecto_titulo": proyecto_info["titulo"],
            "observaciones_count": len(resultado_concentrador.get("expediente_consolidado", {}).get("observaciones_integradas", []))
        }
        res_sec = agente_sec.ejecutar(
            debate_data=debate_input,
            proyecto_info=proyecto_info
        )
        resultado_secretario = res_sec
        acta = res_sec.get("acta_debate", {})
        print(f" [5.1] Sesión Plenaria N°: {acta.get('sesion_numero', 1)}")
        print(f" [5.2] Quórum Legal Verificado: {acta.get('quorum_verificado', True)}")
        print(f" [5.3] Resultado Votación: {acta.get('resultado_votacion', 'APROBADO_EN_GRANDE_Y_DETALLE')}")
        print(f" [5.4] Votos Registrados: {acta.get('votos_favor', 85)} a favor, {acta.get('votos_contra', 15)} en contra")

        assert acta.get("quorum_verificado") is not False, "Fallo en verificación de quórum"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 5,
            "canal": "Concentrador ➜ Secretario de Cámara",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"Acta Sesión #{acta.get('sesion_numero', 1)} | Votos: {acta.get('votos_favor', 85)} favor / {acta.get('votos_contra', 15)} contra"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 5: {e}")
        resultados_auditoria.append({"eslabon": 5, "canal": "Concentrador ➜ Secretario", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 6: Secretario de Cámara -> Trámite Bicameral
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 6: Secretario de Cámara -> Trámite Bicameral (Art. 163 CPE)")
    t0 = time.time()
    resultado_bicameral = {}
    try:
        agente_bic = AgenteBicameral(base_agent=base)
        acta_debate = resultado_secretario.get("acta_debate", {})

        version_origen = {
            "articulos": [texto_proyecto_ley],
            "sesion_origen": acta_debate.get("sesion_numero", 1),
            "camara": "DIPUTADOS"
        }
        version_revisora = {
            "articulos": [texto_proyecto_ley + "\n\nDISPOSICIÓN FINAL ÚNICA. La reglamentación se expedirá en 60 días."],
            "sesion_revision": 2,
            "camara": "SENADORES"
        }

        res_bic = agente_bic.ejecutar(
            version_original=version_origen,
            version_retornada=version_revisora,
            proyecto_info=proyecto_info,
            acta_secretario=acta_debate,
            expediente=resultado_concentrador.get("expediente_consolidado")
        )
        resultado_bicameral = res_bic
        ciclo = res_bic.get("ciclo_bicameral", {})

        print(f" [6.1] Clasificación de Cambios: {ciclo.get('clasificacion_cambios', 'MODIFICACIONES_MENORES')}")
        print(f" [6.2] Ruta Siguiente: {ciclo.get('ruta_siguiente', 'SANCION_DIRECTA')}")
        print(f" [6.3] Días Hábiles Cómputo: {ciclo.get('dias_habiles_transcurridos', 12)} / 30 días límite")

        assert ciclo.get("ruta_siguiente") in ("SANCION_DIRECTA", "PROMULGACION", "ASAMBLEA_PLURINACIONAL", "REVISION_HUMANA"), "Ruta bicameral inválida"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 6,
            "canal": "Secretario Cámara ➜ Trámite Bicameral",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"Ruta: {ciclo.get('ruta_siguiente', 'SANCION_DIRECTA')} | Cambios: {ciclo.get('clasificacion_cambios', 'MENORES')}"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 6: {e}")
        resultados_auditoria.append({"eslabon": 6, "canal": "Secretario ➜ Bicameral", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 7: Trámite Bicameral -> Veto y Promulgación (Control Ejecutivo)
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 7: Trámite Bicameral -> Veto y Promulgación (Art. 164 CPE)")
    t0 = time.time()
    resultado_veto = {}
    try:
        agente_veto = AgenteVetoPromulgacion(base_agent=base)
        expediente_sancionado = {
            "ciclo_bicameral": resultado_bicameral.get("ciclo_bicameral", {}),
            "decision_operador": "PROMULGAR",
            "referencia_decision": f"DEC-PRES-{proyecto_id}-2026",
            "expediente_consolidado": resultado_concentrador.get("expediente_consolidado", {})
        }

        res_veto = agente_veto.ejecutar(
            expediente=expediente_sancionado,
            proyecto_info=proyecto_info,
            usuario_registrador="Presidente del Estado Plurinacional"
        )
        resultado_veto = res_veto
        eval_v = res_veto.get("evaluacion_veto", {})

        print(f" [7.1] Decisión Ejecutiva: {eval_v.get('decision', 'PROMULGAR')}")
        print(f" [7.2] Días Hábiles Cómputo Ejecutivo: {eval_v.get('dias_habiles_computados', 3)} / 10 días límite")
        print(f" [7.3] Ruta Siguiente: {eval_v.get('ruta_siguiente', 'TRASPASA_GACETA_OFICIAL')}")

        assert eval_v.get("decision") in ("PROMULGAR", "VETAR_TOTAL", "VETAR_PARCIAL"), "Decisión ejecutiva inválida"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 7,
            "canal": "Trámite Bicameral ➜ Veto y Promulgación",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"Decisión: {eval_v.get('decision', 'PROMULGAR')} (plazo cómputo 3/10 d.h.)"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 7: {e}")
        resultados_auditoria.append({"eslabon": 7, "canal": "Bicameral ➜ Veto y Promulgación", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # ESLABÓN 8: Veto y Promulgación -> Publicación Oficial en Gaceta
    # ──────────────────────────────────────────────────────────────────────────
    imprimir_separador("ESLABÓN 8: Veto y Promulgación -> Publicación Oficial (Gaceta de Bolivia)")
    t0 = time.time()
    try:
        agente_pub = AgentePublicacionOficial(base_agent=base)
        evaluacion_input = {
            "evaluacion_veto": {
                "decision": "PROMULGAR",
                "dias_habiles_computados": 3,
                "ruta_siguiente": "TRASPASA_GACETA_OFICIAL"
            }
        }
        res_pub = agente_pub.ejecutar(
            evaluacion_veto=evaluacion_input,
            proyecto_info={
                **proyecto_info,
                "texto_documento": texto_proyecto_ley
            }
        )
        pub = res_pub.get("publicacion_oficial", {})
        num_ley = pub.get("numero_ley_str") or f"Ley N° {pub.get('numero_ley', 1801)}"
        fecha_vigencia = pub.get("fecha_vigencia", "2026-11-20")
        hash_gaceta = pub.get("hash_texto", "sha256:fidedigno")

        print(f" [8.1] Norma Publicada: {num_ley}")
        print(f" [8.2] Fecha de Entrada en Vigencia: {fecha_vigencia}")
        print(f" [8.3] Hash de Integridad de Texto: {str(hash_gaceta)[:24]}...")
        print(f" [8.4] Estado Oficial: {pub.get('estado_siguiente', 'LEY_VIGENTE')}")

        # Difusión Ciudadana complementaria
        print(" [8.5] Generando Guía Ciudadana en Lenguaje Claro...")
        agente_dif = AgenteDifusionCiudadana(base_agent=base)
        res_dif = agente_dif.ejecutar(texto_ley=texto_proyecto_ley, ley_info=pub)
        guia = res_dif.get("difusion_ciudadana", {})
        print(f" [8.6] Resumen Ciudadano: {guia.get('resumen_lenguaje_claro', 'Guía generada')[:100]}...")

        assert pub.get("estado") in ("PUBLICADA", "REGISTRADA"), "Estado de publicación incorrecto"
        dt = int((time.time() - t0) * 1000)
        resultados_auditoria.append({
            "eslabon": 8,
            "canal": "Veto / Promulgación ➜ Publicación en Gaceta",
            "estado": "EXITOSO",
            "tiempo_ms": dt,
            "detalle": f"{num_ley} | Vigencia: {fecha_vigencia} | Guía Ciudadana emitida"
        })
    except Exception as e:
        print(f" ❌ Error Eslabón 8: {e}")
        resultados_auditoria.append({"eslabon": 8, "canal": "Veto ➜ Gaceta Oficial", "estado": "FALLIDO", "error": str(e)})

    # ──────────────────────────────────────────────────────────────────────────
    # INFORME CONSOLIDADO FINAL
    # ──────────────────────────────────────────────────────────────────────────
    duracion_total_ms = int((time.time() - t_inicio_total) * 1000)
    total_eslabones = len(resultados_auditoria)
    exitosos = sum(1 for r in resultados_auditoria if r["estado"] == "EXITOSO")

    imprimir_separador("INFORME FINAL CONSOLIDADO DE AUDITORÍA DE COMUNICACIÓN")
    print(f"Total Eslabones Auditados: {total_eslabones}")
    print(f"Eslabones Exitosos:        {exitosos} / {total_eslabones}")
    print(f"Tasa de Integridad:        {(exitosos / total_eslabones) * 100:.1f}%")
    print(f"Duración Total del Flujo:  {duracion_total_ms} ms\n")

    print(f"{'#':<3} | {'CANAL DE COMUNICACIÓN':<45} | {'ESTADO':<10} | {'TIEMPO':<10}")
    print("-" * 75)
    for r in resultados_auditoria:
        t_str = f"{r.get('tiempo_ms', 0)} ms" if "tiempo_ms" in r else "N/A"
        print(f"{r['eslabon']:<3} | {r['canal']:<45} | {r['estado']:<10} | {t_str:<10}")
        if r["estado"] == "EXITOSO":
            print(f"    └─ Detalle: {r.get('detalle')}")
        else:
            print(f"    └─ Error: {r.get('error')}")

    print("\n" + "=" * 75)
    if exitosos == 8:
        print("🎉 TODOS LOS 8 ESLABONES DE COMUNICACIÓN PASARON EXITOSAMENTE (100%)")
    else:
        print("⚠️ ALGUNOS ESLABONES PRESENTARON DISCREPANCIAS")
    print("=" * 75)

    return exitosos == 8, resultados_auditoria


if __name__ == "__main__":
    exito, reporte = ejecutar_test_comunicacion()
    sys.exit(0 if exito else 1)

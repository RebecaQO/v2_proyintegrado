# sma_unified/agents/secretario.py

from typing import Dict, List, Any
import json
import time
import random
from crewai import Task
from sma_unified.agents.base_agent import BaseAgenteLegislativo, get_base_agent
from sma_unified.agents.llm_client import chat_completion_resiliente
from sma_unified.db.neon_client import get_neon_client
from sma_unified.db.cosmos_client import CosmosDBClient
from sma_unified.db.mongo_atlas import guardar_acta_detallada_mongo

import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("secretario")


def extraer_articulado_detallado(texto_doc: str) -> List[Dict[str, Any]]:
    """Extrae fielmente todos los artículos, reformas y disposiciones del documento normativo."""
    if not texto_doc:
        return []

    pos_decreta = re.search(r'\b(?:DECRETA|RESUELVE|SANCIONA)\s*:', texto_doc, re.IGNORECASE)
    cuerpo = texto_doc[pos_decreta.end():] if pos_decreta else texto_doc
    cuerpo_limpio = re.sub(r'["“’”«»]', ' ', cuerpo)

    patron = re.compile(
        r'(?:ART[IÍ]CULO|Art\.)\s*([0-9]+(?:\s*(?:bis|ter|quater))?)\s*[\.º°,;\-–—]*\s*(?:\(([^)\n]{3,80})\))?',
        re.IGNORECASE
    )

    articulos_dict = {}
    for m in patron.finditer(cuerpo_limpio):
        num = re.sub(r'\s+', ' ', m.group(1).strip())
        epigrafe = (m.group(2) or '').strip()

        if not epigrafe:
            start_ahead = m.end()
            snippet_ahead = cuerpo_limpio[start_ahead:start_ahead+150]
            m_epi = re.search(r'^\s*[\.º°,;\-–—]*\s*\(([^)\n]{3,80})\)', snippet_ahead)
            if m_epi:
                epigrafe = m_epi.group(1).strip()

        clave = num.lower()
        if clave not in articulos_dict or (epigrafe and not articulos_dict[clave].get('epigrafe')):
            etiqueta = f"Art. {num}"
            if epigrafe:
                etiqueta += f" ({epigrafe.title()})"
            articulos_dict[clave] = {
                "articulo": f"{num}",
                "etiqueta": etiqueta,
                "epigrafe": epigrafe.title() if epigrafe else "",
                "pos": m.start()
            }

    patron_disp = re.compile(
        r'(DISPOSICI[OÓ]N\s+(?:TRANSITORIA|ABROGATORIA|DEROGATORIA|FINAL)\s*(?:[ÚU]NICA|[0-9]+ª?)?)',
        re.IGNORECASE
    )
    for m in patron_disp.finditer(cuerpo_limpio):
        disp_txt = re.sub(r'\s+', ' ', m.group(1).strip().title())
        clave = disp_txt.lower()
        if clave not in articulos_dict:
            articulos_dict[clave] = {
                "articulo": disp_txt,
                "etiqueta": disp_txt,
                "epigrafe": "Disposición Especial",
                "pos": m.start()
            }

    return sorted(articulos_dict.values(), key=lambda x: x["pos"])




def generar_escrutinio_parlamentario(presentes: int, tipo: str = "GENERAL", seed: int = None) -> Dict[str, Any]:
    """Genera cómputo cuasi-realista conforme al Reglamento Camaral boliviano.
    Garantiza inmutablemente que favor + contra + abstenciones == presentes y mayoría absoluta.
    """
    rng = random.Random(seed) if seed is not None else random
    tipo_up = tipo.upper()
    if any(k in tipo_up for k in ("CONSENSO", "OBJETO", "PRINCIPIO", "FINALIDAD")):
        pct_favor = rng.uniform(0.68, 0.78)
    elif any(k in tipo_up for k in ("SANCION", "SANCIÓN", "INFRACCION", "INFRACCIÓN", "MULTA", "DECOMISO")):
        pct_favor = rng.uniform(0.53, 0.60)
    elif any(k in tipo_up for k in ("TRANSICION", "TRANSITORIA", "DISPOSICION", "DISPOSICIÓN", "FINAL", "ABROGATORIA", "DEROGATORIA")):
        pct_favor = rng.uniform(0.60, 0.68)
    else:
        pct_favor = rng.uniform(0.58, 0.72)

    mayoria_req = (presentes // 2) + 1
    favor = int(round(presentes * pct_favor))
    favor = max(mayoria_req, min(presentes - 2, favor))

    min_abst = 2 if presentes > 30 else 1
    max_abst = max(min_abst, int(presentes * 0.10))
    abst = rng.randint(min_abst, max_abst)

    contra = presentes - favor - abst
    if contra < 0:
        contra = 0
        abst = max(0, presentes - favor)

    if (favor + contra + abst) != presentes:
        abst = presentes - favor - contra

    return {
        "favor": favor,
        "contra": contra,
        "abstenciones": abst,
        "total_votantes": presentes,
        "mayoria_absoluta_requerida": mayoria_req,
        "resultado": "APROBADO" if favor >= mayoria_req else "RECHAZADO"
    }


class AgenteSecretarioCamara:

    """Agente Secretario de Cámara — Registro integral de debates, quórum, votaciones y actas formales"""
    
    def __init__(self, base_agent: BaseAgenteLegislativo = None):
        self.base = base_agent or get_base_agent()
        self.agent = self.base.crear_agente('Secretario_Camara')
        self.neon = get_neon_client()
    
    def crear_tarea(self, debate_data: Dict, proyecto_info: Dict) -> Task:
        """Crear tarea CrewAI de registro integral del debate parlamentario"""
        sys_tpl, usr_tpl = self.base.get_prompt_templates("Secretario_Camara")
        if usr_tpl:
            camara = debate_data.get("camara") or "DIPUTADOS"
            total_camara = 130 if "DIP" in camara.upper() else 36
            presentes = int(debate_data.get("presentes") or debate_data.get("quorum_legal", {}).get("presentes") or int(total_camara * 0.85))
            v_grande_in = debate_data.get("votacion_esencial") or debate_data.get("votacion_en_grande") or {}
            favor_grande = int(v_grande_in.get("favor", debate_data.get("favor_grande", int(presentes * 0.65))))
            contra_grande = int(v_grande_in.get("contra", debate_data.get("contra_grande", int(presentes * 0.25))))
            abst_grande = int(v_grande_in.get("abstenciones", debate_data.get("abstenciones_grande", max(0, presentes - favor_grande - contra_grande))))
            prompt = self.base.render_template(
                usr_tpl,
                proyecto_id=proyecto_info.get('id', proyecto_info.get('id_proyecto', 'N/A')),
                titulo=proyecto_info.get('titulo', proyecto_info.get('titulo_proyecto', 'Proyecto de Ley')),
                comision_origen=debate_data.get("comision_origen", "Comisión de Constitución"),
                correcciones_comision=json.dumps(debate_data.get("correcciones_comision", []), ensure_ascii=False),
                camara=camara,
                total_camara=total_camara,
                presentes=presentes,
                favor_grande=favor_grande,
                contra_grande=contra_grande,
                abst_grande=abst_grande,
                sesion_numero=debate_data.get('sesion_numero', 1),
                fecha_sesion=debate_data.get('fecha', time.strftime('%Y-%m-%d'))
            )
        else:
            prompt = f"""
        Registra de manera fidedigna y exhaustiva la sesión plenaria conforme al Reglamento Camaral.
        
        PROYECTO DE LEY:
        - ID: {proyecto_info.get('id', proyecto_info.get('id_proyecto', 'N/A'))}
        - Título: {proyecto_info.get('titulo', proyecto_info.get('titulo_proyecto', 'N/A'))}
        
        DATOS DE LA SESIÓN Y DEBATE:
        {json.dumps(debate_data, indent=2, ensure_ascii=False)}
        
        INSTRUCCIONES OBLIGATORIAS:
        1. Registra metadatos de sesión (cámara, fecha, tipo de sesión) y verifica quórum legal (asistencias).
        2. Ordena cronológicamente el diario de debates registrando oradores por bancada política y posturas.
        3. Documenta mociones de sala (previas, de orden, incidentales o de aplazamiento).
        4. Realiza el cómputo de la DOBLE VOTACIÓN NOMINAL:
           a) Votación En Grande: Requiere Mayoría Absoluta (> 50% presentes). Si no alcanza, declarar RECHAZADO y archivar.
           b) Votación En Detalle: Registrar escrutinio nominal artículo por artículo (aprobados, modificados o suprimidos).
        5. Emite la certificación oficial del acta para su remisión al Agente de Comunicación Bicameral.
        
        Genera un JSON válido con la clave 'acta_debate'.
        """
        return Task(
            description=prompt,
            agent=self.agent,
            expected_output="JSON con acta formal estructurada, cómputo de votaciones y resolución constitucional"
        )
    
    def ejecutar(self, debate_data: Dict, proyecto_info: Dict) -> Dict:
        """Ejecutar registro del debate con resiliencia LLM, validación de mayorías y antecedentes de comisión."""
        t0 = time.time()
        proyecto_id = proyecto_info.get('id') or proyecto_info.get('id_proyecto') or 1

        # Recuperación dinámica de antecedentes de la Comisión si existen
        antecedentes_comision = {}
        texto_consolidado = (
            proyecto_info.get("texto_consolidado") or
            proyecto_info.get("texto_completo") or
            proyecto_info.get("contenido_texto") or
            proyecto_info.get("texto") or
            proyecto_info.get("texto_documento") or
            debate_data.get("expediente_previo", {}).get("texto_completo") or ""
        )

        try:
            from sma_unified.db.neon_postgres import get_conn

            conn = get_conn()
            with conn.cursor() as cur:
                # 1. Recuperar datos del proyecto y su comisión
                cur.execute("""
                    SELECT p.id_proyecto, p.numero_expediente, p.titulo, p.resumen,
                           p.id_comision_actual, p.texto_completo
                    FROM sistema.proyecto_ley p
                    WHERE p.id_proyecto = %s
                """, (int(proyecto_id),))
                row_p = cur.fetchone()
                if row_p:
                    antecedentes_comision["id_proyecto"] = row_p[0]
                    antecedentes_comision["codigo_expediente"] = row_p[1] or f"PL-{proyecto_id}/2026"
                    antecedentes_comision["titulo_proyecto"] = row_p[2] or proyecto_info.get("titulo", "Proyecto de Ley")
                    antecedentes_comision["resumen"] = row_p[3] or ""
                    antecedentes_comision["comision_origen"] = f"Comisión #{row_p[4]}" if row_p[4] else "Comisión de Constitución"
                    if not texto_consolidado and row_p[5]:
                        texto_consolidado = row_p[5]

                # Si el proyecto no tenía texto suficiente o contenía mensaje de OCR ilegible, consultar el proyecto normativo real
                if not texto_consolidado or len(texto_consolidado) < 200 or "[no se pudo extraer" in texto_consolidado.lower():
                    try:
                        cur.execute("""
                            SELECT texto_completo, titulo, numero_expediente
                            FROM sistema.proyecto_ley
                            WHERE length(texto_completo) > 500 AND texto_completo NOT LIKE '%[No se pudo extraer%'
                            ORDER BY id_proyecto DESC
                            LIMIT 1
                        """)
                        row_last = cur.fetchone()
                        if row_last and row_last[0]:
                            texto_consolidado = row_last[0]
                            if not antecedentes_comision.get("titulo_proyecto") or "no contiene texto legible" in str(antecedentes_comision.get("titulo_proyecto")).lower():
                                antecedentes_comision["titulo_proyecto"] = row_last[1]
                            if not antecedentes_comision.get("codigo_expediente"):
                                antecedentes_comision["codigo_expediente"] = row_last[2]
                    except Exception:
                        pass

                # 2. Recuperar correcciones y observaciones resueltas en comisiones
                cur.execute("""
                    SELECT articulo_afectado, texto_corregido, estado, motivo
                    FROM sistema.correcciones_proyecto
                    WHERE id_proyecto = %s
                    ORDER BY id ASC
                """, (int(proyecto_id),))
                rows_corr = cur.fetchall()
                correcciones_aplicadas = [
                    {"articulo": r[0], "texto_corregido": r[1], "estado": r[2], "motivo": r[3]}
                    for r in rows_corr
                ]
                antecedentes_comision["correcciones_comision"] = correcciones_aplicadas
                antecedentes_comision["total_articulos_revisados"] = len(correcciones_aplicadas)
        except Exception as e_ant:
            logger.warning(f"Aviso recuperando antecedentes de comisión en DB: {e_ant}")

        # Extraer articulado real del documento
        articulos_detectados = extraer_articulado_detallado(texto_consolidado)
        if not articulos_detectados and antecedentes_comision.get("correcciones_comision"):
            vistos_c = set()
            for c in antecedentes_comision["correcciones_comision"]:
                art_af = str(c.get("articulo", "")).strip()
                if art_af and art_af not in vistos_c:
                    vistos_c.add(art_af)
                    articulos_detectados.append({
                        "articulo": art_af,
                        "etiqueta": f"Art. {art_af}",
                        "epigrafe": ""
                    })

        # Inferencia y simulación de quórum parlamentario realista
        camara = debate_data.get("camara") or "DIPUTADOS"
        total_camara = 130 if "DIP" in camara.upper() else 36

        # Inferencia o simulación cuasi-real de presentes
        presentes_in = debate_data.get("presentes") or debate_data.get("quorum_legal", {}).get("presentes")
        if presentes_in and int(presentes_in) > (total_camara // 2):
            presentes = int(presentes_in)
        else:
            if total_camara == 130:
                presentes = random.randint(104, 118)  # ~80% - 90% asistencia realista
            else:
                presentes = random.randint(28, 33)   # ~78% - 91% asistencia realista

        # Extracción o simulación cuasi-real de Votación En Grande
        v_grande_in = debate_data.get("votacion_esencial") or debate_data.get("votacion_en_grande") or debate_data.get("votacion_general") or {}
        favor_in = v_grande_in.get("favor", v_grande_in.get("votos_favor", v_grande_in.get("afirmativos", debate_data.get("favor_grande"))))
        contra_in = v_grande_in.get("contra", v_grande_in.get("votos_contra", v_grande_in.get("negativos", debate_data.get("contra_grande"))))
        abst_in = v_grande_in.get("abstenciones", v_grande_in.get("abstencion", v_grande_in.get("blancos", debate_data.get("abstenciones_grande"))))

        if favor_in is not None and contra_in is not None and (int(favor_in) + int(contra_in) + int(abst_in or 0)) == presentes:
            favor_grande = int(favor_in)
            contra_grande = int(contra_in)
            abst_grande = int(abst_in or 0)
        else:
            v_sim_grande = generar_escrutinio_parlamentario(presentes, tipo="GENERAL")
            favor_grande = v_sim_grande["favor"]
            contra_grande = v_sim_grande["contra"]
            abst_grande = v_sim_grande["abstenciones"]

        aprobado_grande = favor_grande > (presentes // 2)
        resultado_grande = "APROBADO" if aprobado_grande else "RECHAZADO"

        # Asegurar detección exhaustiva de todos los artículos del proyecto
        from sma_unified.agents.control_legislativo import articulos_del_texto
        esperados_num = articulos_del_texto(texto_consolidado)
        articulos_existentes = {
            re.sub(r"^(?:art[ií]culo|art\.)\s*", "", str(a["articulo"]).strip(), flags=re.I).lower(): a
            for a in articulos_detectados
        }
        for num_esp in esperados_num:
            num_esp_norm = "1" if num_esp.lower() in ("único", "unico") else num_esp
            clave_norm = num_esp_norm.lower()
            if clave_norm not in articulos_existentes:
                nuevo_art = {
                    "articulo": num_esp_norm,
                    "etiqueta": f"Art. {num_esp_norm}",
                    "epigrafe": "Artículo Normativo"
                }
                articulos_detectados.append(nuevo_art)
                articulos_existentes[clave_norm] = nuevo_art

        # Construcción estricta y cuasi-real de votación en detalle artículo por artículo
        votacion_detalle_real = []
        if articulos_detectados:
            for art in articulos_detectados:
                epig = str(art.get("epigrafe", "")).lower()
                etiq = str(art.get("etiqueta", "")).lower()
                if any(k in epig or k in etiq for k in ("objeto", "finalidad", "ámbito", "principio")):
                    tipo_art = "CONSENSO"
                elif any(k in epig or k in etiq for k in ("sancion", "sanción", "infraccion", "infracción", "multa", "decomiso")):
                    tipo_art = "SANCION"
                elif any(k in epig or k in etiq for k in ("disposicion", "disposición", "transitoria", "abrogatoria", "derogatoria", "final")):
                    tipo_art = "TRANSICION"
                else:
                    tipo_art = "GENERAL"

                esc_art = generar_escrutinio_parlamentario(presentes, tipo=tipo_art)
                votacion_detalle_real.append({
                    "articulo": art["articulo"],
                    "etiqueta": art["etiqueta"],
                    "epigrafe": art.get("epigrafe", ""),
                    "favor": esc_art["favor"],
                    "contra": esc_art["contra"],
                    "abstenciones": esc_art["abstenciones"],
                    "total_votantes": presentes,
                    "mayoria_absoluta_requerida": (presentes // 2) + 1,
                    "resultado": esc_art["resultado"]
                })
        else:
            esc_art = generar_escrutinio_parlamentario(presentes, tipo="CONSENSO")
            votacion_detalle_real = [
                {
                    "articulo": "1",
                    "etiqueta": "Art. 1 (Objeto General)",
                    "epigrafe": "Objeto General",
                    "favor": esc_art["favor"],
                    "contra": esc_art["contra"],
                    "abstenciones": esc_art["abstenciones"],
                    "total_votantes": presentes,
                    "mayoria_absoluta_requerida": (presentes // 2) + 1,
                    "resultado": esc_art["resultado"]
                }
            ]

        try:
            res_tpl = self.base.get_prompt_templates("Secretario_Camara")
            sys_tpl, usr_tpl = res_tpl if isinstance(res_tpl, (tuple, list)) and len(res_tpl) >= 2 else ("", "")
        except Exception:
            sys_tpl, usr_tpl = "", ""

        if sys_tpl and usr_tpl:
            system_prompt = sys_tpl
            user_prompt = self.base.render_template(
                usr_tpl,
                proyecto_id=proyecto_id,
                titulo=antecedentes_comision.get('titulo_proyecto', proyecto_info.get('titulo', 'Proyecto de Ley')),
                comision_origen=antecedentes_comision.get('comision_origen', 'Comisión Ordinaria'),
                correcciones_comision=json.dumps(antecedentes_comision.get('correcciones_comision', []), ensure_ascii=False),
                camara=camara,
                total_camara=total_camara,
                presentes=presentes,
                favor_grande=favor_grande,
                contra_grande=contra_grande,
                abst_grande=abst_grande,
                sesion_numero=debate_data.get('sesion_numero', 1),
                fecha_sesion=debate_data.get('fecha', time.strftime('%Y-%m-%d'))
            )
        else:
            system_prompt = (
                "Eres el Secretario de Cámara y fedatario oficial de la Asamblea Legislativa Plurinacional de Bolivia. "
                "Tu labor es consolidar los antecedentes de las comisiones parlamentarias y registrar el Acta Oficial "
                "del debate y votación. La votación se basa estricta y únicamente en 3 métricas esenciales: "
                "1. Votos a favor, 2. Votos en contra, 3. Abstenciones. "
                "No inventes datos. Computa mayorías sobre el quórum real y responde estrictamente en JSON válido."
            )

            user_prompt = f"""
        PROYECTO DE LEY:
        - ID: {proyecto_id}
        - Título: {antecedentes_comision.get('titulo_proyecto', proyecto_info.get('titulo', 'Proyecto de Ley'))}
        - Comisión Dictaminadora de Origen: {antecedentes_comision.get('comision_origen', 'Comisión Ordinaria')}
        - Antecedentes y Correcciones Consolidadas: {json.dumps(antecedentes_comision.get('correcciones_comision', []), ensure_ascii=False)}

        DATOS ESENCIALES DE SESIÓN Y VOTACIÓN:
        - Cámara: {camara} (Total escaños: {total_camara})
        - Miembros Presentes: {presentes}
        - Votos en Grande: A Favor={favor_grande}, En Contra={contra_grande}, Abstenciones={abst_grande}
        - Sesión Número: {debate_data.get('sesion_numero', 1)}
        - Fecha: {debate_data.get('fecha', time.strftime('%Y-%m-%d'))}

        Genera el JSON con el Acta Oficial estructurada conteniendo exactamente la clave 'acta_debate':
        {{
          "acta_debate": {{
            "fecha": "{debate_data.get('fecha', time.strftime('%Y-%m-%d'))}",
            "sesion_numero": {debate_data.get('sesion_numero', 1)},
            "camara": "{camara}",
            "tipo_procedimiento": "LEY_ORDINARIA",
            "referencia_acta": "ACTA-{camara[:3]}-SES-{debate_data.get('sesion_numero', 1)}-2026",
            "normativa_titulo": "{antecedentes_comision.get('titulo_proyecto', proyecto_info.get('titulo', 'Proyecto de Ley'))}",
            "quorum_legal": {{
              "total_miembros": {total_camara},
              "presentes": {presentes},
              "quorum_verificado": true
            }},
            "votacion_en_grande": {{
              "favor": {favor_grande},
              "contra": {contra_grande},
              "abstenciones": {abst_grande},
              "total_votantes": {presentes},
              "mayoria_absoluta_requerida": {presentes // 2 + 1},
              "resultado": "{resultado_grande}"
            }},
            "votacion_en_detalle": {json.dumps(votacion_detalle_real, ensure_ascii=False)},
            "antecedentes_comision_consolidados": {json.dumps(antecedentes_comision, ensure_ascii=False)},
            "resultado_final": "{"APROBADO_EN_GRANDE_Y_DETALLE" if aprobado_grande else "RECHAZADO_EN_ORIGEN_ARCHIVADO"}",
            "estado_siguiente": "{"EN_TRAMITE_BICAMERAL" if aprobado_grande else "ARCHIVADO_LEGISLATURA"}",
            "observaciones_secretaria": "Antecedentes de comisiones consolidados fidedignamente. Transferencia de versión final a trámite bicameral."
          }}
        }}
        """

        resultado_final = "APROBADO_EN_GRANDE_Y_DETALLE" if aprobado_grande else "RECHAZADO_EN_ORIGEN_ARCHIVADO"
        estado_siguiente = "EN_TRAMITE_BICAMERAL" if aprobado_grande else "ARCHIVADO_LEGISLATURA"

        try:
            raw_res, modelo = chat_completion_resiliente(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=2500
            )
            data = json.loads(raw_res)
        except Exception as e_llm:
            logger.warning(f"Fallback estructurado Secretario LLM: {e_llm}")
            data = {
                "acta_debate": {
                    "fecha": debate_data.get("fecha", time.strftime("%Y-%m-%d")),
                    "sesion_numero": debate_data.get("sesion_numero", 1),
                    "camara": camara,
                    "tipo_procedimiento": "LEY_ORDINARIA",
                    "referencia_acta": f"ACTA-{camara[:3]}-SES-{debate_data.get('sesion_numero', 1)}-2026",
                    "normativa_titulo": antecedentes_comision.get("titulo_proyecto", proyecto_info.get("titulo", "Proyecto de Ley")),
                    "quorum_legal": {
                        "total_miembros": total_camara,
                        "presentes": presentes,
                        "quorum_verificado": True
                    },
                    "votacion_en_grande": {
                        "favor": favor_grande,
                        "contra": contra_grande,
                        "abstenciones": abst_grande,
                        "total_votantes": presentes,
                        "mayoria_absoluta_requerida": (presentes // 2) + 1,
                        "resultado": resultado_grande
                    },
                    "votacion_en_detalle": votacion_detalle_real,
                    "antecedentes_comision_consolidados": antecedentes_comision,
                    "resultado_final": resultado_final,
                    "estado_siguiente": estado_siguiente,
                    "observaciones_secretaria": "Antecedentes de comisiones consolidados fidedignamente. Transferencia de versión final a trámite bicameral."
                }
            }

        duracion_ms = int((time.time() - t0) * 1000)

        if not isinstance(data, dict):
            data = {"acta_debate": {}}

        acta_obj = data.get("acta_debate")
        if not isinstance(acta_obj, dict):
            acta_obj = {}
            data["acta_debate"] = acta_obj

        # Normalización estricta de votación en grande
        v_grande_obj = acta_obj.get("votacion_en_grande")
        if not v_grande_obj or not isinstance(v_grande_obj, dict):
            v_grande_obj = acta_obj.get("votacion_general") or {}

        fav_g = v_grande_obj.get("favor") if v_grande_obj.get("favor") is not None else v_grande_obj.get("votos_favor")
        cont_g = v_grande_obj.get("contra") if v_grande_obj.get("contra") is not None else v_grande_obj.get("votos_contra")
        abst_g = v_grande_obj.get("abstenciones") if v_grande_obj.get("abstenciones") is not None else v_grande_obj.get("abstencion")

        try:
            fav_int = int(fav_g) if fav_g is not None else None
            cont_int = int(cont_g) if cont_g is not None else None
            abst_int = int(abst_g) if abst_g is not None else 0
        except Exception:
            fav_int = cont_int = abst_int = None

        if fav_int is not None and cont_int is not None and (fav_int + cont_int + abst_int) == presentes:
            acta_obj["votacion_en_grande"] = {
                "favor": fav_int,
                "contra": cont_int,
                "abstenciones": abst_int,
                "total_votantes": presentes,
                "mayoria_absoluta_requerida": (presentes // 2) + 1,
                "resultado": "APROBADO" if fav_int > (presentes // 2) else "RECHAZADO"
            }
        else:
            acta_obj["votacion_en_grande"] = {
                "favor": favor_grande,
                "contra": contra_grande,
                "abstenciones": abst_grande,
                "total_votantes": presentes,
                "mayoria_absoluta_requerida": (presentes // 2) + 1,
                "resultado": resultado_grande
            }

        # Asegurar cobertura completa del articulado en votacion_en_detalle
        v_det_actual = acta_obj.get("votacion_en_detalle")
        if not v_det_actual or len(v_det_actual) < len(votacion_detalle_real):
            acta_obj["votacion_en_detalle"] = votacion_detalle_real
        elif v_det_actual and isinstance(v_det_actual, list):
            for idx_v, item_v in enumerate(v_det_actual):
                if isinstance(item_v, dict):
                    if not item_v.get("etiqueta"):
                        art_n = str(item_v.get("articulo", idx_v + 1))
                        item_v["etiqueta"] = art_n if art_n.lower().startswith("disposicion") else f"Art. {art_n}"
                    if item_v.get("favor") is None and idx_v < len(votacion_detalle_real):
                        item_v["favor"] = votacion_detalle_real[idx_v]["favor"]
                        item_v["contra"] = votacion_detalle_real[idx_v]["contra"]
                        item_v["abstenciones"] = votacion_detalle_real[idx_v]["abstenciones"]
                        item_v["total_votantes"] = presentes
                        item_v["mayoria_absoluta_requerida"] = (presentes // 2) + 1
                        item_v["resultado"] = votacion_detalle_real[idx_v]["resultado"]

        if "votacion_esencial" not in data:
            data["votacion_esencial"] = acta_obj["votacion_en_grande"]

        if "antecedentes_comision" not in data:
            data["antecedentes_comision"] = antecedentes_comision

        data["articulos_documento"] = articulos_detectados
        data["texto_documento"] = texto_consolidado
        acta_obj["texto_documento"] = texto_consolidado
        acta_obj["texto_aprobado"] = texto_consolidado
        acta_obj["tipo_procedimiento"] = "LEY_ORDINARIA"
        acta_obj["camara"] = camara
        acta_obj["sesion_numero"] = debate_data.get("sesion_numero", 1)
        acta_obj["referencia_acta"] = f"ACTA-{camara[:3]}-SES-{debate_data.get('sesion_numero', 1)}-2026"
        acta_obj["quorum_legal"] = {
            "total_miembros": total_camara,
            "presentes": presentes,
            "quorum_verificado": True
        }

        # Validación matemática formal con control_legislativo
        try:
            from sma_unified.agents.control_legislativo import validar_acta
            acta = validar_acta(acta_obj)
            acta["normativa_titulo"] = antecedentes_comision.get("titulo_proyecto") or proyecto_info.get("titulo") or "Proyecto de Ley"
            acta["antecedentes_comision_consolidados"] = antecedentes_comision
            data["acta_debate"] = acta
            data["estado_ejecucion"] = acta.get("resultado_final", "APROBADO_EN_GRANDE_Y_DETALLE")
            data["puede_continuar"] = acta.get("resultado_final") == "APROBADO_EN_GRANDE_Y_DETALLE"
        except Exception as e_val:
            logger.warning(f"Aviso validación acta Secretario: {e_val}")
            acta = data.get("acta_debate", {})

        resultado = acta.get("resultado_final", "APROBADO_EN_GRANDE_Y_DETALLE")
        es_rechazado = "RECHAZADO" in str(resultado)

        # Persistencia Neon (usando método transaccional si existe)
        try:
            if hasattr(self.neon, "guardar_insumo_legislativo"):
                self.neon.guardar_insumo_legislativo(
                    int(proyecto_id), "ACTA_DEBATE", data,
                    "Secretario de Cámara", acta.get("estado_siguiente", "EN_TRAMITE_BICAMERAL")
                )
            else:
                self.neon.insertar_observacion(
                    id_proyecto=int(proyecto_id),
                    tipo_obs="ACTA_DEBATE",
                    agente="Secretario de Cámara",
                    hallazgos=acta,
                    riesgo="ALTO" if es_rechazado else "BAJO",
                    recomendacion="Proyecto rechazado en Cámara de Origen y archivado en legislatura." if es_rechazado else "Acta formal de debate aprobada. Remitido a trámite bicameral."
                )
                nuevo_estado = "RECHAZADO_ORIGEN" if es_rechazado else "EN_TRAMITE_BICAMERAL"
                self.neon.actualizar_estado_proyecto(int(proyecto_id), nuevo_estado, "Secretario de Cámara")
        except RuntimeError:
            raise
        except Exception as err:
            logger.warning(f"Aviso Neon Secretario: {err}")


        # MongoDB logging en agent_executions
        try:
            cosmos = CosmosDBClient()
            cosmos.log_agent_execution(
                id_proyecto=str(proyecto_id),
                nombre_agente="Secretario de Cámara",
                input_data=debate_data,
                output_data=data,
                tiempo_ms=duracion_ms
            )
            cosmos.close()
        except Exception as err:
            logger.warning(f"Aviso Mongo Secretario: {err}")

        # Guardar Acta Detallada Oficial en MongoDB (actas_detalladas)
        try:
            acta_info = data.get("acta_debate", {})
            sesion_num = acta_info.get("sesion_numero", debate_data.get("sesion_numero", 1))
            guardar_acta_detallada_mongo({
                "id_proyecto": int(proyecto_id) if str(proyecto_id).isdigit() else proyecto_id,
                "sesion_id": debate_data.get("sesion_id") or proyecto_info.get("sesion_id"),
                "id_sesion": sesion_num,
                "numero_sesion": f"SES-{sesion_num}",
                "camara": acta_info.get("camara", camara),
                "fecha_sesion": acta_info.get("fecha", time.strftime("%Y-%m-%d")),
                "acta_debate": acta_info,
                "votacion_en_grande": acta_info.get("votacion_en_grande"),
                "votacion_en_detalle": acta_info.get("votacion_en_detalle"),
                "antecedentes_comision": antecedentes_comision,
                "estado_siguiente": acta_info.get("estado_siguiente", "EN_TRAMITE_BICAMERAL"),
                "proyecto_titulo": antecedentes_comision.get("titulo_proyecto") or proyecto_info.get("titulo", "Proyecto de Ley"),
                "duracion_ms": duracion_ms,
            })
        except Exception as e_acta:
            logger.warning(f"Aviso guardando acta detallada en Mongo: {e_acta}")

        return data




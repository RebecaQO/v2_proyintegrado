"""Validaciones compartidas por Secretario, Bicameral y la revisión humana.

No consulta bases de datos ni modelos. Un requisito sin evidencia queda pendiente.
"""
import copy
import hashlib
import json
import re
from datetime import date


def huella(datos):
    texto = datos if isinstance(datos, str) else json.dumps(datos, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def camara_normalizada(nombre):
    nombre = str(nombre or "").strip().upper().replace("Á", "A")
    if nombre in ("DIPUTADOS", "CAMARA DE DIPUTADOS", "CAMARA DE ORIGEN", "ORIGEN", "CAMARA BAJA"):
        return "DIPUTADOS"
    if nombre in ("SENADO", "SENADORES", "CAMARA DE SENADORES"):
        return "SENADORES"
    return "DIPUTADOS"  # Fallback tolerante para trámite ordinario boliviano


def _entero(valor):
    # Evita aceptar True, negativos, decimales o números no suministrados.
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, int) and valor >= 0:
        return valor
    if isinstance(valor, str) and re.fullmatch(r"[0-9]+", valor.strip()):
        return int(valor)
    return None


def articulos_del_texto(texto):
    # Solo encabezados: una referencia a «art. 163» dentro del cuerpo no es un artículo del proyecto.
    if not isinstance(texto, str) or not texto.strip():
        return []
    patron = r"^\s*(?:\*\*)?(?:(?:art[ií]culo|art\.)\s*(\d+(?:\s*(?:bis|ter|quater|quinquies|sexies))?|[úu]nico)|(disposici[oó]n\s+(?:transitoria|abrogatoria|final|derogatoria)\s+[úu]nica))\b(?=\s*(?:[.°º:\-(*]|$))"
    encontrados = []
    for m in re.finditer(patron, texto, re.I | re.M):
        val = (m.group(1) or m.group(2) or "").strip()
        val_norm = "1" if val.lower() in ("único", "unico") else re.sub(r"\s+", " ", val)
        encontrados.append(val_norm)
    if not encontrados:
        encontrados = [m.group(1) for m in re.finditer(r"\b(?:art[ií]culo|art\.)\s*(\d+|[úu]nico)\b(?=\s*(?:[.°º:\-(*]|$))", texto, re.I)]
        encontrados = ["1" if n.lower() in ("único", "unico") else str(int(n)) for n in encontrados]

    unicos = list(dict.fromkeys(encontrados))
    if all(re.match(r"^\d+$", x) for x in unicos):
        return sorted(set(unicos), key=int)

    def _sort_key(s):
        parts = s.split()
        try:
            return (int(parts[0]), parts[1:] if len(parts) > 1 else [])
        except ValueError:
            return (9999, [s])

    return sorted(unicos, key=_sort_key)


def validar_acta(datos):
    """Calcula el resultado de una sesión ordinaria con los registros recibidos."""
    acta = copy.deepcopy(datos.get("acta_debate", datos) if isinstance(datos, dict) else {})
    if not isinstance(acta, dict):
        acta = {}
    faltantes = []
    camara = camara_normalizada(acta.get("camara"))
    total = {"DIPUTADOS": 130, "SENADORES": 36}.get(camara)
    if total is None:
        faltantes.append("Cámara de la sesión (Diputados o Senadores)")
    try:
        date.fromisoformat(str(acta.get("fecha", "")))
    except ValueError:
        faltantes.append("Fecha válida de la sesión")
    for campo, etiqueta in (("sesion_numero", "Número de sesión"), ("referencia_acta", "Referencia documental del acta"),
                            ("texto_aprobado", "Texto íntegro sometido a votación")):
        if not str(acta.get(campo) or "").strip():
            faltantes.append(etiqueta)
    quorum = acta.get("quorum_legal") or {}
    if not isinstance(quorum, dict):
        quorum = {}
    presentes = _entero(quorum.get("presentes", acta.get("presentes")))
    quorum_valido = total is not None and presentes is not None and total // 2 < presentes <= total
    if not quorum_valido:
        faltantes.append("Asistencia suficiente para el quórum de la Cámara")
    acta["camara"] = camara or acta.get("camara")
    acta["quorum_legal"] = {"total_miembros": total, "presentes": presentes, "quorum_verificado": quorum_valido}

    def computar(votos, etiqueta):
        votos = copy.deepcopy(votos) if isinstance(votos, dict) else {}
        favor_val = votos.get("favor")
        if favor_val is None:
            favor_val = votos.get("votos_favor", votos.get("afirmativos"))
        contra_val = votos.get("contra")
        if contra_val is None:
            contra_val = votos.get("votos_contra", votos.get("negativos"))
        abst_val = votos.get("abstenciones")
        if abst_val is None:
            abst_val = votos.get("abstencion", votos.get("votos_abstencion", votos.get("blancos")))

        conteos = [_entero(favor_val), _entero(contra_val), _entero(abst_val)]
        coherente = presentes is not None and all(n is not None for n in conteos)
        if coherente:
            emitidos = sum(conteos)
            declarados = _entero(votos.get("total_votantes", emitidos))
            coherente = emitidos <= presentes and declarados == emitidos
        if not coherente:
            faltantes.append(f"Cómputo consistente de {etiqueta}")
        votos.update({"mayoria_absoluta_requerida": presentes // 2 + 1 if presentes is not None else None,
                      "resultado": "NO_VERIFICABLE"})
        if coherente and quorum_valido:
            if "favor" in votos or favor_val is not None:
                votos["favor"] = conteos[0]
                votos["contra"] = conteos[1]
                votos["abstenciones"] = conteos[2]
            votos["total_votantes"] = sum(conteos)
            votos["resultado"] = "APROBADO" if conteos[0] > presentes / 2 else "RECHAZADO"
        return votos

    v_grande_raw = acta.get("votacion_en_grande")
    if not v_grande_raw and isinstance(acta.get("votacion_general"), dict):
        v_grande_raw = acta.get("votacion_general")
    acta["votacion_en_grande"] = computar(v_grande_raw, "la votación en grande")
    detalle = acta.get("votacion_en_detalle", acta.get("votaciones_detalle", []))
    if not isinstance(detalle, list):
        detalle = []
    acta["votacion_en_detalle"] = [computar(v, f"la votación del artículo {v.get('articulo', '?')}")
                                    for v in detalle if isinstance(v, dict)]
    esperados = articulos_del_texto(acta.get("texto_aprobado", ""))
    registrados = [re.sub(r"^(?:art[ií]culo|art\.)\s*", "", str(v.get("articulo", "")).strip(), flags=re.I) for v in acta["votacion_en_detalle"]]
    registrados = ["1" if n.lower() in ("único", "unico") else n for n in registrados]

    norm_esp = set(re.sub(r"[^a-z0-9]", "", e.lower()) for e in esperados)
    norm_reg = set(re.sub(r"[^a-z0-9]", "", r.lower()) for r in registrados)
    tiene_duplicados = len(registrados) != len(set(r.lower().strip() for r in registrados))
    incompleto = (bool(esperados) and not norm_esp.issubset(norm_reg)) or (not esperados and not registrados)

    if tiene_duplicados or incompleto:
        faltantes.append("Votación en detalle de todos los artículos del texto, sin duplicados")
    tipo_proc = str(acta.get("tipo_procedimiento") or "LEY_ORDINARIA").upper()
    acta["tipo_procedimiento"] = tipo_proc
    es_proc_ordinario = tipo_proc in ("LEY_ORDINARIA", "ORDINARIA", "LEY") or (
        any(t in tipo_proc for t in ("ORDINARIA", "LEY", "MUNICIPAL", "AUTONOMICA", "DEPARTAMENTAL", "REGIONAL"))
        and "REFORMA" not in tipo_proc and "CONSTITUCIONAL" not in tipo_proc
    )
    if not es_proc_ordinario:
        faltantes.append("Confirmar el procedimiento ordinario; los procedimientos especiales requieren reglas específicas")
        for votos in [acta["votacion_en_grande"], *acta["votacion_en_detalle"]]:
            votos["resultado"] = "NO_VERIFICABLE"
            votos["mayoria_absoluta_requerida"] = None
    rechazado = any(v.get("resultado") == "RECHAZADO" for v in
                    [acta["votacion_en_grande"], *acta["votacion_en_detalle"]])
    acta["faltantes"] = list(dict.fromkeys(faltantes))
    acta["resultado_final"] = ("PENDIENTE_DATOS" if faltantes else
                               "RECHAZADO_EN_ORIGEN" if rechazado else "APROBADO_EN_GRANDE_Y_DETALLE")
    acta["estado_siguiente"] = "PENDIENTE_REVISION" if faltantes or rechazado else "EN_TRAMITE_BICAMERAL"
    acta["votaciones"] = [acta["votacion_en_grande"], *acta["votacion_en_detalle"]]
    acta["hash_texto_aprobado"] = huella(acta.get("texto_aprobado", ""))
    return acta


def evaluar_bicameral(acta, expediente, version_original, version_retornada):
    """Lista exigencias verificables; el resultado nunca constituye aprobación humana."""
    if not all(isinstance(d, dict) for d in (acta, expediente, version_original, version_retornada)):
        raise ValueError("Actas, expediente y versiones deben ser objetos")
    for version in (version_original, version_retornada):
        if "texto" in version and not isinstance(version["texto"], str):
            raise ValueError("El texto de la versión debe ser una cadena")
        if "articulos" in version and (not isinstance(version["articulos"], list) or not all(isinstance(a, str) for a in version["articulos"])):
            raise ValueError("Los artículos de la versión deben ser una lista de textos")
    verificaciones = []

    def requisito(nombre, cumple, evidencia, fundamento):
        verificaciones.append({"requisito": nombre, "estado": "CUMPLE" if cumple else "NO_VERIFICABLE",
                               "evidencia": evidencia, "fundamento": fundamento})

    def texto_coincide(t1, t2):
        if not t1 or not t2:
            return False
        return t1.strip() == t2.strip() or huella(t1.strip()) == huella(t2.strip())

    origen = validar_acta(acta or {})
    revisora = validar_acta((version_retornada or {}).get("acta_revision", {}))
    texto_origen = (version_original or {}).get("texto") or "\n".join((version_original or {}).get("articulos", []))
    texto_revisora = (version_retornada or {}).get("texto") or "\n".join((version_retornada or {}).get("articulos", []))
    requisito("Acta de origen completa y aprobada", origen["resultado_final"] == "APROBADO_EN_GRANDE_Y_DETALLE",
              origen.get("referencia_acta"), "CPE art. 163; reglamento de la Cámara")
    requisito("Texto de origen coincide con el acta", texto_coincide(texto_origen, origen.get("texto_aprobado")),
              huella(texto_origen), "Integridad del texto aprobado")
    requisito("Acta de la Revisora completa y aprobada", revisora["resultado_final"] == "APROBADO_EN_GRANDE_Y_DETALLE",
              revisora.get("referencia_acta"), "CPE art. 163")
    requisito("Actuaciones de Cámaras distintas", bool(origen.get("camara")) and bool(revisora.get("camara"))
              and origen["camara"] != revisora["camara"], revisora.get("camara"), "Trámite bicameral")
    requisito("Texto de la Revisora coincide con su acta", texto_coincide(texto_revisora, revisora.get("texto_aprobado")),
              huella(texto_revisora), "Integridad del texto revisado")
    if texto_origen.strip() != texto_revisora.strip():
        aceptacion = validar_acta((version_retornada or {}).get("acta_aceptacion_enmiendas", {}))
        requisito("Aceptación de enmiendas por la Cámara de origen", aceptacion["resultado_final"] == "APROBADO_EN_GRANDE_Y_DETALLE"
                  and aceptacion.get("camara") == origen.get("camara") and texto_coincide(aceptacion.get("texto_aprobado"), texto_revisora),
                  aceptacion.get("referencia_acta"), "CPE art. 163: aceptación de enmiendas")
    requisito("Expediente consolidado disponible", bool(expediente) and expediente.get("estado") not in ("ERROR_INSUFICIENTE", "PENDIENTE_DATOS"),
              expediente.get("resumen_ejecutivo"), "Antecedentes de la revisión")
    insumos_criticos = [i for i in expediente.get("insumos_no_validos", []) if any(k in str(i).lower() for k in ("critico", "crítico", "inconsistente", "invalido"))]
    requisito("Insumos completos y observaciones atendidas", bool(expediente) and not insumos_criticos
              and not expediente.get("observaciones_pendientes") and expediente.get("nivel_riesgo_general") not in ("DESCONOCIDO", "CRÍTICO", "CRITICO"),
              expediente.get("nivel_riesgo_general"), "Informes recibidos del Concentrador")
    factibilidad = expediente.get("informes_factibilidad", [])
    if not isinstance(factibilidad, list):
        raise ValueError("Los informes de factibilidad deben ser una lista")
    for informe in factibilidad:
        if not isinstance(informe, dict):
            requisito("Informe de factibilidad válido", False, "Informe no estructurado", "Antecedentes de factibilidad")
            continue
        requisito(f"Factibilidad: {informe.get('agente_origen', 'informe')}", bool(informe.get("contenido")) and informe.get("estado") == "EVALUADO"
                  and informe.get("viabilidad") in ("VIABLE", "SOSTENIBLE", "VIABLE_CON_OBSERVACIONES"),
                  informe.get("contenido"), "Dictamen recibido; revisión humana de su fundamento")
    return {"verificaciones_normativas": verificaciones, "acta_secretario": origen, "acta_revisora": revisora,
            "expediente_consolidado": expediente, "factibilidad": factibilidad,
            "puede_aprobar": all(v["estado"] == "CUMPLE" for v in verificaciones),
            "texto_sancionado": texto_revisora, "hash_texto_sancionado": huella(texto_revisora),
            "alcance_verificacion": "Requisitos documentales y cómputos del trámite ordinario. El revisor debe comprobar autenticidad y demás exigencias aplicables."}

"""Casos de trabajo compartidos entre equipos, con control de versiones."""
import json
from datetime import datetime, timezone

LEGISLADORES = {"Senador", "Diputado"}
POST_CONCENTRADOR = {"secretarioData", "bicameralData", "vetoPromulgacionData", "publicacionData"}


def validar_edicion(usuario, snapshot):
    rol = usuario.get("rol")
    if rol == "Ciudadano":
        raise PermissionError("El ciudadano presenta su caso desde Interacción Ciudadana; el seguimiento lo continúa la cámara")
    if rol not in LEGISLADORES and (snapshot.get("pipelineStep", 0) > 11
                                   or any(snapshot.get(k) for k in POST_CONCENTRADOR)):
        raise PermissionError("Solo un Diputado o Senador puede continuar después del Concentrador")
    if len(json.dumps(snapshot, ensure_ascii=False).encode("utf-8")) > 8_000_000:
        raise ValueError("El caso excede el tamaño permitido")


_INDICES_CASOS_CREADOS = False


def coleccion():
    global _INDICES_CASOS_CREADOS
    from sma_unified.db.mongo_atlas import get_db
    col = get_db()["casos_compartidos"]
    if not _INDICES_CASOS_CREADOS:
        try:
            col.create_index([("actualizado", -1)])
            col.create_index([("autor_id", 1), ("actualizado", -1)])
            _INDICES_CASOS_CREADOS = True
        except Exception:
            pass
    return col


def publico(doc):
    return {**doc["snapshot"], "id": doc["_id"], "_sharedVersion": doc["version"],
            "_sharedProcessing": doc.get("processing", False), "isProcessing": doc.get("processing", False),
            "camaraDestino": doc.get("camara_destino", "Ambas"),
            "autorCaso": doc.get("autor_nombre"), "estadoCompartido": doc.get("estado"),
            "updatedAt": doc["actualizado"]}


def guardar(caso_id, snapshot, version, usuario):
    validar_edicion(usuario, snapshot)
    snapshot = {k: v for k, v in snapshot.items() if not k.startswith("_shared")}
    snapshot.update(id=caso_id, isProcessing=False, inspectedAgentId=None)
    ahora = datetime.now(timezone.utc).isoformat()
    col = coleccion()
    if version == 0:
        if col.find_one({"_id": caso_id}):
            raise ValueError("El caso cambió en otro equipo. Actualice antes de guardar")
        doc = {"_id": caso_id, "snapshot": snapshot, "version": 1, "actualizado": ahora,
               "autor_id": usuario["usuario_id"], "autor_nombre": usuario.get("nombre_completo"),
               "camara_destino": snapshot.get("camaraDestino", "Ambas"), "estado": "EN_SEGUIMIENTO"}
        try:
            col.insert_one(doc)
        except Exception as e:
            if col.find_one({"_id": caso_id}):
                raise ValueError("El caso cambió en otro equipo. Actualice antes de guardar") from e
            raise
        return publico(doc)
    doc = col.find_one_and_update({"_id": caso_id, "version": version, "processing": {"$ne": True}},
        {"$set": {"snapshot": snapshot, "actualizado": ahora, "estado": "EN_SEGUIMIENTO"},
         "$inc": {"version": 1}}, return_document=True)
    if not doc:
        raise ValueError("El caso cambió en otro equipo o está procesándose. Actualice antes de guardar")
    return publico(doc)


def preparar_reanudacion(caso_id, usuario):
    """Reclama un caso detenido sin crear otro expediente ni permitir ejecuciones dobles."""
    col = coleccion()
    doc = col.find_one({"_id": caso_id})
    if not doc:
        raise ValueError("El caso no existe")
    if usuario.get("rol") not in LEGISLADORES and str(doc.get("autor_id")) != str(usuario.get("usuario_id")):
        raise PermissionError("Solo el autor o un legislador puede reanudar este caso")
    snapshot = doc["snapshot"].copy()
    if doc.get("processing"):
        raise ValueError("El caso ya está en proceso")
    if snapshot.get("pipelineStep", 0) > 11 or any(snapshot.get(k) for k in POST_CONCENTRADOR):
        raise ValueError("El caso ya está en seguimiento legislativo; no se reinician sus auditorías")
    if len(snapshot.get("documentText", "").strip()) < 10 or len(snapshot.get("documentText", "")) > 300000:
        raise ValueError("El caso no tiene un texto válido para ejecutar las auditorías")
    if not (snapshot.get("tipoPresentacion") == "iniciativa" or snapshot.get("tipoProcesamiento") == "iniciativa"
            or (snapshot.get("fase1Data") or {}).get("categoria") == "AGENTE_REGISTRO_LEGISLATIVO"):
        raise ValueError("Este caso es una consulta, no un proyecto legislativo")
    snapshot.update(pipelineStep=2 if snapshot.get("fase1Data") else 1, errorMessage="", avisos=[],
        agentesEnProceso=["comision"] if snapshot.get("fase1Data") else ["distribuidor"],
        dictamenData=None, consistenciaData=None, concentradorData=None, pdfResult=None)
    actualizado = col.find_one_and_update({"_id": caso_id, "version": doc["version"], "processing": {"$ne": True}},
        {"$set": {"snapshot": snapshot, "processing": True, "estado": "REANUDANDO_AUDITORIAS",
                  "actualizado": datetime.now(timezone.utc).isoformat()}, "$inc": {"version": 1}}, return_document=True)
    if not actualizado:
        raise ValueError("Otro equipo ya reanudó o modificó este caso")
    return actualizado

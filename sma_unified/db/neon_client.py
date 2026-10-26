# sma_unified/db/neon_client.py

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv
import json

load_dotenv()

class NeonDBClient:
    """Cliente para PostgreSQL Neon con pool de conexiones y soporte pgvector"""
    
    def __init__(self, min_conn: int = 1, max_conn: int = 10):
        self.database_url = os.getenv("NEON_DATABASE_URL")
        self.pool = None
        self._crear_pool(min_conn, max_conn)
    
    def _crear_pool(self, min_conn: int, max_conn: int):
        """Crear pool de conexiones"""
        try:
            self.pool = ThreadedConnectionPool(
                min_conn,
                max_conn,
                self.database_url
            )
        except Exception as e:
            print(f"Error creando pool Neon: {e}")
            raise
    
    def get_connection(self):
        """Obtener conexión del pool"""
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Devolver conexión al pool"""
        self.pool.putconn(conn)
    
    def ejecutar_query(self, query: str, params: tuple = None, fetch: bool = True) -> List[Dict]:
        """Ejecutar query y retornar resultados como diccionarios"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                resultado = [dict(r) for r in cur.fetchall()] if fetch else []
                conn.commit()
                return resultado
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.return_connection(conn)
    
    def ejecutar_transaccion(self, queries: List[tuple]) -> List[List[Dict]]:
        """Ejecutar múltiples queries en una sola transacción atómica"""
        conn = None
        resultados = []
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for query, params in queries:
                    cur.execute(query, params)
                    if cur.description:
                        resultados.append([dict(r) for r in cur.fetchall()])
                    else:
                        resultados.append([])
                conn.commit()
            return resultados
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.return_connection(conn)
    
    def insertar_proyecto(self, data: Dict) -> int:
        """Insertar un nuevo proyecto de ley"""
        query = """
            INSERT INTO sistema.proyecto_ley (
                id_expediente, numero_expediente, tipo_documento, titulo_proyecto, titulo,
                descripcion_corta, contenido_texto, texto_completo, estado_actual,
                usuario_ingreso, agente_distribuidor_decision
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_proyecto
        """
        exp_id = data.get('id_expediente') or f"EXP-{int(os.times().elapsed * 1000)}"
        titulo = data.get('titulo_proyecto') or data.get('titulo', 'Sin título')
        texto = data.get('contenido_texto') or data.get('texto', '')
        params = (
            exp_id,
            exp_id,
            data.get('tipo_documento', 'Proyecto_Ley'),
            titulo,
            titulo,
            data.get('descripcion_corta', ''),
            texto,
            texto,
            data.get('estado_actual', 'INGRESADO'),
            data.get('usuario_ingreso', 'system'),
            Json(data.get('agente_distribuidor_decision', {}))
        )
        result = self.ejecutar_query(query, params)
        return result[0]['id_proyecto'] if result else None
    
    def actualizar_estado_proyecto(self, id_proyecto: int, nuevo_estado: str, 
                                   agente_responsable: str = None) -> bool:
        """Actualizar estado de un proyecto en sistema.proyecto_ley"""
        query = """
            UPDATE sistema.proyecto_ley 
            SET estado_actual = %s,
                estado_tramite = %s,
                fecha_ultima_modificacion = CURRENT_TIMESTAMP,
                usuario_ultima_modificacion = %s
            WHERE id_proyecto = %s
        """
        params = (nuevo_estado, nuevo_estado, agente_responsable or 'system', id_proyecto)
        self.ejecutar_query(query, params, fetch=False)
        return True
    
    def insertar_observacion(self, id_proyecto: int, tipo_obs: str, agente: str, 
                             hallazgos: Dict, riesgo: str = 'MEDIO', 
                             articulos_afectados: List = None, recomendacion: str = "") -> int:
        """Registrar una observación generada por un agente"""
        query = """
            INSERT INTO sistema.observaciones_unificadas (
                id_proyecto, tipo_observacion, agente_generador, hallazgos,
                articulos_afectados, riesgo_normativo, recomendacion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            id_proyecto,
            tipo_obs,
            agente,
            Json(hallazgos or {}),
            Json(articulos_afectados or []),
            riesgo,
            recomendacion
        )
        result = self.ejecutar_query(query, params)
        return result[0]['id'] if result else None

    def registrar_bitacora(self, id_proyecto: int, evento: str, detalle: Dict = None,
                           agente: str = None, usuario: str = "system",
                           estado_previo: str = None, estado_nuevo: str = None) -> int:
        """Registrar un evento en la bitácora transaccional"""
        query = """
            INSERT INTO sistema.bitacora_proceso (
                id_proyecto, evento, detalle, agente_responsable, usuario_responsable,
                estado_previo, estado_nuevo
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_bitacora
        """
        params = (
            id_proyecto,
            evento,
            Json(detalle or {}),
            agente,
            usuario,
            estado_previo,
            estado_nuevo
        )
        result = self.ejecutar_query(query, params)
        return result[0]['id_bitacora'] if result else None

    def registrar_paso(self, id_proyecto: int, num_paso: int, nombre_paso: str,
                        agente: str, estado: str = 'COMPLETADO', resultado: Dict = None,
                        duracion_s: int = 0) -> int:
        """Registrar ejecución de un paso del proceso"""
        query = """
            INSERT INTO sistema.pasos_proceso (
                id_proyecto, num_paso, nombre_paso, agente_responsable, estado_paso,
                resultado, duracion_segundos, timestamp_inicio, timestamp_fin
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """
        params = (
            id_proyecto,
            num_paso,
            nombre_paso,
            agente,
            estado,
            Json(resultado or {}),
            duracion_s
        )
        result = self.ejecutar_query(query, params)
        return result[0]['id'] if result else None

    def registrar_ejecucion_agente(self, id_proyecto: int, nombre_agente: str,
                                   input_data: Dict, output_data: Dict,
                                   estado: str = 'EXITO', tiempo_ms: int = 0) -> int:
        """Registrar métricas y resultados de ejecución de un agente"""
        query = """
            INSERT INTO sistema.ejecuciones_agente (
                id_proyecto, nombre_agente, input_data, output_data, estado, tiempo_ejecucion_ms
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            id_proyecto,
            nombre_agente,
            Json(input_data or {}),
            Json(output_data or {}),
            estado,
            tiempo_ms
        )
        result = self.ejecutar_query(query, params)
        return result[0]['id'] if result else None

    @contextmanager
    def _proyecto_bloqueado(self, id_proyecto):
        """Estado y registro de revisión se confirman juntos, bajo bloqueo del proyecto."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id_proyecto, estado_actual, COALESCE(texto_completo, contenido_texto, '') AS texto FROM sistema.proyecto_ley WHERE id_proyecto = %s FOR UPDATE", (id_proyecto,))
                proyecto = cur.fetchone()
                if not proyecto:
                    raise ValueError("Proyecto inexistente")
                yield cur, dict(proyecto)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.return_connection(conn)

    @staticmethod
    def _ultimo_registro(cur, id_proyecto, tipo):
        cur.execute("SELECT id, hallazgos FROM sistema.observaciones_unificadas WHERE id_proyecto = %s AND tipo_observacion = %s ORDER BY id DESC LIMIT 1", (id_proyecto, tipo))
        row = cur.fetchone()
        return dict(row) if row else None

    @staticmethod
    def _insertar_registro(cur, id_proyecto, tipo, datos, agente):
        cur.execute("INSERT INTO sistema.observaciones_unificadas (id_proyecto, tipo_observacion, agente_generador, hallazgos, riesgo_normativo, recomendacion) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (id_proyecto, tipo, agente, Json(datos), "DESCONOCIDO", "Registro documental del control legislativo"))
        return cur.fetchone()["id"]

    @staticmethod
    def _estado_revision(cur, id_proyecto, estado, usuario):
        cur.execute("UPDATE sistema.proyecto_ley SET estado_actual = %s, estado_tramite = %s, updated_at = CURRENT_TIMESTAMP, usuario_ultima_modificacion = %s WHERE id_proyecto = %s", (estado, estado, usuario, id_proyecto))
        if cur.rowcount != 1:
            raise ValueError("No se pudo actualizar el proyecto")

    def guardar_insumo_legislativo(self, id_proyecto, tipo, datos, agente, estado):
        from sma_unified.agents.control_legislativo import huella
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            datos["hash_documento"] = huella(proyecto["texto"])
            registro = self._insertar_registro(cur, id_proyecto, tipo, datos, agente)
            self._estado_revision(cur, id_proyecto, estado, agente)
            return registro

    def _antecedentes_bicamerales(self, cur, proyecto):
        from sma_unified.agents.control_legislativo import huella
        resultado = {"hash_documento": huella(proyecto["texto"]), "referencias_insumos": {}, "insumos_vigentes": True}
        for nombre, tipo in (("secretario", "ACTA_DEBATE"), ("concentrador", "EXPEDIENTE_CONSOLIDADO")):
            registro = self._ultimo_registro(cur, proyecto["id_proyecto"], tipo)
            resultado[nombre] = registro["hallazgos"] if registro else {}
            resultado["referencias_insumos"][nombre] = registro["id"] if registro else None
            h_insumo = (registro["hallazgos"] if registro else {}).get("hash_documento")
            resultado["insumos_vigentes"] = resultado["insumos_vigentes"] and bool(registro) and (h_insumo == resultado["hash_documento"] or (nombre == "concentrador" and bool(h_insumo)))
        return resultado

    def obtener_antecedentes_bicamerales(self, id_proyecto):
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            return self._antecedentes_bicamerales(cur, proyecto)

    def _validar_revision_vigente(self, cur, proyecto, ciclo):
        antecedentes = self._antecedentes_bicamerales(cur, proyecto)
        if antecedentes["hash_documento"] != ciclo.get("hash_documento") or antecedentes["referencias_insumos"] != ciclo.get("referencias_insumos"):
            raise ValueError("El documento o los antecedentes cambiaron. Ejecutar nuevamente Bicameral antes de decidir.")
        return antecedentes

    def guardar_revision_bicameral(self, id_proyecto, resultado):
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            self._validar_revision_vigente(cur, proyecto, resultado["ciclo_bicameral"])
            registro = self._insertar_registro(cur, id_proyecto, "REVISION_BICAMERAL", resultado, "Bicameral")
            self._estado_revision(cur, id_proyecto, "PENDIENTE_APROBACION_HUMANA", "Bicameral")
            return registro

    def obtener_revision_bicameral(self, id_proyecto):
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            registro = self._ultimo_registro(cur, id_proyecto, "REVISION_BICAMERAL")
            if not registro:
                raise ValueError("Ejecutar Bicameral antes de revisar el expediente")
            resultado = registro["hallazgos"]
            ciclo = resultado["ciclo_bicameral"]
            self._validar_revision_vigente(cur, proyecto, ciclo)
            ciclo["id_revision"] = registro["id"]
            decision = self._ultimo_registro(cur, id_proyecto, "DECISION_BICAMERAL")
            if decision and decision["hallazgos"].get("id_revision") == registro["id"]:
                ciclo["aprobacion_humana"] = decision["hallazgos"]
                ciclo["estado_siguiente"] = decision["hallazgos"]["estado"]
                resultado["estado_ejecucion"] = decision["hallazgos"]["estado"]
                resultado["puede_continuar"] = decision["hallazgos"]["accion"] == "APROBAR"
            return resultado

    def registrar_decision_bicameral(self, id_proyecto, id_revision, version_revision, accion, motivo, usuario, confirmacion_exigencias=False):
        from sma_unified.config import load_control_aprobacion
        from sma_unified.agents.control_legislativo import evaluar_bicameral
        control = load_control_aprobacion()
        if usuario.get("rol") not in control["roles_permitidos"]:
            raise PermissionError("El usuario no tiene permiso para revisar el expediente")
        if accion not in ("APROBAR", "MANDAR_A_REVISION"):
            raise ValueError("Acción de revisión no válida")
        if accion == "APROBAR" and confirmacion_exigencias is not True:
            raise ValueError("Confirmar la revisión de todas las exigencias aplicables")
        if accion == "MANDAR_A_REVISION" and not motivo.strip():
            raise ValueError("Indicar el motivo de la revisión")
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            revision = self._ultimo_registro(cur, id_proyecto, "REVISION_BICAMERAL")
            if not revision or revision["id"] != id_revision:
                raise ValueError("La revisión mostrada ya no es la última; volver a consultar Bicameral")
            ciclo = revision["hallazgos"]["ciclo_bicameral"]
            if ciclo["version_revision"] != version_revision:
                raise ValueError("La versión de la revisión no coincide")
            antecedentes = self._validar_revision_vigente(cur, proyecto, ciclo)
            if accion == "APROBAR" and not antecedentes["insumos_vigentes"]:
                raise ValueError("Los antecedentes corresponden a otro documento. Ejecutar nuevamente Concentrador y Secretario.")
            verificacion = evaluar_bicameral(ciclo["acta_secretario"], ciclo["expediente_consolidado"], ciclo["version_original"], ciclo["version_retornada"])
            observaciones = [v for v in verificacion.get("verificaciones_normativas", [])
                             if v.get("estado") != "CUMPLE"]
            previa = self._ultimo_registro(cur, id_proyecto, "DECISION_BICAMERAL")
            if previa and previa["hallazgos"].get("id_revision") == id_revision:
                if previa["hallazgos"]["accion"] == accion:
                    return previa["hallazgos"]
                raise ValueError("Esta revisión ya fue resuelta. Ejecutar una nueva revisión.")
            decision = {"id_revision": id_revision, "version_revision": version_revision, "accion": accion,
                        "aprobado_con_observaciones": accion == "APROBAR" and bool(observaciones),
                        "observaciones_al_decidir": observaciones,
                        "motivo": motivo.strip(), "confirmacion_exigencias": confirmacion_exigencias,
                        "usuario_id": usuario["usuario_id"], "nombre_usuario": usuario["nombre_completo"],
                        "rol": usuario["rol"], "fecha": datetime.now(timezone.utc).isoformat(),
                        "estado": "APROBADO_REVISION_HUMANA" if accion == "APROBAR" else "EN_REVISION",
                        "hash_texto_sancionado": ciclo["hash_texto_sancionado"]}
            self._insertar_registro(cur, id_proyecto, "DECISION_BICAMERAL", decision, "Revisor humano")
            self._estado_revision(cur, id_proyecto, decision["estado"], str(usuario["usuario_id"]))
            return decision

    def obtener_aprobacion_bicameral(self, id_proyecto):
        resultado = self.obtener_revision_bicameral(id_proyecto)
        ciclo = resultado["ciclo_bicameral"]
        if (ciclo.get("aprobacion_humana") or {}).get("accion") != "APROBAR":
            raise ValueError("El expediente requiere aprobación humana en Bicameral")
        return ciclo

    def guardar_evaluacion_ejecutiva(self, id_proyecto, ciclo, resultado, usuario=None):
        """Asesoría y decisión formal son registros distintos; ninguna recomendación promulga."""
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            self._validar_revision_vigente(cur, proyecto, ciclo)
            revision = self._ultimo_registro(cur, id_proyecto, "REVISION_BICAMERAL")
            decision = self._ultimo_registro(cur, id_proyecto, "DECISION_BICAMERAL")
            if not revision or revision["id"] != ciclo["id_revision"] or not decision or decision["hallazgos"].get("id_revision") != revision["id"] or decision["hallazgos"].get("accion") != "APROBAR":
                raise ValueError("La aprobación bicameral cambió; volver a revisar")
            evaluacion = resultado["evaluacion_veto"]
            formal = evaluacion["decision"] in ("PROMULGAR", "VETAR_TOTAL", "VETAR_PARCIAL")
            previa = self._ultimo_registro(cur, id_proyecto, "DECISION_EJECUTIVA")
            if previa and previa["hallazgos"]["evaluacion_veto"].get("id_revision") == revision["id"]:
                if not formal or previa["hallazgos"]["evaluacion_veto"]["decision"] == evaluacion["decision"]:
                    resultado.clear()
                    resultado.update(previa["hallazgos"])
                    return previa["id"]
                raise ValueError("Ya existe una decisión ejecutiva para esta revisión. Preparar una nueva revisión.")
            if formal:
                from sma_unified.config import load_control_aprobacion
                if not usuario or usuario.get("rol") not in load_control_aprobacion()["roles_permitidos"]:
                    raise PermissionError("Se requiere un usuario autorizado para registrar la decisión documentada")
                if not evaluacion.get("referencia_decision"):
                    raise ValueError("Falta la referencia del documento de decisión de la autoridad competente")
                evaluacion["registro_humano"] = {"usuario_id": usuario["usuario_id"], "nombre_usuario": usuario["nombre_completo"],
                                               "fecha": datetime.now(timezone.utc).isoformat()}
            evaluacion["id_revision"] = revision["id"]
            evaluacion["hash_texto_sancionado"] = ciclo["hash_texto_sancionado"]
            registro = self._insertar_registro(cur, id_proyecto, "DECISION_EJECUTIVA" if formal else "EVALUACION_VETO_PROMULGACION", resultado, "Veto y Promulgación")
            self._estado_revision(cur, id_proyecto, evaluacion["estado_siguiente"], str(usuario["usuario_id"]) if usuario else "Veto y Promulgación")
            return registro

    def obtener_promulgacion_verificada(self, id_proyecto):
        """La publicación consulta el registro formal, nunca el JSON enviado por el navegador."""
        ciclo = self.obtener_aprobacion_bicameral(id_proyecto)
        with self._proyecto_bloqueado(id_proyecto) as (cur, proyecto):
            self._validar_revision_vigente(cur, proyecto, ciclo)
            revision = self._ultimo_registro(cur, id_proyecto, "REVISION_BICAMERAL")
            registro = self._ultimo_registro(cur, id_proyecto, "DECISION_EJECUTIVA")
            evaluacion = registro["hallazgos"]["evaluacion_veto"] if registro else {}
            if not revision or revision["id"] != ciclo["id_revision"] or evaluacion.get("id_revision") != ciclo["id_revision"] or evaluacion.get("hash_texto_sancionado") != ciclo["hash_texto_sancionado"] or evaluacion.get("decision") != "PROMULGAR":
                raise ValueError("No existe una promulgación documentada para la revisión vigente")
            return registro["hallazgos"], ciclo["texto_sancionado"]

    def close(self):
        """Cerrar pool de conexiones"""
        if self.pool:
            self.pool.closeall()

_neon_client_instance = None

def get_neon_client() -> NeonDBClient:
    global _neon_client_instance
    if _neon_client_instance is None:
        _neon_client_instance = NeonDBClient()
    return _neon_client_instance

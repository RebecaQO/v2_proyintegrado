"""
Agente Notificador de Cámara Opuesta (Trámite Bicameral)
==========================================================
Cuando un Senador confirma la aprobación de un proyecto de ley, este agente
notifica por correo a todos los Diputados registrados en el sistema (y
viceversa: cuando un Diputado confirma, notifica a todos los Senadores).

El correo incluye:
  - El PDF del proyecto de ley original (tal como fue subido a Mesa de Partes).
  - El PDF del informe/dictamen de constitucionalidad y consistencia normativa
    (generado por el Agente Emisor de Resultados).
  - Un resumen HTML institucional con el dictamen de constitucionalidad y los
    hallazgos de consistencia normativa.

Reutiliza la infraestructura de envío de correo (Gmail SMTP / SendGrid) ya
existente en `notificador_comision.py`.
"""
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_notificador_camara_opuesta")

from sma_unified.db.mongo_atlas import publicar_mensaje, marcar_en_proceso, marcar_completado, marcar_error, get_db
from sma_unified.db.neon_postgres import obtener_usuarios_por_rol, registrar_bitacora
from sma_unified.agents.notificador_comision import enviar_correo_hibrido

# Roles válidos de cámara y su opuesto
_CAMARA_OPUESTA = {
    "Senador": "Diputado",
    "Diputado": "Senador",
}


def _generar_html_confirmacion(
    titulo_proyecto: str,
    rol_remitente: str,
    camara_destino: str,
    nombre_remitente: Optional[str],
    datos_constitucionales: Dict[str, Any],
    datos_consistencia: Dict[str, Any],
    pdf_proyecto_filename: Optional[str],
    pdf_informe_filename: Optional[str],
) -> str:
    """Genera el cuerpo HTML institucional del correo de confirmación bicameral."""
    valido = datos_constitucionales.get("valido", True)
    riesgo_constitucional = "BAJO" if valido else (datos_constitucionales.get("nivel_riesgo") or "ALTO")
    contradicciones = datos_constitucionales.get("contradicciones") or []

    riesgo_consistencia = datos_consistencia.get("nivel_riesgo_global") or "BAJO"
    hallazgos = datos_consistencia.get("analisis") or datos_consistencia.get("hallazgos") or []

    color_riesgo = {"BAJO": "#10B981", "MEDIO": "#F59E0B", "ALTO": "#EF4444"}
    color_const = color_riesgo.get(str(riesgo_constitucional).upper(), "#10B981")
    color_cons = color_riesgo.get(str(riesgo_consistencia).upper(), "#10B981")

    filas_contradicciones = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #E2E8F0;font-size:12px;'>{c.get('articulo', '-')}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #E2E8F0;font-size:12px;'>{c.get('descripcion', c.get('detalle', ''))}</td></tr>"
        for c in contradicciones[:10]
    ) or "<tr><td colspan='2' style='padding:8px 10px;font-size:12px;color:#64748B;'>Sin contradicciones constitucionales registradas.</td></tr>"

    filas_hallazgos = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #E2E8F0;font-size:12px;'>{h.get('tipo_relacion', h.get('tipo', '-'))}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #E2E8F0;font-size:12px;'>{h.get('justificacion', h.get('descripcion', ''))}</td></tr>"
        for h in hallazgos[:10]
    ) or "<tr><td colspan='2' style='padding:8px 10px;font-size:12px;color:#64748B;'>Sin hallazgos de consistencia normativa registrados.</td></tr>"

    adjuntos_html = ""
    if pdf_proyecto_filename:
        adjuntos_html += f"<li>📄 Proyecto de Ley (original): <strong>{pdf_proyecto_filename}</strong></li>"
    if pdf_informe_filename:
        adjuntos_html += f"<li>📋 Informe de Constitucionalidad y Consistencia Normativa: <strong>{pdf_informe_filename}</strong></li>"
    if not adjuntos_html:
        adjuntos_html = "<li>Sin documentos adjuntos disponibles.</li>"

    remitente_txt = f"{nombre_remitente} ({rol_remitente})" if nombre_remitente else rol_remitente

    return f"""
    <html>
    <body style="margin:0;padding:0;background:#F1F5F9;font-family:Arial,Helvetica,sans-serif;">
        <div style="max-width:680px;margin:0 auto;background:#FFFFFF;">
            <div style="background:linear-gradient(90deg,#0B2545,#144272);padding:22px 28px;color:#FFFFFF;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.75;">Asamblea Legislativa Plurinacional — SMA Congreso</div>
                <h2 style="margin:6px 0 0 0;font-size:20px;">Confirmación de Aprobación — Trámite Bicameral</h2>
            </div>

            <div style="padding:24px 28px;">
                <p style="font-size:13.5px;color:#1E293B;line-height:1.6;">
                    La <strong>Cámara de {rol_remitente}s</strong>, a través de {remitente_txt}, ha
                    <strong>confirmado la aprobación</strong> del proyecto de ley
                    <strong>"{titulo_proyecto}"</strong>. Conforme al trámite bicameral (Art. 163 CPE),
                    se remite la documentación a la <strong>Cámara de {camara_destino}s</strong> para su
                    conocimiento y trámite correspondiente.
                </p>

                <div style="margin:18px 0;">
                    <span style="display:inline-block;background:{color_const}22;color:{color_const};border:1px solid {color_const};border-radius:6px;padding:4px 10px;font-size:11.5px;font-weight:700;margin-right:8px;">
                        Riesgo Constitucional: {riesgo_constitucional}
                    </span>
                    <span style="display:inline-block;background:{color_cons}22;color:{color_cons};border:1px solid {color_cons};border-radius:6px;padding:4px 10px;font-size:11.5px;font-weight:700;">
                        Riesgo de Consistencia Normativa: {riesgo_consistencia}
                    </span>
                </div>

                <div style="margin-bottom:16px;">
                    <div style="font-size:13px;font-weight:700;color:#1E293B;margin-bottom:6px;">⚖️ Dictamen de Constitucionalidad</div>
                    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:4px;">
                        <thead>
                            <tr style="background:#EEF2FF;text-align:left;color:#475569;font-size:10.5px;text-transform:uppercase;">
                                <th style="padding:8px 10px;">Artículo</th><th style="padding:8px 10px;">Observación</th>
                            </tr>
                        </thead>
                        <tbody>{filas_contradicciones}</tbody>
                    </table>
                </div>

                <div style="margin-bottom:20px;">
                    <div style="font-size:13px;font-weight:700;color:#1E293B;margin-bottom:6px;">🔎 Consistencia Normativa</div>
                    <table style="width:100%;border-collapse:collapse;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:4px;">
                        <thead>
                            <tr style="background:#EEF2FF;text-align:left;color:#475569;font-size:10.5px;text-transform:uppercase;">
                                <th style="padding:8px 10px;">Tipo</th><th style="padding:8px 10px;">Justificación</th>
                            </tr>
                        </thead>
                        <tbody>{filas_hallazgos}</tbody>
                    </table>
                </div>

                <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:14px 16px;">
                    <div style="font-size:12.5px;font-weight:700;color:#1E293B;margin-bottom:6px;">📎 Documentos adjuntos</div>
                    <ul style="margin:0;padding-left:18px;font-size:12.5px;color:#334155;line-height:1.7;">{adjuntos_html}</ul>
                </div>
            </div>

            <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:14px 28px;text-align:center;font-size:11px;color:#94A3B8;">
                Asamblea Legislativa Plurinacional de Bolivia — Mesa de Partes Virtual SMA<br/>
                Mensaje automatizado generado por el <strong>Agente Comunicación Bicameral</strong>.
            </div>
        </div>
    </body>
    </html>
    """


def notificar_camara_opuesta(
    rol_remitente: str,
    titulo_proyecto: str,
    sesion_id: Optional[str] = None,
    id_proyecto: Optional[int] = None,
    nombre_remitente: Optional[str] = None,
    datos_constitucionales: Optional[Dict[str, Any]] = None,
    datos_consistencia: Optional[Dict[str, Any]] = None,
    pdf_proyecto_filename: Optional[str] = None,
    pdf_informe_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Al confirmarse la aprobación de un proyecto de ley por una cámara (Senador o
    Diputado), notifica por correo a todos los usuarios activos de la cámara
    opuesta, adjuntando el PDF del proyecto de ley y el informe de
    constitucionalidad/consistencia.
    """
    rol_remitente = (rol_remitente or "").strip().capitalize()
    camara_destino = _CAMARA_OPUESTA.get(rol_remitente)
    if not camara_destino:
        raise ValueError(
            f"rol_remitente inválido: '{rol_remitente}'. Debe ser 'Senador' o 'Diputado'."
        )

    task_id = publicar_mensaje(
        agente_origen="AGENTE_BICAMERAL",
        agente_destino="AGENTE_NOTIFICADOR_CAMARA_OPUESTA",
        tipo_tarea=f"Notificación de Aprobación {rol_remitente} → {camara_destino}",
        payload={"sesion_id": sesion_id, "id_proyecto": id_proyecto, "rol_remitente": rol_remitente},
        sesion_id=sesion_id,
    )
    marcar_en_proceso(task_id)
    t_inicio = time.time()

    datos_constitucionales = datos_constitucionales or {}
    datos_consistencia = datos_consistencia or {}

    try:
        # 1. Obtener destinatarios: todos los usuarios activos de la cámara opuesta
        usuarios_destino = obtener_usuarios_por_rol(camara_destino)
        destinatarios = [u["correo_electronico"] for u in usuarios_destino if u.get("correo_electronico")]

        if not destinatarios:
            resultado = {
                "status": "sin_destinatarios",
                "mensaje": f"No hay usuarios activos con rol '{camara_destino}' registrados en Usuarios_Sistema.",
                "camara_origen": rol_remitente,
                "camara_destino": camara_destino,
                "destinatarios": [],
                "total_destinatarios": 0,
            }
            marcar_completado(task_id, resultado=resultado, duracion_ms=int((time.time() - t_inicio) * 1000))
            return resultado

        # 2. Redactar el correo HTML institucional
        html_content = _generar_html_confirmacion(
            titulo_proyecto=titulo_proyecto,
            rol_remitente=rol_remitente,
            camara_destino=camara_destino,
            nombre_remitente=nombre_remitente,
            datos_constitucionales=datos_constitucionales,
            datos_consistencia=datos_consistencia,
            pdf_proyecto_filename=pdf_proyecto_filename,
            pdf_informe_filename=pdf_informe_filename,
        )
        asunto = f"[Trámite Bicameral] Aprobación confirmada por la Cámara de {rol_remitente}s — {titulo_proyecto}"

        pdf_adjuntos = [n for n in [pdf_proyecto_filename, pdf_informe_filename] if n]

        # 3. Despachar el correo (Gmail SMTP / SendGrid, con fallback registrado)
        resultado_envio = enviar_correo_hibrido(
            asunto=asunto,
            destinatarios=destinatarios,
            html_content=html_content,
            pdf_filenames=pdf_adjuntos,
        )

        duracion_ms = int((time.time() - t_inicio) * 1000)
        resultado = {
            "status": "notificado",
            "asunto": asunto,
            "camara_origen": rol_remitente,
            "camara_destino": camara_destino,
            "remitente": nombre_remitente,
            "total_destinatarios": len(destinatarios),
            "destinatarios": destinatarios,
            "usuarios_notificados": usuarios_destino,
            "pdf_adjuntos": pdf_adjuntos,
            "envio": resultado_envio,
            "fecha_despacho": datetime.now().isoformat(),
            "duracion_ms": duracion_ms,
        }

        # 4. Registrar en MongoDB y en la bitácora de Neon
        try:
            db = get_db()
            db["notificaciones_bicameral"].insert_one({
                "sesion_id": sesion_id,
                "id_proyecto": id_proyecto,
                **resultado,
            })
        except Exception as me:
            logger.warning(f"No se pudo guardar notificación bicameral en Mongo: {me}")

        if id_proyecto:
            try:
                registrar_bitacora(
                    id_proyecto=int(id_proyecto),
                    agente_accion="Agente_Notificador_Camara_Opuesta",
                    accion_realizada=f"Notificación de Aprobación: Cámara de {rol_remitente}s → Cámara de {camara_destino}s",
                    descripcion=f"Destinatarios: {len(destinatarios)} | Método: {resultado_envio.get('metodo')}",
                    tiempo_segundos=max(1, duracion_ms // 1000),
                )
            except Exception as be:
                logger.warning(f"No se pudo registrar bitácora de notificación bicameral: {be}")

        marcar_completado(task_id, resultado=resultado, duracion_ms=duracion_ms)
        logger.info(
            f"✅ Confirmación de aprobación ({rol_remitente} → {camara_destino}) "
            f"notificada a {len(destinatarios)} destinatarios"
        )
        return resultado

    except Exception as e:
        duracion_ms = int((time.time() - t_inicio) * 1000)
        logger.error(f"❌ Error notificando a la cámara opuesta: {e}")
        try:
            marcar_error(task_id, error=str(e))
        except Exception:
            pass
        raise

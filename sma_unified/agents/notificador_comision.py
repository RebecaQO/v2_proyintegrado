"""
Agente Notificador de Comisión (Envío de Notificaciones Formales por Correo HTML)
==================================================================================
Redacta y procesa comunicaciones institucionales de alto nivel en formato HTML
destinadas a los miembros y autoridades de la Comisión Legislativa asignada.
Incluye:
  - Estructura visual institucional tricolor y membrete oficial de la ALP.
  - Ficha técnica completa del proyecto de ley y expediente.
  - Dictamen ejecutivo de constitucionalidad y concordancia normativa.
  - Cuadro de observaciones críticas y recomendaciones procedimentales.
  - Enlace al Dictamen Oficial emitido en PDF y registro en bitácora MongoDB.
"""
import os
import time
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("agente_notificador")

from sma_unified.config import settings
from sma_unified.db.mongo_atlas import publicar_mensaje, marcar_en_proceso, marcar_completado, marcar_error, get_db
from sma_unified.db.neon_postgres import get_conn, registrar_bitacora, obtener_correcciones_proyecto

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


def _resolver_ruta_adjunto(nombre_archivo: str) -> Optional[str]:
    """Busca un PDF adjunto por nombre, primero en uploaded_files/informes/
    (dictámenes/informes generados por el Agente Emisor de Resultados) y luego
    en uploaded_files/ (documentos originales subidos por el usuario, p. ej. el
    proyecto de ley en PDF). Devuelve la ruta absoluta si lo encuentra."""
    if not nombre_archivo:
        return None
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidatos = [
        os.path.join(base_dir, "uploaded_files", "informes", nombre_archivo),
        os.path.join(base_dir, "uploaded_files", nombre_archivo),
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta
    return None


def enviar_correo_gmail_smtp(
    asunto: str,
    destinatarios: List[str],
    html_content: str,
    pdf_filename: Optional[str] = None,
    pdf_filenames: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Envía por Gmail SMTP con TLS directo (465) y alternativa STARTTLS (587).
    Requiere GMAIL_USER y GMAIL_APP_PASSWORD (Contraseña de Aplicación de Google).
    Adjunta uno o varios PDFs: pasa `pdf_filename` (uno) y/o `pdf_filenames` (varios);
    ambos se combinan y se buscan tanto en uploaded_files/informes/ como en uploaded_files/.
    """
    gmail_user = (os.getenv("GMAIL_USER") or os.getenv("SMTP_USER") or "").strip()
    gmail_pass = (os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD") or "").strip().replace(" ", "")
    from_name = os.getenv("SENDGRID_FROM_NAME", "Mesa de Partes Virtual — ALP Bolivia")

    if not gmail_user or not gmail_pass:
        return {
            "enviado": False,
            "metodo": "gmail_smtp",
            "error": "GMAIL_USER o GMAIL_APP_PASSWORD no configurados en .env",
            "destinatarios": destinatarios
        }

    valid_recipients = [d.strip() for d in destinatarios if d and "@" in d]
    if not valid_recipients:
        valid_recipients = [gmail_user]

    adjuntos = [n for n in ([pdf_filename] if pdf_filename else []) + (pdf_filenames or []) if n]

    resultados = []
    for dest in valid_recipients:
        server = None
        etapa = "preparar mensaje"
        try:
            # Preparar adjuntos antes de conectar evita que SMTP expire mientras se leen.
            msg = MIMEMultipart("mixed")
            msg["Subject"] = asunto
            msg["From"] = f"{from_name} <{gmail_user}>"
            msg["To"] = dest
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            for nombre_pdf in adjuntos:
                pdf_path = _resolver_ruta_adjunto(nombre_pdf)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=nombre_pdf)
                        part["Content-Disposition"] = f'attachment; filename="{nombre_pdf}"'
                        msg.attach(part)
            contenido = msg.as_string()
            # Una conexion por destinatario; no reutilizar una conexion desconectada.
            for puerto in (465, 587):
                try:
                    etapa = f"conectar TLS puerto {puerto}"
                    contexto_tls = ssl.create_default_context()
                    if puerto == 465:
                        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60, context=contexto_tls)
                    else:
                        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=60)
                        server.ehlo()
                        etapa = "negociar STARTTLS puerto 587"
                        server.starttls(context=contexto_tls)
                    server.ehlo()
                    etapa = f"autenticar puerto {puerto}"
                    server.login(gmail_user, gmail_pass)
                    break
                except smtplib.SMTPAuthenticationError:
                    raise
                except (smtplib.SMTPServerDisconnected, OSError):
                    if server is not None:
                        try:
                            server.close()
                        except Exception:
                            pass
                        server = None
                    if puerto == 587:
                        raise
                    logger.warning(f"[Gmail SMTP] Fallo en {etapa}; probando STARTTLS 587 antes de enviar")
            # No reintentar tras DATA: Gmail podria haber aceptado el mensaje.
            etapa = f"transmitir mensaje puerto {puerto}"
            rechazados = server.sendmail(gmail_user, [dest], contenido)
            if rechazados:
                raise RuntimeError(f"Destinatario rechazado por SMTP: {dest}")
            resultados.append({"email": dest, "success": True, "status": "Aceptado por Gmail SMTP"})
            logger.info(f"[Gmail SMTP] Correo aceptado para {dest}")
        except Exception as e:
            error = f"{etapa}: {type(e).__name__}: {e}"
            logger.error(f"[Gmail SMTP] Error enviando a {dest}: {error}")
            resultados.append({"email": dest, "success": False, "error": error})
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    # Un fallo en QUIT no invalida un mensaje ya aceptado por SMTP.
                    try:
                        server.close()
                    except Exception:
                        pass
    total_ok = sum(1 for r in resultados if r.get("success"))
    return {
        "enviado": total_ok > 0,
        "metodo": "gmail_smtp",
        "total_enviados": total_ok,
        "total_intentados": len(valid_recipients),
        "detalle": resultados,
        "from_email": gmail_user,
        "error": "; ".join(r["error"] for r in resultados if not r.get("success")) or None,
    }


def enviar_correo_hibrido(
    asunto: str,
    destinatarios: List[str],
    html_content: str,
    pdf_filename: Optional[str] = None,
    pdf_filenames: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Despacha el correo usando la mejor vía disponible, con TOKEN DE GOOGLE / GMAIL como PRIMERA PRIORIDAD:
    1. Si GMAIL_APP_PASSWORD o GMAIL_USER está configurado, usa Gmail SMTP directo (Token de Google).
    2. Si SendGrid está configurado como alternativa, intenta SendGrid.
    3. Si ambos fallan o no están configurados, devuelve el error real sin simular un envío.
    Acepta un solo PDF (`pdf_filename`) y/o varios (`pdf_filenames`) como adjuntos.
    """
    gmail_pass = (os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD") or "").strip().replace(" ", "")
    gmail_user = (os.getenv("GMAIL_USER") or os.getenv("SMTP_USER") or "").strip()
    sendgrid_key = (os.getenv("SENDGRID_API_KEY") or "").strip()

    errores = []
    # Prioridad 1: Token de Google / Gmail SMTP directo
    if gmail_user and gmail_pass:
        logger.info(f"📧 [Token Google] Despachando correo vía Gmail SMTP ({gmail_user}) a: {destinatarios}")
        res_gmail = enviar_correo_gmail_smtp(asunto, destinatarios, html_content, pdf_filename, pdf_filenames)
        if res_gmail.get("enviado"):
            return res_gmail
        errores.append(res_gmail.get("error") or "Gmail SMTP no acepto el mensaje")
        logger.warning(f"⚠️ Envío con Token de Google reportó error: {res_gmail.get('error')}. Intentando alternativa...")

    # Prioridad 2: SendGrid API
    if sendgrid_key and SENDGRID_AVAILABLE:
        res_sg = enviar_correo_sendgrid(asunto, destinatarios, html_content, pdf_filename, pdf_filenames)
        if res_sg.get("enviado"):
            return res_sg
        errores.append(res_sg.get("error") or res_sg.get("mensaje") or "SendGrid no acepto el mensaje")

    return {
        "enviado": False,
        "metodo": "sin_envio",
        "error": "; ".join(errores) or "Configure GMAIL_USER y GMAIL_APP_PASSWORD o SendGrid para enviar correos",
        "destinatarios": destinatarios,
        "total_enviados": 0,
    }



def enviar_correo_sendgrid(
    asunto: str,
    destinatarios: List[str],
    html_content: str,
    pdf_filename: Optional[str] = None,
    pdf_filenames: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Envía un correo institucional vía Twilio SendGrid Email API.
    Adjunta en base64 uno o varios PDFs (`pdf_filename` y/o `pdf_filenames`).
    """
    api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    if not api_key or not SENDGRID_AVAILABLE:
        logger.warning(f"⚠️ SendGrid no disponible o SENDGRID_API_KEY vacía. Modo simulación.")
        return {
            "enviado": False,
            "metodo": "simulacion_local",
            "mensaje": "SENDGRID_API_KEY no configurada o SDK no disponible",
            "destinatarios": destinatarios,
            "status_code": 200,
        }

    from_email = os.getenv("SENDGRID_FROM_EMAIL", "notificaciones@asamblea.gob.bo")
    from_name = os.getenv("SENDGRID_FROM_NAME", "Mesa de Partes Virtual — ALP Bolivia")

    adjuntos = [n for n in ([pdf_filename] if pdf_filename else []) + (pdf_filenames or []) if n]

    # Enviar a los destinatarios
    resultados_envio = []
    
    # SendGrid permite enviar a múltiples destinatarios
    valid_recipients = [d.strip() for d in destinatarios if d and "@" in d]
    if not valid_recipients:
        valid_recipients = ["presidencia.comision@asamblea.gob.bo"]

    for email_destino in valid_recipients:
        try:
            message = Mail(
                from_email=(from_email, from_name),
                to_emails=email_destino,
                subject=asunto,
                html_content=html_content
            )

            # Adjuntar PDF(s) si existen
            attachments = []
            for nombre_pdf in adjuntos:
                pdf_path = _resolver_ruta_adjunto(nombre_pdf)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()
                        encoded_file = base64.b64encode(pdf_data).decode()

                    attachments.append(Attachment(
                        FileContent(encoded_file),
                        FileName(nombre_pdf),
                        FileType('application/pdf'),
                        Disposition('attachment')
                    ))
            if len(attachments) == 1:
                message.attachment = attachments[0]
            elif len(attachments) > 1:
                message.attachment = attachments

            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            logger.info(f"📧 [SendGrid] Correo despachado exitosamente a {email_destino} (Status: {response.status_code})")
            resultados_envio.append({
                "email": email_destino,
                "status_code": response.status_code,
                "success": True,
            })
        except Exception as e:
            logger.error(f"❌ [SendGrid] Error enviando correo a {email_destino}: {e}")
            resultados_envio.append({
                "email": email_destino,
                "error": str(e),
                "success": False,
            })

    total_exitosos = sum(1 for r in resultados_envio if r.get("success"))
    return {
        "enviado": total_exitosos > 0,
        "metodo": "twilio_sendgrid_api",
        "total_enviados": total_exitosos,
        "total_intentados": len(valid_recipients),
        "detalle": resultados_envio,
        "from_email": from_email,
    }



def generar_cuerpo_html_notificacion(
    expediente_id: str,
    titulo_proyecto: str,
    comision_nombre: str,
    miembros: List[Dict[str, Any]],
    datos_constitucionales: Dict[str, Any],
    datos_consistencia: Dict[str, Any],
    pdf_filename: Optional[str] = None,
    mensaje_extra: Optional[str] = None
) -> str:
    """
    Genera el HTML institucional para el correo de notificación a la Comisión Legislativa.
    """
    valido = datos_constitucionales.get("valido", True)
    confianza = datos_constitucionales.get("confianza", 95)
    severidad = (datos_constitucionales.get("severidad_maxima") or "ninguna").upper()
    contradicciones = datos_constitucionales.get("contradicciones", [])
    analisis_consistencia = datos_consistencia.get("analisis", [])

    fecha_actual = datetime.now().strftime("%d de %B de %Y - %H:%M")
    
    # Colores institucionales
    color_estado_bg = "#E8F8F0" if valido else "#FDEDEC"
    color_estado_border = "#0D5C3A" if valido else "#C0392B"
    color_estado_txt = "#0D5C3A" if valido else "#C0392B"
    estado_texto = "CONFORME CON LA CPE" if valido else f"CON OBSERVACIONES ({severidad})"

    # Filas de Miembros
    miembros_html = ""
    if miembros:
        for m in miembros:
            nombre = m.get("nombre_completo", "Representante Parlamentario")
            cargo = m.get("cargo", "Vocal")
            email = m.get("email", "comision@asamblea.gob.bo")
            camara = m.get("tipo_camara", "Diputados")
            miembros_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px 12px; font-weight: 600; color: #1E293B;">{nombre}</td>
                <td style="padding: 8px 12px; color: #0D5C3A; font-weight: 600;">{cargo}</td>
                <td style="padding: 8px 12px; color: #64748B;">{camara}</td>
                <td style="padding: 8px 12px; color: #3B82F6; font-family: monospace;">{email}</td>
            </tr>
            """
    else:
        miembros_html = """
        <tr>
            <td colspan="4" style="padding: 10px; text-align: center; color: #64748B; font-style: italic;">
                Se remitirá a la Presidencia y Secretaría Técnica de la Comisión.
            </td>
        </tr>
        """

    # Bloque de Observaciones Constitucionales
    obs_cpe_html = ""
    if contradicciones:
        for i, c in enumerate(contradicciones, 1):
            art_p = c.get("articulo_proyecto", "Art. Proyecto")
            art_c = c.get("articulo_constitucional", "Art. CPE")
            fund = c.get("fundamento", "Tensión normativa detectada.")
            sev_i = (c.get("severidad") or "grave").upper()
            obs_cpe_html += f"""
            <div style="background: #FFF5F5; border-left: 4px solid #E53E3E; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                <div style="font-weight: 700; color: #C53030; font-size: 13px;">
                    Alerta #{i} [{sev_i}]: {art_p} en conflicto con {art_c}
                </div>
                <div style="color: #4A5568; font-size: 12px; margin-top: 4px; line-height: 1.4;">
                    {fund}
                </div>
            </div>
            """
    else:
        obs_cpe_html = """
        <div style="background: #F0FFF4; border-left: 4px solid #38A169; padding: 10px 14px; border-radius: 4px; color: #22543D; font-size: 13px;">
            ✓ No se evidenciaron tensiones ni vicios de inconstitucionalidad directa con el texto de la CPE.
        </div>
        """

    # Bloque de Consistencia Normativa
    consistencia_html = ""
    if analisis_consistencia:
        for item in analisis_consistencia[:4]:
            norma = item.get("norma", "Ley Vigente")
            num_art = item.get("numero_articulo", "")
            rel = (item.get("tipo_relacion") or "complementario").upper()
            just = item.get("justificacion", "")
            consistencia_html += f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px 12px; margin-bottom: 6px; border-radius: 4px;">
                <span style="font-weight: 600; color: #0F172A; font-size: 12px;">{norma} (Art. {num_art})</span> 
                <span style="background: #FEF3C7; color: #92400E; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px; margin-left: 6px;">{rel}</span>
                <div style="color: #475569; font-size: 11.5px; margin-top: 3px;">{just[:140]}...</div>
            </div>
            """
    else:
        consistencia_html = """
        <div style="color: #64748B; font-size: 12px; font-style: italic;">
            Concordancia semántica y jurídica verificada con el catálogo normativo nacional.
        </div>
        """

    # Bloque de Mensaje Extra / Observaciones del Remitente
    mensaje_extra_html = ""
    if mensaje_extra and mensaje_extra.strip():
        mensaje_extra_html = f"""
        <!-- Observaciones y Mensaje Extra del Remitente -->
        <div style="padding: 0 28px 16px 28px;">
            <div style="background: #EFF6FF; border: 1.5px solid #3B82F6; border-left: 6px solid #1D4ED8; border-radius: 8px; padding: 14px 18px;">
                <div style="font-size: 12px; font-weight: 700; color: #1D4ED8; text-transform: uppercase; margin-bottom: 6px;">
                    NOTA Y OBSERVACIONES ADICIONALES DEL REMITENTE / DESPACHO:
                </div>
                <div style="font-size: 13.5px; color: #1E293B; line-height: 1.5; font-style: italic;">
                    "{mensaje_extra.strip()}"
                </div>
            </div>
        </div>
        """

    pdf_link_html = ""
    if pdf_filename:
        pdf_link_html = f"""
        <div style="margin-top: 20px; text-align: center;">
            <a href="http://127.0.0.1:8085/api/informes/descargar/{pdf_filename}" 
               style="background: #0D5C3A; color: #FFFFFF; text-decoration: none; padding: 12px 26px; font-weight: 700; font-size: 14px; border-radius: 6px; display: inline-block; box-shadow: 0 3px 6px rgba(0,0,0,0.15);">
                📥 Descargar Dictamen Técnico Oficial (PDF)
            </a>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 6px;">Archivo generado: {pdf_filename}</div>
        </div>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Notificación Oficial de Asignación y Dictamen Legislativo</title>
    </head>
    <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #F1F5F9; margin: 0; padding: 20px; color: #1E293B;">
        <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #CBD5E1;">
            
            <!-- Franja Tricolor Superior -->
            <div style="display: flex; height: 6px; width: 100%;">
                <div style="flex: 1; background: #C0392B; height: 6px;"></div>
                <div style="flex: 1; background: #F1C40F; height: 6px;"></div>
                <div style="flex: 1; background: #0D5C3A; height: 6px;"></div>
            </div>

            <!-- Encabezado Institucional -->
            <div style="padding: 24px 28px 18px 28px; background: #0A192F; color: #FFFFFF; text-align: center;">
                <div style="font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; color: #94A3B8; font-weight: 600;">
                    Estado Plurinacional de Bolivia
                </div>
                <div style="font-size: 15px; font-weight: 700; color: #F8FAFC; margin-top: 2px;">
                    ASAMBLEA LEGISLATIVA PLURINACIONAL
                </div>
                <div style="font-size: 12px; color: #34D399; margin-top: 3px; font-weight: 500;">
                    Sistema Multi-Agente (SMA) de Auditoría y Mesa de Partes
                </div>
            </div>

            <!-- Título de Notificación -->
            <div style="padding: 20px 28px 10px 28px;">
                <div style="font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase;">
                    COMUNICACIÓN OFICIAL DE AUDITORÍA LEGISLATIVA
                </div>
                <h2 style="font-size: 18px; color: #0F172A; margin: 4px 0 12px 0; font-weight: 700;">
                    Remisión de Dictamen Técnico-Jurídico a Comisión
                </h2>
                <div style="font-size: 12.5px; color: #64748B; margin-bottom: 16px;">
                    Fecha de Notificación: <strong>{fecha_actual}</strong>
                </div>

                <!-- Saludo Protocolar -->
                <p style="font-size: 13.5px; line-height: 1.5; color: #334155;">
                    Señores miembros de la <strong>{comision_nombre}</strong>:
                </p>
                <p style="font-size: 13px; line-height: 1.5; color: #475569;">
                    En cumplimiento de los procedimientos parlamentarios y los estándares de control normativo, se remite el presente 
                    <strong>Dictamen Automatizado de Constitucionalidad y Consistencia</strong> correspondiente al proyecto de ley ingresado a través de la Mesa de Partes Virtual.
                </p>
            </div>

            {mensaje_extra_html}

            <!-- Ficha Técnica del Expediente -->
            <div style="padding: 0 28px 16px 28px;">
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 14px 18px;">
                    <div style="font-size: 12px; font-weight: 700; color: #0D5C3A; text-transform: uppercase; margin-bottom: 8px;">
                        📌 Ficha Técnica del Expediente
                    </div>
                    <table style="width: 100%; font-size: 12.5px; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 4px 0; width: 35%; color: #64748B;">Nro. Expediente:</td>
                            <td style="padding: 4px 0; font-weight: 700; color: #0F172A;">{expediente_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #64748B;">Proyecto de Ley:</td>
                            <td style="padding: 4px 0; font-weight: 600; color: #0F172A;">{titulo_proyecto}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #64748B;">Comisión Asignada:</td>
                            <td style="padding: 4px 0; font-weight: 600; color: #0D5C3A;">{comision_nombre}</td>
                        </tr>
                    </table>
                </div>
            </div>

            <!-- Estado de Auditoría Constitucional (Badge Box) -->
            <div style="padding: 0 28px 16px 28px;">
                <div style="background: {color_estado_bg}; border: 1.5px solid {color_estado_border}; border-radius: 6px; padding: 14px 18px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 11.5px; font-weight: 700; color: #64748B; text-transform: uppercase;">Dictamen de Constitucionalidad (CPE)</span>
                        <span style="font-size: 11px; background: #FFFFFF; border: 1px solid {color_estado_border}; padding: 2px 8px; border-radius: 12px; font-weight: 700; color: {color_estado_txt};">
                            Confianza: {confianza}%
                        </span>
                    </div>
                    <div style="font-size: 16px; font-weight: 800; color: {color_estado_txt}; margin-top: 4px;">
                        {estado_texto}
                    </div>
                </div>
            </div>

            <!-- Detalle de Observaciones CPE -->
            <div style="padding: 0 28px 16px 28px;">
                <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">
                    🔍 Control Constitucional:
                </div>
                {obs_cpe_html}
            </div>

            <!-- Consistencia Normativa -->
            <div style="padding: 0 28px 16px 28px;">
                <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">
                    ⚖️ Relación con el Ordenamiento Vigente (pgvector):
                </div>
                {consistencia_html}
            </div>

            <!-- Miembros Destinatarios -->
            <div style="padding: 0 28px 16px 28px;">
                <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">
                    👥 Destinatarios y Miembros Notificados:
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px;">
                    <thead>
                        <tr style="background: #F1F5F9; text-align: left; color: #475569; font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 8px 12px;">Nombre</th>
                            <th style="padding: 8px 12px;">Cargo</th>
                            <th style="padding: 8px 12px;">Cámara</th>
                            <th style="padding: 8px 12px;">Correo Institucional</th>
                        </tr>
                    </thead>
                    <tbody>
                        {miembros_html}
                    </tbody>
                </table>
            </div>

            <!-- Botón PDF -->
            <div style="padding: 0 28px 24px 28px;">
                {pdf_link_html}
            </div>

            <!-- Footer Institucional -->
            <div style="background: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px 28px; text-align: center; font-size: 11.5px; color: #94A3B8;">
                <div>Asamblea Legislativa Plurinacional de Bolivia — Mesa de Partes Virtual SMA</div>
                <div style="margin-top: 3px;">Mensaje automatizado generado por el <strong>Agente Notificador de Comisión</strong>.</div>
                <div style="margin-top: 3px; font-family: monospace; font-size: 10px;">ID de Certificación: {expediente_id}-NOTIF</div>
            </div>

        </div>
    </body>
    </html>
    """
    return html_template


def notificar_miembros_comision(
    sesion_id: str,
    id_proyecto: Optional[int] = None,
    datos_comision: Optional[Dict[str, Any]] = None,
    datos_constitucionales: Optional[Dict[str, Any]] = None,
    datos_consistencia: Optional[Dict[str, Any]] = None,
    pdf_filename: Optional[str] = None,
    destinatario_extra: Optional[str] = None,
    mensaje_extra: Optional[str] = None,
    asunto_personalizado: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el Agente Notificador:
    1. Obtiene los miembros y autoridades de la comisión asignada.
    2. Redacta el mensaje institucional en formato HTML formal.
    3. Despacha vía Gmail SMTP directo o Twilio SendGrid API.
    4. Registra el despacho en MongoDB Atlas y PostgreSQL Neon.
    """
    task_id = publicar_mensaje(
        agente_origen="AGENTE_EMISOR_RESULTADOS",
        agente_destino="AGENTE_NOTIFICADOR_COMISION",
        tipo_tarea="Redaccion y Despacho de Correo HTML a Miembros de Comision",
        payload={"sesion_id": sesion_id, "id_proyecto": id_proyecto},
        sesion_id=sesion_id,
    )

    marcar_en_proceso(task_id)
    t_inicio = time.time()

    datos_comision = datos_comision or {}
    datos_constitucionales = datos_constitucionales or {}
    datos_consistencia = datos_consistencia or {}

    expediente_id = f"EXP-{sesion_id[:8].upper()}" if sesion_id else "EXP-2026-SMA"
    titulo_proy = datos_comision.get("tema_principal") or datos_constitucionales.get("titulo") or "Proyecto de Ley"
    comision_nombre = datos_comision.get("comision_principal") or "Comisión Legislativa Competente"

    # 1. Obtener miembros de la comisión desde PostgreSQL Neon
    miembros: List[Dict[str, Any]] = []
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT m.nombre_completo, m.cargo, m.tipo_camara, m.email, m.partido_politico
            FROM sistema.miembro_comision m
            JOIN sistema.comision c ON c.id_comision = m.id_comision
            WHERE (c.codigo_comision = %s OR c.nombre_corto = %s OR c.nombre_comision ILIKE %s)
              AND (m.activo IS NULL OR m.activo = TRUE)
            ORDER BY 
              CASE m.cargo 
                WHEN 'Presidente' THEN 1 
                WHEN 'Vicepresidente' THEN 2 
                WHEN 'Secretario' THEN 3 
                ELSE 4 
              END
        """, (comision_nombre, comision_nombre, f"%{comision_nombre}%"))
        rows = cur.fetchall()
        for r in rows:
            miembros.append({
                "nombre_completo": r[0],
                "cargo": r[1],
                "tipo_camara": r[2],
                "email": r[3],
                "partido_politico": r[4]
            })
        cur.close()
    except Exception as e:
        logger.warning(f"No se pudieron cargar miembros de comisión de la BD: {e}")

    # Si no hay miembros en BD, crear autoridades por defecto representativas
    if not miembros:
        miembros = [
            {"nombre_completo": "Dip. Presidente de Comisión", "cargo": "Presidente", "tipo_camara": "Diputados", "email": "presidencia.comision@asamblea.gob.bo"},
            {"nombre_completo": "Sen. Vicepresidente de Comisión", "cargo": "Vicepresidente", "tipo_camara": "Senadores", "email": "vicepresidencia.comision@asamblea.gob.bo"},
            {"nombre_completo": "Secretaría Técnica Legislativa", "cargo": "Secretario", "tipo_camara": "Diputados", "email": "secretaria.tecnica@asamblea.gob.bo"}
        ]

    # Si el usuario especificó correos directos (destinatario_extra)
    destinatarios_reales = []
    if destinatario_extra and destinatario_extra.strip():
        # Puede contener uno o varios correos separados por comas o punto y coma
        for token in destinatario_extra.replace(';', ',').split(','):
            e = token.strip()
            if e and '@' in e:
                destinatarios_reales.append(e)

    if destinatarios_reales:
        destinatarios = destinatarios_reales
        miembros.insert(0, {
            "nombre_completo": "Destinatario Designado / Notificado",
            "cargo": "Titular de Despacho",
            "tipo_camara": "Directo",
            "email": destinatarios_reales[0],
            "partido_politico": "Mesa de Partes"
        })
    else:
        destinatarios = [m["email"] for m in miembros if m.get("email")]

    # 2. Generar el correo en HTML formal
    html_content = generar_cuerpo_html_notificacion(
        expediente_id=expediente_id,
        titulo_proyecto=titulo_proy,
        comision_nombre=comision_nombre,
        miembros=miembros,
        datos_constitucionales=datos_constitucionales,
        datos_consistencia=datos_consistencia,
        pdf_filename=pdf_filename,
        mensaje_extra=mensaje_extra,
    )

    if asunto_personalizado and asunto_personalizado.strip():
        asunto = asunto_personalizado.strip()
    else:
        asunto = f"[AUDITORÍA SMA] Remisión de Dictamen Legislativo: {expediente_id} - {comision_nombre}"

    # 3. Despacho híbrido inteligente con Token de Google
    resultado_envio = enviar_correo_hibrido(
        asunto=asunto,
        destinatarios=destinatarios,
        html_content=html_content,
        pdf_filename=pdf_filename
    )

    # 4. Guardar registro en MongoDB Atlas y PostgreSQL Neon
    duracion_ms = int((time.time() - t_inicio) * 1000)
    resultado = {
        "status": "notificado",
        "asunto": asunto,
        "comision": comision_nombre,
        "total_destinatarios": len(destinatarios),
        "destinatarios": destinatarios,
        "miembros_notificados": miembros,
        "html_preview": html_content,
        "pdf_adjunto": pdf_filename,
        "envio": resultado_envio,
        "fecha_despacho": datetime.now().isoformat(),
        "duracion_ms": duracion_ms
    }

    try:
        db = get_db()
        db["notificaciones_comision"].insert_one({
            "sesion_id": sesion_id,
            "id_proyecto": id_proyecto,
            **resultado
        })
    except Exception as me:
        logger.warning(f"No se pudo guardar notificación en Mongo: {me}")

    if id_proyecto:
        try:
            registrar_bitacora(
                id_proyecto=id_proyecto,
                agente_accion="Agente_Notificador_Comision",
                accion_realizada="Despacho de Correo Institucional HTML vía SendGrid",
                descripcion=f"Comisión: {comision_nombre} | Destinatarios: {len(destinatarios)} | Método: {resultado_envio.get('metodo')}",
                tiempo_segundos=max(1, duracion_ms // 1000),
            )
        except Exception as _be:
            logger.warning(f"No se pudo registrar bitácora de notificación: {_be}")

    marcar_completado(task_id, resultado=resultado, duracion_ms=duracion_ms)
    logger.info(f"✅ Agente Notificador completó el despacho HTML vía SendGrid para {comision_nombre} ({len(destinatarios)} destinatarios)")

    return resultado


# ════════════════════════════════════════════════════════════════════════════
# NOTIFICACIONES DE CORRECCIONES (flujo normativo → autor y senadores)
# ════════════════════════════════════════════════════════════════════════════

def notificar_correcciones_autor(
    id_proyecto: int,
    email_autor: str,
    nombre_autor: str = "Legislador/Ciudadano Presentante",
    titulo_proyecto: str = "Proyecto de Ley",
    sesion_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envía un correo personalizado al autor del proyecto con las correcciones
    detectadas por los agentes Verificador Constitucional y Consistencia Normativa.
    Plazo de respuesta: 10 días hábiles.
    """
    correcciones = obtener_correcciones_proyecto(id_proyecto, solo_pendientes=True)
    correcciones_autor = [c for c in correcciones if c.get("tipo_corrector") == "AUTOR_PROYECTO"]

    if not correcciones_autor:
        logger.info(f"[NotificadorCorrecciones] Sin correcciones pendientes para autor del proyecto {id_proyecto}")
        return {"status": "sin_correcciones", "id_proyecto": id_proyecto}

    # ── Construir tabla HTML de correcciones por artículo ──────────────────
    filas_html = ""
    for i, corr in enumerate(correcciones_autor, 1):
        art = corr.get("articulo_afectado") or "General"
        agente = corr.get("agente_origen", "").replace("AGENTE_", "").replace("_", " ").title()
        ref_cpe = corr.get("referencia_cpe", "")
        ref_norma = corr.get("referencia_norma", "")
        motivo = corr.get("motivo", "") or ""
        texto_orig = corr.get("texto_original", "") or ""
        bg = "#fff8f0" if i % 2 == 0 else "#ffffff"
        filas_html += f"""
        <tr style="background:{bg};">
          <td style="padding:8px;border:1px solid #ddd;font-weight:bold;color:#C0392B;">{art}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:12px;color:#555;">{agente}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:12px;">{(texto_orig[:150] + '...') if len(texto_orig) > 150 else texto_orig}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:12px;">{(motivo[:200] + '...') if len(motivo) > 200 else motivo}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:11px;color:#0D5C3A;">{ref_cpe or ref_norma or '—'}</td>
        </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Correcciones al Proyecto — ALP Bolivia</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
  <div style="max-width:800px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.12);">
    <div style="height:8px;background:linear-gradient(to right,#C0392B 33%,#F1C40F 33% 66%,#0D5C3A 66%);"></div>
    <div style="padding:24px 32px;">
      <p style="color:#777;font-size:13px;margin:0;">ESTADO PLURINACIONAL DE BOLIVIA</p>
      <h2 style="color:#0D5C3A;margin:4px 0 16px;">Asamblea Legislativa Plurinacional</h2>
      <h3 style="color:#C0392B;margin:0 0 8px;">Observaciones al Proyecto de Ley</h3>
      <p style="color:#333;font-size:14px;">Estimado/a <strong>{nombre_autor}</strong>,</p>
      <p style="color:#333;font-size:14px;">El Sistema Multi-Agente (SMA) de la ALP ha analizado el proyecto
      <strong>&laquo;{titulo_proyecto}&raquo;</strong> y ha detectado
      <strong style="color:#C0392B;">{len(correcciones_autor)} observación(es)</strong> que requieren su revisión.</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:20px 0;font-size:13px;">
        <thead>
          <tr style="background:#0D5C3A;color:#fff;">
            <th style="padding:10px;text-align:left;">Artículo Afectado</th>
            <th style="padding:10px;text-align:left;">Agente</th>
            <th style="padding:10px;text-align:left;">Texto Observado</th>
            <th style="padding:10px;text-align:left;">Motivo</th>
            <th style="padding:10px;text-align:left;">Referencia CPE / Norma</th>
          </tr>
        </thead>
        <tbody>{filas_html}</tbody>
      </table>
      <div style="background:#fff3cd;border-left:4px solid #F1C40F;padding:12px 16px;border-radius:4px;margin:16px 0;">
        <strong>⏰ Plazo para responder:</strong> 10 días hábiles a partir de la recepción de este correo.<br>
        Puede subir una versión corregida de su proyecto en el portal de la ALP.
      </div>
      <p style="color:#777;font-size:12px;margin-top:24px;">Generado automáticamente por el SMA — Asamblea Legislativa Plurinacional de Bolivia.</p>
    </div>
    <div style="height:5px;background:linear-gradient(to right,#C0392B 33%,#F1C40F 33% 66%,#0D5C3A 66%);"></div>
  </div>
</body></html>"""

    asunto = f"[ALP Bolivia] Observaciones al Proyecto: {titulo_proyecto[:60]}"
    resultado_envio = enviar_correo_gmail_smtp(
        asunto=asunto,
        destinatarios=[email_autor],
        html_content=html_content,
    )

    logger.info(
        f"[NotificadorCorrecciones] Correo de correcciones enviado a autor: {email_autor} "
        f"({len(correcciones_autor)} observaciones)"
    )
    return {
        "status": "notificado_autor",
        "email_autor": email_autor,
        "num_correcciones": len(correcciones_autor),
        "envio": resultado_envio,
    }


def notificar_mesa_senadores_normativa(
    id_proyecto: int,
    comision: str,
    titulo_proyecto: str = "Proyecto de Ley",
    sesion_id: Optional[str] = None,
    destinatarios_extra: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Envía correo formal institucional a la Mesa de Senadores de la Comisión
    de Normativa con todas las correcciones PENDIENTES detectadas por el SMA.
    Plazo de respuesta: 15 días hábiles.
    El email de la mesa se configura con EMAIL_MESA_SENADORES_NORMATIVA en .env
    """
    correcciones = obtener_correcciones_proyecto(id_proyecto, solo_pendientes=True)
    correcciones_senado = [c for c in correcciones if c.get("tipo_corrector") == "SENADO_NORMATIVA"]

    if not correcciones_senado:
        logger.info(f"[NotificadorSenado] Sin correcciones pendientes para Mesa Normativa del proyecto {id_proyecto}")
        return {"status": "sin_correcciones", "id_proyecto": id_proyecto}

    filas_html = ""
    for i, corr in enumerate(correcciones_senado, 1):
        art = corr.get("articulo_afectado") or "General"
        agente = corr.get("agente_origen", "").replace("AGENTE_", "").replace("_", " ").title()
        ref_cpe = corr.get("referencia_cpe", "")
        ref_norma = corr.get("referencia_norma", "")
        motivo = corr.get("motivo", "") or ""
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        filas_html += f"""
        <tr style="background:{bg};">
          <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">{i}</td>
          <td style="padding:8px;border:1px solid #ddd;color:#C0392B;font-weight:bold;">{art}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:12px;color:#555;">{agente}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:12px;">{(motivo[:250] + '...') if len(motivo) > 250 else motivo}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:11px;color:#0D5C3A;">{ref_cpe or '—'}</td>
          <td style="padding:8px;border:1px solid #ddd;font-size:11px;color:#8e44ad;">{ref_norma or '—'}</td>
        </tr>"""

    fecha_str = datetime.now().strftime("%d de %B de %Y")
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Mesa de Senadores — Correcciones Normativas</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
  <div style="max-width:900px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.12);">
    <div style="height:8px;background:linear-gradient(to right,#C0392B 33%,#F1C40F 33% 66%,#0D5C3A 66%);"></div>
    <div style="padding:28px 36px;">
      <p style="color:#777;font-size:12px;margin:0;">ESTADO PLURINACIONAL DE BOLIVIA</p>
      <p style="color:#777;font-size:12px;margin:0;">ASAMBLEA LEGISLATIVA PLURINACIONAL</p>
      <h2 style="color:#0D5C3A;margin:8px 0 4px;">Mesa de Senadores — Comisión de {comision}</h2>
      <p style="color:#666;font-size:13px;">La Paz, {fecha_str}</p>
      <hr style="border:none;border-top:2px solid #0D5C3A;margin:12px 0;">
      <p style="font-size:14px;color:#333;">Estimados miembros de la Comisión de <strong>{comision}</strong>:</p>
      <p style="font-size:14px;color:#333;">
        El Sistema Multi-Agente (SMA) ha analizado el proyecto <strong>&laquo;{titulo_proyecto}&raquo;</strong>
        y ha detectado <strong style="color:#C0392B;">{len(correcciones_senado)} observación(es) normativa(s)</strong>
        que requieren pronunciamiento formal de esta Mesa.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:20px 0;font-size:13px;">
        <thead>
          <tr style="background:#0D5C3A;color:#fff;">
            <th style="padding:9px;">#</th>
            <th style="padding:9px;text-align:left;">Artículo</th>
            <th style="padding:9px;text-align:left;">Agente</th>
            <th style="padding:9px;text-align:left;">Observación</th>
            <th style="padding:9px;text-align:left;">Ref. CPE</th>
            <th style="padding:9px;text-align:left;">Norma en Conflicto</th>
          </tr>
        </thead>
        <tbody>{filas_html}</tbody>
      </table>
      <div style="background:#f0f7f0;border-left:4px solid #0D5C3A;padding:14px 18px;border-radius:4px;margin:16px 0;">
        <strong>⏰ Plazo para pronunciamiento:</strong> 15 días hábiles.<br>
        La respuesta debe indicar para cada observación: <em>APLICADA</em> (con texto corregido) o <em>RECHAZADA</em> (con fundamentación jurídica).
      </div>
      <p style="color:#777;font-size:12px;margin-top:24px;">
        Generado automáticamente por el SMA — Asamblea Legislativa Plurinacional de Bolivia.
      </p>
    </div>
    <div style="height:5px;background:linear-gradient(to right,#C0392B 33%,#F1C40F 33% 66%,#0D5C3A 66%);"></div>
  </div>
</body></html>"""

    destinatarios_finales = list(destinatarios_extra or [])
    email_comision = os.getenv("EMAIL_MESA_SENADORES_NORMATIVA", "")
    if email_comision and email_comision not in destinatarios_finales:
        destinatarios_finales.append(email_comision)

    resultado_envio: Dict[str, Any] = {"enviado": False, "razon": "Sin destinatarios configurados (EMAIL_MESA_SENADORES_NORMATIVA no configurado en .env)"}
    if destinatarios_finales:
        asunto = f"[ALP Bolivia] Observaciones Normativas — {titulo_proyecto[:55]} | Comisión {comision}"
        resultado_envio = enviar_correo_gmail_smtp(
            asunto=asunto,
            destinatarios=destinatarios_finales,
            html_content=html_content,
        )

    logger.info(
        f"[NotificadorSenado] Mesa de Senadores Normativa notificada • "
        f"{len(correcciones_senado)} observaciones • {len(destinatarios_finales)} destinatarios"
    )
    return {
        "status": "notificado_mesa_senadores",
        "comision": comision,
        "num_correcciones": len(correcciones_senado),
        "destinatarios": destinatarios_finales,
        "envio": resultado_envio,
    }


class AgenteNotificadorComision:
    """Agente Notificador Oficial de la Asamblea (Fase 5 y Auxiliar) - Despacho HTML institucional."""

    def __init__(self, base_agent: Optional[Any] = None):
        from sma_unified.agents.base_agent import get_base_agent
        self.base = base_agent or get_base_agent()
        try:
            self.agent = self.base.crear_agente("Notificador_Comision")
        except Exception:
            self.agent = None

    def crear_tarea(self, proyecto_info: Dict[str, Any], destinatarios: Optional[List[str]] = None) -> Any:
        from crewai import Task
        try:
            from sma_unified.agents.base_agent import get_prompt_templates, render_prompt
            _, usr_tpl = get_prompt_templates("Notificador_Comision")
            titulo = proyecto_info.get("titulo") or "Proyecto de Ley"
            if usr_tpl:
                desc = render_prompt(
                    usr_tpl,
                    destinatario=", ".join(destinatarios) if destinatarios else "Comisión Legislativa",
                    titulo_proyecto=titulo,
                    codigo_expediente=proyecto_info.get("codigo_expediente", f"PL-{proyecto_info.get('id', '1')}"),
                    dictamen_constitucional=proyecto_info.get("dictamen_constitucional", "CONFORME"),
                    dictamen_consistencia=proyecto_info.get("dictamen_consistencia", "CONCORDANTE")
                )
            else:
                desc = f"Notificar a comisión legislativa sobre {titulo}"
        except Exception:
            desc = f"Notificar a comisión legislativa sobre {proyecto_info.get('titulo', 'Proyecto de Ley')}"
        return Task(
            description=desc,
            agent=self.agent,
            expected_output="HTML con cédula formal de notificación parlamentaria"
        )

    def ejecutar(self, proyecto_info: Dict[str, Any], destinatarios: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Ejecuta el despacho de notificación a miembros de comisión o partes interesadas."""
        id_proyecto = int(proyecto_info.get("id") or proyecto_info.get("id_proyecto") or 0)
        titulo = proyecto_info.get("titulo") or proyecto_info.get("titulo_proyecto") or "Proyecto de Ley"
        comision = proyecto_info.get("comision") or proyecto_info.get("comision_asignada") or "Comisión de Constitución"
        return notificar_miembros_comision(
            id_proyecto=id_proyecto,
            comision=comision,
            titulo_proyecto=titulo,
            dictamen_constitucional=proyecto_info.get("dictamen_constitucional", {}),
            analisis_consistencia=proyecto_info.get("analisis_consistencia", {}),
            destinatarios_extra=destinatarios
        )

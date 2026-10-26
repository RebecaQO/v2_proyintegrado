"""
Cliente LLM resiliente para tareas de razonamiento y clasificación (NVIDIA NIM)
================================================================================
Implementa la arquitectura de alta resiliencia recomendada para producción:
1. Selección de modelos de texto puro de ultra-baja latencia (evita multimodales/vision).
2. Circuit Breaker: 3 fallos consecutivos abren el circuito por 30s para evitar
   que un modelo defectuoso bloquee o ralentice el pipeline.
3. Política de timeout robusta: connect=30s, read=90s para evitar falsos positivos
   durante generaciones extensas normales.
4. Soporte transparente para `response_format={"type": "json_object"}` con degradación
   suave si un modelo específico no lo soporta.
5. Registro continuo de latencias y métricas (P50, P95, tasa de timeouts y fallos).
"""
import collections
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from datetime import datetime
import json
import re
import time
from threading import BoundedSemaphore
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("llm_client")

from sma_unified.config import settings

NVIDIA_API_BASE = settings.NVIDIA_BASE_URL.rstrip("/")

# Compartido por los dos agentes, incluso cuando corren en paralelo.
_AUDITORIA_LLM_SLOTS = BoundedSemaphore(2)
# Retiro confirmado por HTTP 410 en el proveedor; se amplía durante la sesión.
_MODELOS_RETIRADOS: Set[str] = {"z-ai/glm-5.2"}
_AUDIT_DEADLINE = ContextVar("sma_audit_deadline", default=None)


@contextmanager
def limite_tiempo_auditoria(segundos: float):
    """Limita las llamadas LLM de un cotejo y sus tareas paralelas."""
    deadline = time.monotonic() + max(0.1, float(segundos))
    token = _AUDIT_DEADLINE.set(deadline)
    try:
        yield deadline
    finally:
        _AUDIT_DEADLINE.reset(token)


def map_con_contexto_auditoria(executor, funcion, elementos):
    """Mantiene el presupuesto temporal al enviar análisis a hilos de trabajo."""
    futuros = [executor.submit(copy_context().run, funcion, elemento) for elemento in elementos]
    return [futuro.result() for futuro in futuros]


def _timeout_con_limite(timeout, deadline):
    restante = deadline - time.monotonic()
    if restante < 8.0:
        raise TimeoutError("Se agotó el tiempo máximo de auditoría")
    if isinstance(timeout, (int, float)):
        connect, read = 5.0, float(timeout)
    elif isinstance(timeout, (tuple, list)) and len(timeout) == 2:
        connect, read = float(timeout[0]), float(timeout[1])
    else:
        connect, read = 5.0, 30.0
    connect = min(connect, max(0.1, restante * 0.15))
    read = min(read, max(0.1, restante - connect))
    return (connect, read)


def chat_completion_auditoria(**kwargs: Any) -> Tuple[str, str]:
    """Prioriza el respaldo que respondió y limita la carga conjunta a NVIDIA."""
    modelo_preferido = kwargs.pop("modelo_preferido", settings.LLM_MODEL_CONSISTENCIA)
    deadline = _AUDIT_DEADLINE.get()
    espera = max(0.05, deadline - time.monotonic()) if deadline else None
    if not _AUDITORIA_LLM_SLOTS.acquire(timeout=espera):
        raise TimeoutError("Se agotó el tiempo de espera para ejecutar la auditoría")
    try:
        # La lista general filtra el catálogo NIM; no confiar en un .env antiguo.
        disponibles = _lista_modelos_razonamiento()
        # Los cotejos son de texto: evitar el modelo Omni que devuelve
        # ResourceExhausted y priorizar respaldos antes de razonadores largos.
        modelos_texto = [m for m in disponibles if not any(
            marca in m.lower() for marca in ("omni", "vision", "-vl-"))]
        disponibles = modelos_texto if modelos_texto else disponibles
        prioridad = [modelo_preferido, settings.LLM_MODEL_CONSISTENCIA,
                     settings.LLM_MODEL_CREW, "moonshotai/kimi-k3", settings.LLM_MODEL_NVIDIA]
        modelos = sorted(disponibles, key=lambda m: prioridad.index(m) if m in prioridad else len(prioridad))
        modelos = [m for m in modelos if m not in _MODELOS_RETIRADOS]
        if (modelo_preferido and modelo_preferido not in _MODELOS_RETIRADOS and modelo_preferido not in modelos):
            # El catálogo puede estar desactualizado; intentar primero el modelo
            # solicitado y dejar que el fallback actúe si NIM lo rechaza.
            modelos.insert(0, modelo_preferido)
        if not modelos:
            raise RuntimeError("No hay modelos de auditoría disponibles en el catálogo NIM")
        # connect también afecta la negociación TLS: 5s era insuficiente.
        # Respetar los límites definidos por cada etapa auditora. Antes se
        # reemplazaban todos por 30/60s, alargando incluso los cotejos que
        # especificaban un timeout corto para respuestas JSON.
        kwargs.setdefault("timeout", (30, 60))
        kwargs.setdefault("max_model_attempts", 3)
        kwargs.update(modelos=modelos, require_final_content=True)
        kwargs["deadline_monotonic"] = deadline
        if deadline:
            kwargs["timeout"] = _timeout_con_limite(kwargs["timeout"], deadline)
        return chat_completion_resiliente(**kwargs)
    finally:
        _AUDITORIA_LLM_SLOTS.release()

# ── Circuit Breaker State ──────────────────────────────────────────────────
CIRCUIT_FAILURE_THRESHOLD: int = 3
CIRCUIT_COOLDOWN_SECONDS: float = 20.0   # reducido: ReadTimeouts son transitorios

_CIRCUIT_FAILURES: Dict[str, int] = collections.defaultdict(int)
_CIRCUIT_OPEN_UNTIL: Dict[str, float] = collections.defaultdict(float)

# ── Latency Metrics History (Últimas 250 llamadas) ──────────────────────────
_LATENCY_HISTORY: collections.deque = collections.deque(maxlen=250)

# ── Caché de Modelos Disponibles en NVIDIA NIM ─────────────────────────────
_CACHE_MODELOS_ACTIVOS: Set[str] = set()
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SEGUNDOS: float = 3600.0  # 1 hora


def _reparar_json_truncado(s: str) -> str:
    """
    Intenta reparar de forma heurística un JSON truncado o incompleto 
    agregando comillas dobles y llaves/corchetes de cierre faltantes.
    """
    s = s.strip()
    if not s:
        return s

    # Limpiar comas, dos puntos o barras de escape colgantes al final del texto truncado
    s = re.sub(r'[\,:\\]+\s*$', '', s)

    # Verificar si hay comillas dobles sin cerrar
    num_quotes = len(re.findall(r'(?<!\\)"', s))
    if num_quotes % 2 != 0:
        s += '"'

    # Balancear estructuras de llaves {} y corchetes []
    pila = []
    en_cadena = False
    escape = False

    for char in s:
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            en_cadena = not en_cadena
            continue
        if not en_cadena:
            if char in '{[':
                pila.append(char)
            elif char in '}]':
                if pila:
                    top = pila[-1]
                    if (char == '}' and top == '{') or (char == ']' and top == '['):
                        pila.pop()

    for item in reversed(pila):
        if item == '{':
            s += '}'
        elif item == '[':
            s += ']'

    return s


def extraer_json_de_llm(texto: str) -> Any:
    """
    Extrae de forma extremadamente robusta una estructura JSON (dict o list) de la respuesta de un LLM.
    Maneja trazas de razonamiento (<think>...</think>), bloques markdown (```json ... ```),
    textos truncados por max_tokens y respuestas con comentarios preliminares/posteriores.
    """
    if not texto or not isinstance(texto, str):
        raise ValueError("Respuesta LLM vacía o no es una cadena de texto.")

    # 1. Eliminar etiquetas de razonamiento <think>...</think> o prefijos "Here's a thinking process..."
    texto_limpio = re.sub(r"<think>[\s\S]*?</think>", "", texto)
    texto_limpio = re.sub(
        r"Here's a thinking process[\s\S]*?(?=\{|\`\`\`json|\[)",
        "",
        texto_limpio,
        flags=re.IGNORECASE,
    ).strip()

    # 2. Intentar parsear directo
    try:
        return json.loads(texto_limpio)
    except Exception:
        pass

    # 3. Intentar auto-reparar si el JSON fue truncado al final por max_tokens
    try:
        return json.loads(_reparar_json_truncado(texto_limpio))
    except Exception:
        pass

    # 4. Extraer contenido dentro de bloques ```json ... ``` o ``` ... ```
    match_bloque = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", texto_limpio)
    if match_bloque:
        bloque = match_bloque.group(1).strip()
        try:
            return json.loads(bloque)
        except Exception:
            try:
                return json.loads(_reparar_json_truncado(bloque))
            except Exception:
                pass

    # 5. Buscar la primera ocurrencia de '{' o '[' y recortar desde allí
    idx_llave = texto_limpio.find('{')
    idx_corchete = texto_limpio.find('[')
    
    start_idx = -1
    if idx_llave != -1 and idx_corchete != -1:
        start_idx = min(idx_llave, idx_corchete)
    elif idx_llave != -1:
        start_idx = idx_llave
    elif idx_corchete != -1:
        start_idx = idx_corchete

    if start_idx != -1:
        candidato = texto_limpio[start_idx:]
        try:
            return json.loads(candidato)
        except Exception:
            try:
                return json.loads(_reparar_json_truncado(candidato))
            except Exception:
                pass

    # 6. Extracción por patrones de clave-valor si el JSON fue gravemente cortado
    recuperado: Dict[str, Any] = {}
    claves_comunes = [
        "clasificacion", "fundamento", "severidad", "fragmento_proyecto",
        "tipo_relacion", "justificacion", "sugerencia", "derogacion_tacita",
        "conflicto_especialidad", "riesgo", "articulo_inicio", "articulo_num",
        "nombre_comision", "razon_asignacion", "categoria", "confianza"
    ]
    for k in claves_comunes:
        m_str = re.search(rf'"{k}"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"?', texto_limpio)
        if m_str and m_str.group(1).strip():
            recuperado[k] = m_str.group(1).strip()
            continue
        m_bool = re.search(rf'"{k}"\s*:\s*(true|false)', texto_limpio, re.IGNORECASE)
        if m_bool:
            recuperado[k] = m_bool.group(1).lower() == "true"
            continue
        m_num = re.search(rf'"{k}"\s*:\s*(-?\d+(?:\.\d+)?)', texto_limpio)
        if m_num:
            try:
                recuperado[k] = float(m_num.group(1)) if "." in m_num.group(1) else int(m_num.group(1))
            except Exception:
                pass

    if recuperado:
        return recuperado

    # 7. Último intento desesperado con reparación del texto original
    return json.loads(_reparar_json_truncado(texto.strip()))


def obtener_modelos_disponibles_nim(force_refresh: bool = False) -> Set[str]:
    """
    Consulta dinámicamente el catálogo de modelos disponibles en NVIDIA NIM API (/v1/models).
    Utiliza una caché en memoria para evitar latencias en llamadas repetidas.
    """
    global _CACHE_MODELOS_ACTIVOS, _CACHE_TIMESTAMP
    ahora = time.time()

    if not force_refresh and _CACHE_MODELOS_ACTIVOS and (ahora - _CACHE_TIMESTAMP < _CACHE_TTL_SEGUNDOS):
        return _CACHE_MODELOS_ACTIVOS

    try:
        resp = requests.get(
            f"{NVIDIA_API_BASE}/models",
            headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
            timeout=8,
        )
        if resp.status_code == 200:
            datos = resp.json().get("data", [])
            modelos = {m.get("id") for m in datos if isinstance(m, dict) and "id" in m}
            if modelos:
                _CACHE_MODELOS_ACTIVOS = modelos
                _CACHE_TIMESTAMP = ahora
                logger.debug(f"[NVIDIA NIM] Catálogo actualizado dinámicamente ({len(modelos)} modelos disponibles).")
                return _CACHE_MODELOS_ACTIVOS
    except Exception as e:
        logger.warning(f"[NVIDIA NIM] No se pudo consultar /v1/models dinámicamente: {e}. Usando lista estática.")

    return _CACHE_MODELOS_ACTIVOS


def _lista_modelos_razonamiento() -> List[str]:
    """
    Ordena los dos modelos configurados en .env y valida el catálogo NVIDIA NIM.
    """
    preferidos = [
        settings.LLM_MODEL_CONSISTENCIA,
        settings.LLM_MODEL_NVIDIA,
        settings.LLM_MODEL_CREW,
    ]

    # Respaldo local limitado a los modelos elegidos para este sistema.
    respaldos_vigentes = [
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "moonshotai/kimi-k3",
    ]

    todos_candidatos = preferidos + respaldos_vigentes

    # Eliminar duplicados manteniendo orden
    vistos = set()
    candidatos_ordenados = []
    for m in todos_candidatos:
        if m and m not in vistos:
            vistos.add(m)
            candidatos_ordenados.append(m)

    # Filtrar contra catálogo si está accesible
    modelos_api = obtener_modelos_disponibles_nim()
    if modelos_api:
        candidatos_filtrados = [m for m in candidatos_ordenados if m in modelos_api]
        if candidatos_filtrados:
            return candidatos_filtrados

    return candidatos_ordenados


def _parece_modelo_no_disponible(status_code: Optional[int], texto_error: str) -> bool:
    if status_code in (404, 410):
        return True
    texto_error = (texto_error or "").lower()
    return any(s in texto_error for s in [
        "end of life", "no longer available", "gone", "model_not_found", "unknown model", "unavailable"
    ])


def _registrar_saturacion(modelo, respuesta):
    """Un 429/503 es transitorio; suspender el modelo sin declararlo retirado."""
    try:
        espera = float(respuesta.headers.get("Retry-After", 30))
        if not 0 < espera < 3600:
            espera = 30
    except (TypeError, ValueError, AttributeError):
        espera = 30
    espera = max(CIRCUIT_COOLDOWN_SECONDS, espera)
    _registrar_fallo_circuito(modelo, f"Proveedor saturado (HTTP {respuesta.status_code})")
    _CIRCUIT_OPEN_UNTIL[modelo] = max(_CIRCUIT_OPEN_UNTIL.get(modelo, 0), time.time() + espera)
    logger.warning(f"[NVIDIA] {modelo}: proveedor saturado; se omite durante {espera:.0f}s")


def _esta_circuito_abierto(modelo: str) -> Tuple[bool, float]:
    """
    Verifica si el Circuit Breaker para un modelo está actualmente abierto.
    Retorna (abierto: bool, segundos_restantes: float).

    Patrón de tres estados (CLOSED → OPEN → HALF-OPEN → CLOSED):
    Cuando el cooldown expira, el contador se reinicia a 0 para que el
    siguiente intento comience desde cero, sin acumular fallos históricos.
    """
    tiempo_limite = _CIRCUIT_OPEN_UNTIL.get(modelo, 0.0)
    ahora = time.time()
    if tiempo_limite > ahora:
        return True, round(tiempo_limite - ahora, 1)
    # El cooldown expiró: transición OPEN → HALF-OPEN.
    # Reiniciamos el contador para que la próxima falla cuente desde 0.
    if _CIRCUIT_FAILURES.get(modelo, 0) >= CIRCUIT_FAILURE_THRESHOLD:
        _CIRCUIT_FAILURES[modelo] = 0
        logger.info(f"[Circuit Breaker] Modelo '{modelo}' en HALF-OPEN: cooldown expirado, contador reiniciado.")
    return False, 0.0


def _registrar_exito_circuito(modelo: str) -> None:
    """Restablece los fallos consecutivos del modelo tras una respuesta exitosa."""
    _CIRCUIT_FAILURES[modelo] = 0
    _CIRCUIT_OPEN_UNTIL[modelo] = 0.0


def _registrar_fallo_circuito(modelo: str, motivo: str) -> None:
    """
    Incrementa el contador de fallos consecutivos y abre el circuito si alcanza el umbral.
    Solo emite ERROR en la primera apertura del circuito (al alcanzar exactamente el umbral);
    los fallos adicionales mientras el circuito ya está abierto solo refrescan el timestamp.
    """
    _CIRCUIT_FAILURES[modelo] += 1
    fallos = _CIRCUIT_FAILURES[modelo]
    if fallos == CIRCUIT_FAILURE_THRESHOLD:
        # Primera apertura: notificación ERROR prominente.
        _CIRCUIT_OPEN_UNTIL[modelo] = time.time() + CIRCUIT_COOLDOWN_SECONDS
        logger.error(
            f"[Circuit Breaker] Modelo '{modelo}' alcanzó {fallos} fallos consecutivos ({motivo}). "
            f"CIRCUITO ABIERTO: se omitirá durante {CIRCUIT_COOLDOWN_SECONDS}s."
        )
    elif fallos > CIRCUIT_FAILURE_THRESHOLD:
        # El circuito ya estaba abierto; solo refrescar el timestamp sin spam de ERRORs.
        _CIRCUIT_OPEN_UNTIL[modelo] = time.time() + CIRCUIT_COOLDOWN_SECONDS
        logger.debug(
            f"[Circuit Breaker] Modelo '{modelo}' ({fallos} fallos acum.): circuito ya abierto, cooldown refrescado."
        )
    else:
        logger.warning(
            f"[Circuit Breaker] Modelo '{modelo}' falló ({fallos}/{CIRCUIT_FAILURE_THRESHOLD}): {motivo}"
        )


def _registrar_metrica_latencia(
    modelo: str,
    duracion: float,
    status: str,
    status_code: Optional[int] = None,
    error_msg: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None,
) -> None:
    """Guarda un registro de latencia y estado en el búfer de métricas."""
    registro = {
        "timestamp": time.time(),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modelo": modelo,
        "duracion_segundos": round(duracion, 3),
        "status": status,
        "status_code": status_code,
        "error": error_msg[:180] if error_msg else None,
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "completion_tokens": (usage or {}).get("completion_tokens"),
        "total_tokens": (usage or {}).get("total_tokens"),
    }
    _LATENCY_HISTORY.append(registro)


def obtener_metricas_latencia_llm() -> Dict[str, Any]:
    """
    Calcula estadísticas detalladas de rendimiento (latencia P50, P95, tasa de éxito,
    estado del Circuit Breaker) sobre las últimas llamadas registradas.
    """
    historial = list(_LATENCY_HISTORY)
    ahora = time.time()

    # Estado de Circuit Breakers
    estado_circuitos = {}
    todos_modelos = set(_lista_modelos_razonamiento()) | set(_CIRCUIT_FAILURES.keys())
    for m in todos_modelos:
        abierto, rest = _esta_circuito_abierto(m)
        estado_circuitos[m] = {
            "circuito_abierto": abierto,
            "segundos_cooldown_restantes": rest,
            "fallos_consecutivos": _CIRCUIT_FAILURES.get(m, 0),
            "umbral": CIRCUIT_FAILURE_THRESHOLD,
        }

    # Métricas agregadas por modelo
    stats_por_modelo: Dict[str, Any] = {}
    for item in historial:
        m = item["modelo"]
        if m not in stats_por_modelo:
            stats_por_modelo[m] = {
                "total_llamadas": 0,
                "exitosas": 0,
                "timeouts": 0,
                "errores": 0,
                "latencias": [],
            }
        s = stats_por_modelo[m]
        s["total_llamadas"] += 1
        st = item["status"]
        if st == "ok":
            s["exitosas"] += 1
            s["latencias"].append(item["duracion_segundos"])
        elif st == "timeout":
            s["timeouts"] += 1
        else:
            s["errores"] += 1

    # Calcular P50, P95 y promedio
    resumen_modelos = {}
    for m, s in stats_por_modelo.items():
        lats = sorted(s["latencias"])
        n = len(lats)
        p50 = round(lats[int(n * 0.5)], 2) if n > 0 else 0.0
        p95 = round(lats[min(int(n * 0.95), n - 1)], 2) if n > 0 else 0.0
        avg = round(sum(lats) / n, 2) if n > 0 else 0.0
        resumen_modelos[m] = {
            "total": s["total_llamadas"],
            "exitosas": s["exitosas"],
            "timeouts": s["timeouts"],
            "errores": s["errores"],
            "tasa_exito_pct": round((s["exitosas"] / s["total_llamadas"]) * 100, 1) if s["total_llamadas"] > 0 else 0.0,
            "latencia_promedio_s": avg,
            "latencia_p50_s": p50,
            "latencia_p95_s": p95,
        }

    return {
        "total_registros": len(historial),
        "circuit_breakers": estado_circuitos,
        "rendimiento_por_modelo": resumen_modelos,
        "ultimas_llamadas": historial[-15:] if historial else [],
    }


def chat_completion_resiliente(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1200,
    modelos: Optional[List[str]] = None,
    timeout: Optional[Any] = None,
    response_format: Optional[Dict[str, str]] = None,
    max_model_attempts: Optional[int] = None,
    require_final_content: bool = False,
    razonamiento_breve: bool = False,
    deadline_monotonic: Optional[float] = None,
    **kwargs: Any,
) -> Tuple[str, str]:
    """
    Llama al endpoint de chat de NVIDIA NIM probando una lista de modelos en orden
    con Circuit Breaker activo, timeout ampliado (30s connect, 90s read) y registro
    continuo de latencia.
    """
    modelos = modelos or _lista_modelos_razonamiento()

    # Política de timeout recomendada: connect=30s, read=90s
    if timeout is None:
        timeout_efectivo = (30, 90)
    elif isinstance(timeout, (int, float)):
        timeout_efectivo = (30, float(timeout))
    else:
        timeout_efectivo = timeout

    ultimo_error: Optional[Exception] = None
    intentos = 0
    probados = []

    for modelo in modelos:
        if deadline_monotonic is not None:
            timeout_efectivo = _timeout_con_limite(timeout_efectivo, deadline_monotonic)
        if modelo in _MODELOS_RETIRADOS:
            ultimo_error = RuntimeError(f"Modelo '{modelo}' retirado del proveedor")
            continue
        # 1. Verificar Circuit Breaker
        abierto, seg_rest = _esta_circuito_abierto(modelo)
        if abierto:
            ultimo_error = RuntimeError(
                f"Modelo '{modelo}' suspendido por fallos previos ({seg_rest}s restantes)"
            )
            logger.warning(
                f"[Circuit Breaker] Modelo '{modelo}' con circuito ABIERTO. "
                f"Omitiendo directamente ({seg_rest}s restantes)..."
            )
            _registrar_metrica_latencia(
                modelo=modelo,
                duracion=0.0,
                status="circuit_breaker_open",
                error_msg=f"Circuito abierto por fallos consecutivos ({seg_rest}s restantes)",
            )
            continue

        if max_model_attempts is not None and intentos >= max_model_attempts:
            break
        intentos += 1
        probados.append(modelo)
        t_inicio = time.time()
        try:
            payload: Dict[str, Any] = {
                "model": modelo,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                payload["response_format"] = response_format
            payload.update(kwargs)
            if modelo.startswith("nvidia/nemotron-"):
                payload.setdefault("chat_template_kwargs", {"enable_thinking": False})
            if razonamiento_breve and modelo.startswith("openai/gpt-oss-"):
                # Parámetro oficial NIM para evitar agotar tokens en razonamiento
                # interno antes de entregar el JSON final del cotejo.
                payload["reasoning_effort"] = "low"

            # Intentar llamada al endpoint de NVIDIA NIM
            resp = requests.post(
                f"{NVIDIA_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                json=payload,
                timeout=timeout_efectivo,
            )
            t_fin = time.time()
            duracion = t_fin - t_inicio

            # Manejar caso en que el modelo no soporte response_format (HTTP 400 específico)
            if resp.status_code == 400 and response_format and "response_format" in resp.text.lower():
                logger.info(f"Modelo '{modelo}' no soporta 'response_format', reintentando sin él...")
                payload_sin_rf = dict(payload)
                payload_sin_rf.pop("response_format", None)
                if deadline_monotonic is not None:
                    timeout_efectivo = _timeout_con_limite(timeout_efectivo, deadline_monotonic)
                resp = requests.post(
                    f"{NVIDIA_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                    json=payload_sin_rf,
                    timeout=timeout_efectivo,
                )
                duracion = time.time() - t_inicio

            if resp.status_code in (429, 503):
                _registrar_saturacion(modelo, resp)
                _registrar_metrica_latencia(modelo=modelo, duracion=duracion,
                    status="saturado", status_code=resp.status_code, error_msg=resp.text[:250])
                ultimo_error = RuntimeError(f"Proveedor saturado para '{modelo}' (HTTP {resp.status_code})")
                continue

            # Verificar si el modelo fue retirado o no existe (404/410).
            if _parece_modelo_no_disponible(resp.status_code, resp.text):
                if resp.status_code == 410:
                    _MODELOS_RETIRADOS.add(modelo)
                motivo = f"HTTP {resp.status_code} - modelo no disponible"
                _registrar_fallo_circuito(modelo, motivo)
                _registrar_metrica_latencia(
                    modelo=modelo,
                    duracion=duracion,
                    status="error",
                    status_code=resp.status_code,
                    error_msg=resp.text,
                )
                ultimo_error = RuntimeError(f"Modelo '{modelo}' no disponible: {resp.text[:250]}")
                continue

            resp.raise_for_status()
            datos_resp = resp.json()
            msg_obj = datos_resp["choices"][0]["message"]
            usage = datos_resp.get("usage")

            # Priorizar contenido formal; si está vacío, usar reasoning_content
            contenido = (msg_obj.get("content") or "").strip()
            if not contenido and require_final_content:
                raise ValueError(
                    "El modelo no entregó una respuesta final "
                    f"(finish_reason={datos_resp['choices'][0].get('finish_reason')})"
                )
            if not contenido:
                contenido = (msg_obj.get("reasoning_content") or "").strip()
            if not contenido:
                raise ValueError("El proveedor devolvió una respuesta vacía")

            # Registrar éxito en Circuit Breaker y Métricas
            _registrar_exito_circuito(modelo)
            _registrar_metrica_latencia(
                modelo=modelo,
                duracion=duracion,
                status="ok",
                status_code=resp.status_code,
                usage=usage,
            )

            if modelo != modelos[0]:
                logger.info(f"Se usó el modelo de respaldo '{modelo}' ({duracion:.2f}s) en reemplazo del primario.")
            else:
                logger.debug(f"Respuesta exitosa de '{modelo}' en {duracion:.2f}s.")

            return contenido, modelo

        except (ValueError, KeyError, IndexError) as e:
            _registrar_fallo_circuito(modelo, f"Respuesta incompleta o inválida: {e}")
            _registrar_metrica_latencia(modelo=modelo, duracion=time.time()-t_inicio,
                status="respuesta_invalida", error_msg=str(e))
            ultimo_error = e
            continue

        except requests.exceptions.Timeout as e:
            duracion = time.time() - t_inicio
            motivo = f"ReadTimeout después de {duracion:.1f}s"
            _registrar_fallo_circuito(modelo, motivo)
            _registrar_metrica_latencia(
                modelo=modelo,
                duracion=duracion,
                status="timeout",
                error_msg=str(e),
            )
            ultimo_error = e
            continue

        except requests.exceptions.RequestException as e:
            duracion = time.time() - t_inicio
            motivo = f"RequestException: {e}"
            _registrar_fallo_circuito(modelo, motivo)
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            _registrar_metrica_latencia(
                modelo=modelo,
                duracion=duracion,
                status="error",
                status_code=status_code,
                error_msg=str(e),
            )
            ultimo_error = e
            continue

    raise RuntimeError(
        f"Ningún modelo LLM de razonamiento disponible respondió (probados: {', '.join(probados) or 'ninguno: circuitos abiertos'}). "
        f"Último error: {ultimo_error}"
    )

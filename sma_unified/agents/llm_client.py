"""
Cliente LLM resiliente para tareas de razonamiento (NVIDIA NIM)
==================================================================
Los modelos de terceros en el catálogo de NVIDIA NIM (sobre todo la familia
GLM de Z.ai) rotan de versión con mucha frecuencia y quedan "end of life"
(HTTP 410 Gone) de un día para otro, sin que el código tenga que cambiar de
proveedor. Esta capa prueba, en orden, una lista de modelos candidatos y
sigue automáticamente con el siguiente si el actual ya no está disponible
— así una ingesta o una respuesta del chat no se cae solo porque NVIDIA
retiró un modelo puntual.

Uso:
    contenido, modelo_usado = chat_completion_resiliente(
        messages=[...], temperature=0.2, max_tokens=1000,
    )

Si el modelo configurado (`settings.LLM_MODEL_CONSISTENCIA`) deja de
funcionar seguido, lo más simple es actualizar esa variable en el .env —
esta capa es una red de seguridad, no un reemplazo de mantener el modelo
al día.
"""
import json
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("llm_client")

from sma_unified.config import settings

NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1"

# Caché en memoria para los modelos disponibles en NVIDIA NIM
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
        "nombre_comision", "razon_asignacion"
    ]
    for k in claves_comunes:
        # String value (maneja con o sin comilla de cierre)
        m_str = re.search(rf'"{k}"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"?', texto_limpio)
        if m_str and m_str.group(1).strip():
            recuperado[k] = m_str.group(1).strip()
            continue
        # Boolean value
        m_bool = re.search(rf'"{k}"\s*:\s*(true|false)', texto_limpio, re.IGNORECASE)
        if m_bool:
            recuperado[k] = m_bool.group(1).lower() == "true"
            continue
        # Number value
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
    Orden de preferencia de modelos activos en NVIDIA NIM API:
    1. Modelos explícitamente configurados en el .env / settings.
    2. Modelos vigentes probados de alta velocidad y fidelidad JSON.
    3. Filtrado automático contra los modelos activos consultados en la API.
    """
    # 1. Prioridad absoluta: lo configurado en .env
    preferidos = [
        settings.LLM_MODEL_CONSISTENCIA,
        settings.LLM_MODEL_NVIDIA,
        settings.LLM_MODEL_CREW,
    ]

    # 2. Modelos de respaldo modernos, comprobados activos, rápidos y 100% compatibles con JSON
    respaldos_vigentes = [
        "deepseek-ai/deepseek-v4-flash-0731",
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "openai/gpt-oss-20b",
        "z-ai/glm-5.3-flash",
        "nvidia/nemotron-3-super-120b-a12b",
    ]

    todos_candidatos = preferidos + respaldos_vigentes

    # Eliminar duplicados manteniendo orden
    vistos = set()
    candidatos_ordenados = []
    for m in todos_candidatos:
        if m and m not in vistos:
            vistos.add(m)
            candidatos_ordenados.append(m)

    # 3. Filtrar con la lista dinámica de modelos si está disponible
    modelos_api = obtener_modelos_disponibles_nim()
    if modelos_api:
        candidatos_filtrados = [m for m in candidatos_ordenados if m in modelos_api]
        if candidatos_filtrados:
            return candidatos_filtrados

    return candidatos_ordenados


def _parece_modelo_no_disponible(status_code: Optional[int], texto_error: str) -> bool:
    if status_code in (404, 410, 503):
        return True
    texto_error = (texto_error or "").lower()
    return any(s in texto_error for s in [
        "end of life", "no longer available", "gone", "model_not_found", "unknown model", "unavailable"
    ])


def chat_completion_resiliente(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 1500,
    modelos: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    **kwargs: Any,
) -> Tuple[str, str]:
    """
    Llama al endpoint de chat de NVIDIA NIM probando una lista de modelos en
    orden; si uno ya no está disponible (410/404/503), sigue con el siguiente.
    Timeout acotado para respuesta ultra-rápida.
    """
    modelos = modelos or _lista_modelos_razonamiento()
    timeout_efectivo = timeout or 10  # 10s máximo por intento para no bloquear el sistema
    ultimo_error: Optional[Exception] = None

    for modelo in modelos:
        try:
            payload: Dict[str, Any] = {
                "model": modelo,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            payload.update(kwargs)
            resp = requests.post(
                f"{NVIDIA_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                json=payload,
                timeout=timeout_efectivo,
            )
            if _parece_modelo_no_disponible(resp.status_code, resp.text):
                logger.warning(f"Modelo '{modelo}' no disponible ({resp.status_code}), probando el siguiente...")
                ultimo_error = RuntimeError(f"Modelo '{modelo}' no disponible: {resp.text[:300]}")
                continue
            resp.raise_for_status()
            contenido = resp.json()["choices"][0]["message"]["content"]
            if modelo != modelos[0]:
                logger.info(f"Se usó el modelo de respaldo '{modelo}' (el configurado '{modelos[0]}' no respondió).")
            return contenido, modelo
        except requests.exceptions.RequestException as e:
            logger.warning(f"Modelo '{modelo}' falló: {e}")
            ultimo_error = e
            continue

    raise RuntimeError(
        f"Ningún modelo de razonamiento disponible respondió (probados: {', '.join(modelos)}). "
        f"Último error: {ultimo_error}"
    )


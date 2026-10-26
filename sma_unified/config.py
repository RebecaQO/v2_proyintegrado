"""
Configuración unificada del Sistema Multi-Agente (SMA) Congreso.
Carga variables de entorno desde .env y provee settings tipados.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Carga .env ─────────────────────────────────────────────────────────────
def _load_env(env_path: Path):
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

_load_env(BASE_DIR / ".env")

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=str(BASE_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

        # ── LLM ────────────────────────────────────────────────────────────
        NVIDIA_API_KEY: str = Field(default="")
        NVIDIA_BASE_URL: str = Field(default="https://integrate.api.nvidia.com/v1")
        LLM_MODEL_CREW: str = Field(default="nvidia/nemotron-3.5-lightning-30b-a3b")
        LLM_MODEL_NVIDIA: str = Field(default="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

        # ── Perfiles de modelo por rol de agente (fuente oficial: .env) ─────
        # El YAML declara el PERFIL por agente; base_agent.py lo resuelve con
        # resolver_modelo_por_perfil(). Cambiar un modelo no exige tocar el YAML.
        LLM_MODELO_RAZONAMIENTO: str = Field(default="nvidia/nemotron-3-super-120b-a12b")
        LLM_MODELO_DETERMINISTA: str = Field(default="openai/gpt-oss-20b")
        LLM_MODELO_NORMATIVO: str = Field(default="nvidia/nemotron-3.5-lightning-30b-a3b")
        LLM_MODELO_CONVERSACIONAL: str = Field(default="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

        # ── Agente de Consistencia Normativa (embeddings + pgvector) ────────
        NVIDIA_EMBED_MODEL: str = Field(default="nvidia/nemotron-3-embed-1b")
        NVIDIA_EMBED_DIM: int = Field(default=2048)
        LLM_MODEL_CONSISTENCIA: str = Field(default="nvidia/nemotron-3.5-lightning-30b-a3b")
        UMBRAL_CONSISTENCIA: float = Field(default=0.55)
        TOP_K_CONSISTENCIA: int = Field(default=8)

        # ── MongoDB Atlas ──────────────────────────────────────────────────
        MONGO_URI: str = Field(default="")
        MONGO_DB: str = Field(default="sma_congreso")

        # ── PostgreSQL Neon ────────────────────────────────────────────────
        NEON_DATABASE_URL: str = Field(default="")

        # ── Google Drive ───────────────────────────────────────────────────
        GOOGLE_OAUTH_CLIENT_SECRETS: str = Field(default="client_secrets.json")
        GOOGLE_DRIVE_TOKEN_FILE: str = Field(default="token.json")
        GOOGLE_DRIVE_FOLDER_ID: str = Field(default="")

        # ── Sistema ────────────────────────────────────────────────────────
        AGENTE_VERSION: str = Field(default="2.0.0")
        MAX_REINTENTOS: int = Field(default=3)
        TIMEOUT_LLM_SEG: int = Field(default=120)

        @property
        def uploads_dir(self) -> Path:
            d = BASE_DIR / "data" / "uploads"
            d.mkdir(parents=True, exist_ok=True)
            return d

    settings = Settings()

except Exception:
    class SettingsFallback:
        def __init__(self):
            self.NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
            self.NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            self.LLM_MODEL_CREW = os.getenv("LLM_MODEL_CREW", "nvidia/nemotron-3.5-lightning-30b-a3b")
            self.LLM_MODEL_NVIDIA = os.getenv("LLM_MODEL_NVIDIA", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
            self.LLM_MODELO_RAZONAMIENTO = os.getenv("LLM_MODELO_RAZONAMIENTO", "nvidia/nemotron-3-super-120b-a12b")
            self.LLM_MODELO_DETERMINISTA = os.getenv("LLM_MODELO_DETERMINISTA", "openai/gpt-oss-20b")
            self.LLM_MODELO_NORMATIVO = os.getenv("LLM_MODELO_NORMATIVO", "nvidia/nemotron-3.5-lightning-30b-a3b")
            self.LLM_MODELO_CONVERSACIONAL = os.getenv("LLM_MODELO_CONVERSACIONAL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
            self.NVIDIA_EMBED_MODEL = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b")
            self.NVIDIA_EMBED_DIM = int(os.getenv("NVIDIA_EMBED_DIM", "2048"))
            self.LLM_MODEL_CONSISTENCIA = os.getenv("LLM_MODEL_CONSISTENCIA", "nvidia/nemotron-3.5-lightning-30b-a3b")
            self.UMBRAL_CONSISTENCIA = float(os.getenv("UMBRAL_CONSISTENCIA", "0.55"))
            self.TOP_K_CONSISTENCIA = int(os.getenv("TOP_K_CONSISTENCIA", "8"))
            self.MONGO_URI = os.getenv("MONGO_URI", "")
            self.MONGO_DB = os.getenv("MONGO_DB", "sma_congreso")
            self.NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL", "")
            self.GOOGLE_OAUTH_CLIENT_SECRETS = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", "client_secrets.json")
            self.GOOGLE_DRIVE_TOKEN_FILE = os.getenv("GOOGLE_DRIVE_TOKEN_FILE", "token.json")
            self.GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
            self.AGENTE_VERSION = os.getenv("AGENTE_VERSION", "2.0.0")
            self.MAX_REINTENTOS = int(os.getenv("MAX_REINTENTOS", "3"))
            self.TIMEOUT_LLM_SEG = int(os.getenv("TIMEOUT_LLM_SEG", "120"))

        @property
        def uploads_dir(self) -> Path:
            d = BASE_DIR / "data" / "uploads"
            d.mkdir(parents=True, exist_ok=True)
            return d

    settings = SettingsFallback()

# ── Resolución de perfiles de modelo ───────────────────────────────────────
# Catálogo de perfiles que el YAML puede declarar. El valor concreto del modelo
# vive SOLO en .env: esta tabla traduce perfil -> nombre de variable de entorno.
PERFILES_MODELO = {
    "razonamiento": "LLM_MODELO_RAZONAMIENTO",
    "determinista": "LLM_MODELO_DETERMINISTA",
    "normativo": "LLM_MODELO_NORMATIVO",
    "conversacional": "LLM_MODELO_CONVERSACIONAL",
}


def resolver_modelo_por_perfil(perfil: str, fallback: str = "") -> str:
    """Resuelve un perfil declarado en el YAML a su modelo definido en .env.

    Acepta tanto el nombre corto del perfil ("razonamiento") como la variable
    completa ("LLM_MODELO_RAZONAMIENTO") para tolerar YAML ya escritos con la
    forma larga. Devuelve ``fallback`` (por defecto LLM_MODEL_CREW) si el
    perfil es desconocido o la variable no está definida.
    """
    if not perfil:
        return fallback or getattr(settings, "LLM_MODEL_CREW", "")

    clave = str(perfil).strip()
    # ¿Declararon la variable entera en lugar del perfil corto?
    var = clave if clave in PERFILES_MODELO.values() else PERFILES_MODELO.get(clave.lower())

    if var:
        valor = getattr(settings, var, "") or os.getenv(var, "")
        if valor:
            return valor
    return fallback or getattr(settings, "LLM_MODEL_CREW", "")


# ── Nombres de Agentes (constantes) ───────────────────────────────────────
AGENTE_USUARIO = "Usuario"
AGENTE_DISTRIBUIDOR = "Agente_Distribuidor"
AGENTE_COMISION = "Agente_Comision_Legislativa"
AGENTE_VERIFICADOR = "Agente_Verificador_Constitucional"
AGENTE_ATENCION_CIUDADANA = "Agente_Atencion_Ciudadana"
AGENTE_CORRESPONDENCIA = "Agente_Gestion_Correspondencia"
AGENTE_CONSISTENCIA = "Agente_Consistencia_Normativa"

# ── Relaciones válidas del Agente de Consistencia Normativa ───────────────
TIPOS_RELACION_CONSISTENCIA = {
    "contradiccion", "repeticion", "vacio_llenado", "complementario", "sin_relacion"
}

# ── Categorías de clasificación ───────────────────────────────────────────
CATEGORIAS_VALIDAS = {
    "AGENTE_REGISTRO_LEGISLATIVO",
    "AGENTE_ATENCION_CIUDADANA",
    "AGENTE_GESTION_CORRESPONDENCIA",
}


# ── Cargadores de configuración YAML (CrewAI) ──────────────────────────────
def load_agents_yaml() -> dict:
    """Carga las definiciones de agentes desde config/agents.yaml."""
    import yaml
    yaml_path = Path(__file__).resolve().parent / "config" / "agents.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_tasks_yaml() -> dict:
    """Carga las definiciones de tareas desde config/tasks.yaml."""
    import yaml
    yaml_path = Path(__file__).resolve().parent / "config" / "tasks.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_control_aprobacion() -> dict:
    """Configuración de control de aprobación bicameral y permisos humanos."""
    import yaml
    path = Path(__file__).resolve().parent / "config" / "workflows.yaml"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as archivo:
                config = yaml.safe_load(archivo) or {}
            control = (config.get("workflows", {})
                       .get("Pipeline_Legislativo_Completo", {})
                       .get("etapas", {})
                       # La clave real en workflows.yaml es Fase_3_Actas_y_Bicameral;
                       # con el nombre anterior el YAML nunca se leía y siempre caía
                       # al default hardcodeado de abajo.
                       .get("Fase_3_Actas_y_Bicameral", {})
                       .get("control_aprobacion"))
            if control:
                return control
        except Exception:
            pass
    return {
        "requiere_aprobacion_humana": True,
        "roles_permitidos": ["Diputado", "Senador", "Admin", "Administrador"],
        "requiere_verificacion_normativa": True,
        "requiere_motivo_revision": True,
        "estados": ["PENDIENTE_APROBACION_HUMANA", "APROBADO_REVISION_HUMANA", "EN_REVISION"]
    }

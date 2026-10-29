"""
SMA Unified - Sistema Multi-Agente para Registro y Auditoría Legislativa
"""
import os

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_crewai_storage = os.path.join(_base_dir, ".temp_localappdata")
try:
    os.makedirs(_crewai_storage, exist_ok=True)
    os.environ["LOCALAPPDATA"] = _crewai_storage
    os.environ["CREWAI_STORAGE_DIR"] = _crewai_storage
except Exception:
    pass

__version__ = "2.0.0"
__all__ = ["__version__"]

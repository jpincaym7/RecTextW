"""Cifrado y descifrado de datos sensibles (API keys) usando Fernet."""
import base64
import json
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.utils.logger import get_logger

logger = get_logger()

_SALT = b"InnoTechVideoTutor2025"


@dataclass
class AIConfig:
    """Configuración de un proveedor de IA."""
    provider: str
    api_key: str
    model: str


class SecretsManager:
    """Gestiona el cifrado y descifrado de datos sensibles."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._fernet: Fernet | None = None

    def save_ai_config(self, config: AIConfig) -> None:
        """Cifra y guarda la configuración de IA."""
        data = json.dumps(asdict(config)).encode()
        encrypted = self._get_fernet().encrypt(data)
        self._config_path.write_bytes(encrypted)
        logger.info("Configuración de IA guardada (cifrada)")

    def load_ai_config(self) -> AIConfig | None:
        """Carga y descifra la configuración. Retorna None si no existe."""
        if not self._config_path.exists():
            return None
        try:
            encrypted = self._config_path.read_bytes()
            data = self._get_fernet().decrypt(encrypted)
            parsed = json.loads(data.decode())
            return AIConfig(**parsed)
        except Exception as exc:
            logger.warning("No se pudo descifrar la configuración: %s", exc)
            return None

    def clear(self) -> None:
        """Elimina la configuración guardada."""
        if self._config_path.exists():
            self._config_path.unlink()
            logger.info("Configuración de IA eliminada")

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            key = self._derive_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _derive_key(self) -> bytes:
        """Deriva la clave Fernet del hardware ID del equipo."""
        hardware_id = self._get_hardware_id()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_SALT,
            iterations=100_000,
        )
        raw = kdf.derive(hardware_id.encode())
        return base64.urlsafe_b64encode(raw)

    def _get_hardware_id(self) -> str:
        """Obtiene un identificador único del equipo."""
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "serialnumber"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "SerialNumber"]
            if lines:
                return lines[0]
        except Exception:
            pass
        import os
        return platform.node() + os.getlogin()

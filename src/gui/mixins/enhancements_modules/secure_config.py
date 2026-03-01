"""Secure config helpers extracted from enhancements mixin."""

import json
import logging
import os
from pathlib import Path
from typing import Dict

try:
    from cryptography.fernet import Fernet

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None

logger = logging.getLogger(__name__)


class SecureKeyStorage:
    """Encrypt/decrypt API keys if cryptography is available."""

    def __init__(self, key_file: str = "config/.keyfile"):
        self.key_file = Path(key_file)
        self._fernet = None
        self._init_encryption()

    def _init_encryption(self):
        if not HAS_CRYPTOGRAPHY:
            self._fernet = None
            return

        try:
            if self.key_file.exists():
                with open(self.key_file, "rb") as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                self.key_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.key_file, "wb") as f:
                    f.write(key)
                try:
                    import stat

                    os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)
                except Exception as e:
                    logger.debug("chmod key file failed: %s", e)

            self._fernet = Fernet(key)
        except Exception as e:
            logger.warning("secure key storage init failed: %s", e)
            self._fernet = None

    def encrypt(self, data: str) -> str:
        if self._fernet and data:
            try:
                return self._fernet.encrypt(data.encode()).decode()
            except Exception as e:
                logger.debug("encrypt failed, returning plain text: %s", e)
        return data

    def decrypt(self, data: str) -> str:
        if self._fernet and data:
            try:
                return self._fernet.decrypt(data.encode()).decode()
            except Exception as e:
                logger.debug("decrypt failed, returning raw value: %s", e)
        return data


class SecureConfigMixin:
    """Save/load encrypted API config values."""

    def _init_secure_storage(self):
        try:
            self.secure_storage = SecureKeyStorage()
        except ImportError:
            self.secure_storage = None

    def save_encrypted_config(self, config: Dict, path: str = "config/api_config.json"):
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        encrypted_config = dict(config)
        if self.secure_storage:
            for key in ["api_key", "key", "secret"]:
                if key in encrypted_config and encrypted_config[key]:
                    encrypted_config[key] = self.secure_storage.encrypt(encrypted_config[key])
                    encrypted_config[f"{key}_encrypted"] = True

        with open(config_path, "w") as f:
            json.dump(encrypted_config, f, indent=2)

    def load_encrypted_config(self, path: str = "config/api_config.json") -> Dict:
        config_path = Path(path)
        if not config_path.exists():
            return {}

        with open(config_path, "r") as f:
            config = json.load(f)

        if self.secure_storage:
            for key in ["api_key", "key", "secret"]:
                if config.get(f"{key}_encrypted") and key in config:
                    config[key] = self.secure_storage.decrypt(config[key])

        return config

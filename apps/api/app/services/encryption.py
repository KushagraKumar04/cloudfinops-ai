import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


class EncryptionError(Exception):
    pass


class EncryptionService:
    def __init__(self, key: str | None = None) -> None:
        settings = get_settings()
        raw = key or settings.encryption_key
        if not raw:
            raise EncryptionError(
                "ENCRYPTION_KEY is not configured. Generate one with: "
                "python -c \"import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
            )
        try:
            self.key = base64.urlsafe_b64decode(raw)
        except Exception as exc:
            raise EncryptionError("ENCRYPTION_KEY must be a base64-encoded 32-byte value") from exc
        if len(self.key) != 32:
            raise EncryptionError("ENCRYPTION_KEY must decode to exactly 32 bytes")
        self.aes = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self.aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str) -> str:
        raw = base64.urlsafe_b64decode(token)
        nonce, ciphertext = raw[:12], raw[12:]
        return self.aes.decrypt(nonce, ciphertext, None).decode("utf-8")


def encrypt_secret(plaintext: str) -> str:
    return EncryptionService().encrypt(plaintext)


def decrypt_secret(token: str) -> str:
    return EncryptionService().decrypt(token)
"""Audio object storage. Local filesystem backend for dev; the interface is deliberately
narrow (save/read/delete by key) so a future S3-compatible backend is a drop-in swap behind
`STORAGE_BACKEND`, per ARCHITECTURE.md."""

import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class LocalStorage:
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Recording keys are always "<uuid>/<uuid>.wav" (user_id/recording_id) — never
        # derived from user input — so there's no path-traversal surface to guard here.
        return self.base_path / key

    def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()


def get_storage() -> LocalStorage:
    if settings.storage_backend != "local":
        raise NotImplementedError(
            f"Storage backend '{settings.storage_backend}' is not implemented yet — only "
            "'local' is supported as of Stage 2."
        )
    return LocalStorage(settings.storage_local_path)


def recording_key(user_id: uuid.UUID, recording_id: uuid.UUID) -> str:
    return f"{user_id}/{recording_id}.wav"

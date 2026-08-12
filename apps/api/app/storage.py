"""Audio object storage. Local filesystem backend for dev, Supabase Storage for anywhere the
container's local disk isn't durable (e.g. Cloud Run, wiped on every restart/redeploy). The
interface is deliberately narrow (save/read/exists/delete by key) so either backend is a
drop-in swap behind `STORAGE_BACKEND`, per ARCHITECTURE.md."""

import uuid
from pathlib import Path
from typing import Protocol

from app.config import get_settings

settings = get_settings()


class ObjectStorage(Protocol):
    def save(self, key: str, data: bytes) -> str: ...
    def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


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


class SupabaseStorage:
    """Talks to a private Supabase Storage bucket using the service role key, which bypasses
    Row Level Security — recordings are never made directly fetchable from Supabase; every read
    still goes through our own authenticated, ownership-checked endpoint
    (`GET /api/v1/recordings/{id}/audio`), which downloads server-side and re-serves the bytes.
    """

    def __init__(self, url: str, service_role_key: str, bucket: str) -> None:
        from supabase import create_client

        self._bucket_name = bucket
        self._bucket = create_client(url, service_role_key).storage.from_(bucket)

    def save(self, key: str, data: bytes) -> str:
        # Recording keys are always freshly generated UUIDs (see recording_key) and originals
        # are never destructively overwritten, so a plain create — no upsert — matches actual
        # usage and fails loudly if a key were ever accidentally reused.
        self._bucket.upload(key, data, file_options={"content-type": "audio/wav"})
        return key

    def read(self, key: str) -> bytes:
        return self._bucket.download(key)

    def exists(self, key: str) -> bool:
        folder, _, filename = key.rpartition("/")
        entries = self._bucket.list(path=folder or None)
        return any(entry.get("name") == filename for entry in entries)

    def delete(self, key: str) -> None:
        self._bucket.remove([key])


def get_storage() -> ObjectStorage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_local_path)
    if settings.storage_backend == "supabase":
        return SupabaseStorage(
            settings.supabase_url, settings.supabase_service_role_key, settings.storage_bucket
        )
    raise NotImplementedError(
        f"Storage backend '{settings.storage_backend}' is not implemented — expected 'local' "
        "or 'supabase'."
    )


def recording_key(user_id: uuid.UUID, recording_id: uuid.UUID) -> str:
    return f"{user_id}/{recording_id}.wav"

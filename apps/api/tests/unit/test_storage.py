from unittest.mock import MagicMock, patch

import pytest

from app.storage import LocalStorage, SupabaseStorage


class TestLocalStorage:
    def test_save_then_read_round_trips(self, tmp_path) -> None:
        storage = LocalStorage(str(tmp_path))
        storage.save("u1/r1.wav", b"hello world")
        assert storage.read("u1/r1.wav") == b"hello world"

    def test_exists_reflects_real_presence(self, tmp_path) -> None:
        storage = LocalStorage(str(tmp_path))
        assert storage.exists("u1/r1.wav") is False
        storage.save("u1/r1.wav", b"data")
        assert storage.exists("u1/r1.wav") is True

    def test_delete_removes_the_file(self, tmp_path) -> None:
        storage = LocalStorage(str(tmp_path))
        storage.save("u1/r1.wav", b"data")
        storage.delete("u1/r1.wav")
        assert storage.exists("u1/r1.wav") is False

    def test_delete_is_a_noop_when_nothing_exists(self, tmp_path) -> None:
        storage = LocalStorage(str(tmp_path))
        storage.delete("u1/never-existed.wav")  # must not raise

    def test_save_creates_nested_user_directories(self, tmp_path) -> None:
        storage = LocalStorage(str(tmp_path))
        storage.save("some-user-id/some-recording-id.wav", b"data")
        assert (tmp_path / "some-user-id" / "some-recording-id.wav").read_bytes() == b"data"


class TestSupabaseStorage:
    """Mocks the `supabase` SDK client — no network calls, no real credentials needed. Confirms
    SupabaseStorage drives the SDK correctly and stays a true drop-in for the same
    save/read/exists/delete interface LocalStorage implements."""

    def _make_storage(self):
        with patch("supabase.create_client") as mock_create_client:
            mock_bucket = MagicMock()
            mock_create_client.return_value.storage.from_.return_value = mock_bucket
            storage = SupabaseStorage("https://x.supabase.co", "service-role-key", "recordings")
            return storage, mock_bucket, mock_create_client

    def test_save_uploads_with_wav_content_type(self) -> None:
        storage, mock_bucket, _ = self._make_storage()
        key = storage.save("u1/r1.wav", b"audio-bytes")
        mock_bucket.upload.assert_called_once_with(
            "u1/r1.wav", b"audio-bytes", file_options={"content-type": "audio/wav"}
        )
        assert key == "u1/r1.wav"

    def test_read_downloads_by_key(self) -> None:
        storage, mock_bucket, _ = self._make_storage()
        mock_bucket.download.return_value = b"audio-bytes"
        assert storage.read("u1/r1.wav") == b"audio-bytes"
        mock_bucket.download.assert_called_once_with("u1/r1.wav")

    def test_exists_true_when_key_present_in_folder_listing(self) -> None:
        storage, mock_bucket, _ = self._make_storage()
        mock_bucket.list.return_value = [{"name": "r1.wav"}, {"name": "r2.wav"}]
        assert storage.exists("u1/r1.wav") is True
        mock_bucket.list.assert_called_once_with(path="u1")

    def test_exists_false_when_key_absent_from_folder_listing(self) -> None:
        storage, mock_bucket, _ = self._make_storage()
        mock_bucket.list.return_value = [{"name": "some-other-file.wav"}]
        assert storage.exists("u1/r1.wav") is False

    def test_delete_removes_by_key(self) -> None:
        storage, mock_bucket, _ = self._make_storage()
        storage.delete("u1/r1.wav")
        mock_bucket.remove.assert_called_once_with(["u1/r1.wav"])

    def test_client_created_with_the_given_url_and_service_role_key(self) -> None:
        _storage, _bucket, mock_create_client = self._make_storage()
        mock_create_client.assert_called_once_with("https://x.supabase.co", "service-role-key")


class TestGetStorage:
    def test_unknown_backend_raises(self, monkeypatch) -> None:
        import app.storage as storage_module

        monkeypatch.setattr(storage_module.settings, "storage_backend", "s3")
        with pytest.raises(NotImplementedError):
            storage_module.get_storage()

    def test_local_backend_returns_local_storage(self, monkeypatch, tmp_path) -> None:
        import app.storage as storage_module

        monkeypatch.setattr(storage_module.settings, "storage_backend", "local")
        monkeypatch.setattr(storage_module.settings, "storage_local_path", str(tmp_path))
        assert isinstance(storage_module.get_storage(), LocalStorage)

    def test_supabase_backend_returns_supabase_storage(self, monkeypatch) -> None:
        import app.storage as storage_module

        monkeypatch.setattr(storage_module.settings, "storage_backend", "supabase")
        monkeypatch.setattr(storage_module.settings, "supabase_url", "https://x.supabase.co")
        monkeypatch.setattr(storage_module.settings, "supabase_service_role_key", "key")
        with patch("supabase.create_client"):
            assert isinstance(storage_module.get_storage(), SupabaseStorage)

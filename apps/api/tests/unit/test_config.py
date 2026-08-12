from app.config import Settings


def test_cors_origins_splits_and_trims() -> None:
    settings = Settings(api_cors_origins="http://a.test, http://b.test ,http://c.test")
    assert settings.cors_origins == ["http://a.test", "http://b.test", "http://c.test"]


def test_cors_origins_empty_string_gives_empty_list() -> None:
    settings = Settings(api_cors_origins="")
    assert settings.cors_origins == []


def test_defaults_are_sane() -> None:
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.storage_backend == "local"

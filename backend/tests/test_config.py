import pytest

from config import normalize_database_url, validate_origin


def test_normalizes_legacy_postgres_scheme():
    assert normalize_database_url("postgres://user:pass@host/db") == "postgresql://user:pass@host/db"


def test_leaves_postgresql_scheme_unchanged():
    value = "postgresql://user:pass@host/db"
    assert normalize_database_url(value) == value


def test_frontend_origin_rejects_paths():
    with pytest.raises(ValueError):
        validate_origin("https://example.com/a-path")


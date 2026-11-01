import pytest

from faultline.env import token


def test_token_strips_whitespace_and_newlines(monkeypatch):
    monkeypatch.setenv("X_TOKEN", "  abc123\n")
    assert token("X_TOKEN") == "abc123"


def test_token_rejects_empty_or_missing(monkeypatch):
    monkeypatch.setenv("X_TOKEN", " \n")
    with pytest.raises(RuntimeError, match="X_TOKEN"):
        token("X_TOKEN")
    monkeypatch.delenv("X_TOKEN")
    with pytest.raises(RuntimeError):
        token("X_TOKEN")

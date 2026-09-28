from core.ai.ai_local import dify_api_key, dify_headers
from core.config import config


def test_dify_api_key_leo_and_others(monkeypatch):
    monkeypatch.setattr(config, "AI_DIFY_API_KEY", "leo-key")
    monkeypatch.setattr(config, "AI_DIFY_DOUDOU_API_KEY", "doudou-key")

    assert dify_api_key("leo") == "leo-key"
    assert dify_api_key(" Leo ") == "leo-key"
    assert dify_api_key("other") == "doudou-key"
    assert dify_api_key("") == "doudou-key"
    assert dify_api_key(None) == "doudou-key"


def test_dify_headers_use_selected_key(monkeypatch):
    monkeypatch.setattr(config, "AI_DIFY_API_KEY", "leo-key")
    monkeypatch.setattr(config, "AI_DIFY_DOUDOU_API_KEY", "doudou-key")

    assert dify_headers("leo")["Authorization"] == "Bearer leo-key"
    assert dify_headers("doudou")["Authorization"] == "Bearer doudou-key"

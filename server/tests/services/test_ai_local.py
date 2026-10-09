from core.ai.ai_local import dify_api_key, dify_headers
from core.config import config


def _patch_keys(monkeypatch):
    monkeypatch.setattr(config, "AI_DIFY_API_KEY", "leo-key")
    monkeypatch.setattr(config, "AI_DIFY_ZHAOZHAO_API_KEY", "zhaozhao-key")
    monkeypatch.setattr(config, "AI_DIFY_CANCAN_API_KEY", "cancan-key")


def test_dify_api_key_by_user(monkeypatch):
    _patch_keys(monkeypatch)

    assert dify_api_key("leo") == "leo-key"
    assert dify_api_key(" Leo ") == "leo-key"
    assert dify_api_key("LEO") == "leo-key"

    assert dify_api_key("灿灿") == "cancan-key"
    assert dify_api_key(" 灿灿 ") == "cancan-key"

    assert dify_api_key("昭昭") == "zhaozhao-key"


def test_dify_api_key_fallback_to_zhaozhao(monkeypatch):
    """未单独配置的用户（如 紫夜）沿用改名前的兜底行为。"""
    _patch_keys(monkeypatch)

    assert dify_api_key("紫夜") == "zhaozhao-key"
    assert dify_api_key("other") == "zhaozhao-key"
    assert dify_api_key("") == "zhaozhao-key"
    assert dify_api_key(None) == "zhaozhao-key"


def test_zhaozhao_and_cancan_use_different_keys(monkeypatch):
    """灿灿换机器人后，必须与昭昭走不同应用。"""
    _patch_keys(monkeypatch)

    assert dify_api_key("昭昭") != dify_api_key("灿灿")


def test_dify_headers_use_selected_key(monkeypatch):
    _patch_keys(monkeypatch)

    assert dify_headers("leo")["Authorization"] == "Bearer leo-key"
    assert dify_headers("昭昭")["Authorization"] == "Bearer zhaozhao-key"
    assert dify_headers("灿灿")["Authorization"] == "Bearer cancan-key"

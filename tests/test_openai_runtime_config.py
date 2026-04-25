"""Нормализация имён моделей и fingerprint ключа."""
from app.services.openai_runtime_config import (
    fingerprint_openai_api_key,
    normalize_openai_model_id,
    resolve_chat_models_from_config,
)


def test_normalize_typo_gpt_4_1_min_to_mini():
    fixed, warn = normalize_openai_model_id("gpt-4.1-min", label="GPTS_MODEL")
    assert fixed == "gpt-4.1-mini"
    assert warn is not None and "опечатка" in warn


def test_normalize_correct_mini_unchanged():
    fixed, warn = normalize_openai_model_id("gpt-4.1-mini", label="GPTS_MODEL")
    assert fixed == "gpt-4.1-mini"
    assert warn is None


def test_fingerprint_masks_key():
    fp = fingerprint_openai_api_key("sk-test1234567890abcdefghij")
    assert "sk-" not in fp
    assert "sha256:" in fp
    assert "tail:" in fp


def test_resolve_chat_models_from_config_applies_alias():
    cfg = {"GPTS_MODEL": "gpt-4.1-min", "FALLBACK_MODEL": "gpt-4.1-nano"}
    g, f, warns = resolve_chat_models_from_config(cfg)
    assert g == "gpt-4.1-mini"
    assert f == "gpt-4.1-nano"
    assert len(warns) == 1

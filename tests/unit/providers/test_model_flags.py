"""Unit tests for model flag helpers against issue #1929.

Remote catalogs (DashScope, SiliconFlow, Ollama, vLLM listings, ...) ship
embedding entries without an explicit ``embedding: true`` flag, so
``is_embedding_model`` must also recognise common naming conventions —
mirroring how ``is_vision_model`` already keys off name hints.
"""

from __future__ import annotations

import pytest

from octop.infra.agents.providers.model_flags import (
    is_chat_eligible_model,
    is_embedding_model,
)

EMBEDDING_BY_NAME = [
    "text-embedding-3-small",  # OpenAI
    "text-embedding-v3",  # DashScope
    "qwen3.7-text-embedding-flash",  # DashScope (real-world case from #1929)
    "Qwen3-Embedding-8B",  # uppercase must match too
    "bge-m3",  # BAAI / Ollama
    "nomic-embed-text",  # Ollama builtin
    "bce-embedding-base_v1",  # NetEase BCE
    "e5-large-v2",
    "gte-large-zh",
    "bge-reranker-v2-m3",  # rerankers share the embedding picker
]

CHAT_MODELS = [
    "gpt-4o",
    "deepseek-chat",
    "qwen-max",
    "qwen3-235b-a22b",
    "glm-4.6",
    "claude-sonnet-4",
]


@pytest.mark.parametrize("model_id", EMBEDDING_BY_NAME)
def test_embedding_recognised_by_name_convention(model_id: str) -> None:
    assert is_embedding_model({"id": model_id}) is True


@pytest.mark.parametrize("model_id", CHAT_MODELS)
def test_chat_models_not_flagged_as_embedding(model_id: str) -> None:
    assert is_embedding_model({"id": model_id}) is False


def test_explicit_flags_still_win() -> None:
    assert is_embedding_model({"id": "any-model", "embedding": True}) is True
    assert is_embedding_model({"id": "any-model", "task": "embedding"}) is True


def test_onnx_provider_fallback_unchanged() -> None:
    assert (
        is_embedding_model({}, provider_name="onnx (local)", provider_api_key="onnx")
        is True
    )


def test_blank_or_missing_id_is_not_embedding() -> None:
    assert is_embedding_model({}) is False
    assert is_embedding_model({"id": ""}) is False


def test_chat_eligible_excludes_embedding_models() -> None:
    assert (
        is_chat_eligible_model({"id": "text-embedding-3-small", "enabled": True})
        is False
    )
    assert is_chat_eligible_model({"id": "gpt-4o", "enabled": True}) is True

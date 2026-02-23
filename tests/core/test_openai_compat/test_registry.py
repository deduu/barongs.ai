from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.server.openai_compat.registry import ModelRegistry


def _make_mock_orchestrator() -> AsyncMock:
    return AsyncMock()


class TestModelRegistry:
    def test_register_and_get(self) -> None:
        registry = ModelRegistry()
        orch = _make_mock_orchestrator()
        registry.register("test-model", orch)

        registered = registry.get("test-model")
        assert registered.model_id == "test-model"
        assert registered.orchestrator is orch
        assert registered.owned_by == "pormetheus"

    def test_get_unknown_model_raises(self) -> None:
        registry = ModelRegistry()
        with pytest.raises(KeyError, match="not-registered"):
            registry.get("not-registered")

    def test_get_error_lists_available(self) -> None:
        registry = ModelRegistry()
        registry.register("alpha", _make_mock_orchestrator())
        registry.register("beta", _make_mock_orchestrator())

        with pytest.raises(KeyError, match="alpha"):
            registry.get("gamma")

    def test_list_models_empty(self) -> None:
        registry = ModelRegistry()
        assert registry.list_models() == []

    def test_list_models(self) -> None:
        registry = ModelRegistry()
        registry.register("a", _make_mock_orchestrator())
        registry.register("b", _make_mock_orchestrator(), owned_by="custom")

        models = registry.list_models()
        assert len(models) == 2
        ids = {m.model_id for m in models}
        assert ids == {"a", "b"}

    def test_register_with_metadata(self) -> None:
        registry = ModelRegistry()
        orch = _make_mock_orchestrator()
        stream_agent = AsyncMock()

        registry.register(
            "my-model",
            orch,
            owned_by="my-org",
            description="A test model",
            streamable_agent=stream_agent,
        )

        registered = registry.get("my-model")
        assert registered.owned_by == "my-org"
        assert registered.description == "A test model"
        assert registered.streamable_agent is stream_agent

    def test_re_registration_overwrites(self) -> None:
        registry = ModelRegistry()
        orch1 = _make_mock_orchestrator()
        orch2 = _make_mock_orchestrator()

        registry.register("model", orch1)
        registry.register("model", orch2)

        registered = registry.get("model")
        assert registered.orchestrator is orch2
        assert len(registry.list_models()) == 1

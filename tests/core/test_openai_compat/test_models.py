from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.core.server.openai_compat.models import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelInfo,
    ModelListResponse,
    OpenAIChatMessage,
    OpenAIErrorDetail,
    OpenAIErrorResponse,
    UsageInfo,
)


class TestOpenAIChatMessage:
    def test_user_message(self) -> None:
        msg = OpenAIChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message_no_content(self) -> None:
        msg = OpenAIChatMessage(role="system")
        assert msg.content is None

    def test_valid_roles(self) -> None:
        for role in ("system", "user", "assistant", "tool"):
            msg = OpenAIChatMessage(role=role, content="x")
            assert msg.role == role


class TestChatCompletionRequest:
    def test_minimal_request(self) -> None:
        req = ChatCompletionRequest(
            model="test-model",
            messages=[OpenAIChatMessage(role="user", content="Hi")],
        )
        assert req.model == "test-model"
        assert len(req.messages) == 1
        assert req.stream is False
        assert req.temperature == 0.7
        assert req.max_tokens is None
        assert req.n == 1

    def test_streaming_request(self) -> None:
        req = ChatCompletionRequest(
            model="test-model",
            messages=[OpenAIChatMessage(role="user", content="Hi")],
            stream=True,
            temperature=0.5,
            max_tokens=100,
        )
        assert req.stream is True
        assert req.temperature == 0.5
        assert req.max_tokens == 100

    def test_requires_model(self) -> None:
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[OpenAIChatMessage(role="user", content="Hi")],
            )  # type: ignore[call-arg]

    def test_requires_messages(self) -> None:
        with pytest.raises(ValidationError):
            ChatCompletionRequest(model="m")  # type: ignore[call-arg]


class TestChatCompletionResponse:
    def test_generates_unique_ids(self) -> None:
        r1 = ChatCompletionResponse(
            model="m",
            choices=[
                ChatCompletionChoice(
                    message=OpenAIChatMessage(role="assistant", content="a")
                )
            ],
        )
        r2 = ChatCompletionResponse(
            model="m",
            choices=[
                ChatCompletionChoice(
                    message=OpenAIChatMessage(role="assistant", content="b")
                )
            ],
        )
        assert r1.id != r2.id
        assert r1.id.startswith("chatcmpl-")

    def test_default_fields(self) -> None:
        resp = ChatCompletionResponse(
            model="m",
            choices=[
                ChatCompletionChoice(
                    message=OpenAIChatMessage(role="assistant", content="x")
                )
            ],
        )
        assert resp.object == "chat.completion"
        assert isinstance(resp.created, int)
        assert resp.usage.prompt_tokens == 0

    def test_serialization_matches_openai_format(self) -> None:
        resp = ChatCompletionResponse(
            id="chatcmpl-test123",
            model="search-agent",
            choices=[
                ChatCompletionChoice(
                    message=OpenAIChatMessage(role="assistant", content="Hello!"),
                    finish_reason="stop",
                )
            ],
            usage=UsageInfo(prompt_tokens=5, completion_tokens=1, total_tokens=6),
        )
        data = json.loads(resp.model_dump_json())
        assert data["object"] == "chat.completion"
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert data["choices"][0]["message"]["content"] == "Hello!"
        assert data["choices"][0]["finish_reason"] == "stop"
        assert data["usage"]["total_tokens"] == 6


class TestChatCompletionChunk:
    def test_role_chunk(self) -> None:
        chunk = ChatCompletionChunk(
            id="chatcmpl-abc",
            created=1234567890,
            model="m",
            choices=[
                ChatCompletionChunkChoice(
                    delta=ChatCompletionChunkDelta(role="assistant"),
                )
            ],
        )
        assert chunk.object == "chat.completion.chunk"
        data = json.loads(chunk.model_dump_json())
        assert data["choices"][0]["delta"]["role"] == "assistant"
        assert data["choices"][0]["finish_reason"] is None

    def test_content_chunk(self) -> None:
        chunk = ChatCompletionChunk(
            id="chatcmpl-abc",
            created=1234567890,
            model="m",
            choices=[
                ChatCompletionChunkChoice(
                    delta=ChatCompletionChunkDelta(content="Hello"),
                )
            ],
        )
        data = json.loads(chunk.model_dump_json())
        assert data["choices"][0]["delta"]["content"] == "Hello"

    def test_finish_chunk(self) -> None:
        chunk = ChatCompletionChunk(
            id="chatcmpl-abc",
            created=1234567890,
            model="m",
            choices=[
                ChatCompletionChunkChoice(
                    delta=ChatCompletionChunkDelta(),
                    finish_reason="stop",
                )
            ],
        )
        data = json.loads(chunk.model_dump_json())
        assert data["choices"][0]["finish_reason"] == "stop"


class TestModelListResponse:
    def test_structure(self) -> None:
        resp = ModelListResponse(
            data=[
                ModelInfo(id="search-agent", owned_by="barongsai"),
                ModelInfo(id="chat-agent", owned_by="barongsai"),
            ]
        )
        assert resp.object == "list"
        assert len(resp.data) == 2
        assert resp.data[0].id == "search-agent"
        assert resp.data[0].object == "model"


class TestOpenAIErrorResponse:
    def test_error_format(self) -> None:
        err = OpenAIErrorResponse(
            error=OpenAIErrorDetail(
                message="Model not found",
                type="invalid_request_error",
                code="model_not_found",
            )
        )
        data = json.loads(err.model_dump_json())
        assert data["error"]["message"] == "Model not found"
        assert data["error"]["type"] == "invalid_request_error"

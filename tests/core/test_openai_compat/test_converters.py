from __future__ import annotations

from src.core.models.results import AgentResult
from src.core.server.openai_compat.converters import (
    agent_result_to_openai_response,
    make_stream_chunk,
    openai_request_to_context,
)
from src.core.server.openai_compat.models import (
    ChatCompletionRequest,
    OpenAIChatMessage,
)


class TestOpenAIRequestToContext:
    def test_extracts_last_user_message(self) -> None:
        req = ChatCompletionRequest(
            model="m",
            messages=[
                OpenAIChatMessage(role="user", content="first"),
                OpenAIChatMessage(role="assistant", content="reply"),
                OpenAIChatMessage(role="user", content="second"),
            ],
        )
        ctx = openai_request_to_context(req)
        assert ctx.user_message == "second"

    def test_puts_other_messages_in_history(self) -> None:
        req = ChatCompletionRequest(
            model="m",
            messages=[
                OpenAIChatMessage(role="system", content="Be helpful"),
                OpenAIChatMessage(role="user", content="Hi"),
            ],
        )
        ctx = openai_request_to_context(req)
        assert ctx.user_message == "Hi"
        assert len(ctx.conversation_history) == 1
        assert ctx.conversation_history[0]["role"] == "system"
        assert ctx.conversation_history[0]["content"] == "Be helpful"

    def test_stores_params_in_metadata(self) -> None:
        req = ChatCompletionRequest(
            model="my-model",
            messages=[OpenAIChatMessage(role="user", content="x")],
            temperature=0.5,
            max_tokens=200,
            stream=True,
        )
        ctx = openai_request_to_context(req)
        assert ctx.metadata["openai_model"] == "my-model"
        assert ctx.metadata["temperature"] == 0.5
        assert ctx.metadata["max_tokens"] == 200
        assert ctx.metadata["stream"] is True

    def test_no_user_message(self) -> None:
        req = ChatCompletionRequest(
            model="m",
            messages=[OpenAIChatMessage(role="system", content="sys")],
        )
        ctx = openai_request_to_context(req)
        assert ctx.user_message == ""
        assert len(ctx.conversation_history) == 1

    def test_handles_none_content(self) -> None:
        req = ChatCompletionRequest(
            model="m",
            messages=[
                OpenAIChatMessage(role="user", content=None),
            ],
        )
        ctx = openai_request_to_context(req)
        assert ctx.user_message == ""

    def test_multi_turn_conversation(self) -> None:
        req = ChatCompletionRequest(
            model="m",
            messages=[
                OpenAIChatMessage(role="system", content="sys"),
                OpenAIChatMessage(role="user", content="q1"),
                OpenAIChatMessage(role="assistant", content="a1"),
                OpenAIChatMessage(role="user", content="q2"),
            ],
        )
        ctx = openai_request_to_context(req)
        assert ctx.user_message == "q2"
        # History contains system, first user, and assistant
        assert len(ctx.conversation_history) == 3
        roles = [h["role"] for h in ctx.conversation_history]
        assert roles == ["system", "user", "assistant"]


class TestAgentResultToOpenAIResponse:
    def test_maps_fields(self) -> None:
        result = AgentResult(
            agent_name="test",
            response="Hello world",
            token_usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )
        resp = agent_result_to_openai_response(result, model="test-model")
        assert resp.model == "test-model"
        assert resp.choices[0].message.content == "Hello world"
        assert resp.choices[0].message.role == "assistant"
        assert resp.choices[0].finish_reason == "stop"
        assert resp.usage.total_tokens == 15

    def test_custom_completion_id(self) -> None:
        result = AgentResult(agent_name="a", response="x")
        resp = agent_result_to_openai_response(
            result, model="m", completion_id="chatcmpl-custom"
        )
        assert resp.id == "chatcmpl-custom"

    def test_empty_token_usage(self) -> None:
        result = AgentResult(agent_name="a", response="x")
        resp = agent_result_to_openai_response(result, model="m")
        assert resp.usage.prompt_tokens == 0
        assert resp.usage.completion_tokens == 0
        assert resp.usage.total_tokens == 0


class TestMakeStreamChunk:
    def test_role_chunk(self) -> None:
        chunk = make_stream_chunk(
            "chatcmpl-abc", "m", 1234567890, role="assistant"
        )
        assert chunk.choices[0].delta.role == "assistant"
        assert chunk.choices[0].delta.content is None
        assert chunk.choices[0].finish_reason is None

    def test_content_chunk(self) -> None:
        chunk = make_stream_chunk(
            "chatcmpl-abc", "m", 1234567890, content="Hello"
        )
        assert chunk.choices[0].delta.content == "Hello"
        assert chunk.choices[0].delta.role is None

    def test_finish_chunk(self) -> None:
        chunk = make_stream_chunk(
            "chatcmpl-abc", "m", 1234567890, finish_reason="stop"
        )
        assert chunk.choices[0].finish_reason == "stop"
        assert chunk.choices[0].delta.content is None

    def test_chunk_metadata(self) -> None:
        chunk = make_stream_chunk("id-1", "my-model", 999, content="x")
        assert chunk.id == "id-1"
        assert chunk.model == "my-model"
        assert chunk.created == 999
        assert chunk.object == "chat.completion.chunk"

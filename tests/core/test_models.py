"""Tests for core Pydantic models — validation, immutability, defaults."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.models.config import AppSettings
from src.core.models.context import AgentContext, ToolInput
from src.core.models.messages import Conversation, Message, Role
from src.core.models.results import AgentResult, ToolCallRecord, ToolResult


class TestAgentContext:
    def test_creates_with_defaults(self):
        ctx = AgentContext(user_message="hello")
        assert ctx.user_message == "hello"
        assert ctx.conversation_history == []
        assert ctx.available_tools == []
        assert ctx.request_id is not None

    def test_is_frozen(self):
        ctx = AgentContext(user_message="hello")
        with pytest.raises(ValidationError):
            ctx.user_message = "changed"  # type: ignore[misc]

    def test_model_copy_creates_new_context(self):
        ctx = AgentContext(user_message="hello")
        new_ctx = ctx.model_copy(update={"user_message": "new message"})
        assert new_ctx.user_message == "new message"
        assert ctx.user_message == "hello"

    def test_requires_user_message(self):
        with pytest.raises(ValidationError):
            AgentContext()  # type: ignore[call-arg]


class TestToolInput:
    def test_creates_with_defaults(self):
        ti = ToolInput(tool_name="test")
        assert ti.tool_name == "test"
        assert ti.parameters == {}
        assert ti.request_id is not None

    def test_with_parameters(self):
        ti = ToolInput(tool_name="search", parameters={"query": "hello"})
        assert ti.parameters["query"] == "hello"


class TestAgentResult:
    def test_creates_with_required_fields(self):
        result = AgentResult(agent_name="test", response="hello")
        assert result.agent_name == "test"
        assert result.response == "hello"
        assert result.tool_calls == []
        assert result.token_usage == {}

    def test_with_tool_calls(self):
        tc = ToolCallRecord(
            tool_name="search",
            input_params={"q": "test"},
            output="result",
            duration_ms=100.0,
            success=True,
        )
        result = AgentResult(agent_name="test", response="hello", tool_calls=[tc])
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "search"


class TestToolResult:
    def test_success_by_default(self):
        result = ToolResult(tool_name="test", output="data")
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        result = ToolResult(tool_name="test", output=None, success=False, error="timeout")
        assert result.success is False
        assert result.error == "timeout"


class TestMessage:
    def test_creates_message(self):
        msg = Message(role=Role.USER, content="hello")
        assert msg.role == Role.USER
        assert msg.content == "hello"
        assert msg.timestamp is not None


class TestConversation:
    def test_add_message(self):
        conv = Conversation(conversation_id="test-conv")
        msg = conv.add(Role.USER, "hello")
        assert len(conv.messages) == 1
        assert msg.role == Role.USER
        assert msg.content == "hello"

    def test_multiple_messages(self):
        conv = Conversation(conversation_id="test-conv")
        conv.add(Role.USER, "hello")
        conv.add(Role.ASSISTANT, "hi there")
        assert len(conv.messages) == 2


class TestAppSettings:
    def test_defaults(self):
        settings = AppSettings()
        assert settings.app_name == "barongsai"
        assert settings.debug is False
        assert settings.agent_timeout_seconds == 30.0
        assert settings.tool_timeout_seconds == 15.0

    def test_override(self):
        settings = AppSettings(app_name="custom", debug=True)
        assert settings.app_name == "custom"
        assert settings.debug is True

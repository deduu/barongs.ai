from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.applications.deep_search.models.research_mode import ResearchMode
from src.applications.deep_search.prompts.planner_prompts import PLANNER_PROMPTS
from src.applications.deep_search.prompts.synthesizer_prompts import SYNTH_PROMPTS
from src.core.models.context import AgentContext

# --- ResearchMode enum tests ---


class TestResearchMode:
    def test_enum_values(self) -> None:
        assert ResearchMode.GENERAL == "general"
        assert ResearchMode.ACADEMIC == "academic"
        assert ResearchMode.CONSULTANT == "consultant"

    def test_enum_from_string(self) -> None:
        assert ResearchMode("general") is ResearchMode.GENERAL
        assert ResearchMode("academic") is ResearchMode.ACADEMIC
        assert ResearchMode("consultant") is ResearchMode.CONSULTANT

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            ResearchMode("invalid")


# --- Prompt selection tests ---


class TestSynthesizerPromptSelection:
    def test_all_modes_have_prompts(self) -> None:
        for mode in ResearchMode:
            assert mode in SYNTH_PROMPTS
            assert isinstance(SYNTH_PROMPTS[mode], str)
            assert len(SYNTH_PROMPTS[mode]) > 100

    def test_general_prompt_has_executive_summary(self) -> None:
        prompt = SYNTH_PROMPTS[ResearchMode.GENERAL]
        assert "Executive Summary" in prompt

    def test_academic_prompt_has_journal_sections(self) -> None:
        prompt = SYNTH_PROMPTS[ResearchMode.ACADEMIC]
        assert "Introduction" in prompt
        assert "Literature Review" in prompt
        assert "Methodology" in prompt
        assert "Results" in prompt
        assert "Discussion" in prompt
        assert "Conclusion" in prompt

    def test_consultant_prompt_has_report_sections(self) -> None:
        prompt = SYNTH_PROMPTS[ResearchMode.CONSULTANT]
        assert "Executive Summary" in prompt
        assert "Recommendations" in prompt
        assert "Implementation" in prompt

    def test_prompts_have_template_variables(self) -> None:
        for mode in ResearchMode:
            prompt = SYNTH_PROMPTS[mode]
            assert "{entity_context}" in prompt
            assert "{entity_name}" in prompt
            assert "{findings_text}" in prompt


class TestPlannerPromptSelection:
    def test_all_modes_have_prompts(self) -> None:
        for mode in ResearchMode:
            assert mode in PLANNER_PROMPTS
            assert isinstance(PLANNER_PROMPTS[mode], str)
            assert len(PLANNER_PROMPTS[mode]) > 100

    def test_prompts_have_template_variables(self) -> None:
        for mode in ResearchMode:
            prompt = PLANNER_PROMPTS[mode]
            assert "{entity_context}" in prompt
            assert "{entity_name}" in prompt

    def test_academic_planner_mentions_literature(self) -> None:
        prompt = PLANNER_PROMPTS[ResearchMode.ACADEMIC]
        assert "literature" in prompt.lower() or "academic" in prompt.lower()

    def test_consultant_planner_mentions_business(self) -> None:
        prompt = PLANNER_PROMPTS[ResearchMode.CONSULTANT]
        lower = prompt.lower()
        assert "business" in lower or "market" in lower or "strategic" in lower


# --- Agent mode-awareness tests ---


class TestDeepSynthesizerWithModes:
    async def test_default_mode_is_general(self) -> None:
        from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Report text"
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        agent = DeepSynthesizerAgent(llm_provider=mock_llm)
        context = AgentContext(
            user_message="test query",
            metadata={"findings": []},
        )
        await agent.run(context)

        # Verify the system prompt used is the general one
        call_args = mock_llm.generate.call_args[0][0]
        assert "Executive Summary" in call_args.system_prompt

    async def test_academic_mode_uses_academic_prompt(self) -> None:
        from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Academic report"
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        agent = DeepSynthesizerAgent(llm_provider=mock_llm)
        context = AgentContext(
            user_message="test query",
            metadata={"findings": [], "research_mode": "academic"},
        )
        await agent.run(context)

        call_args = mock_llm.generate.call_args[0][0]
        assert "Literature Review" in call_args.system_prompt

    async def test_consultant_mode_uses_consultant_prompt(self) -> None:
        from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Consulting report"
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        agent = DeepSynthesizerAgent(llm_provider=mock_llm)
        context = AgentContext(
            user_message="test query",
            metadata={"findings": [], "research_mode": "consultant"},
        )
        await agent.run(context)

        call_args = mock_llm.generate.call_args[0][0]
        assert "Recommendations" in call_args.system_prompt


class TestResearchPlannerWithModes:
    async def test_default_mode_is_general(self) -> None:
        from src.applications.deep_search.agents.research_planner import ResearchPlannerAgent

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"tasks": []}'
        mock_response.usage = {"prompt_tokens": 50, "completion_tokens": 20}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        agent = ResearchPlannerAgent(llm_provider=mock_llm)
        context = AgentContext(user_message="test query", metadata={})
        await agent.run(context)

        call_args = mock_llm.generate.call_args[0][0]
        assert "secondary_web" in call_args.system_prompt

    async def test_academic_mode_uses_academic_planner(self) -> None:
        from src.applications.deep_search.agents.research_planner import ResearchPlannerAgent

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"tasks": []}'
        mock_response.usage = {"prompt_tokens": 50, "completion_tokens": 20}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        agent = ResearchPlannerAgent(llm_provider=mock_llm)
        context = AgentContext(
            user_message="test query",
            metadata={"research_mode": "academic"},
        )
        await agent.run(context)

        call_args = mock_llm.generate.call_args[0][0]
        lower = call_args.system_prompt.lower()
        assert "literature" in lower or "academic" in lower


# --- API model tests ---


class TestDeepSearchRequestWithMode:
    def test_default_mode_is_general(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        req = DeepSearchRequest(query="test")
        assert req.research_mode == "general"

    def test_valid_modes_accepted(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        for mode in ["general", "academic", "consultant"]:
            req = DeepSearchRequest(query="test", research_mode=mode)
            assert req.research_mode == mode

    def test_invalid_mode_rejected(self) -> None:
        from pydantic import ValidationError

        from src.applications.deep_search.models.api import DeepSearchRequest

        with pytest.raises(ValidationError):
            DeepSearchRequest(query="test", research_mode="invalid")


class TestDeepSearchResponseWithMode:
    def test_default_mode_in_response(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchResponse

        resp = DeepSearchResponse(executive_summary="test", sections=[])
        assert resp.research_mode == "general"

    def test_mode_preserved_in_response(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchResponse

        resp = DeepSearchResponse(executive_summary="test", sections=[], research_mode="academic")
        assert resp.research_mode == "academic"

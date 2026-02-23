from __future__ import annotations

from fastapi import FastAPI

from src.applications.search_agent.agents.direct_answerer import DirectAnswererAgent
from src.applications.search_agent.agents.query_analyzer import QueryAnalyzerAgent
from src.applications.search_agent.agents.search_pipeline import SearchPipelineAgent
from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
from src.applications.search_agent.agents.web_researcher import WebResearcherAgent
from src.applications.search_agent.config import SearchAgentSettings
from src.applications.search_agent.routes import create_router
from src.applications.search_agent.streaming_pipeline import StreamableSearchPipeline
from src.applications.search_agent.tools.content_fetcher import ContentFetcherTool
from src.applications.search_agent.tools.search_api import BraveSearchTool, DuckDuckGoSearchTool
from src.applications.search_agent.tools.url_validator import URLValidatorTool
from src.core.interfaces.orchestrator import Orchestrator
from src.core.llm.providers.openai import OpenAIProvider
from src.core.llm.providers.openai_compatible import OpenAICompatibleProvider
from src.core.llm.registry import LLMProviderRegistry
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy
from src.core.server.factory import create_app
from src.core.server.openai_compat import ModelRegistry, create_openai_router


def create_search_app(settings: SearchAgentSettings | None = None) -> FastAPI:
    """Composition root: wire agents, tools, LLM, memory, orchestrator, and routes."""
    settings = settings or SearchAgentSettings()

    # --- LLM Setup ---
    registry = LLMProviderRegistry()

    if settings.llm_base_url:
        # OpenAI-compatible local model
        provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            default_model=settings.llm_model,
            provider_name=settings.llm_provider,
        )
    else:
        # Standard OpenAI
        provider = OpenAIProvider(  # type: ignore[assignment]
            api_key=settings.llm_api_key,
            default_model=settings.llm_model,
        )
    registry.register(provider)
    llm = registry.get(settings.llm_provider)

    # --- Tools ---
    search_tool: BraveSearchTool | DuckDuckGoSearchTool
    if settings.search_provider == "brave":
        search_tool = BraveSearchTool(
            api_key=settings.search_api_key,
            max_results=settings.search_max_results,
        )
    else:
        search_tool = DuckDuckGoSearchTool(
            max_results=settings.search_max_results,
        )
    content_fetcher = ContentFetcherTool(
        max_content_length=settings.search_max_content_length,
    )
    url_validator = URLValidatorTool()

    # --- Agents ---
    query_analyzer = QueryAnalyzerAgent(llm_provider=llm, model=settings.llm_model)
    web_researcher = WebResearcherAgent(
        search_tool=search_tool,
        content_fetcher=content_fetcher,
        url_validator=url_validator,
    )
    synthesizer = SynthesizerAgent(llm_provider=llm, model=settings.llm_model)
    direct_answerer = DirectAnswererAgent(llm_provider=llm, model=settings.llm_model)

    search_pipeline = SearchPipelineAgent(
        query_analyzer=query_analyzer,
        web_researcher=web_researcher,
        synthesizer=synthesizer,
        direct_answerer=direct_answerer,
    )

    # --- Orchestrator ---
    orchestrator = Orchestrator(
        strategy=SingleAgentStrategy(),
        agents=[search_pipeline],
        timeout_seconds=settings.agent_timeout_seconds,
    )

    # --- FastAPI App ---
    fastapi_app = create_app(settings)
    router = create_router(
        orchestrator,
        settings,
        web_researcher=web_researcher,
        synthesizer=synthesizer,
    )
    fastapi_app.include_router(router)

    # --- OpenAI-compatible API (for Open WebUI) ---
    streamable_pipeline = StreamableSearchPipeline(web_researcher, synthesizer)
    model_registry = ModelRegistry()
    model_registry.register(
        settings.llm_model,
        orchestrator,
        description="Search agent with web research and synthesis",
        streamable_agent=streamable_pipeline,
    )
    openai_router = create_openai_router(model_registry, settings)
    fastapi_app.include_router(openai_router)

    return fastapi_app


# For: uvicorn src.applications.search_agent.main:app --reload
app = create_search_app()

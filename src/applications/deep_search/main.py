from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI

from src.applications.deep_search.agents.academic_researcher import AcademicResearcherAgent
from src.applications.deep_search.agents.data_analyst import DataAnalystAgent
from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent
from src.applications.deep_search.agents.deep_web_researcher import DeepWebResearcherAgent
from src.applications.deep_search.agents.fact_checker import FactCheckerAgent
from src.applications.deep_search.agents.reflection import ReflectionAgent
from src.applications.deep_search.agents.research_planner import ResearchPlannerAgent
from src.applications.deep_search.config import DeepSearchSettings
from src.applications.deep_search.routes import create_router
from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline
from src.applications.deep_search.tools.academic_search import AcademicSearchTool
from src.applications.deep_search.tools.code_execution import CodeExecutionTool
from src.applications.deep_search.tools.deep_crawler import DeepCrawlerTool
from src.applications.deep_search.tools.source_scorer import SourceScorerTool
from src.applications.search_agent.tools.content_fetcher import ContentFetcherTool
from src.applications.search_agent.tools.search_api import BraveSearchTool, DuckDuckGoSearchTool
from src.core.http.client import HttpClientPool
from src.core.interfaces.orchestrator import Orchestrator
from src.core.llm.base import LLMProvider
from src.core.llm.providers.openai import OpenAIProvider
from src.core.llm.providers.openai_compatible import OpenAICompatibleProvider
from src.core.llm.registry import LLMProviderRegistry
from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy
from src.core.server.factory import create_app

logger = logging.getLogger(__name__)


def create_deep_search_app(settings: DeepSearchSettings | None = None) -> FastAPI:
    """Composition root: wire tools, agents, orchestrator, pipeline, and routes."""
    settings = settings or DeepSearchSettings()

    startup_hooks: list[Callable[[], Awaitable[None]]] = []
    shutdown_hooks: list[Callable[[], Awaitable[None]]] = []

    # --- LLM Setup ---
    registry = LLMProviderRegistry()

    provider: LLMProvider
    if settings.llm_base_url:
        provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            default_model=settings.llm_model,
            provider_name=settings.llm_provider,
        )
    else:
        provider = OpenAIProvider(
            api_key=settings.llm_api_key,
            default_model=settings.llm_model,
        )
    registry.register(provider)
    llm = registry.get(settings.llm_provider)

    # --- HTTP Client Pool ---
    http_pool = HttpClientPool(
        max_connections=settings.http_max_connections,
        max_keepalive=settings.http_max_keepalive,
        max_concurrent=settings.http_max_concurrent_requests,
    )

    async def _close_http_pool() -> None:
        await http_pool.aclose()

    shutdown_hooks.append(_close_http_pool)

    # --- Tools ---
    search_tool: BraveSearchTool | DuckDuckGoSearchTool
    if settings.search_provider == "brave":
        search_tool = BraveSearchTool(
            api_key=settings.search_api_key,
            max_results=settings.search_max_results,
            http_client=http_pool,
        )
    else:
        search_tool = DuckDuckGoSearchTool(max_results=settings.search_max_results)

    academic_search = AcademicSearchTool(
        http_client=http_pool,
        max_results=settings.academic_max_results,
        semantic_scholar_url=settings.semantic_scholar_api_url,
        arxiv_url=settings.arxiv_api_url,
    )
    deep_crawler = DeepCrawlerTool(
        http_client=http_pool,
        max_depth=settings.deep_crawler_max_depth,
        max_pages=settings.deep_crawler_max_pages,
    )
    code_execution = CodeExecutionTool(
        docker_image=settings.docker_image,
        memory_limit=settings.docker_memory_limit,
        timeout_seconds=settings.docker_timeout_seconds,
        network_disabled=settings.docker_network_disabled,
    )
    source_scorer = SourceScorerTool()
    content_fetcher = ContentFetcherTool(http_client=http_pool)

    # --- Agents ---
    planner = ResearchPlannerAgent(llm_provider=llm, model=settings.llm_model)
    academic_researcher = AcademicResearcherAgent(
        llm_provider=llm,
        academic_search_tool=academic_search,
        source_scorer_tool=source_scorer,
        model=settings.llm_model,
    )
    deep_web_researcher = DeepWebResearcherAgent(
        llm_provider=llm,
        search_tool=search_tool,
        deep_crawler_tool=deep_crawler,
        source_scorer_tool=source_scorer,
        model=settings.llm_model,
    )
    data_analyst = DataAnalystAgent(
        llm_provider=llm,
        code_execution_tool=code_execution,
        model=settings.llm_model,
    )
    fact_checker = FactCheckerAgent(llm_provider=llm, model=settings.llm_model)
    reflection = ReflectionAgent(llm_provider=llm, model=settings.llm_model)
    synthesizer = DeepSynthesizerAgent(llm_provider=llm, model=settings.llm_model)

    all_agents = [
        planner,
        academic_researcher,
        deep_web_researcher,
        data_analyst,
        fact_checker,
        reflection,
        synthesizer,
    ]

    # --- Orchestrator ---
    strategy = ResearchDAGStrategy(max_iterations=settings.research_max_iterations)
    orchestrator = Orchestrator(
        strategy=strategy,
        agents=all_agents,
        timeout_seconds=settings.agent_timeout_seconds,
    )

    # --- Streaming Pipeline ---
    pipeline = StreamableDeepSearchPipeline(
        planner=planner,
        synthesizer=synthesizer,
        strategy=strategy,
        agents=[
            academic_researcher,
            deep_web_researcher,
            data_analyst,
            fact_checker,
            reflection,
        ],
        content_fetcher=content_fetcher,
        llm_provider=llm,
        model=settings.llm_model,
    )

    # --- FastAPI App ---
    fastapi_app = create_app(settings, on_startup=startup_hooks, on_shutdown=shutdown_hooks)

    router = create_router(orchestrator, settings, pipeline=pipeline)
    fastapi_app.include_router(router)

    return fastapi_app


# For: uvicorn src.applications.deep_search.main:app --reload
app = create_deep_search_app()

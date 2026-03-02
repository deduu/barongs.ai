"""ARQ worker entry point for background job processing.

Start with: ``python -m arq src.applications.search_agent.worker.WorkerSettings``
"""

from __future__ import annotations

import logging
import os
from typing import Any

from arq.connections import RedisSettings

from src.applications.search_agent.jobs import run_search

logger = logging.getLogger(__name__)


def _redis_settings() -> RedisSettings:
    """Parse BGS_REDIS_URL into ARQ RedisSettings."""
    url = os.environ.get("BGS_REDIS_URL", "redis://localhost:6379/0")
    # redis://:password@host:port/db
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup: initialise shared dependencies."""
    import redis.asyncio as aioredis

    from src.applications.search_agent.config import SearchAgentSettings
    from src.core.jobs.service import JobService

    settings = SearchAgentSettings()
    redis_url = settings.redis_url or os.environ.get("BGS_REDIS_URL", "redis://localhost:6379/0")
    redis_client = aioredis.from_url(redis_url, decode_responses=True)

    job_service = JobService(redis_client, result_ttl_seconds=settings.job_result_ttl_seconds)

    # Build a minimal orchestrator for executing search jobs
    from src.applications.search_agent.agents.direct_answerer import DirectAnswererAgent
    from src.applications.search_agent.agents.query_analyzer import QueryAnalyzerAgent
    from src.applications.search_agent.agents.search_pipeline import SearchPipelineAgent
    from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
    from src.applications.search_agent.agents.web_researcher import WebResearcherAgent
    from src.applications.search_agent.tools.content_fetcher import ContentFetcherTool
    from src.applications.search_agent.tools.search_api import BraveSearchTool, DuckDuckGoSearchTool
    from src.applications.search_agent.tools.url_validator import URLValidatorTool
    from src.core.http.client import HttpClientPool
    from src.core.interfaces.orchestrator import Orchestrator
    from src.core.llm.providers.openai import OpenAIProvider
    from src.core.llm.providers.openai_compatible import OpenAICompatibleProvider
    from src.core.llm.registry import LLMProviderRegistry
    from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy

    # LLM
    llm_registry = LLMProviderRegistry()
    if settings.llm_base_url:
        provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            default_model=settings.llm_model,
            provider_name=settings.llm_provider,
        )
    else:
        provider = OpenAIProvider(  # type: ignore[assignment]
            api_key=settings.llm_api_key,
            default_model=settings.llm_model,
        )
    llm_registry.register(provider)
    llm = llm_registry.get(settings.llm_provider)

    # HTTP pool
    http_pool = HttpClientPool()

    # Tools
    search_tool: BraveSearchTool | DuckDuckGoSearchTool
    if settings.search_provider == "brave":
        search_tool = BraveSearchTool(
            api_key=settings.search_api_key,
            max_results=settings.search_max_results,
            http_client=http_pool,
        )
    else:
        search_tool = DuckDuckGoSearchTool(max_results=settings.search_max_results)
    content_fetcher = ContentFetcherTool(
        max_content_length=settings.search_max_content_length,
        http_client=http_pool,
    )
    url_validator = URLValidatorTool()

    # Agents
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

    orchestrator = Orchestrator(
        strategy=SingleAgentStrategy(),
        agents=[search_pipeline],
        timeout_seconds=settings.agent_timeout_seconds,
    )

    ctx["job_service"] = job_service
    ctx["orchestrator"] = orchestrator
    ctx["redis_client"] = redis_client
    ctx["http_pool"] = http_pool
    logger.info("ARQ worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown: clean up resources."""
    if "http_pool" in ctx:
        await ctx["http_pool"].aclose()
    if "redis_client" in ctx:
        await ctx["redis_client"].aclose()
    logger.info("ARQ worker shut down")


class WorkerSettings:
    """ARQ worker configuration."""

    redis_settings = _redis_settings()
    functions = [run_search]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300
    max_tries = 3

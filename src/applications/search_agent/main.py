from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

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
from src.core.http.client import HttpClientPool
from src.core.interfaces.orchestrator import Orchestrator
from src.core.llm.base import LLMProvider
from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
from src.core.llm.providers.openai import OpenAIProvider
from src.core.llm.providers.openai_compatible import OpenAICompatibleProvider
from src.core.llm.registry import LLMProviderRegistry
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy
from src.core.server.factory import create_app
from src.core.server.openai_compat import ModelRegistry, create_openai_router

logger = logging.getLogger(__name__)


def create_search_app(settings: SearchAgentSettings | None = None) -> FastAPI:
    """Composition root: wire agents, tools, LLM, memory, orchestrator, and routes."""
    settings = settings or SearchAgentSettings()

    startup_hooks: list[Callable[[], Awaitable[None]]] = []
    shutdown_hooks: list[Callable[[], Awaitable[None]]] = []

    # --- LLM Setup ---
    registry = LLMProviderRegistry()

    provider: LLMProvider
    if settings.llm_provider == "huggingface":
        # Local HuggingFace Transformers model
        hf_config = HuggingFaceConfig(
            model_id=settings.hf_model_id,
            device_map=settings.hf_device_map,
            quantization=settings.hf_quantization,  # type: ignore[arg-type]
            torch_dtype=settings.hf_torch_dtype,
            max_new_tokens=settings.hf_max_new_tokens,
            trust_remote_code=settings.hf_trust_remote_code,
        )
        provider = HuggingFaceProvider(config=hf_config)
    elif settings.llm_base_url:
        # OpenAI-compatible local model
        provider = OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            default_model=settings.llm_model,
            provider_name=settings.llm_provider,
        )
    else:
        # Standard OpenAI
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
        search_tool = DuckDuckGoSearchTool(
            max_results=settings.search_max_results,
        )
    content_fetcher = ContentFetcherTool(
        max_content_length=settings.search_max_content_length,
        http_client=http_pool,
    )
    url_validator = URLValidatorTool()

    # --- Memory (session persistence) ---
    redis_client = None
    if settings.redis_url:
        import redis.asyncio as aioredis

        from src.applications.search_agent.memory.redis_conversation_memory import (
            RedisConversationMemory,
        )

        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        conversation_memory = RedisConversationMemory(
            client=redis_client,
            window_size=settings.conversation_window_size,
        )
        logger.info("Using Redis-backed conversation memory (%s)", settings.redis_url)

        async def _close_redis() -> None:
            if redis_client is not None:
                await redis_client.aclose()

        shutdown_hooks.append(_close_redis)
    else:
        from src.applications.search_agent.memory.conversation_memory import ConversationMemory

        conversation_memory = ConversationMemory(  # type: ignore[assignment]
            window_size=settings.conversation_window_size,
        )
        logger.info("Using in-memory conversation memory (no Redis URL configured)")

    # --- Distributed Rate Limiter (optional) ---
    rate_limiter = None
    if settings.rate_limit_distributed and redis_client is not None:
        from src.core.middleware.rate_limiter import RedisRateLimiter

        rate_limiter = RedisRateLimiter(
            redis_client,
            max_tokens=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        logger.info("Using Redis-backed distributed rate limiter")

    # --- Job Service (optional) ---
    job_service = None
    if settings.job_queue_enabled and redis_client is not None:
        from src.core.jobs.router import create_job_router
        from src.core.jobs.service import JobService

        job_service = JobService(
            redis_client, result_ttl_seconds=settings.job_result_ttl_seconds
        )
        logger.info("Job queue enabled")

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

    # --- User Auth (optional) ---
    auth_dependency = None
    if settings.user_auth_enabled:
        from src.core.auth.routes import create_auth_router
        from src.core.auth.user_repository import UserRepository
        from src.core.middleware.auth import create_unified_auth_dependency

        if not settings.database_url:
            raise ValueError("database_url is required when user_auth_enabled is True")

        user_repo = UserRepository(database_url=settings.database_url)
        startup_hooks.append(user_repo.initialize)
        shutdown_hooks.append(user_repo.close)

        auth_dependency = create_unified_auth_dependency(settings)
        logger.info("User auth enabled (JWT + API key)")

    # --- RAG (optional) ---
    rag_router = None
    if settings.rag_enabled:
        from src.applications.search_agent.agents.rag_synthesizer import RAGSynthesizerAgent
        from src.applications.search_agent.rag_routes import create_rag_router
        from src.core.rag.models import RAGConfig
        from src.core.rag.retriever import HybridRetriever

        rag_synthesizer = RAGSynthesizerAgent(llm_provider=llm, model=settings.llm_model)

        # Embedder
        embedding_api_key = settings.rag_embedding_api_key or settings.llm_api_key
        if settings.rag_embedding_provider == "sentence_transformer":
            from src.core.rag.providers.embedders.sentence_transformer import (
                SentenceTransformerEmbedder,
            )

            rag_embedder = SentenceTransformerEmbedder(model_name=settings.rag_embedding_model)
        else:
            from src.core.rag.providers.embedders.openai import OpenAIEmbedder

            rag_embedder = OpenAIEmbedder(
                api_key=embedding_api_key,
                model=settings.rag_embedding_model,
                base_url=settings.rag_embedding_base_url,
                dimension=settings.rag_embedding_dimension,
            )

        # Vector store
        if settings.rag_vector_store == "qdrant":
            from src.core.rag.providers.vector_stores.qdrant import QdrantVectorStore

            rag_vector_store = QdrantVectorStore(
                collection_name=settings.rag_qdrant_collection,
                dimension=settings.rag_embedding_dimension,
                url=settings.rag_qdrant_url,
                api_key=settings.rag_qdrant_api_key,
            )
        else:
            from src.core.rag.providers.vector_stores.faiss import FAISSVectorStore

            rag_vector_store = FAISSVectorStore(dimension=settings.rag_embedding_dimension)

        # Sparse retriever
        rag_sparse = None
        if settings.rag_sparse_retriever == "bm25":
            from src.core.rag.providers.sparse_retrievers.bm25 import BM25Retriever

            rag_sparse = BM25Retriever()

        # Reranker
        rag_reranker = None
        if settings.rag_reranker == "cross_encoder":
            from src.core.rag.providers.rerankers.cross_encoder import CrossEncoderReranker

            rag_reranker = CrossEncoderReranker(
                model_name=settings.rag_reranker_model or None,
            )
        elif settings.rag_reranker == "cohere":
            from src.core.rag.providers.rerankers.cohere import CohereReranker

            rag_reranker = CohereReranker(
                api_key=settings.rag_cohere_api_key,
                model=settings.rag_reranker_model or None,
            )

        rag_config = RAGConfig(
            dense_weight=settings.rag_dense_weight,
            sparse_weight=settings.rag_sparse_weight,
            dense_top_k=settings.rag_dense_top_k,
            sparse_top_k=settings.rag_sparse_top_k,
            rerank_top_k=settings.rag_rerank_top_k,
            enable_reranker=settings.rag_reranker != "none",
        )

        hybrid_retriever = HybridRetriever(
            embedder=rag_embedder,
            vector_store=rag_vector_store,
            sparse_retriever=rag_sparse,
            reranker=rag_reranker,
            config=rag_config,
        )

        # Wrap with PostgreSQL persistence if database_url is configured
        rag_retriever: HybridRetriever | object = hybrid_retriever
        if settings.database_url:
            from src.core.rag.persistence.pg_document_store import PgDocumentStore
            from src.core.rag.persistent_retriever import PersistentHybridRetriever

            pg_store = PgDocumentStore(database_url=settings.database_url)
            persistent_retriever = PersistentHybridRetriever(
                retriever=hybrid_retriever, store=pg_store
            )
            rag_retriever = persistent_retriever
            startup_hooks.append(persistent_retriever.initialize)
            shutdown_hooks.append(persistent_retriever.close)
            logger.info("RAG persistence enabled via PostgreSQL")
        else:
            logger.info("RAG running in-memory (no database_url configured)")

        from src.core.rag.parsers.registry import create_default_registry

        parser_registry = create_default_registry(
            llm_provider=llm,
            vision_model=settings.llm_model,
        )

        rag_router = create_rag_router(
            settings,
            retriever=rag_retriever,  # type: ignore[arg-type]
            synthesizer=rag_synthesizer,
            parser_registry=parser_registry,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            max_file_size_mb=settings.rag_max_file_size_mb,
            auth_dependency=auth_dependency,
        )

    # --- FastAPI App ---
    fastapi_app = create_app(
        settings,
        on_startup=startup_hooks,
        on_shutdown=shutdown_hooks,
        rate_limiter=rate_limiter,
    )

    # Include auth router if user auth is enabled
    if settings.user_auth_enabled:
        fastapi_app.include_router(create_auth_router(settings, user_repo))

    router = create_router(
        orchestrator,
        settings,
        web_researcher=web_researcher,
        synthesizer=synthesizer,
        auth_dependency=auth_dependency,
        job_service=job_service,
    )
    fastapi_app.include_router(router)

    if job_service is not None:
        job_router = create_job_router(job_service)
        fastapi_app.include_router(job_router)

    if rag_router is not None:
        fastapi_app.include_router(rag_router)

    # --- Deep Search (optional) ---
    try:
        from src.applications.deep_search.agents.academic_researcher import AcademicResearcherAgent
        from src.applications.deep_search.agents.data_analyst import DataAnalystAgent
        from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent
        from src.applications.deep_search.agents.deep_web_researcher import DeepWebResearcherAgent
        from src.applications.deep_search.agents.fact_checker import FactCheckerAgent
        from src.applications.deep_search.agents.reflection import ReflectionAgent
        from src.applications.deep_search.agents.research_planner import ResearchPlannerAgent
        from src.applications.deep_search.config import DeepSearchSettings
        from src.applications.deep_search.routes import create_router as create_deep_search_router
        from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline
        from src.applications.deep_search.tools.academic_search import AcademicSearchTool
        from src.applications.deep_search.tools.code_execution import CodeExecutionTool
        from src.applications.deep_search.tools.deep_crawler import DeepCrawlerTool
        from src.applications.deep_search.tools.source_scorer import SourceScorerTool
        from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy

        ds_settings = DeepSearchSettings()

        academic_search = AcademicSearchTool(
            http_client=http_pool,
            max_results=ds_settings.academic_max_results,
        )
        deep_crawler = DeepCrawlerTool(
            http_client=http_pool,
            max_depth=ds_settings.deep_crawler_max_depth,
            max_pages=ds_settings.deep_crawler_max_pages,
        )
        code_execution = CodeExecutionTool(
            docker_image=ds_settings.docker_image,
            memory_limit=ds_settings.docker_memory_limit,
            timeout_seconds=ds_settings.docker_timeout_seconds,
            network_disabled=ds_settings.docker_network_disabled,
        )
        source_scorer = SourceScorerTool()

        ds_planner = ResearchPlannerAgent(llm_provider=llm, model=settings.llm_model)
        ds_academic = AcademicResearcherAgent(
            llm_provider=llm,
            academic_search_tool=academic_search,
            source_scorer_tool=source_scorer,
            model=settings.llm_model,
        )
        ds_web = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=deep_crawler,
            source_scorer_tool=source_scorer,
            model=settings.llm_model,
        )
        ds_analyst = DataAnalystAgent(
            llm_provider=llm,
            code_execution_tool=code_execution,
            model=settings.llm_model,
        )
        ds_fact_checker = FactCheckerAgent(llm_provider=llm, model=settings.llm_model)
        ds_reflection = ReflectionAgent(llm_provider=llm, model=settings.llm_model)
        ds_synthesizer = DeepSynthesizerAgent(llm_provider=llm, model=settings.llm_model)

        ds_agents = [ds_web, ds_academic, ds_analyst, ds_fact_checker, ds_reflection]
        ds_strategy = ResearchDAGStrategy(max_iterations=ds_settings.research_max_iterations)
        ds_orchestrator = Orchestrator(
            strategy=ds_strategy,
            agents=ds_agents,
            timeout_seconds=settings.agent_timeout_seconds,
        )
        ds_pipeline = StreamableDeepSearchPipeline(
            planner=ds_planner,
            synthesizer=ds_synthesizer,
            strategy=ds_strategy,
            agents=ds_agents,
        )
        ds_router = create_deep_search_router(
            ds_orchestrator, ds_settings, pipeline=ds_pipeline, auth_dependency=auth_dependency,
        )
        fastapi_app.include_router(ds_router)
        logger.info("Deep Search routes mounted at /api/deep-search")
    except Exception:
        logger.exception("Failed to mount Deep Search routes")

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

    # --- Static assets & Chat UI ---
    _base = Path(__file__).parent.parent.parent.parent  # project root
    _assets = _base / "assets"
    _frontend_dist = _base / "frontend" / "dist"

    if _assets.exists():
        from fastapi.staticfiles import StaticFiles

        fastapi_app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    if _frontend_dist.exists():
        from fastapi.staticfiles import StaticFiles as _SF

        # Serve Vite-built JS/CSS chunks
        _static_dir = _frontend_dist / "static"
        if _static_dir.exists():
            fastapi_app.mount("/static", _SF(directory=str(_static_dir)), name="static")

        from src.core.server.ui_router import create_ui_router

        fastapi_app.include_router(create_ui_router(_frontend_dist))

    return fastapi_app


# For: uvicorn src.applications.search_agent.main:app --reload
app = create_search_app()

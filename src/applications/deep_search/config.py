from __future__ import annotations

from src.core.models.config import AppSettings


class DeepSearchSettings(AppSettings):
    """Settings for the deep search application."""

    app_name: str = "deep-search"

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    llm_base_url: str | None = None

    # Search
    search_provider: str = "duckduckgo"
    search_api_key: str = ""
    search_max_results: int = 20

    # Academic
    semantic_scholar_api_url: str = "https://api.semanticscholar.org/graph/v1/paper/search"
    arxiv_api_url: str = "http://export.arxiv.org/api/query"
    academic_max_results: int = 10

    # Docker / Code Execution
    docker_image: str = "python:3.11-slim"
    docker_memory_limit: str = "256m"
    docker_timeout_seconds: int = 30
    docker_network_disabled: bool = True
    code_execution_enabled: bool = False

    # Crawler
    deep_crawler_max_depth: int = 2
    deep_crawler_max_pages: int = 10

    # Budget
    research_max_iterations: int = 3
    research_max_llm_tokens: int = 100_000
    research_max_api_calls: int = 50
    research_max_time_seconds: int = 300

from __future__ import annotations

from pydantic import Field

from src.core.models.config import AppSettings


class SearchAgentSettings(AppSettings):
    """Settings for the search agent application."""

    app_name: str = "search-agent"

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    llm_base_url: str | None = None  # For OpenAI-compatible local models

    # Search
    search_provider: str = "duckduckgo"  # "duckduckgo" (no key) | "brave" (needs key)
    search_api_key: str = ""  # Brave Search API key (only needed if search_provider=brave)
    search_max_results: int = 10
    search_max_content_length: int = 5000

    # Memory
    conversation_window_size: int = 20
    semantic_memory_enabled: bool = True

    # MCP
    mcp_servers: list[str] = Field(default_factory=list)
    skills_md_path: str | None = None

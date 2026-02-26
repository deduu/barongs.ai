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
    search_max_results: int = 20
    search_max_content_length: int = 10000

    # HuggingFace local model
    hf_model_id: str = "Qwen/Qwen3-4B"
    hf_device_map: str = "auto"
    hf_quantization: str = "4bit"  # "none" | "4bit" | "8bit"
    hf_torch_dtype: str = "float16"
    hf_max_new_tokens: int = 2048
    hf_trust_remote_code: bool = True

    # Memory
    conversation_window_size: int = 20
    semantic_memory_enabled: bool = True

    # MCP
    mcp_servers: list[str] = Field(default_factory=list)
    skills_md_path: str | None = None

    # RAG
    rag_enabled: bool = False
    rag_embedding_provider: str = "openai"  # "openai" | "sentence_transformer"
    rag_embedding_model: str = "text-embedding-3-small"
    rag_embedding_dimension: int = 1536
    rag_embedding_api_key: str = ""  # Falls back to llm_api_key if empty
    rag_embedding_base_url: str | None = None  # For Azure OpenAI

    rag_vector_store: str = "faiss"  # "faiss" | "qdrant"
    rag_qdrant_url: str | None = None  # None = in-memory
    rag_qdrant_api_key: str | None = None
    rag_qdrant_collection: str = "barongsai"

    rag_sparse_retriever: str = "bm25"  # "bm25" | "none"
    rag_reranker: str = "none"  # "none" | "cross_encoder" | "cohere"
    rag_reranker_model: str = ""
    rag_cohere_api_key: str = ""

    rag_dense_weight: float = 0.7
    rag_sparse_weight: float = 0.3
    rag_dense_top_k: int = 20
    rag_sparse_top_k: int = 20
    rag_rerank_top_k: int = 5

    rag_max_file_size_mb: int = 10
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200

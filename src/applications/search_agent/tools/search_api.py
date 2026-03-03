from __future__ import annotations

# Backward-compatible re-exports (tools moved to src.core.tools.web)
from src.core.tools.web.brave_search import BraveSearchTool
from src.core.tools.web.duckduckgo_search import DuckDuckGoSearchTool

__all__ = ["BraveSearchTool", "DuckDuckGoSearchTool"]

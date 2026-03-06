from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeepSearchRequest(BaseModel):
    """API request for deep search."""

    query: str
    max_iterations: int = Field(default=3, ge=1, le=8)
    max_time_seconds: int = Field(default=300, ge=30, le=3600)
    enable_code_execution: bool = False
    enable_academic_search: bool = True
    session_id: str | None = None
    # User-configurable settings (optional, defaults match current behavior)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_sources: int | None = Field(default=None, ge=3, le=10)
    extraction_detail: str | None = Field(default=None, pattern=r"^(low|medium|high)$")
    crawl_depth: int | None = Field(default=None, ge=1, le=3)
    research_mode: str = Field(
        default="general",
        pattern=r"^(general|academic|consultant)$",
        description="Output format: general, academic (journal paper), or consultant (consulting report)",
    )
    interactive_outline: bool = Field(
        default=False,
        description="If true, pause after planning to allow outline editing before research starts",
    )


class DeepSearchResponse(BaseModel):
    """API response for deep search."""

    executive_summary: str
    sections: list[dict[str, Any]]
    findings: list[dict[str, Any]] = Field(default_factory=list)
    methodology_notes: str = ""
    overall_confidence: float = 0.5
    sources: list[str] = Field(default_factory=list)
    research_mode: str = "general"

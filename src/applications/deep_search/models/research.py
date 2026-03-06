from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchTaskType(StrEnum):
    SECONDARY_WEB = "secondary_web"
    SECONDARY_ACADEMIC = "secondary_academic"
    PRIMARY_CODE = "primary_code"
    FACT_CHECK = "fact_check"
    REFLECTION = "reflection"


class ResearchTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResearchTask(BaseModel):
    """Single node in the research DAG."""

    task_id: str
    query: str
    task_type: ResearchTaskType
    depends_on: list[str] = Field(default_factory=list)
    status: ResearchTaskStatus = ResearchTaskStatus.PENDING
    priority: int = 1
    agent_name: str | None = None


class EntityGrounding(BaseModel):
    """Structured identity of the entity under research, used to prevent hallucination."""

    name: str = ""
    description: str = ""
    key_attributes: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    primary_source_content: str = ""
    needs_disambiguation: bool = False
    clarification_prompt: str = ""


class ResearchPlan(BaseModel):
    """DAG container for research tasks."""

    original_query: str
    tasks: list[ResearchTask]
    max_iterations: int = 3


class SourceCredibility(BaseModel):
    """Credibility assessment of a source."""

    domain_authority: float = 0.5
    recency_score: float = 0.5
    citation_count: int = 0
    is_peer_reviewed: bool = False
    overall_score: float = 0.5


class ResearchFinding(BaseModel):
    """A single finding from research."""

    finding_id: str
    content: str
    source_url: str
    confidence: float = 0.5
    methodology_tag: str = "secondary"
    credibility: SourceCredibility = Field(default_factory=SourceCredibility)
    citations: list[str] = Field(default_factory=list)
    entity_match: bool = True


class ResearchBudget(BaseModel):
    """Budget tracking for research execution."""

    max_llm_tokens: int = 100_000
    max_api_calls: int = 50
    max_time_seconds: int = 300
    used_llm_tokens: int = 0
    used_api_calls: int = 0
    used_time_seconds: float = 0.0

    @property
    def is_exhausted(self) -> bool:
        return (
            self.used_llm_tokens >= self.max_llm_tokens
            or self.used_api_calls >= self.max_api_calls
            or self.used_time_seconds >= self.max_time_seconds
        )


class ReportSection(BaseModel):
    """A section in the final research report."""

    heading: str
    content: str
    findings: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class ResearchReport(BaseModel):
    """Final research report."""

    executive_summary: str
    sections: list[ReportSection]
    findings: list[ResearchFinding] = Field(default_factory=list)
    methodology_notes: str = ""
    limitations: str = ""
    overall_confidence: float = 0.5

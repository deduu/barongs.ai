from __future__ import annotations

from pydantic import BaseModel, Field


class OutlineSection(BaseModel):
    """A section in the proposed research report outline."""

    heading: str
    description: str = ""


class ResearchTask(BaseModel):
    """A research task in the proposed outline."""

    task_id: str
    query: str
    task_type: str
    agent_name: str
    depends_on: list[str] = Field(default_factory=list)


class ResearchOutline(BaseModel):
    """The proposed research outline presented to the user for editing."""

    session_id: str
    query: str
    research_mode: str = "general"
    sections: list[OutlineSection]
    research_tasks: list[ResearchTask]


class OutlineConfirmation(BaseModel):
    """User's response to the proposed outline."""

    session_id: str
    approved: bool = True
    sections: list[OutlineSection] | None = None
    research_tasks: list[ResearchTask] | None = None

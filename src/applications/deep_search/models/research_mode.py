from __future__ import annotations

from enum import StrEnum


class ResearchMode(StrEnum):
    """Controls the output format and planning strategy for deep search."""

    GENERAL = "general"
    ACADEMIC = "academic"
    CONSULTANT = "consultant"

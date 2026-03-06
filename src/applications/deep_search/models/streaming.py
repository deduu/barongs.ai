from __future__ import annotations

from enum import StrEnum


class DeepSearchEventType(StrEnum):
    STATUS = "status"
    DISAMBIGUATION_REQUIRED = "disambiguation_required"
    DISAMBIGUATION_CONFIRMED = "disambiguation_confirmed"
    PLANNING = "planning"
    RESEARCHING = "researching"
    FINDING = "finding"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"
    CHUNK = "chunk"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    BUDGET_UPDATE = "budget_update"
    OUTLINE_READY = "outline_ready"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    OUTLINE_CONFIRMED = "outline_confirmed"
    DONE = "done"
    ERROR = "error"

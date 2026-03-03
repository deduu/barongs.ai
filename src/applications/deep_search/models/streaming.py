from __future__ import annotations

from enum import StrEnum


class DeepSearchEventType(StrEnum):
    STATUS = "status"
    PLANNING = "planning"
    RESEARCHING = "researching"
    FINDING = "finding"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"
    CHUNK = "chunk"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    BUDGET_UPDATE = "budget_update"
    DONE = "done"
    ERROR = "error"

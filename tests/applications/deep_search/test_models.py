from __future__ import annotations

import pytest

from src.applications.deep_search.models.api import DeepSearchRequest, DeepSearchResponse
from src.applications.deep_search.models.research import (
    ReportSection,
    ResearchBudget,
    ResearchFinding,
    ResearchPlan,
    ResearchReport,
    ResearchTask,
    ResearchTaskStatus,
    ResearchTaskType,
    SourceCredibility,
)
from src.applications.deep_search.models.streaming import DeepSearchEventType

# --- ResearchTaskType ---


class TestResearchTaskType:
    def test_values(self):
        assert ResearchTaskType.SECONDARY_WEB == "secondary_web"
        assert ResearchTaskType.SECONDARY_ACADEMIC == "secondary_academic"
        assert ResearchTaskType.PRIMARY_CODE == "primary_code"
        assert ResearchTaskType.FACT_CHECK == "fact_check"
        assert ResearchTaskType.REFLECTION == "reflection"


# --- ResearchTaskStatus ---


class TestResearchTaskStatus:
    def test_values(self):
        assert ResearchTaskStatus.PENDING == "pending"
        assert ResearchTaskStatus.RUNNING == "running"
        assert ResearchTaskStatus.COMPLETED == "completed"
        assert ResearchTaskStatus.FAILED == "failed"
        assert ResearchTaskStatus.SKIPPED == "skipped"


# --- ResearchTask ---


class TestResearchTask:
    def test_defaults(self):
        task = ResearchTask(
            task_id="t1",
            query="What is Python?",
            task_type=ResearchTaskType.SECONDARY_WEB,
        )
        assert task.task_id == "t1"
        assert task.status == ResearchTaskStatus.PENDING
        assert task.depends_on == []
        assert task.priority == 1
        assert task.agent_name is None

    def test_with_dependencies(self):
        task = ResearchTask(
            task_id="t2",
            query="Verify claims",
            task_type=ResearchTaskType.FACT_CHECK,
            depends_on=["t1"],
            priority=2,
            agent_name="fact_checker",
        )
        assert task.depends_on == ["t1"]
        assert task.priority == 2
        assert task.agent_name == "fact_checker"

    def test_serialization(self):
        task = ResearchTask(
            task_id="t1",
            query="test",
            task_type=ResearchTaskType.SECONDARY_WEB,
        )
        data = task.model_dump()
        assert data["task_id"] == "t1"
        assert data["task_type"] == "secondary_web"
        restored = ResearchTask.model_validate(data)
        assert restored == task


# --- ResearchPlan ---


class TestResearchPlan:
    def test_defaults(self):
        plan = ResearchPlan(
            original_query="How does Python GIL work?",
            tasks=[
                ResearchTask(
                    task_id="t1",
                    query="Python GIL mechanism",
                    task_type=ResearchTaskType.SECONDARY_WEB,
                ),
            ],
        )
        assert plan.max_iterations == 3
        assert len(plan.tasks) == 1
        assert plan.original_query == "How does Python GIL work?"

    def test_custom_max_iterations(self):
        plan = ResearchPlan(
            original_query="test",
            tasks=[],
            max_iterations=5,
        )
        assert plan.max_iterations == 5


# --- SourceCredibility ---


class TestSourceCredibility:
    def test_defaults(self):
        cred = SourceCredibility()
        assert cred.domain_authority == 0.5
        assert cred.recency_score == 0.5
        assert cred.citation_count == 0
        assert cred.is_peer_reviewed is False
        assert cred.overall_score == 0.5

    def test_custom_values(self):
        cred = SourceCredibility(
            domain_authority=0.9,
            recency_score=0.8,
            citation_count=42,
            is_peer_reviewed=True,
            overall_score=0.85,
        )
        assert cred.domain_authority == 0.9
        assert cred.citation_count == 42
        assert cred.is_peer_reviewed is True


# --- ResearchFinding ---


class TestResearchFinding:
    def test_defaults(self):
        finding = ResearchFinding(
            finding_id="f1",
            content="Python uses a GIL",
            source_url="https://example.com",
        )
        assert finding.confidence == 0.5
        assert finding.methodology_tag == "secondary"
        assert finding.credibility is not None
        assert finding.citations == []

    def test_with_full_data(self):
        cred = SourceCredibility(overall_score=0.9)
        finding = ResearchFinding(
            finding_id="f1",
            content="Test finding",
            source_url="https://example.com",
            confidence=0.95,
            methodology_tag="data_analysis",
            credibility=cred,
            citations=["ref1", "ref2"],
        )
        assert finding.confidence == 0.95
        assert finding.methodology_tag == "data_analysis"
        assert len(finding.citations) == 2


# --- ResearchBudget ---


class TestResearchBudget:
    def test_defaults(self):
        budget = ResearchBudget()
        assert budget.max_llm_tokens == 100_000
        assert budget.max_api_calls == 50
        assert budget.max_time_seconds == 300
        assert budget.used_llm_tokens == 0
        assert budget.used_api_calls == 0
        assert budget.used_time_seconds == 0.0
        assert budget.is_exhausted is False

    def test_token_exhaustion(self):
        budget = ResearchBudget(max_llm_tokens=100, used_llm_tokens=100)
        assert budget.is_exhausted is True

    def test_api_call_exhaustion(self):
        budget = ResearchBudget(max_api_calls=5, used_api_calls=5)
        assert budget.is_exhausted is True

    def test_time_exhaustion(self):
        budget = ResearchBudget(max_time_seconds=60, used_time_seconds=60.0)
        assert budget.is_exhausted is True

    def test_partial_use_not_exhausted(self):
        budget = ResearchBudget(
            max_llm_tokens=1000,
            max_api_calls=10,
            max_time_seconds=300,
            used_llm_tokens=500,
            used_api_calls=3,
            used_time_seconds=100.0,
        )
        assert budget.is_exhausted is False


# --- ReportSection ---


class TestReportSection:
    def test_defaults(self):
        section = ReportSection(heading="Introduction", content="Some content")
        assert section.findings == []
        assert section.confidence == 0.5

    def test_with_findings(self):
        section = ReportSection(
            heading="Analysis",
            content="Data shows ...",
            findings=["f1", "f2"],
            confidence=0.8,
        )
        assert section.findings == ["f1", "f2"]


# --- ResearchReport ---


class TestResearchReport:
    def test_minimal(self):
        report = ResearchReport(
            executive_summary="Summary",
            sections=[ReportSection(heading="H1", content="C1")],
        )
        assert report.findings == []
        assert report.methodology_notes == ""
        assert report.limitations == ""
        assert report.overall_confidence == 0.5

    def test_full(self):
        finding = ResearchFinding(
            finding_id="f1",
            content="test",
            source_url="https://example.com",
        )
        report = ResearchReport(
            executive_summary="Summary",
            sections=[
                ReportSection(heading="H1", content="C1", findings=["f1"]),
            ],
            findings=[finding],
            methodology_notes="Used secondary research",
            limitations="Limited data",
            overall_confidence=0.85,
        )
        assert len(report.findings) == 1
        assert report.overall_confidence == 0.85

    def test_serialization_roundtrip(self):
        report = ResearchReport(
            executive_summary="Summary",
            sections=[ReportSection(heading="H1", content="C1")],
            overall_confidence=0.7,
        )
        json_str = report.model_dump_json()
        restored = ResearchReport.model_validate_json(json_str)
        assert restored.executive_summary == "Summary"
        assert restored.overall_confidence == 0.7


# --- DeepSearchEventType ---


class TestDeepSearchEventType:
    def test_all_event_types(self):
        expected = {
            "status", "planning", "researching", "finding", "reflecting",
            "synthesizing", "chunk", "knowledge_graph", "budget_update",
            "done", "error",
        }
        actual = {e.value for e in DeepSearchEventType}
        assert actual == expected


# --- API Models ---


class TestDeepSearchRequest:
    def test_defaults(self):
        req = DeepSearchRequest(query="What is quantum computing?")
        assert req.query == "What is quantum computing?"
        assert req.max_iterations == 3
        assert req.max_time_seconds == 300
        assert req.enable_code_execution is False
        assert req.enable_academic_search is True
        assert req.session_id is None

    def test_custom_values(self):
        req = DeepSearchRequest(
            query="test",
            max_iterations=5,
            max_time_seconds=600,
            enable_code_execution=True,
            enable_academic_search=False,
            session_id="sess-123",
        )
        assert req.max_iterations == 5
        assert req.enable_code_execution is True
        assert req.session_id == "sess-123"

    def test_query_required(self):
        with pytest.raises(ValueError):
            DeepSearchRequest()  # type: ignore[call-arg]


class TestDeepSearchResponse:
    def test_defaults(self):
        resp = DeepSearchResponse(
            executive_summary="Summary",
            sections=[],
        )
        assert resp.findings == []
        assert resp.methodology_notes == ""
        assert resp.overall_confidence == 0.5
        assert resp.sources == []

    def test_full(self):
        resp = DeepSearchResponse(
            executive_summary="Summary",
            sections=[{"heading": "H1", "content": "C1"}],
            findings=[{"id": "f1", "content": "test"}],
            methodology_notes="Secondary research",
            overall_confidence=0.9,
            sources=["https://example.com"],
        )
        assert len(resp.sources) == 1

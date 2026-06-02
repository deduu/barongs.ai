from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from src.applications.search_agent.agents.search_path import SearchPathAgent
from src.applications.search_agent.agents.search_pipeline import SearchPipelineAgent
from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.parallel import ParallelStrategy
from src.core.orchestrator.strategies.pipeline import PipelineStrategy
from src.core.orchestrator.strategies.pipeline_metadata import (
    PipelineWithMetadataStrategy,
)
from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy
from src.core.orchestrator.strategies.router import RouterStrategy
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy


def section(title: str) -> None:
    print(f"\n{'=' * 16} {title} {'=' * 16}")


def show_result(label: str, result: AgentResult) -> None:
    print(f"{label}:")
    print(f"  agent_name = {result.agent_name}")
    print(f"  response   = {result.response}")
    print(f"  metadata   = {result.metadata}")
    print(f"  tokens     = {result.token_usage}")


@dataclass
class DemoSource:
    url: str
    title: str
    snippet: str
    content: str
    index: int


class EchoAgent(Agent):
    def __init__(self, agent_name: str, prefix: str) -> None:
        self._name = agent_name
        self._prefix = prefix

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AgentContext) -> AgentResult:
        print(f"[{self.name}] received user_message={context.user_message!r}")
        return AgentResult(
            agent_name=self.name,
            response=f"{self._prefix}: {context.user_message}",
        )


class MetadataAgent(Agent):
    def __init__(
        self,
        agent_name: str,
        *,
        read_key: str | None,
        write_key: str,
        write_value: Any,
    ) -> None:
        self._name = agent_name
        self._read_key = read_key
        self._write_key = write_key
        self._write_value = write_value

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AgentContext) -> AgentResult:
        observed = context.metadata.get(self._read_key) if self._read_key else None
        print(
            f"[{self.name}] read metadata[{self._read_key!r}]={observed!r}; "
            f"writing {self._write_key!r}"
        )
        return AgentResult(
            agent_name=self.name,
            response=f"{self.name} saw {observed!r}",
            metadata={self._write_key: self._write_value},
        )


class SlowAgent(Agent):
    def __init__(self, agent_name: str, delay_seconds: float) -> None:
        self._name = agent_name
        self._delay_seconds = delay_seconds

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AgentContext) -> AgentResult:
        print(f"[{self.name}] starting work for {self._delay_seconds:.1f}s")
        await asyncio.sleep(self._delay_seconds)
        print(f"[{self.name}] finished")
        return AgentResult(
            agent_name=self.name,
            response=f"{self.name} handled {context.user_message}",
            token_usage={"completion_tokens": 10},
        )


class ClassifierAgent(Agent):
    @property
    def name(self) -> str:
        return "query_analyzer"

    async def run(self, context: AgentContext) -> AgentResult:
        query_type = context.metadata.get("force_query_type", "search")
        refined_queries = [
            f"{context.user_message} overview",
            f"{context.user_message} latest facts",
        ]
        print(
            f"[query_analyzer] classified query_type={query_type!r} "
            f"with refined_queries={refined_queries!r}"
        )
        return AgentResult(
            agent_name=self.name,
            response="classification complete",
            metadata={
                "query_type": query_type,
                "refined_queries": refined_queries,
            },
            token_usage={"prompt_tokens": 20, "completion_tokens": 5},
        )


class DemoWebResearcher(Agent):
    @property
    def name(self) -> str:
        return "web_researcher"

    async def run(self, context: AgentContext) -> AgentResult:
        refined_queries = context.metadata.get("refined_queries", [context.user_message])
        print(f"[web_researcher] refined_queries={refined_queries!r}")
        sources = [
            DemoSource(
                url="https://example.com/overview",
                title="Overview",
                snippet="High-level summary",
                content="This source explains the topic from a broad perspective.",
                index=1,
            ).__dict__,
            DemoSource(
                url="https://example.com/details",
                title="Details",
                snippet="Detailed notes",
                content="This source adds supporting details and caveats.",
                index=2,
            ).__dict__,
        ]
        return AgentResult(
            agent_name=self.name,
            response=f"Found {len(sources)} demo sources.",
            metadata={"sources": sources},
        )


class DemoSynthesizer(Agent):
    @property
    def name(self) -> str:
        return "synthesizer"

    async def run(self, context: AgentContext) -> AgentResult:
        sources = context.metadata.get("sources", [])
        source_titles = [source["title"] for source in sources]
        print(
            f"[synthesizer] user_message={context.user_message!r}; "
            f"sources={source_titles!r}"
        )
        return AgentResult(
            agent_name=self.name,
            response=(
                f"Final answer for {context.user_message!r} using "
                f"{len(sources)} sources: {', '.join(source_titles)}"
            ),
            metadata={"sources": sources},
            token_usage={"prompt_tokens": 50, "completion_tokens": 40},
        )


class DemoDirectAnswerer(Agent):
    @property
    def name(self) -> str:
        return "direct_answerer"

    async def run(self, context: AgentContext) -> AgentResult:
        print(f"[direct_answerer] answering directly for {context.user_message!r}")
        return AgentResult(
            agent_name=self.name,
            response=f"Direct answer: {context.user_message}",
            token_usage={"prompt_tokens": 8, "completion_tokens": 12},
        )


class DAGWorkerAgent(Agent):
    def __init__(self, agent_name: str, finding_prefix: str) -> None:
        self._name = agent_name
        self._finding_prefix = finding_prefix

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AgentContext) -> AgentResult:
        task_id = context.metadata.get("task_id")
        task_type = context.metadata.get("task_type")
        prior_findings = context.metadata.get("all_findings", [])
        print(
            f"[{self.name}] task_id={task_id!r} task_type={task_type!r} "
            f"prior_findings_count={len(prior_findings)}"
        )
        return AgentResult(
            agent_name=self.name,
            response=f"{self.name} completed task {task_id}",
            metadata={
                "findings": [
                    {
                        "finding_id": f"{task_id}-finding",
                        "summary": f"{self._finding_prefix} for {context.user_message}",
                    }
                ]
            },
            token_usage={"prompt_tokens": 15, "completion_tokens": 10},
        )


async def demo_single_agent() -> None:
    section("Single Agent Strategy")
    orchestrator = Orchestrator(
        strategy=SingleAgentStrategy(),
        agents=[EchoAgent("echo", "Echo")],
    )
    result = await orchestrator.run(AgentContext(user_message="hello orchestrator"))
    show_result("single agent output", result)


async def demo_pipeline() -> None:
    section("Pipeline Strategy")
    orchestrator = Orchestrator(
        strategy=PipelineStrategy(),
        agents=[
            EchoAgent("stage_1", "normalized"),
            EchoAgent("stage_2", "validated"),
            EchoAgent("stage_3", "finalized"),
        ],
    )
    result = await orchestrator.run(AgentContext(user_message="build a todo app"))
    show_result("pipeline output", result)
    print("Note: each stage received the previous stage's response as user_message.")


async def demo_pipeline_with_metadata() -> None:
    section("Pipeline With Metadata Strategy")
    orchestrator = Orchestrator(
        strategy=PipelineWithMetadataStrategy(),
        agents=[
            MetadataAgent(
                "parse_requirements",
                read_key=None,
                write_key="requirements",
                write_value={"entities": ["Task"], "auth": True},
            ),
            MetadataAgent(
                "generate_files",
                read_key="requirements",
                write_key="files",
                write_value=["models.py", "routes.py"],
            ),
            MetadataAgent(
                "validate_output",
                read_key="files",
                write_key="valid",
                write_value=True,
            ),
        ],
    )
    result = await orchestrator.run(
        AgentContext(user_message="generate an API", metadata={"job_id": "job-123"})
    )
    show_result("pipeline+metadata output", result)
    print("Note: metadata is accumulated and forwarded to later stages.")


async def demo_parallel() -> None:
    section("Parallel Strategy")
    orchestrator = Orchestrator(
        strategy=ParallelStrategy(),
        agents=[
            SlowAgent("search_news", 0.3),
            SlowAgent("search_docs", 0.1),
            SlowAgent("search_forums", 0.2),
        ],
    )
    result = await orchestrator.run(AgentContext(user_message="python async patterns"))
    show_result("parallel output", result)
    print("Note: the default merge concatenates responses and sums token usage.")


async def demo_router() -> None:
    section("Router Strategy")

    async def choose_agent(agents: list[Agent], context: AgentContext) -> Agent:
        preferred = "calculator" if "math" in context.user_message else "generalist"
        selected = next(agent for agent in agents if agent.name == preferred)
        print(f"[router] selected {selected.name!r}")
        return selected

    orchestrator = Orchestrator(
        strategy=RouterStrategy(routing_fn=choose_agent),
        agents=[
            EchoAgent("generalist", "General"),
            EchoAgent("calculator", "Math"),
        ],
    )
    result = await orchestrator.run(AgentContext(user_message="math: 12 * 8"))
    show_result("router output", result)


async def demo_search_pipeline() -> None:
    section("Search Pipeline Agent")
    search_path = SearchPathAgent(
        web_researcher=DemoWebResearcher(),
        synthesizer=DemoSynthesizer(),
    )
    pipeline = SearchPipelineAgent(
        query_analyzer=ClassifierAgent(),
        search_path=search_path,
        direct_answerer=DemoDirectAnswerer(),
    )
    outer_orchestrator = Orchestrator(
        strategy=SingleAgentStrategy(),
        agents=[pipeline],
    )

    search_result = await outer_orchestrator.run(
        AgentContext(
            user_message="What is retrieval augmented generation?",
            metadata={"force_query_type": "search"},
        )
    )
    show_result("search path output", search_result)

    direct_result = await outer_orchestrator.run(
        AgentContext(
            user_message="Say hello",
            metadata={"force_query_type": "direct"},
        )
    )
    show_result("direct path output", direct_result)

    print("Note: the outer orchestrator sees only one agent: search_pipeline.")
    print("Inside that agent:")
    print("  1. query_analyzer decides direct vs search")
    print("  2. search_path runs web_researcher -> synthesizer with metadata propagation")
    print("  3. direct_answerer bypasses web research when classification is direct")


async def demo_research_dag() -> None:
    section("Research DAG Strategy")
    strategy = ResearchDAGStrategy(max_iterations=2, per_agent_timeout=5.0)

    async def task_progress(payload: dict[str, Any]) -> None:
        print(f"[task_progress] {payload}")

    async def budget_progress(payload: dict[str, Any]) -> None:
        print(f"[budget_progress] {payload}")

    context = AgentContext(
        user_message="Evaluate the AI agent framework landscape",
        metadata={
            "research_plan": {
                "max_iterations": 2,
                "tasks": [
                    {
                        "task_id": "t1",
                        "query": "Survey commercial AI agent frameworks",
                        "task_type": "secondary_web",
                        "agent_name": "deep_web_researcher",
                        "depends_on": [],
                    },
                    {
                        "task_id": "t2",
                        "query": "Survey academic work on agent orchestration",
                        "task_type": "secondary_academic",
                        "agent_name": "academic_researcher",
                        "depends_on": [],
                    },
                    {
                        "task_id": "t3",
                        "query": "Cross-check overlap and contradictions",
                        "task_type": "fact_check",
                        "agent_name": "fact_checker",
                        "depends_on": ["t1", "t2"],
                    },
                    {
                        "task_id": "t4",
                        "query": "Identify gaps worth a follow-up pass",
                        "task_type": "reflection",
                        "agent_name": "reflection",
                        "depends_on": ["t3"],
                    },
                ],
            },
            "research_budget": {
                "max_llm_tokens": 500,
                "max_api_calls": 10,
                "max_time_seconds": 30.0,
                "used_llm_tokens": 0,
                "used_api_calls": 0,
                "used_time_seconds": 0.0,
            },
            "_task_progress_callback": task_progress,
            "_budget_progress_callback": budget_progress,
        },
    )

    orchestrator = Orchestrator(
        strategy=strategy,
        agents=[
            DAGWorkerAgent("deep_web_researcher", "web finding"),
            DAGWorkerAgent("academic_researcher", "academic finding"),
            DAGWorkerAgent("fact_checker", "fact-check finding"),
            DAGWorkerAgent("reflection", "reflection finding"),
        ],
        timeout_seconds=30.0,
    )

    result = await orchestrator.run(context)
    show_result("research dag output", result)
    print("Note: independent tasks run in the same wave, dependents wait until prerequisites finish.")


async def main() -> None:
    print("Run this file from the repository root with:")
    print("  py docs/orchestration_walkthrough.py")

    await demo_single_agent()
    await demo_pipeline()
    await demo_pipeline_with_metadata()
    await demo_parallel()
    await demo_router()
    await demo_search_pipeline()
    await demo_research_dag()


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.interfaces.tool import Tool
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext, ToolInput
from src.core.models.results import AgentResult

logger = logging.getLogger(__name__)

CODE_GEN_PROMPT = """You are a data analyst. Write Python code to answer the user's question.
Output ONLY the Python code, no explanation. The code should print results to stdout."""

INTERPRET_PROMPT = """You are a data analyst. Interpret the code execution results and provide a clear finding.
Be specific about what the data shows. Provide the finding in 2-3 sentences."""


class DataAnalystAgent(Agent):
    """Generates and executes Python code for primary data analysis."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        code_execution_tool: Tool,
        model: str = "gpt-4o",
        max_retries: int = 1,
    ) -> None:
        self._llm = llm_provider
        self._code_tool = code_execution_tool
        self._model = model
        self._max_retries = max_retries

    @property
    def name(self) -> str:
        return "data_analyst"

    @property
    def description(self) -> str:
        return "Generates and executes Python code for data analysis."

    async def run(self, context: AgentContext) -> AgentResult:
        query = context.user_message

        # Step 1: Generate code
        code = await self._generate_code(query)
        if not code:
            return AgentResult(
                agent_name=self.name,
                response="Failed to generate analysis code.",
                metadata={"findings": []},
            )

        # Step 2: Execute with retry
        exec_result = None
        for attempt in range(1 + self._max_retries):
            exec_result = await self._code_tool.execute(
                ToolInput(tool_name=self._code_tool.name, parameters={"code": code})
            )

            if exec_result.success and exec_result.output:
                if exec_result.output.get("exit_code", 1) == 0:
                    break
                # Code error — ask LLM to fix
                if attempt < self._max_retries:
                    error_msg = exec_result.output.get("stderr", "Unknown error")
                    code = await self._fix_code(query, code, error_msg)

        if not exec_result or not exec_result.success or not exec_result.output:
            return AgentResult(
                agent_name=self.name,
                response="Code execution failed.",
                metadata={"findings": []},
            )

        # Step 3: Interpret results
        stdout = exec_result.output.get("stdout", "")
        stderr = exec_result.output.get("stderr", "")
        interpretation = await self._interpret_results(query, code, stdout, stderr)

        finding: dict[str, Any] = {
            "finding_id": f"f_{uuid.uuid4().hex[:8]}",
            "content": interpretation,
            "source_url": "code_execution",
            "confidence": 0.8 if exec_result.output.get("exit_code") == 0 else 0.4,
            "methodology_tag": "data_analysis",
            "credibility": {"domain_authority": 0.8, "overall_score": 0.8},
            "citations": [],
        }

        return AgentResult(
            agent_name=self.name,
            response=interpretation,
            metadata={"findings": [finding], "code": code, "output": stdout},
        )

    async def _generate_code(self, query: str) -> str:
        request = LLMRequest(
            messages=[LLMMessage(role="user", content=query)],
            model=self._model,
            system_prompt=CODE_GEN_PROMPT,
            temperature=0.2,
        )
        response = await self._llm.generate(request)
        return self._strip_code_fences(response.content)

    async def _fix_code(self, query: str, code: str, error: str) -> str:
        request = LLMRequest(
            messages=[
                LLMMessage(
                    role="user",
                    content=f"Fix this code that had an error.\n\nQuery: {query}\n\nCode:\n{code}\n\nError:\n{error}",
                )
            ],
            model=self._model,
            system_prompt="Fix the Python code. Output ONLY the corrected code.",
            temperature=0.2,
        )
        response = await self._llm.generate(request)
        return self._strip_code_fences(response.content)

    async def _interpret_results(self, query: str, code: str, stdout: str, stderr: str) -> str:
        request = LLMRequest(
            messages=[
                LLMMessage(
                    role="user",
                    content=f"Query: {query}\n\nCode:\n{code}\n\nOutput:\n{stdout}\n\nErrors:\n{stderr}",
                )
            ],
            model=self._model,
            system_prompt=INTERPRET_PROMPT,
            temperature=0.3,
        )
        response = await self._llm.generate(request)
        return response.content

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        import re

        match = re.search(r"```(?:python)?\s*([\s\S]*?)```", content)
        return match.group(1).strip() if match else content.strip()

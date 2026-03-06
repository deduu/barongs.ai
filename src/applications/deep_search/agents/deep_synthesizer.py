from __future__ import annotations

from collections import Counter
from collections.abc import AsyncIterator
import re
from typing import Any

from src.applications.deep_search.models.research_mode import ResearchMode
from src.applications.deep_search.prompts.synthesizer_prompts import SYNTH_PROMPTS
from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class DeepSynthesizerAgent(Agent):
    """Produces final research report with structured sections and streaming support."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "deep_synthesizer"

    @property
    def description(self) -> str:
        return "Synthesizes research findings into a comprehensive report."

    def _format_findings(self, findings: list[dict[str, Any]]) -> str:
        if not findings:
            return (
                "WARNING: No verified findings are available about this specific entity. "
                "Do NOT fabricate information. Instead, explain what was searched and that "
                "insufficient verified information was found."
            )
        parts: list[str] = []
        for f in findings:
            parts.append(
                f"[{f.get('finding_id', 'unknown')}] (confidence: {f.get('confidence', 'N/A')})\n"
                f"Source: {f.get('source_url', 'unknown')}\n"
                f"Content: {f.get('content', '')[:4000]}\n"
            )
        return "\n".join(parts)

    @staticmethod
    def _relevant_findings(context: AgentContext) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = context.metadata.get("findings", [])
        misattributed_ids = set(context.metadata.get("misattributed_ids", []))
        return [f for f in findings if f.get("finding_id") not in misattributed_ids]

    @staticmethod
    def _attempted_sources(context: AgentContext) -> list[dict[str, Any]]:
        attempted = context.metadata.get("attempted_sources", [])
        if not isinstance(attempted, list):
            return []
        normalized: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for source in attempted:
            if not isinstance(source, dict):
                continue
            url = source.get("url")
            if not isinstance(url, str) or not url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            normalized.append(source)
        return normalized

    def _reference_catalog(
        self,
        findings: list[dict[str, Any]],
        attempted_sources: list[dict[str, Any]],
    ) -> str:
        if not findings and not attempted_sources:
            return "No verified findings or attempted references were captured."

        lines: list[str] = []
        for f in findings:
            finding_id = f.get("finding_id", "unknown")
            url = f.get("source_url", "unknown")
            title = ""
            citations = f.get("citations")
            if isinstance(citations, list) and citations:
                title = str(citations[0])
            label = title if title else "Untitled source"
            lines.append(f"- [{finding_id}] {label} | {url}")
        finding_urls = {
            str(f.get("source_url", ""))
            for f in findings
            if isinstance(f.get("source_url"), str)
        }
        supplemental_sources = [
            source
            for source in attempted_sources
            if str(source.get("url", "")) and str(source.get("url", "")) not in finding_urls
        ]
        if supplemental_sources:
            if lines:
                lines.append("- [search_log] Supplemental search coverage below")
            for idx, source in enumerate(supplemental_sources, start=1):
                url = source.get("url", "unknown")
                title = source.get("title") or "Untitled source"
                status = source.get("status") or "attempted"
                lines.append(f"- [s{idx}] {title} | {url} | status: {status}")
        return "\n".join(lines)

    def _length_guidance(self, findings: list[dict[str, Any]]) -> str:
        if not findings:
            return (
                "Evidence may be sparse, but still produce a full report with all required sections. "
                "Target 900-1500 words focused on search scope, source coverage, evidence gaps, "
                "limitations, and concrete next steps. Do not collapse into a stub response."
            )
        if len(findings) >= 8:
            return "Target 1800-3000 words with substantive evidence in each section."
        if len(findings) >= 4:
            return "Target 1200-2200 words with detailed evidence and citations."
        return "Target 800-1400 words and avoid filler."

    def _auto_reference_section(self, findings: list[dict[str, Any]]) -> str:
        if not findings:
            return ""
        lines = ["## References"]
        for idx, f in enumerate(findings, start=1):
            finding_id = f.get("finding_id", "unknown")
            url = f.get("source_url", "unknown")
            title = ""
            citations = f.get("citations")
            if isinstance(citations, list) and citations:
                title = str(citations[0])
            if title:
                lines.append(f"{idx}. [[{finding_id}]]({url}) {title}")
            else:
                lines.append(f"{idx}. [[{finding_id}]]({url})")
        return "\n".join(lines)

    def _attempted_reference_section(self, attempted_sources: list[dict[str, Any]]) -> str:
        if not attempted_sources:
            return ""
        lines = ["## Search Log References"]
        for idx, source in enumerate(attempted_sources, start=1):
            url = source.get("url", "unknown")
            title = source.get("title") or "Untitled source"
            status = source.get("status") or "attempted"
            lines.append(f"{idx}. [{title}]({url}) - status: {status}")
        return "\n".join(lines)

    def _source_status_summary(self, attempted_sources: list[dict[str, Any]]) -> str:
        if not attempted_sources:
            return "No source attempts were recorded."
        counts = Counter(str(source.get("status", "attempted")) for source in attempted_sources)
        return ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))

    def _build_no_findings_report(self, context: AgentContext) -> str:
        attempted_sources = self._attempted_sources(context)
        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "the requested topic")
        research_mode = ResearchMode(context.metadata.get("research_mode", "general"))
        search_log = self._attempted_reference_section(attempted_sources)
        coverage = self._source_status_summary(attempted_sources)

        if research_mode is ResearchMode.ACADEMIC:
            sections = [
                "# Abstract",
                (
                    f"This deep-search run did not produce verified findings specifically about "
                    f"{entity_name}. The retrieval pipeline searched available academic and web "
                    "sources, but no source passed both relevance and extraction checks strongly "
                    "enough to support evidence-backed claims."
                ),
                "## 1. Introduction",
                (
                    f"The query focused on {entity_name}. Because the run ended without verified "
                    "findings, this report should be read as a retrieval-status summary rather than "
                    "a substantive literature review."
                ),
                "## 2. Methodology",
                (
                    "The system attempted web and academic retrieval, then applied relevance and "
                    "extraction filters to candidate sources. Attempted source statuses: "
                    f"{coverage}."
                ),
                "## 3. Results",
                (
                    "No findings met the threshold for inclusion. This does not prove the topic is "
                    "unsupported in the literature; it indicates this run failed to capture enough "
                    "verified evidence."
                ),
                "## 4. Limitations",
                (
                    "Possible failure modes include ambiguous entity naming, noisy search queries, "
                    "limited accessible page content, or over-aggressive relevance filtering."
                ),
                "## 5. Recommended Next Steps",
                (
                    "Retry with a tighter entity description, seed the search with known primary "
                    "URLs, or broaden retrieval limits before drawing conclusions."
                ),
                "## References",
                "No verified sources were cited because no findings passed the evidence threshold.",
            ]
        elif research_mode is ResearchMode.CONSULTANT:
            sections = [
                "# Executive Summary",
                (
                    f"This run did not produce verified findings about {entity_name}. Treat the "
                    "output as a search-status diagnostic, not as evidence that the risks are absent."
                ),
                "## Situation Assessment",
                (
                    "The pipeline attempted targeted web and academic retrieval but did not keep any "
                    f"source as a validated finding. Attempted source statuses: {coverage}."
                ),
                "## Risk Analysis",
                (
                    "The primary risk is false confidence from sparse or misclassified evidence. A "
                    "failed retrieval pass should trigger more targeted collection, not a definitive conclusion."
                ),
                "## Recommendations",
                (
                    "Use a narrower search query, provide known seed sources, and rerun with broader "
                    "source limits before presenting conclusions to stakeholders."
                ),
                "## References",
                "No verified references were cited in this run.",
            ]
        else:
            sections = [
                "# Executive Summary",
                (
                    f"No verified findings were produced for {entity_name} in this deep-search run. "
                    "The result is inconclusive rather than negative."
                ),
                "## Search Coverage",
                (
                    f"Attempted source statuses: {coverage}. Candidate sources were retrieved, but no "
                    "evidence passed all relevance and extraction checks."
                ),
                "## Limitations",
                (
                    "This can happen when the query is noisy, the entity is ambiguous, or the crawler "
                    "cannot capture enough source text for reliable extraction."
                ),
                "## Next Steps",
                (
                    "Retry with a tighter entity label, add seed URLs, or expand retrieval limits to "
                    "improve recall before drawing conclusions."
                ),
                "## References",
                "No verified references were cited in this run.",
            ]

        report = "\n\n".join(sections)
        if search_log:
            report = f"{report}\n\n{search_log}"
        return report

    def _postprocess_output(self, content: str, context: AgentContext) -> str:
        findings = self._relevant_findings(context)
        attempted_sources = self._attempted_sources(context)
        if not findings:
            if not attempted_sources:
                return content
            additions: list[str] = []
            if "## Search Log References" not in content:
                search_log_section = self._attempted_reference_section(attempted_sources)
                if search_log_section:
                    additions.append(search_log_section)
            if additions:
                return content.rstrip() + "\n\n" + "\n\n".join(additions)
            return content

        needs_refs = "## References" not in content
        has_clickable_citation = bool(re.search(r"\[\[[^\]]+\]\]\(https?://", content))

        additions: list[str] = []
        if not has_clickable_citation:
            additions.append("## Citation Index")
            for f in findings:
                fid = f.get("finding_id", "unknown")
                url = f.get("source_url", "unknown")
                additions.append(f"- [[{fid}]]({url})")

        if needs_refs:
            additions.append(self._auto_reference_section(findings))

        if attempted_sources and "## Search Log References" not in content:
            search_log_section = self._attempted_reference_section(attempted_sources)
            if search_log_section:
                additions.append(search_log_section)

        if not additions:
            return content
        return content.rstrip() + "\n\n" + "\n\n".join(a for a in additions if a)

    def _build_request(self, context: AgentContext) -> LLMRequest:
        attempted_sources = self._attempted_sources(context)
        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "the subject")
        entity_desc = entity_grounding.get("description", "")

        relevant_findings = self._relevant_findings(context)

        entity_context = ""
        if entity_desc:
            source_urls = entity_grounding.get("source_urls", [])
            entity_context = (
                f"TARGET ENTITY: {entity_name}\n"
                f"Description: {entity_desc}\n"
                f"Primary sources: {', '.join(source_urls)}\n"
            )

        findings_text = self._format_findings(relevant_findings)
        reference_catalog = self._reference_catalog(relevant_findings, attempted_sources)
        length_guidance = self._length_guidance(relevant_findings)

        custom_sections = context.metadata.get("custom_sections")
        if custom_sections:
            section_instructions = "\n".join(
                f"## {s['heading']}\n{s.get('description', '')}"
                for s in custom_sections
            )
            system_prompt = (
                f"You are a deep research synthesizer. Create a comprehensive research report "
                f"from the findings.\n\n{entity_context}\n\n"
                f"REFERENCE CATALOG:\n{reference_catalog}\n\n"
                f"Structure your response using EXACTLY these sections:\n\n{section_instructions}\n\n"
                f"FINDINGS:\n{findings_text}\n\n"
                f"IMPORTANT RULES:\n"
                f"- Every claim must reference a finding.\n"
                f"- Use clickable inline citations in this exact format: [[finding_id]](URL)\n"
                f"- ONLY include information that is specifically about {entity_name}.\n"
                f"- If a finding appears to be about a different entity, DISCARD it.\n"
                f"- Include a final '## References' section listing cited URLs."
            )
        else:
            research_mode = ResearchMode(context.metadata.get("research_mode", "general"))
            template = SYNTH_PROMPTS[research_mode]
            system_prompt = template.format(
                findings_text=findings_text,
                entity_context=entity_context,
                entity_name=entity_name,
                reference_catalog=reference_catalog,
                length_guidance=length_guidance,
            )

        temperature = context.metadata.get("temperature", 0.3)

        return LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if not self._relevant_findings(context):
            final_text = self._build_no_findings_report(context)
            return AgentResult(
                agent_name=self.name,
                response=final_text,
                metadata={"findings": context.metadata.get("findings", [])},
            )

        request = self._build_request(context)
        response = await self._llm.generate(request)
        final_text = self._postprocess_output(response.content, context)

        return AgentResult(
            agent_name=self.name,
            response=final_text,
            metadata={"findings": context.metadata.get("findings", [])},
            token_usage=response.usage,
        )

    async def stream_run(self, context: AgentContext) -> AsyncIterator[str]:
        """Yield response tokens as they arrive from the LLM."""
        if not self._relevant_findings(context):
            yield self._build_no_findings_report(context)
            return

        request = self._build_request(context)
        parts: list[str] = []
        async for token in self._llm.stream(request):
            parts.append(token)
            yield token
        final_text = "".join(parts)
        postprocessed = self._postprocess_output(final_text, context)
        if postprocessed != final_text:
            suffix = postprocessed[len(final_text):]
            if suffix:
                yield suffix

"""AI Worker — automatiza el trabajo humano que las plataformas requieren.

El principio es simple: usa IA para hacer el trabajo que las plataformas necesitan.
Es meta — IA haciendo trabajo de IA.

Cubre:
1. Pulse: evaluación de respuestas IA, etiquetado de datos, microtareas
2. Forge: propuestas de código, fixes para dev bounties
3. Freelancer: propuestas de proyectos, cover letters
4. Scope: verificación automática de scope desde reglas de programa
5. Triage: respuestas automáticas a preguntas de triage
6. Aplicación: postulación automática a jobs/bounties

Usa UnifiedAIProvider para asegurar mismos free models que IDE:
- OmniRoute (DeepSeek, Qwen, Gemini, Groq, Samba)
- NVIDIA NIM (Mistral, Llama, Nemotron)
- Ollama (local models)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from cores.ai.unified_provider import get_unified_provider

logger = logging.getLogger("orion.ai_worker")


# ── LLM Client Abstraction ─────────────────────────────────────


class LLMClient:
    """Unified LLM client using same free models as IDE."""

    def __init__(self, provider: str = "", model: str = ""):
        self._provider = get_unified_provider()
        self._default_model = model or "oc/deepseek-v4-flash-free"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from LLM using unified provider."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = await self._provider.chat(
            messages=messages,
            model=self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return result.get("content", "")


# ── Pulse Worker — AI Training & Microtasks ────────────────────


class PulseWorker:
    """Automates AI training tasks: evaluation, labeling, classification."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def evaluate_ai_response(
        self,
        prompt: str,
        response_a: str,
        response_b: str,
        criteria: str = "accuracy, helpfulness, safety",
    ) -> dict[str, Any]:
        """Evaluate which AI response is better (Outlier/DataAnnotation task)."""
        system = """You are an AI response evaluator. Compare two responses and determine which is better based on the given criteria. Respond with JSON: {"winner": "A" or "B", "reason": "brief explanation", "scores": {"A": score, "B": score}}"""

        user = f"""Evaluate these responses based on: {criteria}

Original prompt:
{prompt}

Response A:
{response_a}

Response B:
{response_b}

Which response is better? Be objective and brief."""

        result = await self._llm.generate(system, user, max_tokens=512, temperature=0.3)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"winner": "A", "reason": result, "raw": result}

    async def label_data(
        self,
        data: str,
        labels: list[str],
        instructions: str = "",
    ) -> dict[str, Any]:
        """Label/classify data according to given categories."""
        system = f"""You are a data labeler. Classify the given data into one of these categories: {", ".join(labels)}. Respond with JSON: {{"label": "chosen_label", "confidence": 0.0-1.0, "reason": "brief reason"}}"""

        user = f"""Labels: {", ".join(labels)}
Instructions: {instructions}

Data to classify:
{data}

Classification:"""

        result = await self._llm.generate(system, user, max_tokens=256, temperature=0.2)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"label": labels[0] if labels else "unknown", "reason": result}

    async def answer_survey(
        self,
        questions: list[dict[str, Any]],
        context: str = "",
    ) -> list[dict[str, Any]]:
        """Answer survey/research questions (common in AI work)."""
        system = """You are completing a research survey. Answer questions naturally and consistently. Respond with JSON array: [{"question": "...", "answer": "..."}]"""

        q_text = "\n".join([f"- {q.get('text', q)}" for q in questions])
        user = f"""Context: {context}

Questions:
{q_text}

Answer each question thoughtfully."""

        result = await self._llm.generate(system, user, max_tokens=1024, temperature=0.7)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return [{"question": q.get("text", str(q)), "answer": result} for q in questions]


# ── Forge Worker — Code Proposals & Fixes ──────────────────────


class ForgeWorker:
    """Automates dev bounty work: code proposals, fixes, and PRs."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def generate_fix_proposal(
        self,
        issue_description: str,
        code_context: str = "",
        language: str = "python",
    ) -> dict[str, Any]:
        """Generate a code fix proposal for a dev bounty."""
        system = f"""You are an expert {language} developer. Generate a fix for the described issue. Respond with {{"analysis": "brief analysis", "solution": "solution description", "code": "code diff or snippet", "files": ["affected files"], "testing": "how to test"}}"""

        user = f"""Issue:
{issue_description}

Code context:
{code_context or "N/A"}

Generate a fix proposal. Be specific and include actual code."""

        result = await self._llm.generate(system, user, max_tokens=2048, temperature=0.5)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"analysis": "Generated fix", "code": result, "raw": result}

    async def write_pr_description(
        self,
        issue_title: str,
        changes_summary: str,
        files_changed: list[str],
    ) -> str:
        """Write a PR description for a code fix."""
        system = """You write clear, concise PR descriptions. Follow standard format: Summary, Changes, Testing, Checklist."""

        user = f"""Issue: {issue_title}

Changes:
{changes_summary}

Files changed: {", ".join(files_changed)}

Write a PR description."""

        return await self._llm.generate(system, user, max_tokens=512, temperature=0.5)


# ── Proposal Worker — Freelancer & Job Applications ────────────


class ProposalWorker:
    """Generates project proposals and job applications."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def generate_proposal(
        self,
        project_description: str,
        budget: str = "",
        skills: list[str] = None,
        experience: str = "",
    ) -> dict[str, Any]:
        """Generate a winning project proposal."""
        system = """You write compelling freelance project proposals. Be specific, show expertise, and address the client's exact needs. Respond with {"title": "proposal title", "cover_letter": "full proposal text", "approach": "your approach", "timeline": "estimated timeline", "price_suggestion": "price range"}"""

        user = f"""Project: {project_description}
Budget: {budget or "Not specified"}
Your skills: {", ".join(skills or ["software development"])}
Experience: {experience or "Professional developer with 5+ years"}

Generate a compelling proposal."""

        result = await self._llm.generate(system, user, max_tokens=1024, temperature=0.7)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"cover_letter": result, "title": "Proposal"}

    async def generate_cover_letter(
        self,
        job_description: str,
        skills: list[str],
        experience: str = "",
    ) -> str:
        """Generate a tailored cover letter for job applications."""
        system = """You write personalized cover letters. Match the job requirements with relevant skills. Be concise and professional."""

        user = f"""Job description:
{job_description}

Your skills: {", ".join(skills)}
Experience: {experience or "Relevant professional experience"}

Write a cover letter."""

        return await self._llm.generate(system, user, max_tokens=512, temperature=0.7)

    async def answer_screening_questions(
        self,
        questions: list[str],
        skills: list[str],
        experience: str = "",
    ) -> list[dict[str, str]]:
        """Answer job screening questions."""
        system = (
            """Answer job screening questions professionally and concisely. Highlight relevant skills and experience."""
        )

        q_text = "\n".join([f"Q: {q}" for q in questions])
        user = f"""Questions:
{q_text}

Skills: {", ".join(skills)}
Experience: {experience}

Answer each question in 2-3 sentences."""

        result = await self._llm.generate(system, user, max_tokens=512, temperature=0.5)
        answers = []
        for _i, q in enumerate(questions):
            answers.append({"question": q, "answer": result})
        return answers


# ── Scope Worker — Automatic Scope Verification ────────────────


class ScopeWorker:
    """Automatically parses and verifies program scope rules."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def parse_scope_rules(
        self,
        scope_text: str,
    ) -> dict[str, Any]:
        """Parse program scope rules into structured format."""
        system = """You parse bug bounty program scope rules. Extract: in_scope domains, out_of_scope domains, allowed vulnerability types, forbidden actions, bounty ranges. Respond with JSON: {"in_scope": ["domain patterns"], "out_of_scope": ["domain patterns"], "allowed_vulns": ["type1", "type2"], "forbidden": ["action1"], "bounty_range": {"min": 0, "max": 0}, "rules": ["additional rules"]}"""

        user = f"""Scope rules:
{scope_text}

Parse into structured format."""

        result = await self._llm.generate(system, user, max_tokens=1024, temperature=0.2)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"in_scope": [], "out_scope": [], "raw": result}

    async def check_endpoint_in_scope(
        self,
        endpoint: str,
        vulnerability_type: str,
        scope_rules: dict[str, Any],
    ) -> dict[str, Any]:
        """Check if an endpoint + vuln type is in scope."""
        system = """You verify if a vulnerability finding is within program scope. Respond with JSON: {"in_scope": true/false, "reason": "explanation", "confidence": 0.0-1.0, "bounty_estimate": "estimated range"}"""

        user = f"""Endpoint: {endpoint}
Vulnerability type: {vulnerability_type}
Scope rules: {json.dumps(scope_rules, indent=2)}

Is this finding in scope?"""

        result = await self._llm.generate(system, user, max_tokens=512, temperature=0.2)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"in_scope": True, "reason": result, "confidence": 0.5}


# ── Triage Worker — Auto-respond to Triage Questions ──────────


class TriageWorker:
    """Auto-responds to platform triage questions using evidence."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def respond_triage_question(
        self,
        question: str,
        finding_data: dict[str, Any],
        evidence: str = "",
    ) -> str:
        """Generate a response to a triage question based on evidence."""
        system = """You are a security researcher responding to bug bounty triage questions. Be factual, professional, and reference specific evidence. Keep responses concise (2-3 paragraphs max)."""

        user = f"""Finding: {finding_data.get("title", "N/A")}
Type: {finding_data.get("vulnerability_type", "N/A")}
Endpoint: {finding_data.get("endpoint", "N/A")}
Evidence: {evidence or "See attached report"}

Triage question: {question}

Respond professionally."""

        return await self._llm.generate(system, user, max_tokens=512, temperature=0.4)

    async def generate_reproduction_steps(
        self,
        finding_data: dict[str, Any],
    ) -> list[str]:
        """Generate clear reproduction steps from finding data."""
        system = """You write clear, step-by-step reproduction instructions for security vulnerabilities. Number each step. Include exact commands where applicable."""

        user = f"""Finding: {json.dumps(finding_data, indent=2)}

Generate reproduction steps."""

        result = await self._llm.generate(system, user, max_tokens=512, temperature=0.4)
        steps = [s.strip() for s in result.split("\n") if s.strip()]
        return steps


# ── Auto Applicator — Apply to Bounties & Jobs ─────────────────


class AutoApplicant:
    """Automatically applies to bounties and submits work."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def submit_forge_bounty(
        self,
        platform: str,
        bounty_id: str,
        fix_code: str,
        description: str,
        api_key: str = "",
    ) -> dict[str, Any]:
        """Submit a fix to a dev bounty platform."""
        # Generate PR description
        proposal = ForgeWorker(self._llm)
        pr_desc = await proposal.write_pr_description(
            issue_title=f"Fix for {bounty_id}",
            changes_summary=description,
            files_changed=["fix.patch"],
        )

        logger.info("[AUTO_APPLICANT] Generated fix for %s/%s", platform, bounty_id)
        return {
            "platform": platform,
            "bounty_id": bounty_id,
            "pr_description": pr_desc,
            "code": fix_code,
            "submitted": False,  # Actual submission needs platform-specific API
        }

    async def submit_freelancer_proposal(
        self,
        project_id: str,
        proposal_text: str,
        bid_amount: float,
        delivery_days: int,
    ) -> dict[str, Any]:
        """Submit a proposal to Freelancer.com."""
        logger.info("[AUTO_APPLICANT] Generated proposal for project %s", project_id)
        return {
            "project_id": project_id,
            "proposal": proposal_text,
            "bid_amount": bid_amount,
            "delivery_days": delivery_days,
            "submitted": False,
        }


# ── Main Orchestrator ──────────────────────────────────────────


class AIWorkerOrchestrator:
    """Main entry point — coordinates all AI workers."""

    def __init__(self) -> None:
        self._llm = LLMClient()
        self._pulse = PulseWorker(self._llm)
        self._forge = ForgeWorker(self._llm)
        self._proposal = ProposalWorker(self._llm)
        self._scope = ScopeWorker(self._llm)
        self._triage = TriageWorker(self._llm)
        self._applicant = AutoApplicant(self._llm)

    @property
    def pulse(self) -> PulseWorker:
        return self._pulse

    @property
    def forge(self) -> ForgeWorker:
        return self._forge

    @property
    def proposal(self) -> ProposalWorker:
        return self._proposal

    @property
    def scope(self) -> ScopeWorker:
        return self._scope

    @property
    def triage(self) -> TriageWorker:
        return self._triage

    @property
    def applicant(self) -> AutoApplicant:
        return self._applicant

    @property
    def llm(self) -> LLMClient:
        return self._llm

    async def auto_process_pulse_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Process a Pulse (AI work) task end-to-end."""
        task_type = task.get("type", "")
        result: dict[str, Any] = {"task_id": task.get("id"), "type": task_type}

        if task_type == "evaluate":
            evaluation = await self._pulse.evaluate_ai_response(
                prompt=task.get("prompt", ""),
                response_a=task.get("response_a", ""),
                response_b=task.get("response_b", ""),
                criteria=task.get("criteria", "accuracy, helpfulness"),
            )
            result["evaluation"] = evaluation

        elif task_type == "label":
            labeling = await self._pulse.label_data(
                data=task.get("data", ""),
                labels=task.get("labels", []),
                instructions=task.get("instructions", ""),
            )
            result["labeling"] = labeling

        elif task_type == "survey":
            answers = await self._pulse.answer_survey(
                questions=task.get("questions", []),
                context=task.get("context", ""),
            )
            result["answers"] = answers

        else:
            result["error"] = f"Unknown task type: {task_type}"

        result["processed_at"] = datetime.now(UTC).isoformat()
        return result

    async def auto_process_forge_bounty(self, bounty: dict[str, Any]) -> dict[str, Any]:
        """Process a Forge (dev bounty) end-to-end."""
        proposal = await self._forge.generate_fix_proposal(
            issue_description=bounty.get("description", ""),
            code_context=bounty.get("code_context", ""),
            language=bounty.get("language", "python"),
        )

        pr_desc = await self._forge.write_pr_description(
            issue_title=bounty.get("title", "Fix"),
            changes_summary=proposal.get("solution", ""),
            files_changed=proposal.get("files", ["fix.patch"]),
        )

        return {
            "bounty_id": bounty.get("id"),
            "platform": bounty.get("platform"),
            "proposal": proposal,
            "pr_description": pr_desc,
            "processed_at": datetime.now(UTC).isoformat(),
        }

    async def auto_process_freelancer_project(self, project: dict[str, Any]) -> dict[str, Any]:
        """Process a Freelancer project end-to-end."""
        proposal = await self._proposal.generate_proposal(
            project_description=project.get("description", ""),
            budget=project.get("budget", ""),
            skills=project.get("required_skills", []),
        )

        return {
            "project_id": project.get("id"),
            "proposal": proposal,
            "processed_at": datetime.now(UTC).isoformat(),
        }

    async def auto_verify_scope(
        self,
        scope_text: str,
        endpoint: str,
        vuln_type: str,
    ) -> dict[str, Any]:
        """Auto-verify if a finding is in scope."""
        rules = await self._scope.parse_scope_rules(scope_text)
        check = await self._scope.check_endpoint_in_scope(endpoint, vuln_type, rules)
        return {
            "endpoint": endpoint,
            "vulnerability_type": vuln_type,
            "scope_rules": rules,
            "verification": check,
        }


_orchestrator: AIWorkerOrchestrator | None = None


def get_ai_worker() -> AIWorkerOrchestrator:
    """Get singleton AIWorkerOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIWorkerOrchestrator()
    return _orchestrator

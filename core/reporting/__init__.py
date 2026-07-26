"""Report generation for the Validation Engine pipeline.

Transforms a promoted Finding (from ValidationPromoter) into a professional
bug bounty report with executive summary, CVSS, PoC, evidence, and remediation.

Pipeline:
  PromoteDecision + AttackCandidate + ValidationResult
    → ValidatorReport
      → markdown output (save to file or return as string)
      → optional: JSON structured data for API responses
"""

from core.reporting.validator_report import ValidatorReport

__all__ = ["ValidatorReport", "generate_and_save_report"]


def generate_and_save_report(
    finding_id: int,
    finding_title: str,
    severity: str,
    target_name: str,
    endpoint_path: str,
    method: str,
    vulnerability_type: str,
    description: str,
    confidence: float,
    poc_curl: str,
    poc_python: str,
    evidence_data: dict | None = None,
    signals: list[str] | None = None,
    reproducible: bool = False,
    output_path: str | None = None,
) -> str:
    """One-shot: generate a report from raw data and optionally save it.

    Returns the markdown string.
    """
    report = ValidatorReport(
        finding_id=finding_id,
        title=finding_title,
        severity=severity,
        target_name=target_name,
        endpoint_path=endpoint_path,
        method=method,
        vulnerability_type=vulnerability_type,
        description=description,
        confidence=confidence,
        poc_curl=poc_curl,
        poc_python=poc_python,
        evidence_data=evidence_data or {},
        signals=signals or [],
        reproducible=reproducible,
    )
    md = report.to_markdown()
    if output_path:
        import datetime
        import pathlib

        path = pathlib.Path(output_path)
        if path.is_dir():
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = path / f"report_{finding_id}_{ts}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
    return md

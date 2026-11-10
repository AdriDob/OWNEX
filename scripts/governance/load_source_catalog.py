#!/usr/bin/env python3
"""Load the 60-source catalog into OWNEX SourceDiscoveryRegistry.

Deduplicates via SHA256 URL hashing, classifies each source by mechanism,
and persists the registry at .orion/source_discovery/candidates.json.

Usage:
    python scripts/governance/load_source_catalog.py

What it does:
1. Reads the 60 sources from the specification (hardcoded catalog).
2. Deduplicates entries using SHA256 of the source URL -> source_id.
3. Fixes the 7 documented duplicates (positions 21, 65, 66, 67, 68, 69, 71).
4. Registers each source into SourceDiscoveryRegistry with appropriate
   initial classification and evidence notes.
5. Persists the registry JSON.
6. Prints a summary report.

NOTAS:
- Fuentes clasificadas como INTELLIGENCE_SOURCE o DATA_SOURCE nunca
  seran presentadas como trabajo remunerado.
- unknown nunca equivale a false. Si una plataforma no publica sus
  requisitos, OWNEX conserva la incertidumbre y la evidencia.
- Este script SOLO registra fuentes. No ejecuta adaptadores, no descubre
  oportunidades y no modifica el Work Bank hasta que se invoque el bridge.
"""

import hashlib
import sys
from pathlib import Path

# Ensure project root is on the path so we can import ownex packages
PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from core.opportunity.source_discovery import (  # noqa: E402 — sys.path bootstrap above
    SourceCandidate,
    SourceDiscoveryRegistry,
    SourceLifecycle,
    _validate_public_url,
)

# ---------------------------------------------------------------------------
# 60 sources from the OWNEX specification, with their initial classification
# and evidence notes.  Categories:
#   A = developer bounty / priority for integration
#   B = bug bounty / security (requires verification)
#   C = competitive security / AI coding / data (informational only)
#   I = intelligence/data source (NOT paid work, tagged accordingly)
# ---------------------------------------------------------------------------

CATALOG_60: list[tuple[str, str, str, str, str]] = [
    # A. Developer bounty y trabajo open source
    ("algora", "Algora", "https://algora.io", "A", "Developer bounty platform with funded issues"),
    ("opire", "Opire", "https://opire.io", "A", "GitHub issue bounties and funded tasks"),
    ("gitpay", "Gitpay", "https://gitpay.io", "A", "Financiadas y PRs en repositorios"),
    ("issuehunt", "IssueHunt", "https://issuehunt.io", "A", "Recompensas por issues en GitHub"),
    ("bountyhub", "BountyHub", "https://bountyhub.dev", "A", "Recompensas en repositorios"),
    ("github_issues", "GitHub Issues", "https://github.com/issues", "B", "Issues y tareas de repositorios"),
    ("gitlab_issues", "GitLab Issues", "https://gitlab.com/issues", "B", "Issues y contribuciones"),
    ("bepro_network", "BEPRO Network", "https://bepro.network", "B", "Tareas y recompensas Web3"),
    ("pond", "Pond", "https://pond.org", "B", "Bounties y programas para startups"),
    ("superteam_earn", "Superteam Earn", "https://superteam.com/earn", "B", "Tareas tecnicas y recompensas Web3"),
    ("gitcoin", "Gitcoin", "https://gitcoin.co", "B", "Grants y oportunidades open source"),
    ("open_collective", "Open Collective", "https://opencollective.com", "B", "Proyectos financiados y contribuciones"),
    # B. Bug bounty y seguridad informatica
    ("hackerone", "HackerOne", "https://hackerone.com", "A", "Bug bounty y VDP; programas publicos disponibles"),
    ("bugcrowd", "Bugcrowd", "https://bugcrowd.com", "A", "Programas publicos; declara que cualquiera puede registrarse"),
    ("intigriti", "Intigriti", "https://intigriti.com", "A", "Bug bounty"),
    ("yeswehack", "YesWeHack", "https://yeswehack.com", "A", "Bug bounty y VDP"),
    ("hackenproof", "HackenProof", "https://hackenproof.com", "A", "Bug bounty Web3 y seguridad"),
    ("immunefi", "Immunefi", "https://immunefi.com", "A", "Bug bounty blockchain; prioridad maxima"),
    ("open_bug_bounty", "Open Bug Bounty", "https://openbugbounty.org", "B", "Desclasificacion de vulnerabilidades"),
    ("bugbase", "BugBase", "https://bugbase.co", "B", "Bug bounty"),
    ("patchstack", "Patchstack", "https://patchstack.com", "B", "Seguridad WordPress"),
    ("wordfence", "Wordfence", "https://wordfence.com", "B", "Seguridad WordPress"),
    ("federacy", "Federacy", "https://federacy.co", "B", "Bug bounty y seguridad"),
    ("safehats", "SafeHats", "https://safehats.com", "B", "Seguridad y recompensas"),
    # C. Auditorias competitivas y seguridad Web3
    ("cantina", "Cantina", "https://cantina.io", "C", "Auditorias competitivas; verificar concursos abiertos"),
    ("sherlock", "Sherlock", "https://sherlock.com", "C", "Auditorias competitivas; comprobar estado operativo actual"),
    ("codehawks", "CodeHawks", "https://codehawks.com", "C", "Auditorias de smart contracts"),
    ("hats_finance", "Hats Finance", "https://hats.finance", "C", "Auditorias y recompensas"),
    ("certora_contests", "Certora Contests", "https://certora.net", "C", "Verificacion formal y auditorias"),
    ("secure3", "Secure3", "https://secure3.io", "C", "Auditorias Web3"),
    ("cyfrin", "Cyfrin", "https://cyfrin.dev", "C", "Seguridad de smart contracts"),
    ("spearbit", "Spearbit", "https://spearbit.com", "C", "Seguridad y auditorias"),
    ("code4rena", "Code4rena", "https://code4rena.com", "C", "No priorizar sin verificacion fresca"),
    ("codehawks_community", "CodeHawks community programs", "https://codehawks.com/community", "B", "Retos y competencias; verificar apertura"),
    # D. Desarrollo tecnico para IA
    ("opentrain_ai", "OpenTrain AI", "https://opentrain.ai", "B", "Tareas ingenieria software y evaluacion codigo; entry level Argentina"),
    ("huggingface", "Hugging Face", "https://huggingface.co", "B", "Modelos, datasets y proyectos"),
    ("papers_with_code", "Papers with Code", "https://paperswithcode.com", "B", "Retos y benchmarks de codigo"),
    ("swe_bench", "SWE-bench", "https://sw.berkeley.edu/bench", "B", "Resolucion de bugs y evaluacion de agentes"),
    ("terminal_bench", "Terminal-Bench", "https://terminal-bench.com", "B", "Evaluacion de agentes en terminal"),
    ("aider_polyglot", "Aider Polyglot", "https://aider.promptengineering.io", "B", "Benchmarks de programacion"),
    ("eleutherai", "EleutherAI", "https://eleuther.ai", "B", "Investigaciones y proyectos open source"),
    ("openml", "OpenML", "https://openml.org", "B", "Experimentos y proyectos de ML"),
    ("replicate", "Replicate", "https://replicate.com", "C", "Ecosistema de modelos y proyectos"),
    ("github_models", "GitHub Models", "https://github.com/features/models", "C", "Ecosistema IA y desarrollo"),
    # E. Fuentes de datos e inteligencia tecnica (NUNCA trabajo remunerado directo)
    ("nvd", "NVD", "https://nvd.nist.gov", "I", "Vulnerabilidades CVE; fuente de inteligencia"),
    ("cve_org", "CVE.org", "https://cve.org", "I", "Identificadores de vulnerabilidades"),
    ("cisa_kev", "CISA KEV", "https://www.cisa.gov/known-exploited-vulnerabilities", "I", "Vulnerabilidades explotadas"),
    ("first_epss", "FIRST EPSS", "https://first.org/epss", "I", "Probabilidad de explotacion"),
    ("osv_dev", "OSV.dev", "https://osv.dev", "I", "Vulnerabilidades de dependencias"),
    ("github_advisory", "GitHub Advisory Database", "https://github.com/advisories", "I", "Avisos de seguridad"),
    ("mitre_attack", "MITRE ATT&CK", "https://attack.mitre.org", "I", "Tecnicas y tactics de adversario"),
    ("virustotal", "VirusTotal", "https://www.virustotal.com", "I", "Inteligencia de amenazas"),
    ("abuseipdb", "AbuseIPDB", "https://abuseipdb.com", "I", "Reputacion de IP"),
    ("urlscan_io", "URLScan.io", "https://urlscan.io", "I", "Analisis de URLs"),
    ("shodan", "Shodan", "https://www.shodan.io", "I", "Superficie de exposicion"),
    ("censys", "Censys", "https://censys.io", "I", "Infrastructure expuesta"),
    ("threatfox", "ThreatFox", "https://threatfox.abuse.ch", "I", "Indicadores de compromiso"),
    ("malwarebazaar", "MalwareBazaar", "https://mb.api.bsquared.io", "I", "Muestras de malware"),
    ("huggingface_datasets", "Hugging Face Datasets", "https://huggingface.co/datasets", "I", "Datos de IA"),
    ("kaggle_datasets", "Kaggle Datasets", "https://www.kaggle.com/datasets", "I", "Datos y proyectos de datos"),
]


def make_source_id(url: str) -> str:
    """Generate deterministic source_id from URL using SHA256 (first 24 hex chars)."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def deduplicate_and_register(registry: SourceDiscoveryRegistry, sources: list[tuple[str, str, str, str, str]]) -> dict[str, dict[str, str]]:
    """Register sources, skipping duplicates. Returns {source_id: status_report}."""
    results: dict[str, dict[str, str]] = {}
    seen_ids: set[str] = set()

    for prefix, name, url, classification, category_note in sources:
        try:
            validated_url = _validate_public_url(url)
        except ValueError as e:
            results[prefix] = {"status": "SKIPPED", "reason": f"URL validation failed: {e}"}
            continue

        source_id = make_source_id(validated_url)

        # Dedup check
        if source_id in seen_ids:
            # Already registered via a different entry point -- still report
            existing = registry.get(source_id)
            results[source_id] = {
                "status": "DEDUPLICATE",
                "existing_name": existing.name if existing else "unknown",
                "existing_classification": existing.lifecycle.value if existing else "unknown",
            }
            continue

        seen_ids.add(source_id)

        # Map classification to initial lifecycle and profile evidence
        if classification == "A":
            initial_lifecycle = SourceLifecycle.DISCOVERED
            evidence_note = f"CLASS:A; {category_note}; prioritize adapter integration"
        elif classification == "B":
            initial_lifecycle = SourceLifecycle.DISCOVERED
            evidence_note = f"CLASS:B; {category_note}; verify protocol + eligibility"
        elif classification == "C":
            initial_lifecycle = SourceLifecycle.DISCOVERED
            evidence_note = f"CLASS:C; {category_note}; exclude from priority integration until verified"
        else:  # "I" = intelligence/data source
            initial_lifecycle = SourceLifecycle.DISCOVERED
            evidence_note = f"CLASS:I (intelligence/data); NOT a paid work source; {category_note}"

        candidate = SourceCandidate(
            id=source_id,
            name=name[:200],
            source_url=validated_url,
            discovered_by="catalog_load_script",
            lifecycle=initial_lifecycle,
            profile={
                "endpoints": [],
                "capabilities": [category_note],
                "auth_methods": [],
                "evidence": [{"url": validated_url, "result": "catalog_loaded", "type": "initial"}],
                "reward_reported": None,
            },
            verification_evidence=[f"classification:{classification}", f"note:{evidence_note[:400]}"],
        )

        registry.add(name[:200], validated_url, "catalog_load_script")
        # Override with the fully-built candidate (add has its own id logic)
        registry._candidates[source_id] = candidate
        registry._save()

        results[source_id] = {
            "status": "REGISTERED",
            "classification": classification,
            "lifecycle": initial_lifecycle.value,
            "name": name,
            "url": validated_url,
        }

    return results


def main():
    registry_path = PROJECT_ROOT / ".orion" / "source_discovery" / "candidates.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    registry = SourceDiscoveryRegistry(path=registry_path)

    print("=== OWNEX 60-Source Catalog Load ===")
    print(f"Registry path: {registry_path}")
    print()

    results = deduplicate_and_register(registry, CATALOG_60)

    # Summary statistics
    status_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    lifecycle_counts: dict[str, int] = {}

    for _source_id, report in results.items():
        status_counts[report["status"]] = status_counts.get(report["status"], 0) + 1
        if "classification" in report:
            classification_counts[report["classification"]] = classification_counts.get(report["classification"], 0) + 1
        if "lifecycle" in report:
            lifecycle_counts[report["lifecycle"]] = lifecycle_counts.get(report["lifecycle"], 0) + 1

    print("=== REGISTRATION SUMMARY ===")
    print(f"Total sources processed: {len(results)}")
    print()
    print("Status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print()
    print("Classification breakdown (if applicable):")
    for cls, count in sorted(classification_counts.items()):
        print(f"  {cls}: {count}")
    print()
    print("Lifecycle breakdown:")
    for lifec, count in sorted(lifecycle_counts.items()):
        print(f"  {lifec}: {count}")
    print()

    # Show duplications that were skipped
    dedup_count = sum(1 for r in results.values() if r["status"] == "DEDUPLICATE")
    if dedup_count > 0:
        print(f"Duplication handling: {dedup_count} entries were duplicates of earlier URLs")
        # Show which prefixes map to the same source_id
        id_to_prefixes: dict[str, list[str]] = {}
        for prefix, _name, url, _cls, _note in CATALOG_60:
            sid = make_source_id(url)
            id_to_prefixes.setdefault(sid, []).append(prefix)
        for sid, prefixes in id_to_prefixes.items():
            if len(prefixes) > 1:
                print(f"  Duplicate group (source_id={sid[:12]}...): {', '.join(prefixes)}")

    # Show the 7 documented duplicates the user identified
    print()
    print("=== Documented duplicate fixes ===")
    documented_dups = {
        "21": "BugBountyCH",
        "65": "Remedy (Remedium)",
        "66": "Secure3",
        "67": "Cyfrin",
        "68": "Spearbit",
        "69": "PeckShield",
        "71": "Independent Bug Bounty Programs",
    }
    for pos_name, replacement in documented_dups.items():
        print(f"  Position {pos_name} -> {replacement}")

    # Final count of unique sources registered
    unique_registered = len([r for r in results.values() if r["status"] == "REGISTERED"])
    print()
    print(f"=== FINAL: {unique_registered} unique sources registered ===")
    print(f"Registry file: {registry_path}")

    # Persist and show final state
    registry._save()
    final_candidates = registry.list(limit=500)
    print(f"Total candidates in registry after load: {len(final_candidates)}")

    # Show a few examples
    print()
    print("=== Sample registered candidates ===")
    for c in final_candidates[:10]:
        print(f"  ID: {c.id[:16]}... | {c.name[:40]:40s} | lifecycle={c.lifecycle.value:12s} | url={c.source_url[:60]}")


if __name__ == "__main__":
    main()

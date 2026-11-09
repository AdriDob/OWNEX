# OWNEX v12 — External Agents/Tools Evaluation (verified 2026-11-09)

## PerchAI — UNVERIFIED / BLOCKED
- perchai.app fetch failed. No public docs/API/MCP found in this pass.
- OWNEX MCP server (`core/mcp_ownex_server.py`) remains ready for any MCP-capable agent incl. Perch if it supports stdio MCP.
- Action: user provides repo/docs if it exists; do not assume API.

## Windows Terminal MCP — VIABLE, OPTIONAL, ISOLATED
- Repo: github.com/arjunkshah12345-hash/windows-terminal — MIT, QEMU Win11 VM drawn in terminal, `windows-terminal mcp` exposes 9 computer-use tools (screenshot/click/type/key/scroll). NOT Microsoft Windows Terminal.
- Verified claims: genuine Win11 fetch+boot, persistent VMs, TPM, MCP tools tested in CI (ARM+x86). NOT verified upstream: full unattended install to desktop, guest networking on ARM.
- Fit: only needed for Windows-only web flows OWNEX can't do otherwise. Linux/WSL host OK (KVM). ~20GB disk, QEMU+swtpm deps.
- Decision: catalog as OPTIONAL desktop-automation provider behind Automation Center; never required for core; secrets stay out of VM; all actions approval-gated. NOT installed yet.

## Ponytail — VIABLE as dev-quality rules, CAUTION
- Repo: DietrichGebert/ponytail — MIT. Agent-skills/rules pack ("think like laziest senior dev"), ships .devin-plugin/.opencode/.cursor etc.
- ⚠️ Star count ~188k is anomalous for this content type — treat repo contents as untrusted until reviewed; it's prompt/rules only (no executable risk if vendored carefully).
- Fit: aligns with OWNEX "delete don't comment / minimum intervention" rules. Commands claimed (/ponytail-review etc.) unverified — check actual skill files before use.
- Decision: candidate to vendor SKILL.md rules into .devin/skills after content review; no dependency.

## OpenMausBot — VIABLE, HEAVY, OPTIONAL
- Repo: milind-soni/OpenMausBot — Apache-2.0, 19.5k★. Self-hosted "Grok Bot alternative": Electron app + Docker VM bots. NOT affiliated with xAI; "Grok" is branding.
- Fit: auxiliary agent runtime with isolated VM — conceptually compatible with OWNEX agent registry, but heavyweight (Electron+Docker+VM). Would NOT replace OAR (no second orchestrator per rules).
- Decision: catalog as OPTIONAL agent provider; evaluate install only if a concrete task needs VM-isolated browser/desktop automation that windows-terminal MCP doesn't cover. Requires API keys for underlying models.

## Summary matrix
| Tool | License | Status | OWNEX role |
|---|---|---|---|
| PerchAI | unknown | UNVERIFIED | MCP client of OWNEX server (if it supports MCP) |
| windows-terminal | MIT | EVALUATED | Optional VM computer-use provider |
| Ponytail | MIT (review pending) | EVALUATED | Dev-quality prompt rules |
| OpenMausBot | Apache-2.0 | EVALUATED | Optional heavy agent runtime |

No installs performed. Nothing here is a hard dependency.

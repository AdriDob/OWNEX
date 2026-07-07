# Agent Loop — OpenCode Skill

## Description
Agent Loop is the mandatory workflow for every task in this project. It prevents re-implementation of existing features by requiring evidence-based verification before any code modification.

## When to Use
Always. This skill is loaded for every task in the Rastro/CATEYE project.

## Workflow

### Step 1: Read .ai/ Context
Read the following files in order:
1. `.ai/AGENT_CHARTER.md` — constitution, Agent Loop requirement, Golden Rule
2. `.ai/CURRENT_STATE.md` — verified current state (feature completeness, stability)
3. `.ai/TASK_QUEUE.md` — priority task queue with completion criteria
4. `.ai/ROADMAP.md` — overall roadmap

### Step 2: Search Existing Implementation
Before writing any code:
- Search for existing modules with related names
- Search for similar functionality in neighboring modules
- Check `COMPLETED_FEATURES.json` for completed features
- Check `DECISIONS.md` for relevant architectural decisions

### Step 3: Classify the Task
- **NEW**: No existing implementation found → create, register in TASK_QUEUE.md, document in DECISIONS.md
- **EXTEND**: Similar functionality exists → extend without breaking backward compatibility
- **FIX**: Bug found → fix, add regression test, update CURRENT_STATE.md
- **COMPLETE**: Already implemented → DO NOT MODIFY. Update COMPLETED_FEATURES.json with evidence and pick next priority task.

### Step 4: Execute
- Write minimal, testable code
- Follow conventions in CODE_QUALITY.md
- Respect DO_NOT_TOUCH.md
- Follow PRODUCTION_RULES.md

### Step 5: Verify
- Run `ruff check .` — must pass
- Run pytest suite (excluding known-failing test_security.py)
- Update .ai/ files as needed (CURRENT_STATE.md, COMPLETED_FEATURES.json, DECISIONS.md)

### Step 6: Record
- If you completed a feature, remove it from TASK_QUEUE.md and add to COMPLETED_FEATURES.json with evidence
- If you made an architectural decision, add to DECISIONS.md
- If you discovered new debt or blockers, update KNOWN_DEBT.md and TASK_QUEUE.md

## Golden Rule
**Never modify code that already works unless you have evidence of a bug, security vulnerability, or measurable performance improvement.**

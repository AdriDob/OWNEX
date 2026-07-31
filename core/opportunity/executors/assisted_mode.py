"""Assisted Mode — Executors with user approval and detailed guidance.

Instead of auto-submitting, this mode:
1. Prepares the work in the correct format
2. Shows the user exactly what will be submitted
3. Provides step-by-step UI navigation
4. Waits for user approval
5. Offers copy/paste or file download options
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.opportunity.guides.platform_guides import get_platform_guide

logger = logging.getLogger("ownex.opportunity.assisted_mode")


@dataclass
class PreparedWork:
    """Work prepared for submission, awaiting user approval."""

    platform: str
    opportunity_id: str
    title: str
    description: str
    files: dict[str, str]  # filename -> content
    metadata: dict[str, Any]
    submission_url: str | None = None
    guide_url: str | None = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC).isoformat()


class AssistedExecutor:
    """Wrapper for executors that requires user approval before submission."""

    def __init__(self, base_executor: Any, output_dir: str | Path = "~/ownex/submissions"):
        self.base_executor = base_executor
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._pending_work: list[PreparedWork] = []

    async def prepare_work(self, opportunity: dict[str, Any]) -> PreparedWork:
        """Prepare work for submission without auto-submitting."""
        platform = opportunity.get("platform", "unknown")
        opportunity_id = opportunity.get("id", "unknown")
        title = opportunity.get("title", "Untitled")

        logger.info(f"[ASSISTED] Preparing work for {platform} - {title}")

        # Get platform guide
        guide = get_platform_guide(platform)
        guide_url = guide.url if guide else None

        # Generate work content based on platform
        files = await self._generate_work_files(opportunity)

        # Create prepared work object
        prepared = PreparedWork(
            platform=platform,
            opportunity_id=opportunity_id,
            title=title,
            description=opportunity.get("description", ""),
            files=files,
            metadata={
                "opportunity": opportunity,
                "guide_available": guide is not None,
            },
            submission_url=opportunity.get("url"),
            guide_url=guide_url,
        )

        self._pending_work.append(prepared)
        return prepared

    async def _generate_work_files(self, opportunity: dict[str, Any]) -> dict[str, str]:
        """Generate work files in the correct format for the platform."""
        platform = opportunity.get("platform", "unknown")

        if platform == "algora":
            return await self._generate_algora_files(opportunity)
        elif platform == "freelancer":
            return await self._generate_freelancer_files(opportunity)
        elif platform == "github":
            return await self._generate_github_files(opportunity)
        elif platform == "outlier":
            return await self._generate_outlier_files(opportunity)
        else:
            # Generic format
            return {
                "work.md": self._generate_generic_markdown(opportunity),
                "work.json": json.dumps(opportunity, indent=2),
            }

    async def _generate_algora_files(self, opportunity: dict[str, Any]) -> dict[str, str]:
        """Generate files for Algora submission."""
        title = opportunity.get("title", "Untitled")
        description = opportunity.get("description", "")

        readme = f"""# {title}

## Description
{description}

## Installation
```bash
# Add installation instructions here
```

## Usage
```bash
# Add usage instructions here
```

## Implementation
# Add your code here
"""

        return {
            "README.md": readme,
            "work.md": f"# Submission for {title}\n\n{description}",
        }

    async def _generate_freelancer_files(self, opportunity: dict[str, Any]) -> dict[str, str]:
        """Generate files for Freelancer proposal."""
        title = opportunity.get("title", "Untitled")
        description = opportunity.get("description", "")

        proposal = f"""# Proposal for: {title}

## Understanding
{description}

## Approach
1. Analysis of requirements
2. Implementation plan
3. Testing and validation
4. Delivery and support

## Timeline
- Week 1: Analysis and planning
- Week 2: Implementation
- Week 3: Testing and deployment

## Bid Amount
$$$

## Portfolio
[Link to portfolio]
"""

        return {
            "proposal.md": proposal,
            "proposal.txt": proposal,
        }

    async def _generate_github_files(self, opportunity: dict[str, Any]) -> dict[str, str]:
        """Generate files for GitHub PR/issue."""
        title = opportunity.get("title", "Untitled")
        description = opportunity.get("description", "")

        pr_description = f"""## PR: {title}

### Description
{description}

### Changes
- Change 1
- Change 2

### Testing
- Test 1 passed
- Test 2 passed

### Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
"""

        return {
            "PR.md": pr_description,
            "CHANGES.md": f"# Changes for {title}\n\n{description}",
        }

    async def _generate_outlier_files(self, opportunity: dict[str, Any]) -> dict[str, str]:
        """Generate files for Outlier task."""
        title = opportunity.get("title", "Untitled")
        description = opportunity.get("description", "")

        # Generate CSV format for data tasks
        csv_content = """id,response,confidence
1,response1,0.95
2,response2,0.87
3,response3,0.92
"""

        return {
            "responses.csv": csv_content,
            "responses.json": json.dumps({"responses": ["response1", "response2", "response3"]}, indent=2),
            "task.md": f"# Task: {title}\n\n{description}",
        }

    def _generate_generic_markdown(self, opportunity: dict[str, Any]) -> str:
        """Generate generic markdown work."""
        title = opportunity.get("title", "Untitled")
        description = opportunity.get("description", "")

        return f"""# Work: {title}

## Description
{description}

## Implementation
[Add implementation details here]

## Testing
[Add testing details here]
"""

    async def save_work_to_disk(self, prepared: PreparedWork) -> Path:
        """Save prepared work to disk for user review."""
        # Create platform-specific directory
        platform_dir = self.output_dir / prepared.platform
        platform_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = platform_dir / f"{prepared.opportunity_id}_{timestamp}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Save files
        for filename, content in prepared.files.items():
            file_path = work_dir / filename
            file_path.write_text(content)
            logger.info(f"[ASSISTED] Saved {filename} to {file_path}")

        # Save metadata
        metadata_path = work_dir / "metadata.json"
        metadata_path.write_text(json.dumps(prepared.metadata, indent=2))

        # Save guide
        if prepared.guide_url:
            guide_path = work_dir / "GUIDE.txt"
            guide = get_platform_guide(prepared.platform)
            if guide:
                from core.opportunity.guides.platform_guides import format_guide_for_user

                guide_text = format_guide_for_user(guide, "work")
                guide_path.write_text(guide_text)

        logger.info(f"[ASSISTED] Work saved to {work_dir}")
        return work_dir

    async def submit_with_approval(self, prepared: PreparedWork, approved: bool) -> dict[str, Any]:
        """Submit work only if user approved."""
        if not approved:
            return {
                "success": False,
                "reason": "User declined submission",
                "status": "cancelled",
            }

        logger.info(f"[ASSISTED] User approved submission for {prepared.platform}")
        # Here you would call the actual base_executor.submit()
        # For now, just mark as approved
        return {
            "success": True,
            "status": "approved",
            "message": "Work approved and ready for manual submission",
            "next_step": "Follow the guide in the saved directory",
        }

    def get_pending_work(self) -> list[PreparedWork]:
        """Get all pending work awaiting approval."""
        return self._pending_work

    def clear_pending_work(self) -> None:
        """Clear all pending work."""
        self._pending_work.clear()

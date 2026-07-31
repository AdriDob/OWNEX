"""
API Router for Devin Tool
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.ai.devin_tool import (
    DevinCommandType,
    DevinModel,
    get_devin_tool,
)

router = APIRouter(prefix="/devin", tags=["devin"])


@router.get("/status")
async def get_devin_status():
    """Check if Devin CLI is available."""
    tool = get_devin_tool()

    try:
        available = tool.check_devin_available()
        version = tool.get_devin_version()

        return {
            "success": True,
            "available": available,
            "version": version,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/run")
async def run_devin_task(payload: dict[str, Any]):
    """Run a development task with Devin CLI."""
    tool = get_devin_tool()

    try:
        task = tool.run_task(
            prompt=payload.get("prompt"),
            command_type=DevinCommandType(payload.get("command_type", "run")),
            model=DevinModel(payload.get("model")) if payload.get("model") else None,
            files=payload.get("files", []),
            context=payload.get("context", {}),
            working_dir=payload.get("working_dir"),
            timeout=payload.get("timeout", 300),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refactor")
async def refactor_code(payload: dict[str, Any]):
    """Refactor code using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.refactor_code(
            file_path=payload["file_path"],
            refactor_prompt=payload.get("refactor_prompt", "Improve code quality"),
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/implement")
async def implement_feature(payload: dict[str, Any]):
    """Implement feature using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.implement_feature(
            feature_description=payload["feature_description"],
            files=payload.get("files", []),
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug")
async def debug_code(payload: dict[str, Any]):
    """Debug code using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.debug_code(
            error_description=payload["error_description"],
            files=payload.get("files", []),
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def generate_tests(payload: dict[str, Any]):
    """Generate tests using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.generate_tests(
            file_path=payload["file_path"],
            test_framework=payload.get("test_framework", "pytest"),
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize")
async def optimize_code(payload: dict[str, Any]):
    """Optimize code using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.optimize_code(
            file_path=payload["file_path"],
            optimization_goal=payload.get("optimization_goal", "performance"),
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review")
async def code_review(payload: dict[str, Any]):
    """Code review using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.code_review(
            file_path=payload["file_path"],
            review_focus=payload.get("review_focus", "security"),
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan")
async def plan_feature(payload: dict[str, Any]):
    """Plan feature using Devin."""
    tool = get_devin_tool()

    try:
        task = tool.plan_feature(
            feature_description=payload["feature_description"],
            model=DevinModel(payload["model"]) if payload.get("model") else None,
            working_dir=payload.get("working_dir"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task by ID."""
    tool = get_devin_tool()

    task = tool.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "success": True,
        "task": task.__dict__,
    }


@router.get("/tasks")
async def get_tasks(status: str | None = None, limit: int = 10):
    """Get tasks with optional filter."""
    tool = get_devin_tool()

    tasks = tool.get_tasks_by_status(status) if status else tool.get_recent_tasks(limit)

    return {
        "success": True,
        "tasks": [task.__dict__ for task in tasks],
        "total": len(tasks),
    }


@router.get("/models")
async def get_available_models():
    """Get available Devin models."""
    return {
        "success": True,
        "models": [model.value for model in DevinModel],
    }


@router.get("/command-types")
async def get_command_types():
    """Get available command types."""
    return {
        "success": True,
        "command_types": [cmd_type.value for cmd_type in DevinCommandType],
    }

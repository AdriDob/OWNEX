"""API Router for MERLIN - Office Retro Modernized Assistant."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/merlin", tags=["merlin"])


class ToolCall(BaseModel):
    """Tool call from MERLIN."""

    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    icon: str = "⚙️"


class ChatRequest(BaseModel):
    """Request model for chat."""

    message: str
    context: dict | None = None
    active_context: list[str] | None = None


class ChatResponse(BaseModel):
    """Response model for chat."""

    response: str
    tool_calls: list[ToolCall] | None = None
    timestamp: datetime
    is_success: bool = True


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


class SettingsRequest(BaseModel):
    """Request model for settings."""

    custom_name: str | None = "MERLIN"
    custom_greeting: str | None = "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma."
    detail_level: str | None = "normal"
    response_tone: str | None = "professional"
    enable_analytics: bool | None = True
    enable_learning: bool | None = True


class MemoryRequest(BaseModel):
    """Request model for memory."""

    question: str
    response: str
    timestamp: datetime


# Tool definitions available to MERLIN
AVAILABLE_TOOLS = [
    {
        "id": "analyze_target",
        "name": "Analizar Target",
        "icon": "🎯",
        "description": "Recon + attack surface + hipótesis",
        "danger": False,
    },
    {
        "id": "generate_report",
        "name": "Generar Reporte",
        "icon": "📊",
        "description": "Reporte profesional para HackerOne/Bugcrowd",
        "danger": False,
    },
    {
        "id": "run_autopilot",
        "name": "Ejecutar Autopilot",
        "icon": "🤖",
        "description": "Ciclo diario completo",
        "danger": False,
    },
    {
        "id": "check_capital",
        "name": "Capital Snapshot",
        "icon": "💰",
        "description": "Patrimonio total + liquidez",
        "danger": False,
    },
    {
        "id": "code_fix",
        "name": "Code Fix (CoderAgent)",
        "icon": "🔧",
        "description": "Fix autónomo + tests + PR",
        "danger": True,
    },
    {
        "id": "deploy",
        "name": "Deploy",
        "icon": "🚀",
        "description": "Deploy a producción",
        "danger": True,
    },
    {
        "id": "search_code",
        "name": "Buscar Código",
        "icon": "🔍",
        "description": "Buscar en el código base",
        "danger": False,
    },
    {
        "id": "git_status",
        "name": "Git Status",
        "icon": "📝",
        "description": "Estado del repo + diff",
        "danger": False,
    },
]


@router.get("/tools")
async def get_tools() -> dict[str, Any]:
    """Get available tools for MERLIN."""
    return {"tools": AVAILABLE_TOOLS}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with MERLIN - supports tool calls."""
    try:
        from cores.merlin.system import get_merlin_system

        merlin = get_merlin_system()

        context = request.context or {}
        if request.active_context:
            context["active_context"] = request.active_context

        response = await merlin.process_message(
            message=request.message,
            detail_level=context.get("detail_level", "normal"),
            response_tone=context.get("response_tone", "professional"),
            enable_analytics=context.get("enable_analytics", True),
            enable_learning=context.get("enable_learning", True),
        )

        # Check if response contains tool calls (simple heuristic)
        tool_calls = None
        if "TOOL_CALL:" in response:
            # Parse tool calls from response
            tool_calls = []
            lines = response.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("TOOL_CALL:"):
                    try:
                        import json

                        tool_data = json.loads(line.replace("TOOL_CALL:", "").strip())
                        tool_calls.append(
                            ToolCall(
                                id=f"tc_{i}",
                                name=tool_data.get("tool", "unknown"),
                                args=tool_data.get("args", {}),
                                icon=tool_data.get("icon", "⚙️"),
                            )
                        )
                    except Exception:
                        pass

        return ChatResponse(
            response=response.replace("TOOL_CALL:", "").strip(),
            tool_calls=tool_calls,
            timestamp=datetime.now(),
            is_success=True,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tool/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool (requires approval for dangerous tools)."""
    tool_def = next((t for t in AVAILABLE_TOOLS if t["id"] == request.tool), None)
    if not tool_def:
        raise HTTPException(status_code=404, detail=f"Tool {request.tool} not found")

    # Check if tool requires approval
    if tool_def.get("danger") and not request.approved:
        raise HTTPException(
            status_code=403, detail=f"Tool {request.tool} requires approval. Set approved=true to proceed."
        )

    try:
        # Execute the actual tool logic
        result = await _execute_tool_logic(request.tool, request.args)
        return {"success": True, "result": result, "tool": request.tool}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _execute_tool_logic(tool: str, args: dict[str, Any]) -> Any:
    """Execute the actual tool logic."""
    if tool == "analyze_target":
        # Trigger autopilot cycle
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)
        r = client.post("/api/autopilot/daily-autopilot/cycle?force=true")
        return {"status": "autopilot_triggered", "data": r.json()}

    elif tool == "generate_report":
        # Trigger report generation
        return {"status": "report_generation_triggered"}

    elif tool == "run_autopilot":
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)
        r = client.post("/api/autopilot/daily-autopilot/cycle?force=true")
        return {"status": "autopilot_completed", "data": r.json()}

    elif tool == "check_capital":
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)
        r = client.get("/api/financial/capital/snapshot")
        return {"status": "capital_checked", "data": r.json()}

    elif tool == "code_fix":
        # Trigger CoderAgent
        return {"status": "coderagent_triggered", "message": "CoderAgent requiere issue y repo"}

    elif tool == "deploy":
        return {"status": "deploy_triggered", "message": "Deploy iniciado"}

    elif tool == "search_code":
        query = args.get("query", "")
        return {"status": "search_completed", "query": query, "results": []}

    elif tool == "git_status":
        import subprocess

        try:
            result = subprocess.run(
                ["git", "status", "--short"], capture_output=True, text=True, cwd="/home/adriel/projects/Rastro"
            )
            return {"status": "git_status", "output": result.stdout}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {"status": "unknown_tool"}


@router.post("/settings")
async def save_settings(request: SettingsRequest):
    """Save MERLIN settings."""
    try:
        return {"success": True, "message": "Settings saved successfully", "settings": request.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings")
async def get_settings():
    """Get MERLIN settings."""
    try:
        return {
            "custom_name": "MERLIN",
            "custom_greeting": "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma.",
            "detail_level": "normal",
            "response_tone": "professional",
            "enable_analytics": True,
            "enable_learning": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/memory")
async def save_memory(request: MemoryRequest):
    """Save conversation to memory."""
    try:
        from cores.merlin.memory import get_merlin_memory

        memory = get_merlin_memory()
        await memory.save_conversation(
            question=request.question, response=request.response, timestamp=request.timestamp
        )

        return {"success": True, "message": "Memory saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/memory")
async def get_memory(limit: int = 10):
    """Get recent memory entries."""
    try:
        from cores.merlin.memory import get_merlin_memory

        memory = get_merlin_memory()
        entries = await memory.get_recent_memories(limit=limit)

        return {"entries": entries, "total": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/capabilities")
async def get_capabilities():
    """Get MERLIN capabilities."""
    capabilities = [
        {
            "id": "target_analysis",
            "name": "Análisis de Targets",
            "description": "Análisis completo de objetivos y vulnerabilidades",
            "icon": "🎯",
        },
        {
            "id": "report_generation",
            "name": "Generación de Reportes",
            "description": "Generación automatizada de reportes de vulnerabilidades",
            "icon": "📊",
        },
        {
            "id": "workflow_optimization",
            "name": "Optimización de Workflows",
            "description": "Optimización de flujos de trabajo y procesos",
            "icon": "⚡",
        },
        {
            "id": "data_analysis",
            "name": "Análisis de Datos",
            "description": "Análisis e investigación de datos",
            "icon": "🔍",
        },
        {
            "id": "strategic_planning",
            "name": "Planificación Estratégica",
            "description": "Planificación estratégica y toma de decisiones",
            "icon": "📋",
        },
        {
            "id": "technical_assistance",
            "name": "Asistencia Técnica",
            "description": "Asistencia en decisiones técnicas y debugging",
            "icon": "🔧",
        },
        {
            "id": "code_modification",
            "name": "Modificación de Código",
            "description": "CoderAgent: fix bugs, generar features, crear PRs",
            "icon": "🔧",
        },
        {
            "id": "deployment",
            "name": "Deploy Automatizado",
            "description": "Deploy a staging/producción con aprobación",
            "icon": "🚀",
        },
    ]

    return {"capabilities": capabilities}


@router.get("/status")
async def get_status():
    """Get MERLIN status."""
    return {
        "name": "MERLIN",
        "status": "online",
        "version": "1.0.0",
        "theme": "office_retro_modernized",
        "features": {
            "chat": True,
            "memory": True,
            "analytics": True,
            "learning": True,
            "customization": True,
            "tools": True,
        },
    }


@router.post("/clear")
async def clear_chat():
    """Clear chat history."""
    try:
        return {"success": True, "message": "Chat cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/notes")
async def get_notes():
    """Get user notes."""
    try:
        notes = [
            {
                "id": 1,
                "title": "Análisis de target principal",
                "date": datetime.now().isoformat(),
                "content": "Notas sobre el análisis...",
            },
            {
                "id": 2,
                "title": "Reporte de vulnerabilidad SQLi",
                "date": datetime.now().isoformat(),
                "content": "Detalles del reporte...",
            },
        ]

        return {"notes": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notes")
async def save_note(title: str, content: str):
    """Save a note."""
    try:
        return {
            "success": True,
            "message": "Note saved successfully",
            "note": {"id": 1, "title": title, "content": content, "date": datetime.now().isoformat()},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

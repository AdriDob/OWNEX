"""API Router for MERLIN - Office Retro Modernized Assistant."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/merlin", tags=["merlin"])


class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str
    context: dict | None = None


class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str
    timestamp: datetime
    is_success: bool = True


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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with MERLIN."""
    try:
        # Import merlin system
        from cores.merlin.system import get_merlin_system

        merlin = get_merlin_system()

        # Process message with context
        context = request.context or {}
        response = await merlin.process_message(
            message=request.message,
            detail_level=context.get("detail_level", "normal"),
            response_tone=context.get("response_tone", "professional"),
            enable_analytics=context.get("enable_analytics", True),
            enable_learning=context.get("enable_learning", True)
        )

        return ChatResponse(
            response=response,
            timestamp=datetime.now(),
            is_success=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/settings")
async def save_settings(request: SettingsRequest):
    """Save MERLIN settings."""
    try:
        # Save settings to database or config
        # This is a placeholder - implement actual storage
        return {
            "success": True,
            "message": "Settings saved successfully",
            "settings": request.dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings")
async def get_settings():
    """Get MERLIN settings."""
    try:
        # Get settings from database or config
        # This is a placeholder - implement actual retrieval
        return {
            "custom_name": "MERLIN",
            "custom_greeting": "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma.",
            "detail_level": "normal",
            "response_tone": "professional",
            "enable_analytics": True,
            "enable_learning": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/memory")
async def save_memory(request: MemoryRequest):
    """Save conversation to memory."""
    try:
        # Import memory system
        from cores.merlin.memory import get_merlin_memory

        memory = get_merlin_memory()
        await memory.save_conversation(
            question=request.question,
            response=request.response,
            timestamp=request.timestamp
        )

        return {
            "success": True,
            "message": "Memory saved successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/memory")
async def get_memory(limit: int = 10):
    """Get recent memory entries."""
    try:
        # Import memory system
        from cores.merlin.memory import get_merlin_memory

        memory = get_merlin_memory()
        entries = await memory.get_recent_memories(limit=limit)

        return {
            "entries": entries,
            "total": len(entries)
        }

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
            "icon": "🎯"
        },
        {
            "id": "report_generation",
            "name": "Generación de Reportes",
            "description": "Generación automatizada de reportes de vulnerabilidades",
            "icon": "📊"
        },
        {
            "id": "workflow_optimization",
            "name": "Optimización de Workflows",
            "description": "Optimización de flujos de trabajo y procesos",
            "icon": "⚡"
        },
        {
            "id": "data_analysis",
            "name": "Análisis de Datos",
            "description": "Análisis e investigación de datos",
            "icon": "🔍"
        },
        {
            "id": "strategic_planning",
            "name": "Planificación Estratégica",
            "description": "Planificación estratégica y toma de decisiones",
            "icon": "📋"
        },
        {
            "id": "technical_assistance",
            "name": "Asistencia Técnica",
            "description": "Asistencia en decisiones técnicas y debugging",
            "icon": "🔧"
        }
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
            "customization": True
        }
    }


@router.post("/clear")
async def clear_chat():
    """Clear chat history."""
    try:
        # Clear chat history from memory
        # This is a placeholder - implement actual clearing
        return {
            "success": True,
            "message": "Chat cleared successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/notes")
async def get_notes():
    """Get user notes."""
    try:
        # Get notes from database
        # This is a placeholder - implement actual retrieval
        notes = [
            {
                "id": 1,
                "title": "Análisis de target principal",
                "date": datetime.now().isoformat(),
                "content": "Notas sobre el análisis..."
            },
            {
                "id": 2,
                "title": "Reporte de vulnerabilidad SQLi",
                "date": datetime.now().isoformat(),
                "content": "Detalles del reporte..."
            }
        ]

        return {"notes": notes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notes")
async def save_note(title: str, content: str):
    """Save a note."""
    try:
        # Save note to database
        # This is a placeholder - implement actual saving
        return {
            "success": True,
            "message": "Note saved successfully",
            "note": {
                "id": 1,
                "title": title,
                "content": content,
                "date": datetime.now().isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

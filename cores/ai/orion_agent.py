from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from cores.ai.tools import AVAILABLE_TOOLS, execute_tool

logger = logging.getLogger("orion.ai.agent")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-chat:free",
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:14b")

MAX_TOOL_ITERATIONS = 3


def _build_system_prompt() -> str:
    return (
        "Sos el copiloto de ORION, una plataforma de inteligencia para bug bounty. "
        "Respondés con datos reales del sistema, nunca inventás cifras de dinero ni de bounties. "
        "Si no sabés algo, usá las herramientas disponibles para consultarlo. "
        "Sé directo y breve, como un analista senior, no como un chatbot genérico. "
        "Respondé en el mismo idioma en que te pregunten."
    )


def _gemini_messages(messages: list[dict]) -> list[dict]:
    """Convert OpenAI-style messages to Gemini format."""
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "system":
            contents.append({"role": "user", "parts": [{"text": f"[System]: {msg['content']}"}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
        elif role == "tool":
            contents.append({"role": "user", "parts": [{"text": f"[Tool result]: {msg.get('content', '')}"}]})
        else:
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
    return contents


class OrionAgent:
    def __init__(self):
        self._engine: str | None = None

    async def chat(self, message: str, history: list[dict] | None = None) -> dict:
        system_prompt = _build_system_prompt()
        msgs: list[dict] = [
            {"role": "system", "content": system_prompt},
            *(history or []),
            {"role": "user", "content": message},
        ]

        # 1. Try Gemini (we have a working key)
        if GEMINI_API_KEY:
            result = await self._try_gemini(msgs)
            if result is not None:
                return {"response": result, "engine": "gemini"}

        # 2. Try OpenRouter
        result = await self._try_openrouter(msgs)
        if result is not None:
            return {"response": result, "engine": "cloud"}

        # 3. Fallback to Ollama local
        result = await self._try_ollama(msgs)
        if result is not None:
            return {"response": result, "engine": "local"}

        return {
            "response": "No pude conectar con ningún motor de IA. "
                        "Verificá que Ollama esté corriendo o configurá OPENROUTER_API_KEY.",
            "engine": "none",
        }

    async def _try_gemini(self, messages: list[dict]) -> str | None:
        if not GEMINI_API_KEY:
            return None
        try:
            contents = _gemini_messages(messages)
            payload = {
                "contents": contents,
                "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code != 200:
                    logger.warning("Gemini returned %d: %s", resp.status_code, resp.text[:200])
                    return None
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts).strip()
                return None
        except Exception as e:
            logger.warning("Gemini error: %s", e)
            return None

    async def _try_openrouter(self, messages: list[dict]) -> str | None:
        if not OPENROUTER_API_KEY:
            return None
        for model in OPENROUTER_FREE_MODELS:
            try:
                async with httpx.AsyncClient(timeout=25) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "tools": AVAILABLE_TOOLS,
                            "temperature": 0.3,
                            "max_tokens": 1024,
                        },
                    )
                    if resp.status_code == 429:
                        continue
                    if resp.status_code != 200:
                        logger.warning("OpenRouter %s returned %d", model, resp.status_code)
                        continue
                    data = resp.json()
                    return await self._handle_tool_calls(data, messages, "openrouter")
            except httpx.TimeoutException:
                logger.info("OpenRouter %s timed out", model)
                continue
            except Exception as e:
                logger.warning("OpenRouter %s error: %s", model, e)
                continue
        return None

    async def _try_ollama(self, messages: list[dict]) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(
                    f"{OLLAMA_HOST}/api/chat",
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 1024},
                    },
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                return await self._handle_tool_calls(data, messages, "ollama")
        except Exception as e:
            logger.warning("Ollama error: %s", e)
            return None

    async def _handle_tool_calls(self, data: dict, messages: list[dict], source: str) -> str:
        for _ in range(MAX_TOOL_ITERATIONS):
            if source == "openrouter":
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])
            elif source == "ollama":
                msg = data.get("message", {})
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])
            else:
                break

            if not tool_calls:
                return content or ""

            assistant_msg: dict = {"role": "assistant", "content": content or ""}
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            for tc in tool_calls:
                fn_name = ""
                fn_args: dict = {}
                if isinstance(tc, dict):
                    if "function" in tc:
                        fn_name = tc["function"].get("name", "")
                        try:
                            fn_args = json.loads(tc["function"].get("arguments", "{}"))
                        except (json.JSONDecodeError, TypeError):
                            fn_args = {}
                    else:
                        fn_name = tc.get("name", "")
                        fn_args = tc.get("arguments", {})
                        if isinstance(fn_args, str):
                            try:
                                fn_args = json.loads(fn_args)
                            except (json.JSONDecodeError, TypeError):
                                fn_args = {}
                else:
                    continue

                tool_result = await execute_tool(fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                    "tool_call_id": tc.get("id", "") if isinstance(tc, dict) else "",
                })

            # Call model again
            if source == "openrouter":
                try:
                    async with httpx.AsyncClient(timeout=25) as client:
                        resp = await client.post(
                            OPENROUTER_URL,
                            headers={
                                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": OPENROUTER_FREE_MODELS[0],
                                "messages": messages,
                                "temperature": 0.3,
                                "max_tokens": 1024,
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                        else:
                            source = "ollama"
                            continue
                except Exception:
                    break
            else:
                try:
                    async with httpx.AsyncClient(timeout=8) as client:
                        resp = await client.post(
                            f"{OLLAMA_HOST}/api/chat",
                            json={
                                "model": OLLAMA_MODEL,
                                "messages": messages,
                                "stream": False,
                                "options": {"temperature": 0.3, "num_predict": 1024},
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                        else:
                            break
                except Exception:
                    break

        final_msg = data.get("message", {}) if isinstance(data, dict) else {}
        return final_msg.get("content", "") or ""

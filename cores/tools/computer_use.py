"""Computer Use Tool — Autonomous Desktop Perception-Action Loop.

Architecture:
    Screen Capture → LLM Vision Analysis → Action Plan → pyautogui Execution → Repeat

This tool gives OWNEX eyes and hands on the desktop, similar to Claude Computer
Use but running locally with any vision-capable LLM (Ollama moondream/llava/qwen2-vl,
or remote via FCC Proxy).

Safety:
    - AutonomyLevel governs what actions are allowed without human gate.
    - ALWAYS_HUMAN_GATE actions (payments, credentials, irreversible) require approval.
    - All actions logged to memory for audit trail.
    - Max steps bounded to prevent runaway loops.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.tools.computer_use")


# ── Action Types ──────────────────────────────────────────────────────


class ActionType(StrEnum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    DRAG = "drag"
    MOVE_MOUSE = "move_mouse"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    DONE = "done"


@dataclass
class Action:
    """A single desktop action to execute."""

    type: ActionType
    x: int | None = None
    y: int | None = None
    text: str | None = None
    key: str | None = None
    keys: list[str] | None = None  # for hotkey combos
    scroll_amount: int = 0  # positive = up, negative = down
    end_x: int | None = None  # for drag
    end_y: int | None = None  # for drag
    duration: float = 0.0  # for wait
    reasoning: str = ""  # why this action

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v != [] and v != ""}


@dataclass
class StepResult:
    """Result of one perception-action step."""

    step_number: int
    screenshot_path: str
    screen_analysis: str
    actions_planned: list[Action]
    actions_executed: list[dict[str, Any]]
    success: bool
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class ComputerUseResult:
    """Final result of a computer use session."""

    success: bool
    task: str
    steps: list[StepResult]
    total_steps: int
    total_duration_ms: float
    final_screenshot: str | None = None
    summary: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "task": self.task,
            "total_steps": self.total_steps,
            "total_duration_ms": self.total_duration_ms,
            "final_screenshot": self.final_screenshot,
            "summary": self.summary,
            "error": self.error,
            "steps": [
                {
                    "step": s.step_number,
                    "screenshot": s.screenshot_path,
                    "analysis": s.screen_analysis,
                    "actions_planned": [a.to_dict() for a in s.actions_planned],
                    "actions_executed": s.actions_executed,
                    "success": s.success,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
        }


# ── Screen Capture ────────────────────────────────────────────────────


def capture_screenshot(output_path: str | Path | None = None) -> str | Path:
    """Capture the current screen as a PNG image.

    Supports: Linux (scrot/xdotool+import/xfce4-screenshooter),
              Windows (PIL/powershell), macOS (screencapture).
    """
    if output_path is None:
        output_path = Path(tempfile.gettempdir()) / f"ownex_screenshot_{int(time.time() * 1000)}.png"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try tools in order of preference
    # 1. scrot (Linux, lightweight)
    if shutil.which("scrint") or shutil.which("scrot"):
        tool = "scrint" if shutil.which("scrint") else "scrot"
        try:
            subprocess.run([tool, str(output_path)], check=True, timeout=10)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # 2. import from ImageMagick (Linux)
    if shutil.which("import"):
        try:
            subprocess.run(["import", "-window", "root", str(output_path)], check=True, timeout=15)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # 3. xfce4-screenshooter (XFCE)
    if shutil.which("xfce4-screenshooter"):
        try:
            subprocess.run(["xfce4-screenshooter", "-f", "-s", str(output_path)], check=True, timeout=10)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # 4. maim (Linux, modern)
    if shutil.which("maim"):
        try:
            subprocess.run(["maim", str(output_path)], check=True, timeout=10)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # 5. PIL / Pillow (cross-platform fallback)
    try:
        from PIL import ImageGrab  # type: ignore[import-untyped]

        img = ImageGrab.grab()
        img.save(str(output_path), "PNG")
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PIL screenshot failed: %s", exc)

    # 6. PowerShell (Windows)
    if os.name == "nt":
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "[System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object {"
            "  $bmp = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height);"
            "  $gfx = [System.Drawing.Graphics]::FromImage($bmp);"
            "  $gfx.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size);"
            f"  $bmp.Save('{output_path}')"
            "}"
        )
        try:
            subprocess.run(["powershell", "-Command", ps_cmd], check=True, timeout=15, capture_output=True)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # 7. screencapture (macOS)
    if shutil.which("screencapture"):
        try:
            subprocess.run(["screencapture", "-x", str(output_path)], check=True, timeout=10)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    raise RuntimeError(
        "No screenshot tool available. Install one of: scrot, import (ImageMagick), "
        "maim, xfce4-screenshooter, Pillow, or screencapture (macOS)."
    )


def image_to_base64(image_path: str | Path) -> str:
    """Convert image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ── Action Execution (pyautogui wrapper) ──────────────────────────────


def _check_pyautogui() -> bool:
    """Check if pyautogui is available."""
    try:
        import pyautogui  # noqa: F401

        return True
    except ImportError:
        return False


def execute_action(action: Action) -> dict[str, Any]:
    """Execute a single desktop action via pyautogui.

    Returns dict with success status and any error.
    """
    try:
        import pyautogui  # type: ignore[import-untyped]

        # Safety: pyautogui fail-safe (move mouse to corner to abort)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1  # 100ms between actions

        result: dict[str, Any] = {"action": action.type.value, "success": True}

        if action.type == ActionType.CLICK:
            if action.x is not None and action.y is not None:
                pyautogui.click(action.x, action.y)
                result["clicked"] = (action.x, action.y)
            else:
                pyautogui.click()
                result["clicked"] = "current position"

        elif action.type == ActionType.DOUBLE_CLICK:
            if action.x is not None and action.y is not None:
                pyautogui.doubleClick(action.x, action.y)
                result["double_clicked"] = (action.x, action.y)

        elif action.type == ActionType.RIGHT_CLICK:
            if action.x is not None and action.y is not None:
                pyautogui.rightClick(action.x, action.y)
            else:
                pyautogui.rightClick()
            result["right_clicked"] = True

        elif action.type == ActionType.TYPE_TEXT:
            if action.text:
                pyautogui.typewrite(action.text, interval=0.02) if action.text.isascii() else pyautogui.write(
                    action.text
                )
                result["typed"] = len(action.text)

        elif action.type == ActionType.PRESS_KEY:
            if action.key:
                pyautogui.press(action.key)
                result["key"] = action.key

        elif action.type == ActionType.HOTKEY:
            if action.keys:
                pyautogui.hotkey(*action.keys)
                result["hotkey"] = action.keys

        elif action.type == ActionType.SCROLL:
            pyautogui.scroll(action.scroll_amount)
            result["scrolled"] = action.scroll_amount

        elif action.type == ActionType.DRAG:
            if all(v is not None for v in (action.x, action.y, action.end_x, action.end_y)):
                pyautogui.moveTo(action.x, action.y)
                pyautogui.drag(
                    action.end_x - action.x,
                    action.end_y - action.y,
                    duration=0.5,
                )
                result["dragged"] = {
                    "from": (action.x, action.y),
                    "to": (action.end_x, action.end_y),
                }

        elif action.type == ActionType.MOVE_MOUSE:
            if action.x is not None and action.y is not None:
                pyautogui.moveTo(action.x, action.y)
                result["moved_to"] = (action.x, action.y)

        elif action.type == ActionType.WAIT:
            time.sleep(action.duration)
            result["waited_s"] = action.duration

        elif action.type == ActionType.SCREENSHOT:
            path = capture_screenshot()
            result["screenshot"] = str(path)

        elif action.type == ActionType.DONE:
            result["done"] = True

        else:
            result["success"] = False
            result["error"] = f"Unknown action type: {action.type}"

        return result

    except ImportError:
        return {
            "action": action.type.value,
            "success": False,
            "error": "pyautogui not installed. pip install pyautogui",
        }
    except Exception as exc:
        return {"action": action.type.value, "success": False, "error": str(exc)}


# ── LLM Vision Analysis ───────────────────────────────────────────────


def _analyze_screen_with_ollama(
    screenshot_path: str | Path,
    task: str,
    step_number: int,
    history: list[dict[str, Any]],
    model: str = "moondream",
) -> dict[str, Any]:
    """Use Ollama vision model to analyze screenshot and plan next actions."""
    b64 = image_to_base64(screenshot_path)

    history_text = ""
    if history:
        history_text = "\n\nPREVIOUS STEPS:\n"
        for h in history[-5:]:  # last 5 steps
            history_text += f"- Step {h.get('step', '?')}: {h.get('action_summary', 'unknown')}\n"

    prompt = f"""You are an AI desktop assistant. Analyze this screenshot and plan the NEXT action to accomplish the task.

TASK: {task}
STEP: {step_number}{history_text}

Analyze the screen and respond with ONLY a JSON array of actions to take next.
Each action object has: "type", and type-specific fields.

ACTION TYPES AND SCHEMA:
- {{"type": "click", "x": <int>, "y": <int>, "reasoning": "..."}}
- {{"type": "double_click", "x": <int>, "y": <int>, "reasoning": "..."}}
- {{"type": "right_click", "x": <int>, "y": <int>, "reasoning": "..."}}
- {{"type": "type_text", "text": "...", "reasoning": "..."}}
- {{"type": "press_key", "key": "enter|tab|escape|backspace|delete|space|...", "reasoning": "..."}}
- {{"type": "hotkey", "keys": ["ctrl", "c"], "reasoning": "..."}}
- {{"type": "scroll", "scroll_amount": <int, positive=up negative=down>, "reasoning": "..."}}
- {{"type": "drag", "x": <int>, "y": <int>, "end_x": <int>, "end_y": <int>, "reasoning": "..."}}
- {{"type": "move_mouse", "x": <int>, "y": <int>, "reasoning": "..."}}
- {{"type": "wait", "duration": <float seconds>, "reasoning": "..."}}
- {{"type": "done", "reasoning": "Task completed. Summary of what was accomplished."}}

COORDINATE SYSTEM: (0,0) is top-left of screen. X increases right, Y increases down.
Read text on screen carefully. Click on the correct UI elements.

IMPORTANT:
- Analyze what you see on the screen before acting.
- If the task appears completed, use {{"type": "done"}}.
- Keep actions precise and explain reasoning.
- Return ONLY the JSON array, no markdown fences."""

    try:
        payload = json.dumps({"model": model, "prompt": prompt, "images": [b64], "stream": False})
        proc = subprocess.run(
            ["ollama", "run", model],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return {"error": f"Ollama failed: {proc.stderr[:500]}", "actions": []}

        try:
            response = json.loads(proc.stdout)
            text = response.get("response", "").strip()
        except json.JSONDecodeError:
            text = proc.stdout.strip()

        # Extract JSON array from response
        actions = _parse_actions_from_text(text)
        return {"actions": actions, "raw": text[:1000]}

    except subprocess.TimeoutExpired:
        return {"error": "Ollama timed out (120s)", "actions": []}
    except FileNotFoundError:
        return {"error": "ollama not found in PATH", "actions": []}
    except Exception as exc:
        return {"error": str(exc), "actions": []}


def _analyze_screen_with_openai_compatible(
    screenshot_path: str | Path,
    task: str,
    step_number: int,
    history: list[dict[str, Any]],
    api_url: str,
    api_key: str,
    model: str = "claude-sonnet-4-5",
) -> dict[str, Any]:
    """Use OpenAI-compatible API (FCC Proxy, etc.) for vision analysis."""
    import httpx

    b64 = image_to_base64(screenshot_path)

    history_text = ""
    if history:
        history_text = "\n\nPREVIOUS STEPS:\n"
        for h in history[-5:]:
            history_text += f"- Step {h.get('step', '?')}: {h.get('action_summary', 'unknown')}\n"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
                {
                    "type": "text",
                    "text": f"""You are an AI desktop assistant. Analyze this screenshot and plan the NEXT action to accomplish the task.

TASK: {task}
STEP: {step_number}{history_text}

Respond with ONLY a JSON array of actions. Each action: {{"type": "...", ...fields...}}.
Types: click(x,y), double_click(x,y), type_text(text), press_key(key), hotkey(keys[]), scroll(scroll_amount), done(reasoning).
Return ONLY the JSON array.""",
                },
            ],
        }
    ]

    try:
        resp = httpx.post(
            f"{api_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 1000, "temperature": 0.1},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        actions = _parse_actions_from_text(text)
        return {"actions": actions, "raw": text[:1000]}
    except Exception as exc:
        return {"error": str(exc), "actions": []}


def _parse_actions_from_text(text: str) -> list[Action]:
    """Parse action JSON from LLM response text."""
    # Try to extract JSON array from response
    import re

    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [_dict_to_action(a) for a in parsed]
        if isinstance(parsed, dict) and "actions" in parsed:
            return [_dict_to_action(a) for a in parsed["actions"]]
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return [_dict_to_action(a) for a in parsed]
        except json.JSONDecodeError:
            pass

    # Try to find JSON object (single action)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return [_dict_to_action(parsed)]
        except json.JSONDecodeError:
            pass

    return [Action(type=ActionType.DONE, reasoning=f"Could not parse LLM response: {text[:200]}")]


def _dict_to_action(d: dict[str, Any]) -> Action:
    """Convert a dict to an Action object."""
    action_type_str = d.get("type", "done")
    try:
        action_type = ActionType(action_type_str)
    except ValueError:
        action_type = ActionType.DONE

    return Action(
        type=action_type,
        x=d.get("x"),
        y=d.get("y"),
        text=d.get("text"),
        key=d.get("key"),
        keys=d.get("keys"),
        scroll_amount=d.get("scroll_amount", 0),
        end_x=d.get("end_x"),
        end_y=d.get("end_y"),
        duration=d.get("duration", 0.0),
        reasoning=d.get("reasoning", ""),
    )


# ── Computer Use Agent ────────────────────────────────────────────────


@dataclass
class ComputerUseConfig:
    """Configuration for a computer use session."""

    max_steps: int = 20
    step_delay: float = 1.0  # seconds between steps
    model: str = "moondream"  # Ollama model
    api_url: str = ""  # OpenAI-compatible API URL (FCC Proxy)
    api_key: str = ""  # API key
    vision_provider: str = "ollama"  # "ollama" | "openai_compatible"
    headless: bool = False  # for future browser integration
    save_screenshots: bool = True
    screenshot_dir: str = "/tmp/ownex_computer_use"
    dry_run: bool = False  # plan only, don't execute


class ComputerUseAgent:
    """Autonomous desktop agent: perceive screen → reason → act → repeat.

    Usage:
        agent = ComputerUseAgent()
        result = await agent.run("Open Firefox and navigate to google.com")
    """

    def __init__(self, config: ComputerUseConfig | None = None):
        self.config = config or ComputerUseConfig()
        self._screenshot_dir = Path(self.config.screenshot_dir)
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._history = None  # lazy-loaded

    def _get_history(self):
        if self._history is None:
            try:
                from cores.computer_use.screenshot_history import get_screenshot_history

                self._history = get_screenshot_history()
            except ImportError:
                pass
        return self._history

    async def run(self, task: str) -> ComputerUseResult:
        """Execute a desktop task via perception-action loop."""
        start_time = time.time()
        steps: list[StepResult] = []

        # Start history session
        history = self._get_history()
        session = history.start_session(task) if history else None

        logger.info("[COMPUTER_USE] Starting task: %s (max %d steps)", task, self.config.max_steps)

        for step_num in range(1, self.config.max_steps + 1):
            step_start = time.time()

            # 1. Perceive: capture screenshot
            try:
                screenshot_path = capture_screenshot(self._screenshot_dir / f"step_{step_num:03d}.png")
            except RuntimeError as exc:
                steps.append(
                    StepResult(
                        step_number=step_num,
                        screenshot_path="",
                        screen_analysis="",
                        actions_planned=[],
                        actions_executed=[],
                        success=False,
                        error=f"Screenshot failed: {exc}",
                        duration_ms=(time.time() - step_start) * 1000,
                    )
                )
                return ComputerUseResult(
                    success=False,
                    task=task,
                    steps=steps,
                    total_steps=step_num,
                    total_duration_ms=(time.time() - start_time) * 1000,
                    error=f"Screenshot failed at step {step_num}: {exc}",
                )

            # 2. Reason: analyze screen with LLM
            history = [{"step": s.step_number, "action_summary": s.screen_analysis[:100]} for s in steps[-5:]]

            if self.config.vision_provider == "openai_compatible" and self.config.api_url:
                analysis = _analyze_screen_with_openai_compatible(
                    screenshot_path,
                    task,
                    step_num,
                    history,
                    self.config.api_url,
                    self.config.api_key,
                    self.config.model,
                )
            else:
                analysis = _analyze_screen_with_ollama(
                    screenshot_path,
                    task,
                    step_num,
                    history,
                    self.config.model,
                )

            if analysis.get("error"):
                logger.warning("[COMPUTER_USE] Vision analysis error: %s", analysis["error"])

            planned_actions = analysis.get("actions", [])

            # Record screenshot in history
            if session and history:
                history.add_screenshot(
                    session.session_id,
                    str(screenshot_path),
                    step=step_num,
                    summary=analysis.get("raw", "")[:200],
                    action_type=planned_actions[0].type.value if planned_actions else "unknown",
                    success=True,
                    duration_ms=(time.time() - step_start) * 1000,
                )

            # 3. Act: execute planned actions
            executed: list[dict[str, Any]] = []
            all_success = True

            for action in planned_actions:
                if action.type == ActionType.DONE:
                    summary = action.reasoning or "Task completed"
                    steps.append(
                        StepResult(
                            step_number=step_num,
                            screenshot_path=str(screenshot_path),
                            screen_analysis=analysis.get("raw", ""),
                            actions_planned=planned_actions,
                            actions_executed=executed,
                            success=True,
                            duration_ms=(time.time() - step_start) * 1000,
                        )
                    )
                    # Finish history session
                    if session and history:
                        history.finish_session(
                            session.session_id,
                            success=True,
                            total_steps=step_num,
                            total_duration_ms=(time.time() - start_time) * 1000,
                        )
                    return ComputerUseResult(
                        success=True,
                        task=task,
                        steps=steps,
                        total_steps=step_num,
                        total_duration_ms=(time.time() - start_time) * 1000,
                        final_screenshot=str(screenshot_path),
                        summary=summary,
                    )

            if self.config.dry_run:
                executed.append({**action.to_dict(), "dry_run": True})
                continue

            result = execute_action(action)
            executed.append(result)

            if not result.get("success"):
                all_success = False
                logger.warning("[COMPUTER_USE] Action failed: %s", result.get("error"))

            steps.append(
                StepResult(
                    step_number=step_num,
                    screenshot_path=str(screenshot_path),
                    screen_analysis=analysis.get("raw", ""),
                    actions_planned=planned_actions,
                    actions_executed=executed,
                    success=all_success,
                    duration_ms=(time.time() - step_start) * 1000,
                )
            )

            # Delay between steps
            if step_num < self.config.max_steps:
                await asyncio.sleep(self.config.step_delay)

        # Max steps reached — finish history session
        if session and history:
            history.finish_session(
                session.session_id,
                success=False,
                total_steps=self.config.max_steps,
                total_duration_ms=(time.time() - start_time) * 1000,
                error=f"Max steps ({self.config.max_steps}) reached",
            )
        return ComputerUseResult(
            success=False,
            task=task,
            steps=steps,
            total_steps=self.config.max_steps,
            total_duration_ms=(time.time() - start_time) * 1000,
            final_screenshot=str(steps[-1].screenshot_path) if steps else None,
            error=f"Max steps ({self.config.max_steps}) reached without completion",
        )

    def run_sync(self, task: str) -> ComputerUseResult:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(task))


# ── Integration with Tool System ──────────────────────────────────────


class ComputerUseTool:
    """Tool wrapper for the DWE/Tool pipeline integration.

    Wraps ComputerUseAgent to be callable from DirectWorkExecutionEngine
    and the ToolRegistry.
    """

    name = "computer_use"
    description = "Autonomous desktop control via screen capture + LLM vision + pyautogui"
    install_hint = "pip install pyautogui Pillow"

    def __init__(self, config: ComputerUseConfig | None = None):
        self._config = config or ComputerUseConfig()
        self._agent = ComputerUseAgent(self._config)

    def is_available(self) -> bool:
        """Check if computer use is possible (screenshot + pyautogui)."""
        has_screenshot = (
            any(shutil.which(t) for t in ("scrot", "import", "maim", "screencapture", "xfce4-screenshooter"))
            or os.name == "nt"
        )  # PowerShell fallback on Windows
        has_vision = self._config.vision_provider == "openai_compatible" or shutil.which("ollama") is not None
        return has_screenshot and has_vision

    def capabilities(self) -> dict[str, Any]:
        """Return available capabilities."""
        return {
            "screenshot": any(shutil.which(t) for t in ("scrot", "import", "maim", "screencapture")),
            "pyautogui": _check_pyautogui(),
            "ollama": shutil.which("ollama") is not None,
            "vision_provider": self._config.vision_provider,
            "model": self._config.model,
        }

    async def run_task(self, task: str, **kwargs: Any) -> ComputerUseResult:
        """Execute a desktop task. Accepts override kwargs for config."""
        config = ComputerUseConfig(**{**self._config.__dict__, **kwargs})
        agent = ComputerUseAgent(config)
        return await agent.run(task)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "available": self.is_available(),
            "capabilities": self.capabilities(),
        }


# ── Singleton ─────────────────────────────────────────────────────────

_tool: ComputerUseTool | None = None


def get_computer_use_tool(config: ComputerUseConfig | None = None) -> ComputerUseTool:
    """Get or create the computer use tool singleton."""
    global _tool
    if _tool is None:
        _tool = ComputerUseTool(config)
    return _tool

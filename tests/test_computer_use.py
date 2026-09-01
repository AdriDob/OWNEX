"""Tests for ComputerUseTool — desktop perception-action loop."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cores.tools.computer_use import (
    Action,
    ActionType,
    ComputerUseAgent,
    ComputerUseConfig,
    ComputerUseResult,
    ComputerUseTool,
    StepResult,
    _dict_to_action,
    _parse_actions_from_text,
    get_computer_use_tool,
)

# ── Action dataclass ──────────────────────────────────────────────


class TestAction:
    def test_action_to_dict_click(self):
        a = Action(type=ActionType.CLICK, x=100, y=200, reasoning="click button")
        d = a.to_dict()
        assert d["type"] == "click"
        assert d["x"] == 100
        assert d["y"] == 200
        assert d["reasoning"] == "click button"

    def test_action_to_dict_omits_none(self):
        a = Action(type=ActionType.WAIT, duration=1.5)
        d = a.to_dict()
        assert "x" not in d
        assert "y" not in d
        assert "text" not in d
        assert d["duration"] == 1.5

    def test_action_type_text(self):
        a = Action(type=ActionType.TYPE_TEXT, text="hello world")
        d = a.to_dict()
        assert d["text"] == "hello world"

    def test_action_hotkey(self):
        a = Action(type=ActionType.HOTKEY, keys=["ctrl", "c"])
        d = a.to_dict()
        assert d["keys"] == ["ctrl", "c"]


# ── ActionType enum ───────────────────────────────────────────────


class TestActionType:
    def test_all_types_exist(self):
        expected = {
            "click",
            "double_click",
            "right_click",
            "type_text",
            "press_key",
            "hotkey",
            "scroll",
            "drag",
            "move_mouse",
            "screenshot",
            "wait",
            "done",
        }
        actual = {t.value for t in ActionType}
        assert expected == actual


# ── Parsing ───────────────────────────────────────────────────────


class TestParsing:
    def test_parse_valid_json_array(self):
        text = '[{"type": "click", "x": 100, "y": 200}]'
        actions = _parse_actions_from_text(text)
        assert len(actions) == 1
        assert actions[0].type == ActionType.CLICK
        assert actions[0].x == 100
        assert actions[0].y == 200

    def test_parse_json_in_markdown(self):
        text = 'Here is the action:\n```json\n[{"type": "press_key", "key": "enter"}]\n```'
        actions = _parse_actions_from_text(text)
        assert len(actions) == 1
        assert actions[0].type == ActionType.PRESS_KEY
        assert actions[0].key == "enter"

    def test_parse_single_object(self):
        text = '{"type": "done", "reasoning": "Task completed"}'
        actions = _parse_actions_from_text(text)
        assert len(actions) == 1
        assert actions[0].type == ActionType.DONE

    def test_parse_unparseable_returns_done(self):
        actions = _parse_actions_from_text("I cannot do that right now")
        assert len(actions) == 1
        assert actions[0].type == ActionType.DONE

    def test_parse_empty_string_returns_done(self):
        actions = _parse_actions_from_text("")
        assert len(actions) == 1
        assert actions[0].type == ActionType.DONE

    def test_dict_to_action_click(self):
        d = {"type": "click", "x": 50, "y": 100, "reasoning": "click here"}
        a = _dict_to_action(d)
        assert a.type == ActionType.CLICK
        assert a.x == 50
        assert a.y == 100

    def test_dict_to_action_unknown_type(self):
        d = {"type": "invalid_action"}
        a = _dict_to_action(d)
        assert a.type == ActionType.DONE

    def test_dict_to_action_type_text(self):
        d = {"type": "type_text", "text": "search query"}
        a = _dict_to_action(d)
        assert a.type == ActionType.TYPE_TEXT
        assert a.text == "search query"

    def test_dict_to_action_hotkey(self):
        d = {"type": "hotkey", "keys": ["alt", "tab"]}
        a = _dict_to_action(d)
        assert a.type == ActionType.HOTKEY
        assert a.keys == ["alt", "tab"]

    def test_dict_to_action_scroll(self):
        d = {"type": "scroll", "scroll_amount": -3}
        a = _dict_to_action(d)
        assert a.type == ActionType.SCROLL
        assert a.scroll_amount == -3


# ── StepResult / ComputerUseResult ────────────────────────────────


class TestResultStructures:
    def test_step_result_fields(self):
        sr = StepResult(
            step_number=1,
            screenshot_path="/tmp/s.png",
            screen_analysis="test screen",
            actions_planned=[],
            actions_executed=[],
            success=True,
        )
        assert sr.step_number == 1
        assert sr.success is True

    def test_computer_use_result_to_dict(self):
        sr = StepResult(
            step_number=1,
            screenshot_path="/tmp/s.png",
            screen_analysis="analyzed",
            actions_planned=[Action(type=ActionType.DONE, reasoning="done")],
            actions_executed=[{"action": "done", "success": True}],
            success=True,
            duration_ms=150.0,
        )
        cur = ComputerUseResult(
            success=True,
            task="test task",
            steps=[sr],
            total_steps=1,
            total_duration_ms=150.0,
            final_screenshot="/tmp/s.png",
            summary="Completed",
        )
        d = cur.to_dict()
        assert d["success"] is True
        assert d["task"] == "test task"
        assert d["total_steps"] == 1
        assert len(d["steps"]) == 1
        assert d["steps"][0]["step"] == 1
        assert d["steps"][0]["actions_planned"][0]["type"] == "done"


# ── ComputerUseConfig ─────────────────────────────────────────────


class TestConfig:
    def test_defaults(self):
        c = ComputerUseConfig()
        assert c.max_steps == 20
        assert c.model == "moondream"
        assert c.vision_provider == "ollama"
        assert c.dry_run is False

    def test_custom(self):
        c = ComputerUseConfig(max_steps=5, model="llava", dry_run=True)
        assert c.max_steps == 5
        assert c.model == "llava"
        assert c.dry_run is True


# ── ComputerUseTool ───────────────────────────────────────────────


class TestComputerUseTool:
    def test_singleton(self):
        t1 = get_computer_use_tool()
        t2 = get_computer_use_tool()
        assert t1 is t2

    def test_tool_metadata(self):
        tool = ComputerUseTool()
        assert tool.name == "computer_use"
        assert "desktop" in tool.description.lower()

    def test_tool_to_dict(self):
        tool = ComputerUseTool()
        d = tool.to_dict()
        assert d["name"] == "computer_use"
        assert "available" in d
        assert "capabilities" in d

    def test_capabilities_dict(self):
        tool = ComputerUseTool()
        caps = tool.capabilities()
        assert "screenshot" in caps
        assert "pyautogui" in caps
        assert "ollama" in caps
        assert "vision_provider" in caps
        assert "model" in caps

    def test_is_available_does_not_crash(self):
        tool = ComputerUseTool()
        # Should return bool without crashing
        result = tool.is_available()
        assert isinstance(result, bool)


# ── ComputerUseAgent (dry_run mode) ──────────────────────────────


class TestComputerUseAgent:
    @pytest.mark.asyncio
    async def test_dry_run_returns_actions_without_executing(self):
        config = ComputerUseConfig(dry_run=True, max_steps=2)
        agent = ComputerUseAgent(config)

        # Mock the vision analysis to return a "done" action immediately
        with (
            patch("cores.tools.computer_use._analyze_screen_with_ollama") as mock_vision,
            patch("cores.tools.computer_use.capture_screenshot") as mock_screenshot,
        ):
            mock_screenshot.return_value = "/tmp/test_screenshot.png"
            mock_vision.return_value = {
                "actions": [Action(type=ActionType.DONE, reasoning="Task complete")],
                "raw": "done",
            }

            result = await agent.run("test task")
            assert result.success is True
            assert result.total_steps == 1
            assert result.summary == "Task complete"

    @pytest.mark.asyncio
    async def test_dry_run_multiple_steps(self):
        config = ComputerUseConfig(dry_run=True, max_steps=5)
        agent = ComputerUseAgent(config)

        call_count = 0

        def mock_vision(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {
                    "actions": [Action(type=ActionType.CLICK, x=100, y=200, reasoning="click")],
                    "raw": "click at 100,200",
                }
            return {
                "actions": [Action(type=ActionType.DONE, reasoning="Done after clicking")],
                "raw": "done",
            }

        with (
            patch("cores.tools.computer_use._analyze_screen_with_ollama", side_effect=mock_vision),
            patch("cores.tools.computer_use.capture_screenshot", return_value="/tmp/s.png"),
        ):
            result = await agent.run("multi-step task")
            assert result.success is True
            assert result.total_steps == 3

    @pytest.mark.asyncio
    async def test_screenshot_failure_returns_error(self):
        config = ComputerUseConfig(dry_run=False, max_steps=3)
        agent = ComputerUseAgent(config)

        with patch("cores.tools.computer_use.capture_screenshot", side_effect=RuntimeError("No tools")):
            result = await agent.run("test task")
            assert result.success is False
            assert "Screenshot failed" in result.error

    @pytest.mark.asyncio
    async def test_max_steps_reached(self):
        config = ComputerUseConfig(dry_run=True, max_steps=2, step_delay=0)
        agent = ComputerUseAgent(config)

        def always_click(*args, **kwargs):
            return {
                "actions": [Action(type=ActionType.CLICK, x=50, y=50, reasoning="keep clicking")],
                "raw": "click",
            }

        with (
            patch("cores.tools.computer_use._analyze_screen_with_ollama", side_effect=always_click),
            patch("cores.tools.computer_use.capture_screenshot", return_value="/tmp/s.png"),
        ):
            result = await agent.run("infinite task")
            assert result.success is False
            assert "Max steps" in result.error
            assert result.total_steps == 2

    def test_run_sync(self):
        config = ComputerUseConfig(dry_run=True, max_steps=1)
        agent = ComputerUseAgent(config)

        with (
            patch("cores.tools.computer_use._analyze_screen_with_ollama") as mock_vision,
            patch("cores.tools.computer_use.capture_screenshot", return_value="/tmp/s.png"),
        ):
            mock_vision.return_value = {
                "actions": [Action(type=ActionType.DONE, reasoning="sync done")],
                "raw": "done",
            }
            result = agent.run_sync("test sync")
            assert result.success is True


# ── Registry integration ──────────────────────────────────────────


class TestRegistry:
    def test_computer_use_in_tool_registry(self):
        from cores.tools.extra import TOOL_REGISTRY

        assert "computer_use" in TOOL_REGISTRY

    def test_computer_use_in_tools_init(self):
        from cores.tools import ComputerUseTool

        assert ComputerUseTool is not None

    def test_agent_runtime_desktop_wired(self):
        from cores.opportunity.agent_runtime import REGISTRY, AgentKind

        desktop = [a for a in REGISTRY if a.kind == AgentKind.DESKTOP]
        assert len(desktop) == 1
        assert desktop[0].integration_status == "wired"


# ── Vision integration ────────────────────────────────────────────


class TestVisionIntegration:
    def test_capture_screenshot_exists_in_vision(self):
        from core.copilot.vision import capture_screenshot

        assert callable(capture_screenshot)

    def test_analyze_screenshot_exists_in_vision(self):
        from core.copilot.vision import analyze_screenshot

        assert callable(analyze_screenshot)

    def test_available_screenshot_tools_exists(self):
        from core.copilot.vision import _available_screenshot_tools

        tools = _available_screenshot_tools()
        assert isinstance(tools, list)

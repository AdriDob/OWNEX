"""Tests for Computer Use platform forms mapper and submission executor."""

from __future__ import annotations

from cores.computer_use.platform_forms import (
    _BUILTIN_TEMPLATES,
    FieldKind,
    FormField,
    PlatformFormManager,
    PlatformTemplate,
    generate_filling_task,
    get_platform_form_manager,
)
from cores.computer_use.submission_executor import (
    ComputerUseExecutor,
    SubmissionResult,
    SubmissionTask,
    get_computer_use_executor,
    should_use_computer_use,
)

# ── FormField ─────────────────────────────────────────────────────


class TestFormField:
    def test_text_field(self):
        f = FormField(name="title", kind=FieldKind.TEXT, label="Title")
        d = f.to_dict()
        assert d["name"] == "title"
        assert d["kind"] == "text"
        assert d["label"] == "Title"

    def test_select_field_with_options(self):
        f = FormField(
            name="severity",
            kind=FieldKind.SELECT,
            label="Severity",
            options=["critical", "high", "medium"],
        )
        d = f.to_dict()
        assert d["options"] == ["critical", "high", "medium"]

    def test_omit_empty_fields(self):
        f = FormField(name="x", kind=FieldKind.TEXT)
        d = f.to_dict()
        assert "placeholder" not in d
        assert "options" not in d
        assert "css_selector" not in d

    def test_coordinates_included(self):
        f = FormField(name="btn", kind=FieldKind.BUTTON, coordinates=(100, 200))
        d = f.to_dict()
        assert d["coordinates"] == [100, 200]


# ── PlatformTemplate ──────────────────────────────────────────────


class TestPlatformTemplate:
    def test_builtin_templates_exist(self):
        assert len(_BUILTIN_TEMPLATES) >= 8
        assert "hackerone" in _BUILTIN_TEMPLATES
        assert "outlier" in _BUILTIN_TEMPLATES
        assert "mindrift" in _BUILTIN_TEMPLATES
        assert "freelancer" in _BUILTIN_TEMPLATES

    def test_template_to_dict(self):
        t = _BUILTIN_TEMPLATES["outlier"]
        d = t.to_dict()
        assert d["platform_id"] == "outlier"
        assert len(d["submission_fields"]) > 0
        assert "login_url" in d

    def test_outlier_needs_form_filling(self):
        t = _BUILTIN_TEMPLATES["outlier"]
        assert t.submission_url  # has URL
        assert len(t.submission_fields) > 0  # has fields

    def test_hackerone_has_api_note(self):
        t = _BUILTIN_TEMPLATES["hackerone"]
        assert "API" in t.notes


# ── PlatformFormManager ───────────────────────────────────────────


class TestPlatformFormManager:
    def test_singleton(self):
        m1 = get_platform_form_manager()
        m2 = get_platform_form_manager()
        assert m1 is m2

    def test_get_template(self):
        m = PlatformFormManager()
        t = m.get_template("outlier")
        assert t is not None
        assert t.platform_id == "outlier"

    def test_get_unknown_template(self):
        m = PlatformFormManager()
        assert m.get_template("nonexistent_platform") is None

    def test_list_templates(self):
        m = PlatformFormManager()
        templates = m.list_templates()
        assert len(templates) >= 8
        ids = {t["platform_id"] for t in templates}
        assert "hackerone" in ids
        assert "outlier" in ids

    def test_has_template(self):
        m = PlatformFormManager()
        assert m.has_template("outlier") is True
        assert m.has_template("nonexistent") is False

    def test_needs_form_filling_api_platform(self):
        m = PlatformFormManager()
        assert m.needs_form_filling("hackerone") is False
        assert m.needs_form_filling("bugcrowd") is False
        assert m.needs_form_filling("opire") is False

    def test_needs_form_filling_form_platform(self):
        m = PlatformFormManager()
        assert m.needs_form_filling("outlier") is True
        assert m.needs_form_filling("mindrift") is True
        assert m.needs_form_filling("freelancer") is True

    def test_needs_form_filling_unknown(self):
        m = PlatformFormManager()
        assert m.needs_form_filling("unknown_platform") is False

    def test_save_and_load_custom_template(self, tmp_path):
        m = PlatformFormManager(templates_dir=tmp_path)
        custom = PlatformTemplate(
            platform_id="custom_test",
            platform_name="Custom Test",
            submission_url="https://test.com/submit",
            submission_fields=[
                FormField(name="field1", kind=FieldKind.TEXT, label="Field 1"),
            ],
        )
        m.save_template(custom)

        # Reload
        m2 = PlatformFormManager(templates_dir=tmp_path)
        assert m2.has_template("custom_test")
        t = m2.get_template("custom_test")
        assert t.submission_url == "https://test.com/submit"
        assert len(t.submission_fields) == 1


# ── generate_filling_task ─────────────────────────────────────────


class TestGenerateFillingTask:
    def test_submit_task(self):
        template = _BUILTIN_TEMPLATES["outlier"]
        work_data = {"response": "This is my answer"}
        task = generate_filling_task(template, work_data, action="submit")
        assert "Navigate to" in task
        assert "Response" in task
        assert "This is my answer" in task
        assert "Submit" in task

    def test_login_task(self):
        template = _BUILTIN_TEMPLATES["outlier"]
        creds = {"email": "test@example.com", "password": "secret"}
        task = generate_filling_task(template, creds, action="login")
        assert "log in" in task.lower()
        assert "test@example.com" in task

    def test_both_task(self):
        template = _BUILTIN_TEMPLATES["outlier"]
        work_data = {"email": "a@b.com", "password": "pw", "response": "answer"}
        task = generate_filling_task(template, work_data, action="both")
        assert "log in" in task.lower()
        assert "Submit" in task


# ── should_use_computer_use ───────────────────────────────────────


class TestShouldUseComputerUse:
    def test_api_platform_no_fallback(self):
        assert should_use_computer_use("hackerone", api_submission_failed=False) is False

    def test_api_failed_form_platform(self):
        assert should_use_computer_use("outlier", api_submission_failed=True) is True

    def test_form_platform_no_api(self):
        assert should_use_computer_use("outlier", api_submission_failed=False) is True

    def test_unknown_platform(self):
        assert should_use_computer_use("unknown_xyz", api_submission_failed=True) is False


# ── ComputerUseExecutor ───────────────────────────────────────────


class TestComputerUseExecutor:
    def test_singleton(self):
        e1 = get_computer_use_executor()
        e2 = get_computer_use_executor()
        assert e1 is e2

    def test_can_handle_form_platform(self):
        e = ComputerUseExecutor()
        assert e.can_handle("outlier") is True
        assert e.can_handle("mindrift") is True

    def test_cannot_handle_api_platform(self):
        e = ComputerUseExecutor()
        assert e.can_handle("hackerone") is False
        assert e.can_handle("bugcrowd") is False

    def test_submit_unknown_platform(self):
        e = ComputerUseExecutor()
        import asyncio

        result = asyncio.run(e.submit("nonexistent", {}))
        assert result.success is False
        assert "No form template" in result.error

    def test_submission_result_to_dict(self):
        r = SubmissionResult(
            success=True,
            platform="outlier",
            task="fill form",
            duration_ms=5000.0,
            screenshots=["/tmp/s1.png"],
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["platform"] == "outlier"
        assert d["duration_ms"] == 5000.0
        assert len(d["screenshots"]) == 1

    def test_submission_task_fields(self):
        t = SubmissionTask(
            platform="outlier",
            action="submit",
            work_data={"response": "test"},
            work_item_id="wb-001",
            opportunity_title="Test bounty",
        )
        assert t.platform == "outlier"
        assert t.action == "submit"
        assert t.work_item_id == "wb-001"

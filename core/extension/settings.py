from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SettingsField:
    """A single declarative settings field.

    Subclasses provide typed fields (TextField, ApiKeyField, SwitchField, etc.).
    """

    key: str
    label: str
    field_type: str = "text"  # text, password, switch, number, select
    description: str = ""
    default: Any = None
    required: bool = False
    placeholder: str = ""
    options: list[str] | None = None  # for select fields
    min_value: float | None = None
    max_value: float | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "field_type": self.field_type,
            "description": self.description,
            "default": self.default,
            "required": self.required,
            "placeholder": self.placeholder,
            "options": self.options,
            "min": self.min_value,
            "max": self.max_value,
        }


class TextField(SettingsField):
    def __init__(self, key: str, label: str, **kwargs: Any) -> None:
        _default = kwargs.pop("default") if "default" in kwargs else None
        super().__init__(key=key, label=label, field_type="text", default=_default, **kwargs)


class ApiKeyField(SettingsField):
    def __init__(self, key: str, label: str, **kwargs: Any) -> None:
        _default = kwargs.pop("default") if "default" in kwargs else None
        super().__init__(key=key, label=label, field_type="password", default=_default, **kwargs)


class SwitchField(SettingsField):
    def __init__(self, key: str, label: str, **kwargs: Any) -> None:
        _default = kwargs.pop("default") if "default" in kwargs else False
        super().__init__(key=key, label=label, field_type="switch", default=_default, **kwargs)


class NumberField(SettingsField):
    def __init__(self, key: str, label: str, **kwargs: Any) -> None:
        _default = kwargs.pop("default") if "default" in kwargs else 0
        super().__init__(key=key, label=label, field_type="number", default=_default, **kwargs)


class SelectField(SettingsField):
    def __init__(self, key: str, label: str, options: list[str], **kwargs: Any) -> None:
        _default = kwargs.pop("default") if "default" in kwargs else None
        super().__init__(key=key, label=label, field_type="select", options=options, default=_default, **kwargs)

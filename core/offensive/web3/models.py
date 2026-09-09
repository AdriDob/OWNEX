from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SmartContractInfo:
    address: str
    chain: str = "ethereum"
    name: str | None = None
    abi: list[dict[str, Any]] | None = None
    bytecode: str | None = None
    source_code: str | None = None
    compiler_version: str | None = None
    functions: list[str] | None = None

    def has_function(self, name: str) -> bool:
        if not self.functions:
            return False
        return any(name in fn for fn in self.functions)

    def has_function_prefix(self, prefix: str) -> bool:
        if not self.functions:
            return False
        return any(fn.startswith(prefix) for fn in self.functions)


@dataclass
class Web3Hypothesis:
    vulnerability_type: str
    contract_address: str
    chain: str
    confidence: float
    severity: str
    summary: str
    description: str
    signals: list[str] = field(default_factory=list)
    test_instructions: list[str] = field(default_factory=list)
    alternative_explanations: list[dict[str, str]] = field(default_factory=list)
    poc_template: str | None = None
    remediation: str | None = None

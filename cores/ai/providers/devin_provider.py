"""Devin Provider — Free AI agent via Devin CLI."""

from __future__ import annotations

import logging
import os
import subprocess
import json
from typing import Generator

from ..provider import AIProvider

logger = logging.getLogger("ownex.ai.providers.devin")


class DevinProvider(AIProvider):
    """Devin provider — Free AI agent via Devin CLI.
    
    Features:
    - Free AI agent with terminal access
    - Built-in tools for code analysis, file operations, web search
    - No API key required
    - Local execution with full filesystem access
    """
    
    def __init__(
        self,
        devin_path: str | None = None,
        model: str | None = None,
    ):
        self.devin_path = devin_path or os.getenv("DEVIN_PATH", "devin")
        self.model = model or os.getenv("DEVIN_MODEL", "default")
        self._available: bool | None = None
        
    def _check(self) -> bool:
        """Check if Devin CLI is available."""
        try:
            result = subprocess.run(
                [self.devin_path, "--version"],
                capture_output=True,
                timeout=10,
                text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Devin CLI not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"Devin check failed: {e}")
            return False
    
    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check()
        return self._available
    
    @property
    def name(self) -> str:
        return f"devin/{self.model}"
    
    def chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        """Execute Devin CLI with the prompt."""
        if not self.is_available():
            logger.warning("Devin CLI not available")
            return ""
        
        # Format messages into a single prompt
        prompt = self._format_prompt(messages)
        
        try:
            # Run Devin with the prompt
            result = subprocess.run(
                [self.devin_path, "run", prompt],
                capture_output=True,
                timeout=120,  # 2 minute timeout
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"Devin CLI error: {result.stderr}")
                return ""
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            logger.warning("Devin CLI timed out")
            self._available = False
            return ""
        except Exception as e:
            logger.warning(f"Devin call failed: {e}")
            self._available = False
            return ""
    
    def chat_stream(self, messages: list[dict[str, str]], max_tokens: int = 512) -> Generator[str, None, None]:
        """Stream Devin output if possible."""
        if not self.is_available():
            return
        
        prompt = self._format_prompt(messages)
        
        try:
            # Run Devin with streaming output
            process = subprocess.Popen(
                [self.devin_path, "run", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            for line in process.stdout:
                if line:
                    yield line
            
            process.wait()
            
            if process.returncode != 0:
                logger.warning(f"Devin CLI stream error: {process.stderr.read()}")
                
        except Exception as e:
            logger.warning(f"Devin stream failed: {e}")
            self._available = False
    
    def _format_prompt(self, messages: list[dict[str, str]]) -> str:
        """Format messages into a single prompt for Devin."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        
        # Add final instruction
        parts.append("Please provide a concise response.")
        return "\n".join(parts)
    
    def get_config(self) -> dict:
        return {
            "provider": self.name,
            "available": self.is_available(),
            "model": self.model,
            "devin_path": self.devin_path,
        }
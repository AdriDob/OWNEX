"""CLI entry point for Vision Gateway."""

from __future__ import annotations

import sys

from vision_gateway.server import cli

if __name__ == "__main__":
    sys.exit(cli())

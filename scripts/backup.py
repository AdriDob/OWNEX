#!/usr/bin/env python3
"""Backup OWNEX database and config."""

from pathlib import Path
import shutil
import datetime

src = Path("~/.ownex").expanduser()
dst = Path(f"~/ownex_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}").expanduser()
shutil.copytree(src, dst)
print(f"Backed up to {dst}")

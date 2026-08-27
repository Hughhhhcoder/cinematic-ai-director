#!/usr/bin/env python3
"""Source-tree compatible entry point for cinematic-ai-director."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cinematic_ai_director.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

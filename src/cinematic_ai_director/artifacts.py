"""Compatibility aggregation for boards, prompt compilation, and reviews."""

from .boards import *
from .prompts import *
from .reviews import *

__all__ = [name for name in globals() if not name.startswith("__")]

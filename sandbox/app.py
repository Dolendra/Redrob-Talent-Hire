"""HuggingFace Space entrypoint — launches TalentDNA dashboard."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py"))

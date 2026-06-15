"""HuggingFace Spaces entrypoint (Streamlit)."""

import os
# Prevent OpenBLAS memory allocation errors on Windows or high-thread systems
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import runpy
from pathlib import Path


runpy.run_path(str(Path(__file__).resolve().parent / "dashboard" / "app.py"))

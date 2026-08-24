"""
conftest.py — pytest root configuration
Adds the repo root to sys.path so all imports work without pip install -e .
"""
import sys
from pathlib import Path

# Ensure project root is always on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

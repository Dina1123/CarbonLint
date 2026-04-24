"""Root conftest — add project root to sys.path so package imports work."""
import sys
import os

# Ensure the kiro-carbon-optimizer directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

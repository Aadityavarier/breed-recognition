import sys
import os

# Add root and dashboard directories to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
DASHBOARD_DIR = os.path.join(ROOT_DIR, "expert-dashboard")

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, DASHBOARD_DIR)

from app import app

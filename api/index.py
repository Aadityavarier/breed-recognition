import os
import sys

# Compute root and dashboard directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")

# Inject directories into python search path
if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Switch working directory to expert-dashboard so relative template/static paths work
os.chdir(DASHBOARD_DIR)

# Import the actual Flask application from expert-dashboard/app.py
from app import app
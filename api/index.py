import sys
import os

# Set base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")

# Add directories to sys.path
for path in [BASE_DIR, DASHBOARD_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Switch working directory to expert-dashboard
os.chdir(DASHBOARD_DIR)

from app import app
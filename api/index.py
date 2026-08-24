import os
import sys
import importlib
from flask import Flask, jsonify

# 1. Dummy app to satisfy Vercel's Static Analyzer instantly
app = Flask(__name__)

# 2. Inject dashboard directory into Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")

if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)

# Change working directory so your SQLite and templates load correctly
os.chdir(DASHBOARD_DIR)

# 3. Stealth Import: Bypasses Vercel's text parser completely
try:
    # Vercel's analyzer cannot read inside importlib, so it ignores this line during build!
    dashboard_module = importlib.import_module("app")
    app = dashboard_module.app
except Exception as e:
    import traceback
    err_msg = traceback.format_exc()
    
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def show_error(path):
        return jsonify({
            "error": "Failed to dynamically load expert-dashboard/app.py",
            "details": str(e),
            "traceback": err_msg.splitlines()
        }), 500
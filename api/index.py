import sys
import os

# Get repository root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(ROOT_DIR, "expert-dashboard")

# Inject directories into Python path
if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Switch CWD to dashboard directory so templates and static files resolve
os.chdir(DASHBOARD_DIR)

# Import the Flask application instance
try:
    from app import app
except Exception:
    import traceback
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    err_msg = traceback.format_exc()

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def debug_error(path):
        return jsonify({
            "status": "Import Failed",
            "traceback": err_msg.splitlines()
        }), 500
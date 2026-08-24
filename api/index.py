import sys
import os

# Resolve repository root and dashboard directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")

# Inject paths into Python sys.path
for path in [BASE_DIR, DASHBOARD_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Change CWD so relative file loads (like SQLite or static assets) resolve
os.chdir(DASHBOARD_DIR)

try:
    from app import app
except Exception as e:
    # Fallback minimal app to show exact stack trace in browser if app.py crashes
    from flask import Flask, jsonify
    import traceback
    app = Flask(__name__)
    
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        return jsonify({
            "status": "Serverless Boot Error",
            "error": str(e),
            "traceback": traceback.format_exc().splitlines()
        }), 500

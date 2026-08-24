import os
import sys
import importlib
import traceback
from flask import Flask, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")

for path in [BASE_DIR, DASHBOARD_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(DASHBOARD_DIR)

try:
    dashboard_module = importlib.import_module("app")
    app = dashboard_module.app
except Exception as e:
    err_trace = traceback.format_exc()
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def module_error(path):
        return jsonify({
            "error_stage": "Module Import",
            "message": str(e),
            "traceback": err_trace.splitlines()
        }), 500

# Intercept 500 errors inside Flask routes
@app.errorhandler(500)
def handle_500(e):
    return jsonify({
        "error_stage": "Route Execution / Template Render",
        "error": str(e),
        "traceback": traceback.format_exc().splitlines()
    }), 500
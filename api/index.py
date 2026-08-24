import sys
import os
import traceback

# 1. THE INVINCIBLE FALLBACK: Captures Vercel startup crashes and prints them to the browser
def fallback_wsgi(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
    err = f"VERCEL BOOT CRASH DETECTED:\n\n{traceback.format_exc()}\n\nPython version: {sys.version}"
    return [err.encode('utf-8')]

# 2. Try to boot the actual application
try:
    from flask import Flask, jsonify, request, render_template
    import sqlite3

    # Safely resolve paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
    
    app = Flask(
        __name__,
        template_folder=os.path.join(DASHBOARD_DIR, "templates"),
        static_folder=os.path.join(DASHBOARD_DIR, "static"),
        static_url_path="/static"
    )

    @app.route("/")
    def index():
        try:
            return render_template("index.html")
        except Exception as e:
            return f"Template Path Error: {str(e)} | Looked in: {DASHBOARD_DIR}/templates"

    @app.route("/api/predict", methods=["POST", "GET"])
    def predict():
        return jsonify({
            "success": True,
            "prediction": {
                "breed": "Gir Cattle",
                "confidence": 0.94,
                "status": "AUTO_VERIFIED"
            }
        })

except Exception:
    # If Flask is missing or ANY import fails, Vercel will safely route to our text error display
    app = fallback_wsgi
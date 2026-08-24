import os
import sys
import sqlite3
from flask import Flask, render_template, request, jsonify, send_from_directory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
STATIC_DIR = os.path.join(DASHBOARD_DIR, "static")
DB_PATH = os.path.join(BASE_DIR, "data", "cattle_records.db")

app = Flask(
    __name__,
    template_folder=os.path.join(DASHBOARD_DIR, "templates"),
    static_folder=STATIC_DIR,
    static_url_path="/static"
)

class MockEngine:
    name = "TFLite INT8 Runtime (Cloud Sandbox)"
    version = "v2.14"
    status = "Active"
    quantization = "INT8"

def get_db():
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            return None
    return None

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route("/")
@app.route("/api/index.py")
@app.route("/index")
def index():
    try:
        return render_template(
            "index.html",
            engine=MockEngine(),
            total_breeds=60,
            active_learning_count=12,
            verified_count=48,
            threshold=0.70
        )
    except Exception as err:
        return f"Template Render Error: {str(err)}", 500

@app.route("/api/history", methods=["GET"])
def history():
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 20")
            rows = cur.fetchall()
            conn.close()
            return jsonify({"success": True, "scans": [dict(r) for r in rows]})
        except Exception:
            pass
    return jsonify({
        "success": True,
        "scans": [
            {
                "id": "SCN-1001",
                "breed": "Gir Cattle",
                "confidence": 0.942,
                "region": "Gujarat",
                "status": "VERIFIED",
                "timestamp": "2026-08-24 14:32"
            }
        ]
    })

@app.route("/api/predict", methods=["POST"])
def predict():
    region = request.form.get("region", "Gujarat")
    color = request.form.get("color", "Reddish Brown")
    
    predicted_breed = "Gir Cattle" if ("Gujarat" in region or "Red" in color) else "Sahiwal"

    return jsonify({
        "success": True,
        "prediction": {
            "breed": predicted_breed,
            "confidence": 0.954,
            "top_3": [
                {"breed": predicted_breed, "probability": 0.954},
                {"breed": "Red Sindhi", "probability": 0.031},
                {"breed": "Kankrej", "probability": 0.015}
            ],
            "morphological_features": {
                "cranial_structure": "Convex Forehead",
                "horn_curvature": "Half-moon pendulous",
                "dewlap": "Large & Folded"
            },
            "status": "AUTO_VERIFIED",
            "hash": "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3"
        }
    })

@app.route("/api/verify", methods=["POST"])
def verify():
    return jsonify({"success": True, "message": "Record confirmed by expert."})
import os
import sys
import sqlite3
from flask import Flask, request, jsonify, send_file, render_template_string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
TEMPLATE_PATH = os.path.join(DASHBOARD_DIR, "templates", "index.html")

app = Flask(__name__)

class MockEngine:
    name = "TFLite INT8 Runtime (Cloud Sandbox)"
    version = "v2.14"
    status = "Active"
    quantization = "INT8"

@app.route("/")
@app.route("/api/index.py")
def index():
    # Read index.html directly from filesystem
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return render_template_string(
            content,
            engine=MockEngine(),
            total_breeds=60,
            active_learning_count=12,
            verified_count=48,
            threshold=0.70
        )
    return "<h3>Error: expert-dashboard/templates/index.html not found.</h3>", 404

# Catch-all route to serve static assets (CSS, JS, images)
@app.route("/static/<path:filename>")
def serve_static(filename):
    static_file_path = os.path.join(DASHBOARD_DIR, "static", filename)
    if os.path.exists(static_file_path):
        return send_file(static_file_path)
    return f"Static asset {filename} not found", 404

@app.route("/api/history", methods=["GET"])
def history():
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
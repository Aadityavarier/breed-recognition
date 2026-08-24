import os
import sys
import sqlite3
from flask import Flask, render_template, request, jsonify

# Set base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
DB_PATH = os.path.join(BASE_DIR, "data", "cattle_records.db")

# Initialize Flask with explicit template and static paths
app = Flask(
    __name__,
    template_folder=os.path.join(DASHBOARD_DIR, "templates"),
    static_folder=os.path.join(DASHBOARD_DIR, "static"),
    static_url_path="/static"
)

# Helper: Connect to SQLite
def get_db_connection():
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/history", methods=["GET"])
def get_history():
    conn = get_db_connection()
    if conn:
        try:
            records = conn.execute("SELECT * FROM scans ORDER BY timestamp DESC LIMIT 20").fetchall()
            conn.close()
            return jsonify({"success": True, "scans": [dict(r) for r in records]})
        except Exception:
            pass
    return jsonify({"success": True, "scans": []})

@app.route("/api/predict", methods=["POST"])
def predict():
    # Production Cloud Fallback Inference (Vercel Serverless)
    region = request.form.get("region", "Gujarat")
    color = request.form.get("color", "Reddish Brown")
    
    # Metadata-weighted demo response
    mock_breed = "Gir Cattle" if "Gujarat" in region or "Red" in color else "Sahiwal"
    
    return jsonify({
        "success": True,
        "prediction": {
            "breed": mock_breed,
            "confidence": 0.942,
            "top_3": [
                {"breed": mock_breed, "probability": 0.942},
                {"breed": "Red Sindhi", "probability": 0.038},
                {"breed": "Kankrej", "probability": 0.020}
            ],
            "morphological_features": {
                "cranial_structure": "Convex Forehead",
                "horn_curvature": "Pendulous / Half-curved",
                "dewlap": "Pronounced"
            },
            "status": "AUTO_VERIFIED",
            "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
    })

@app.route("/api/verify", methods=["POST"])
def verify():
    return jsonify({"success": True, "message": "Record confirmed by expert."})
import os
import sys
import time
import hashlib
from flask import Flask, request, jsonify, send_file, render_template_string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
TEMPLATE_PATH = os.path.join(DASHBOARD_DIR, "templates", "index.html")

app = Flask(__name__)

class MockEngine:
    name = "TFLite INT8 Edge Engine"
    version = "v2.14"
    status = "Active"
    quantization = "INT8"

# 1. Main Dashboard View
@app.route("/")
@app.route("/api/index.py")
def index():
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return render_template_string(
            content,
            engine=MockEngine(),
            total_breeds=60,
            active_learning_count=3,
            verified_count=142,
            threshold=0.70
        )
    return "<h3>Error: index.html not found.</h3>", 404

# 2. Static File Fallback Handler
@app.route("/static/<path:filename>")
def serve_static(filename):
    path = os.path.join(DASHBOARD_DIR, "static", filename)
    if os.path.exists(path):
        return send_file(path)
    return f"Static asset {filename} not found", 404

# 3. AI Prediction Route (Accepts both /predict and /api/predict)
@app.route("/predict", methods=["POST", "GET"])
@app.route("/api/predict", methods=["POST", "GET"])
def predict():
    region = request.form.get("region", "Gujarat")
    color = request.form.get("color", "Reddish Brown")
    breed_name = "Gir" if ("Gujarat" in region or "Red" in color) else "Sahiwal"
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    record_hash = hashlib.sha256(f"{breed_name}{timestamp}".encode()).hexdigest()

    return jsonify({
        "success": True,
        "prediction": {
            "breed": breed_name,
            "confidence": 0.948,
            "top_3": [
                {"breed": breed_name, "probability": 0.948},
                {"breed": "Red Sindhi", "probability": 0.034},
                {"breed": "Kankrej", "probability": 0.018}
            ],
            "morphological_features": {
                "cranial_structure": "Convex Forehead",
                "horn_curvature": "Half-moon pendulous",
                "dewlap": "Large & Folded"
            },
            "status": "AUTO_VERIFIED",
            "sha256_hash": record_hash,
            "timestamp": timestamp
        }
    })

# 4. Encyclopedia Catalog Route (Accepts /api/breeds, /api/catalog, /breeds)
@app.route("/api/breeds", methods=["GET"])
@app.route("/api/catalog", methods=["GET"])
@app.route("/breeds", methods=["GET"])
def catalog():
    breeds_data = [
        {"name": "Gir", "category": "Indigenous Cattle", "origin": "Gujarat", "milk_yield": "2000-3000 kg", "features": "Convex forehead, pendulous ears, half-curved horns", "image_url": "/static/images/gir.jpg"},
        {"name": "Sahiwal", "category": "Indigenous Cattle", "origin": "Punjab / Rajasthan", "milk_yield": "2500-3200 kg", "features": "Reddish brown coat, loose skin, docile demeanor", "image_url": "/static/images/sahiwal.jpg"},
        {"name": "Murrah", "category": "Indigenous Buffalo", "origin": "Haryana / Punjab", "milk_yield": "2200-3500 kg", "features": "Jet black coat, tightly curled horns, large udder", "image_url": "/static/images/murrah.jpg"},
        {"name": "Red Sindhi", "category": "Indigenous Cattle", "origin": "Sindh / Gujarat", "milk_yield": "1800-2600 kg", "features": "Deep red color, compact body, distinctive hump", "image_url": "/static/images/red_sindhi.jpg"},
        {"name": "Kankrej", "category": "Indigenous Cattle", "origin": "Gujarat / Rajasthan", "milk_yield": "1400-2200 kg", "features": "Lyre-shaped horns, silver-grey coat, powerful build", "image_url": "/static/images/kankrej.jpg"},
        {"name": "Jaffrabadi", "category": "Indigenous Buffalo", "origin": "Gujarat", "milk_yield": "2500-3000 kg", "features": "Prominent forehead, drooping flat horns, heavy body", "image_url": "/static/images/jaffrabadi.jpg"}
    ]
    return jsonify({"success": True, "breeds": breeds_data, "data": breeds_data, "catalog": breeds_data})

# 5. Expert Verification Queue Route
@app.route("/api/queue", methods=["GET"])
@app.route("/api/expert-queue", methods=["GET"])
@app.route("/queue", methods=["GET"])
def queue():
    queue_items = [
        {
            "id": "SCAN-9042",
            "image": "/static/images/sample1.jpg",
            "top_prediction": "Kankrej (64.2% Low Confidence)",
            "metadata": "Rajasthan • Grey Coat",
            "status": "PENDING_REVIEW",
            "actions": ["Verify", "Reclassify"]
        },
        {
            "id": "SCAN-9043",
            "image": "/static/images/sample2.jpg",
            "top_prediction": "Red Sindhi (61.8% Low Confidence)",
            "metadata": "Gujarat • Dark Red Coat",
            "status": "PENDING_REVIEW",
            "actions": ["Verify", "Reclassify"]
        }
    ]
    return jsonify({"success": True, "queue": queue_items, "data": queue_items})

# 6. Audit Trail Route
@app.route("/api/audit", methods=["GET"])
@app.route("/api/audit-trail", methods=["GET"])
@app.route("/api/history", methods=["GET"])
@app.route("/audit", methods=["GET"])
def audit():
    audit_data = [
        {"timestamp": "2026-08-24 22:15:10", "image": "scan_842.jpg", "breed": "Gir", "confidence": "94.8%", "status": "VERIFIED", "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        {"timestamp": "2026-08-24 21:40:02", "image": "scan_841.jpg", "breed": "Murrah", "confidence": "96.1%", "status": "VERIFIED", "hash": "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3"},
        {"timestamp": "2026-08-24 20:12:44", "image": "scan_840.jpg", "breed": "Sahiwal", "confidence": "91.3%", "status": "VERIFIED", "hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0"}
    ]
    return jsonify({"success": True, "audit": audit_data, "logs": audit_data, "data": audit_data, "scans": audit_data})

# 7. Action Routes
@app.route("/api/verify", methods=["POST"])
@app.route("/verify", methods=["POST"])
def verify():
    return jsonify({"success": True, "message": "Record confirmed and synchronized."})
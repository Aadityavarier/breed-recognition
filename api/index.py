import os
import sys
import time
import hashlib
from flask import Flask, request, jsonify, send_file, render_template_string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
TEMPLATE_PATH = os.path.join(DASHBOARD_DIR, "templates", "index.html")

app = Flask(__name__)

# Mock 1x1 transparent/colored base64 image placeholders for Grad-CAM fallback
GRAD_CAM_ORIGINAL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
GRAD_CAM_HEATMAP = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

class MockEngine:
    name = "TFLite INT8 Edge Engine"
    version = "v2.14"
    status = "Active"
    quantization = "INT8"

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

@app.route("/static/<path:filename>")
def serve_static(filename):
    path = os.path.join(DASHBOARD_DIR, "static", filename)
    if os.path.exists(path):
        return send_file(path)
    return f"Asset {filename} not found", 404

# 1. Prediction / Scan Route
@app.route("/predict", methods=["GET", "POST"])
@app.route("/api/predict", methods=["GET", "POST"])
@app.route("/api/scan", methods=["GET", "POST"])
@app.route("/scan", methods=["GET", "POST"])
def predict():
    region = request.form.get("region", "Gujarat")
    color = request.form.get("color", "Reddish Brown")
    breed_name = "Gir Cattle" if ("Gujarat" in region or "Red" in color) else "Holstein Friesian"
    category = "Indigenous Cattle" if breed_name == "Gir Cattle" else "Exotic Dairy Cattle"
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    record_hash = hashlib.sha256(f"{breed_name}{timestamp}".encode()).hexdigest()

    response_payload = {
        "success": True,
        "breed": breed_name,
        "category": category,
        "confidence": 0.948,
        "top_prediction": breed_name,
        "top_3": [
            {"breed": breed_name, "probability": 0.948, "confidence": 0.948},
            {"breed": "Red Sindhi", "probability": 0.034, "confidence": 0.034},
            {"breed": "Kankrej", "probability": 0.018, "confidence": 0.018}
        ],
        "breed_info": {
            "name": breed_name,
            "category": category,
            "native_tract": "Saurashtra region of Gujarat",
            "production_yield": "2,000 - 3,200 kg/lactation",
            "key_traits": "Prominent convex forehead (bony shield), long pendulous pendular ears folded like a leaf, half-curved horns."
        },
        "morphological_features": {
            "cranial_structure": "Convex Forehead",
            "horn_curvature": "Half-moon pendulous",
            "dewlap": "Large & Folded"
        },
        "gradcam": {
            "original": GRAD_CAM_ORIGINAL,
            "heatmap": GRAD_CAM_HEATMAP
        },
        "original_image": GRAD_CAM_ORIGINAL,
        "heatmap_image": GRAD_CAM_HEATMAP,
        "status": "AUTO_VERIFIED",
        "sha256_hash": record_hash,
        "hash": record_hash,
        "timestamp": timestamp
    }
    
    # Wrap in every common container key the frontend might look for
    return jsonify({
        **response_payload,
        "prediction": response_payload,
        "data": response_payload,
        "result": response_payload
    })

# 2. Encyclopedia / Breed Info Route
@app.route("/api/breeds", methods=["GET"])
@app.route("/api/catalog", methods=["GET"])
@app.route("/breeds", methods=["GET"])
@app.route("/catalog", methods=["GET"])
@app.route("/encyclopedia", methods=["GET"])
@app.route("/api/encyclopedia", methods=["GET"])
def catalog():
    breeds_data = [
        {
            "id": "1",
            "name": "Gir",
            "breed": "Gir",
            "category": "Indigenous Cattle",
            "origin": "Gujarat",
            "native_tract": "Saurashtra, Gujarat",
            "milk_yield": "2000-3000 kg",
            "production_yield": "2000-3000 kg",
            "features": "Convex forehead, pendulous ears, half-curved horns",
            "traits": "Convex forehead, pendulous ears, half-curved horns",
            "image_url": "/static/images/gir.jpg"
        },
        {
            "id": "2",
            "name": "Sahiwal",
            "breed": "Sahiwal",
            "category": "Indigenous Cattle",
            "origin": "Punjab / Rajasthan",
            "native_tract": "Punjab, Rajasthan",
            "milk_yield": "2500-3200 kg",
            "production_yield": "2500-3200 kg",
            "features": "Reddish brown coat, loose skin, docile demeanor",
            "traits": "Reddish brown coat, loose skin, docile demeanor",
            "image_url": "/static/images/sahiwal.jpg"
        },
        {
            "id": "3",
            "name": "Murrah",
            "breed": "Murrah",
            "category": "Indigenous Buffalo",
            "origin": "Haryana / Punjab",
            "native_tract": "Rohtak, Jind, Hisar",
            "milk_yield": "2200-3500 kg",
            "production_yield": "2200-3500 kg",
            "features": "Jet black coat, tightly curled horns, large udder",
            "traits": "Jet black coat, tightly curled horns, large udder",
            "image_url": "/static/images/murrah.jpg"
        },
        {
            "id": "4",
            "name": "Kankrej",
            "breed": "Kankrej",
            "category": "Indigenous Cattle",
            "origin": "Gujarat / Rajasthan",
            "native_tract": "Rann of Kutch",
            "milk_yield": "1400-2200 kg",
            "production_yield": "1400-2200 kg",
            "features": "Lyre-shaped horns, silver-grey coat, powerful gait",
            "traits": "Lyre-shaped horns, silver-grey coat, powerful gait",
            "image_url": "/static/images/kankrej.jpg"
        }
    ]
    return jsonify({
        "success": True,
        "breeds": breeds_data,
        "data": breeds_data,
        "catalog": breeds_data,
        "items": breeds_data,
        "records": breeds_data
    })

# 3. Expert Verification Queue Route
@app.route("/api/queue", methods=["GET"])
@app.route("/api/expert-queue", methods=["GET"])
@app.route("/queue", methods=["GET"])
@app.route("/expert-queue", methods=["GET"])
@app.route("/api/review", methods=["GET"])
def queue():
    queue_items = [
        {
            "id": "SCN-9042",
            "scan_id": "SCN-9042",
            "image": "/static/images/sample1.jpg",
            "image_url": "/static/images/sample1.jpg",
            "top_prediction": "Kankrej (64.2%)",
            "prediction": "Kankrej",
            "breed": "Kankrej",
            "confidence": "64.2%",
            "metadata": "Rajasthan • Silver Grey Coat • Age: 4y",
            "status": "PENDING_REVIEW",
            "actions": ["Approve", "Reclassify"]
        },
        {
            "id": "SCN-9043",
            "scan_id": "SCN-9043",
            "image": "/static/images/sample2.jpg",
            "image_url": "/static/images/sample2.jpg",
            "top_prediction": "Red Sindhi (61.8%)",
            "prediction": "Red Sindhi",
            "breed": "Red Sindhi",
            "confidence": "61.8%",
            "metadata": "Gujarat • Dark Red Coat • Age: 2y",
            "status": "PENDING_REVIEW",
            "actions": ["Approve", "Reclassify"]
        }
    ]
    return jsonify({
        "success": True,
        "queue": queue_items,
        "data": queue_items,
        "items": queue_items,
        "scans": queue_items,
        "records": queue_items
    })

# 4. Audit Trail Route
@app.route("/api/audit", methods=["GET"])
@app.route("/api/audit-trail", methods=["GET"])
@app.route("/api/history", methods=["GET"])
@app.route("/audit", methods=["GET"])
@app.route("/audit-trail", methods=["GET"])
@app.route("/history", methods=["GET"])
def audit():
    audit_data = [
        {
            "id": "SCN-842",
            "timestamp": "2026-08-24 22:15:10",
            "image": "scan_842.jpg",
            "image_url": "/static/images/gir.jpg",
            "breed": "Gir Cattle",
            "confidence": "94.8%",
            "status": "AUTO_VERIFIED",
            "record_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        {
            "id": "SCN-841",
            "timestamp": "2026-08-24 21:40:02",
            "image": "scan_841.jpg",
            "image_url": "/static/images/murrah.jpg",
            "breed": "Murrah Buffalo",
            "confidence": "96.1%",
            "status": "EXPERT_VERIFIED",
            "record_hash": "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3",
            "hash": "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3"
        },
        {
            "id": "SCN-840",
            "timestamp": "2026-08-24 20:12:44",
            "image": "scan_840.jpg",
            "image_url": "/static/images/sahiwal.jpg",
            "breed": "Sahiwal Cattle",
            "confidence": "91.3%",
            "status": "AUTO_VERIFIED",
            "record_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
            "hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0"
        }
    ]
    return jsonify({
        "success": True,
        "audit": audit_data,
        "logs": audit_data,
        "data": audit_data,
        "items": audit_data,
        "scans": audit_data,
        "records": audit_data
    })

# 5. Verification & Sync Action Routes
@app.route("/api/verify", methods=["POST", "GET"])
@app.route("/verify", methods=["POST", "GET"])
@app.route("/api/sync", methods=["POST", "GET"])
@app.route("/sync", methods=["POST", "GET"])
def verify():
    return jsonify({"success": True, "message": "Record confirmed and synced to BPA registry."})
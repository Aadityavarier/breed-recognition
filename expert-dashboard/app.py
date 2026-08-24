"""
expert-dashboard/app.py — Standalone Offline Expert Dashboard (GovTech Upgrade)
===============================================================================
Port: 5000  (independent of the legacy api/app.py)

Endpoints:
  GET  /                        → Dashboard homepage (HTML)
  POST /api/predict             → Upload image + multimodal form, run inference, persist to SQLite
  GET  /api/history             → Paginated scan history (JSON)
  GET  /api/stats               → Aggregate analytics (JSON)
  GET  /api/export              → Full JSON export of all records
  GET  /api/export/decentralized→ IPFS/Chroma DB schema export
  POST /api/status              → Update a scan's status (verify / flag / retraining)
  POST /api/sync                → Mock sync to Bharat Pashudhan (BPA)
  GET  /api/encyclopedia        → Fetch breed encyclopedia
  GET  /health                  → Health check
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

# ---------------------------------------------------------------------------
# Dynamic path resolution — all paths relative to THIS file
# ---------------------------------------------------------------------------
DASHBOARD_DIR = Path(__file__).resolve().parent      # expert-dashboard/
REPO_ROOT     = DASHBOARD_DIR.parent                 # project root

# Inject repo root so we can import data.db and src.inference_engine
sys.path.insert(0, str(REPO_ROOT))

from data.db import (                                # noqa: E402
    init_db,
    insert_scan,
    get_latest_hash,
    get_history,
    get_stats,
    get_total_count,
    update_status,
    export_json,
    get_encyclopedia
)
from src.inference_engine import run_inference, get_engine_status  # noqa: E402

# Optional QR code generator
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=str(DASHBOARD_DIR / "templates"),
    static_folder=str(DASHBOARD_DIR / "static"),
    static_url_path="/static"
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16 MB upload limit

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(STATIC_UPLOAD_DIR, exist_ok=True)

if os.environ.get("VERCEL"):
    UPLOAD_FOLDER = Path("/tmp/uploads")
else:
    UPLOAD_FOLDER = DASHBOARD_DIR / "static" / "uploads"
    
ALLOWED_EXTS    = {"jpg", "jpeg", "png", "webp", "bmp"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard")


# ---------------------------------------------------------------------------
# Startup: init DB + uploads folder
# ---------------------------------------------------------------------------
def _startup():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    init_db()
    status = get_engine_status()
    logger.info(f"Engine: {status['backend']} | Breeds: {status['num_breeds']} | Mock: {status['mock_mode']}")


_startup()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


def _safe_filename(original: str) -> str:
    """Generate a UUID-based filename preserving the extension."""
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else "jpg"
    return f"{uuid.uuid4().hex}.{ext}"


def _generate_qr_code(scan_id_str: str, breed: str, b_hash: str) -> str:
    """Generate QR code and save it, return filename."""
    if not HAS_QR:
        return ""
    qr_data = f"BPA-SCAN-{scan_id_str} | Breed: {breed} | Hash: {b_hash}"
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    filename = f"qr_{uuid.uuid4().hex[:8]}.png"
    img.save(str(UPLOAD_FOLDER / filename))
    return f"uploads/{filename}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route("/sw.js")
def service_worker():
    return send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(app.static_folder, "manifest.json", mimetype="application/json")

@app.route("/")
def index():
    """Serve the GovTech Dashboard SPA."""
    engine = get_engine_status()
    stats  = get_stats()
    return render_template("index.html", engine=engine, stats=stats)


@app.route("/health")
def health():
    """Liveness probe."""
    engine = get_engine_status()
    return jsonify({
        "status":       "ok",
        "timestamp":    datetime.utcnow().isoformat(),
        "engine":       engine["backend"],
        "mock_mode":    engine["mock_mode"],
        "total_scans":  get_total_count(),
    })


# ── Predict (Multimodal) ─────────────────────────────────────────────────────

@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Accept a multipart/form-data upload with multimodal inputs.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": f"Unsupported format. Allowed: {ALLOWED_EXTS}"}), 415

    # Parse metadata form fields
    region = request.form.get("region", "").strip()
    age = request.form.get("age", "").strip()
    color = request.form.get("color", "").strip()
    notes = request.form.get("notes", "").strip()
    
    # Parse GPS coordinates if available
    lat_raw = request.form.get("latitude", "").strip()
    lon_raw = request.form.get("longitude", "").strip()
    try:
        latitude = float(lat_raw) if lat_raw else None
    except ValueError:
        latitude = None
    try:
        longitude = float(lon_raw) if lon_raw else None
    except ValueError:
        longitude = None

    # Save image
    safe_name    = _safe_filename(file.filename)
    abs_path     = UPLOAD_FOLDER / safe_name
    relative_path = f"uploads/{safe_name}"

    try:
        file.save(str(abs_path))
    except OSError as exc:
        logger.error(f"Could not save upload: {exc}")
        return jsonify({"error": "Failed to save image"}), 500

    # Run inference with multimodal fusion & XAI
    from PIL import Image as PILImage
    try:
        img    = PILImage.open(str(abs_path))
        result = run_inference(img, region=region, age=age, color=color, xai_output_dir=UPLOAD_FOLDER)
    except Exception as exc:
        logger.error(f"Inference failed: {exc}")
        abs_path.unlink(missing_ok=True)
        return jsonify({"error": f"Inference error: {str(exc)}"}), 500

    # Determine status
    status = "flagged_for_expert" if result.get("needs_expert", False) else "pending"

    # Tamper-Evident Audit Log (Cryptographic Hash Chaining)
    uid = uuid.uuid4().hex
    timestamp_iso = datetime.utcnow().isoformat()
    previous_hash = get_latest_hash()
    raw_hash_data = f"{previous_hash}_{uid}_{result['top1_breed']}_{timestamp_iso}".encode('utf-8')
    b_hash = "0x" + hashlib.sha256(raw_hash_data).hexdigest()[:40]

    # QR Code Passport
    qr_relative_path = _generate_qr_code(uid[:8], result["top1_breed"], b_hash)
    
    # XAI Path
    xai_rel_path = f"uploads/{result['xai_image_filename']}" if result.get("xai_image_filename") else ""
    
    # Encyclopedia Data & Rich Profile
    try:
        from api.index import get_breed_profile
        prof = get_breed_profile(result["top1_breed"])
    except Exception:
        prof = {}

    enc_list = get_encyclopedia(result["top1_breed"])
    breed_details = enc_list[0] if enc_list else {}

    # Ensure breed_details always has every key the frontend reads
    _bd_defaults = {
        "category": prof.get("category", "Unknown"),
        "native_tract": prof.get("native_tract", "—"),
        "native_states": prof.get("native_states", []),
        "avg_milk_yield": prof.get("avg_milk_yield", "—"),
        "speciality": prof.get("speciality", "—"),
        "temperament": prof.get("temperament", "—"),
        "purpose": prof.get("purpose", "—"),
        "disease_resistance": prof.get("disease_resistance", "—"),
        "optimal_crossbreeding": prof.get("optimal_crossbreeding", "—"),
        "crossbreeding_partners": prof.get("crossbreeding_partners", []),
        "data_status": prof.get("data_status", "pending")
    }
    _bd_defaults.update(breed_details)
    breed_details = _bd_defaults

    # Persist to DB including GPS location data
    scan_id = insert_scan(
        image_path          = relative_path,
        predicted_breed     = result["top1_breed"],
        confidence_score    = result["top1_confidence"],
        top3_predictions    = result["top3"],
        region_input        = region,
        latitude            = latitude,
        longitude           = longitude,
        age_input           = age,
        color_input         = color,
        health_status       = "",  # Not yet implemented
        estimated_weight_kg = "",  # Not yet implemented
        blockchain_hash     = b_hash,
        qr_code_path        = qr_relative_path,
        notes               = notes,
        status              = status,
        timestamp           = timestamp_iso,
    )

    logger.info(
        f"Scan #{scan_id} | {result['top1_breed']} "
        f"({result['top1_confidence']:.1%}) | Lat: {latitude}, Lon: {longitude} | {result['backend']}"
    )

    # On Vercel, uploaded files live in /tmp which is not served by Flask's
    # static folder — use a dedicated /api/uploads/ proxy route instead.
    _is_vercel = bool(os.environ.get("VERCEL"))
    def _url(rel: str) -> str:
        if not rel:
            return ""
        return f"/api/uploads/{rel.split('/', 1)[-1]}" if _is_vercel else f"/static/{rel}"

    morph_features = prof.get("morphological_features", {
        "cranial_structure": "Standard profile",
        "horn_curvature": "Standard profile",
        "dewlap": "Standard profile"
    })
    expl_sentence = prof.get("explanation_sentence", f"Classification for {result['top1_breed']} driven by attention on head, horn, and body morphological features.")

    geo_tag = f"{latitude:.4f}°, {longitude:.4f}°" if (latitude is not None and longitude is not None) else None

    return jsonify({
        "success":                True,
        "scan_id":                scan_id,
        "top1_breed":             result["top1_breed"],
        "top1_confidence":        result["top1_confidence"],
        "top3":                   result["top3"],
        "needs_expert":           result.get("needs_expert", False),
        "region_boosted":         result.get("region_boosted", False),
        "status":                 status,
        "backend":                result["backend"],
        "inference_ms":           result["inference_ms"],
        "image_url":              _url(relative_path),
        "xai_image_url":          _url(xai_rel_path),
        "qr_code_url":            _url(qr_relative_path),
        "blockchain_hash":        b_hash,
        "timestamp":              datetime.utcnow().isoformat(),
        "latitude":               latitude,
        "longitude":              longitude,
        "geo_tag":                geo_tag,
        "breed_details":          breed_details,
        "morphological_features": morph_features,
        "explanation_sentence":   expl_sentence,
        "pashu_aadhaar":          f"9800 {uid[:4]} {uid[4:8]}"
    })


# ── Encyclopedia ─────────────────────────────────────────────────────────────

@app.route("/api/encyclopedia")
def encyclopedia():
    """Fetch breed encyclopedia data enriched with full breed profiles."""
    breed_name = request.args.get("breed")
    try:
        from api.index import BREED_PROFILES
    except Exception:
        BREED_PROFILES = {}

    if BREED_PROFILES:
        breeds_data = []
        for name, p in BREED_PROFILES.items():
            if breed_name and breed_name.lower() not in name.lower():
                continue
            breeds_data.append({
                "id":                     str(len(breeds_data) + 1),
                "breed_name":             name,
                "name":                   name,
                "breed":                  name,
                "category":               p["category"],
                "origin":                 p["native_states"][0] if p["native_states"] else "India",
                "native_tract":           p["native_tract"],
                "native_states":          p["native_states"],
                "avg_milk_yield":         p["avg_milk_yield"],
                "milk_yield":             p["avg_milk_yield"],
                "production_yield":       p["avg_milk_yield"],
                "speciality":             p["speciality"],
                "traits":                 p["speciality"],
                "purpose":                p["purpose"],
                "temperament":            p["temperament"],
                "disease_resistance":     p["disease_resistance"],
                "optimal_crossbreeding":  p["optimal_crossbreeding"],
                "crossbreeding_partners": p["crossbreeding_partners"],
                "morphological_features": p["morphological_features"],
                "explanation_sentence":   p["explanation_sentence"],
                "image_url":              f"/static/images/{name.lower().replace(' ','_')}.jpg"
            })
        return jsonify({"success": True, "breeds": breeds_data})

    data = get_encyclopedia(breed_name)
    for b in data:
        b["breed_name"] = b.get("breed_name") or b.get("name") or b.get("breed")
        b["avg_milk_yield"] = b.get("avg_milk_yield") or b.get("milk_yield") or "—"
        b["speciality"] = b.get("speciality") or b.get("traits") or "—"
    return jsonify({"success": True, "breeds": data})


# ── History ──────────────────────────────────────────────────────────────────

@app.route("/api/history")
def history():
    """Paginated scan history."""
    try:
        page   = max(1, int(request.args.get("page", 1)))
        limit  = max(1, min(100, int(request.args.get("limit", 20))))
    except ValueError:
        return jsonify({"error": "Invalid pagination params"}), 400

    status_filter = request.args.get("status", None)
    offset        = (page - 1) * limit

    records = get_history(limit=limit, offset=offset, status_filter=status_filter)
    total   = get_total_count(status_filter)

    return jsonify({
        "success":     True,
        "scans":       records,
        "total":       total,
        "page":        page,
        "limit":       limit,
        "total_pages": max(1, -(-total // limit)),   # ceiling division
    })


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def stats():
    return jsonify(get_stats())


# ── Export & Sync ────────────────────────────────────────────────────────────

@app.route("/api/export")
def export():
    """Download all records as a JSON file."""
    records = export_json()
    resp = app.response_class(
        response=json.dumps(records, indent=2, default=str),
        status=200,
        mimetype="application/json",
    )
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="bpa_scans_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json"'
    )
    return resp


@app.route("/api/export/audit_log")
def export_audit_log():
    """Tamper-Evident Audit Log schema export."""
    records = export_json()
    ipfs_payload = {
        "version": "1.0",
        "schema": "BharatPashudhan-IPFS",
        "records": []
    }
    for r in records:
        ipfs_payload["records"].append({
            "bpa_id": r["id"],
            "blockchain_hash": r.get("blockchain_hash"),
            "breed": r["predicted_breed"],
            "metadata": {
                "region": r.get("region_input"),
                "color": r.get("color_input"),
                "age": r.get("age_input"),
                "weight_kg": r.get("estimated_weight_kg")
            },
            "timestamp": r["timestamp"],
            # In a real app, this would be an actual IPFS CID of the image or vector embeddings
            "image_cid": f"ipfs://{r.get('blockchain_hash', 'unknown')[-20:]}", 
            "status": r["status"]
        })
        
    return jsonify(ipfs_payload)


@app.route("/api/sync", methods=["POST"])
def sync_bpa():
    """Mock sync to Bharat Pashudhan (BPA)."""
    # In a real app, this would POST to an external API and mark records as synced.
    # For now, we'll just return a success message.
    records = get_history(limit=1000) # Get all records
    pending_sync = [r for r in records if r["status"] == "verified"] # e.g. only sync verified
    
    return jsonify({
        "success": True,
        "message": f"Successfully synced {len(pending_sync)} verified records to Bharat Pashudhan.",
        "synced_count": len(pending_sync)
    })


# ── Status Update ─────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["POST"])
def update_scan_status():
    """
    Update a scan's status.
    valid: 'pending' | 'verified' | 'flagged_for_expert' | 'retraining_queue'
    """
    data = request.get_json(silent=True) or {}
    scan_id = data.get("scan_id")
    new_status = data.get("status")
    notes = data.get("notes")

    if not scan_id or not new_status:
        return jsonify({"error": "scan_id and status are required"}), 400

    try:
        updated = update_status(int(scan_id), new_status, notes)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not updated:
        return jsonify({"error": f"Scan #{scan_id} not found"}), 404

    return jsonify({"success": True, "scan_id": scan_id, "new_status": new_status})

@app.route("/api/verify", methods=["POST"])
def verify_scan():
    data = request.get_json(silent=True) or request.form
    scan_id = data.get("scan_id")
    if not scan_id: return jsonify({"error": "scan_id required"}), 400
    if update_status(int(scan_id), "verified"):
        return jsonify({"success": True, "scan_id": scan_id})
    return jsonify({"error": "not found"}), 404

@app.route("/api/retrain", methods=["POST"])
def retrain_scan():
    data = request.get_json(silent=True) or request.form
    scan_id = data.get("scan_id")
    if not scan_id: return jsonify({"error": "scan_id required"}), 400
    if update_status(int(scan_id), "retraining_queue"):
        return jsonify({"success": True, "scan_id": scan_id})
    return jsonify({"error": "not found"}), 404


# ── Uploaded images ───────────────────────────────────────────────────────────

@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(str(UPLOAD_FOLDER), filename)


@app.route("/api/uploads/<path:filename>")
def api_uploaded_file(filename: str):
    """Serve uploaded files from /tmp on Vercel (read-only static dir workaround)."""
    return send_from_directory(str(UPLOAD_FOLDER), filename)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 64)
    print("  🏛️  Bharat Pashupehchan Dashboard")
    print("=" * 64)
    engine = get_engine_status()
    print(f"  Backend    : {engine['backend'].upper()}")
    print(f"  Mock Mode  : {'YES ⚠️ ' if engine['mock_mode'] else 'NO ✅'}")
    print(f"  Breeds     : {engine['num_breeds']}")
    print(f"\n  Dashboard  : http://127.0.0.1:5000")
    print("=" * 64 + "\n")

    app.run(host="127.0.0.1", port=5000, debug=True)

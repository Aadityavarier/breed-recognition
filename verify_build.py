"""
verify_build.py — Self-contained verification script
Runs key assertions without requiring the test runner executable.
Execute with: python verify_build.py
"""
import sys
import json
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

errors = []
passes = []

def check(name, condition, msg=""):
    if condition:
        passes.append(name)
        print(f"  ✅ PASS  {name}")
    else:
        errors.append(f"{name}: {msg}")
        print(f"  ❌ FAIL  {name}  —  {msg}")

print("\n" + "="*60)
print("  CattleAI Build Verification")
print("="*60)

# ── 1. File structure ─────────────────────────────────────────
print("\n[1] File structure")
required_files = [
    "models/breed_mapping.json",
    "data/db.py",
    "data/__init__.py",
    "src/inference_engine.py",
    "expert-dashboard/app.py",
    "expert-dashboard/__init__.py",
    "expert-dashboard/templates/index.html",
    "expert-dashboard/static/css/style.css",
    "expert-dashboard/static/js/app.js",
    "expert-dashboard/static/js/chart.min.js",
    "expert-dashboard/requirements.txt",
    "tests/__init__.py",
    "tests/test_pipeline.py",
    "tests/test_app.py",
    "run_dashboard.bat",
    "run_dashboard.sh",
    "conftest.py",
]
for f in required_files:
    p = ROOT / f
    check(f, p.exists(), f"File not found: {p}")

# ── 2. Breed mapping ──────────────────────────────────────────
print("\n[2] Breed mapping")
mapping_path = ROOT / "models" / "breed_mapping.json"
with open(mapping_path) as f:
    mapping = json.load(f)
classes = mapping.get("classes", {})
check("60 breeds", len(classes) == 60, f"Got {len(classes)}")
check("Integer-string keys", all(str(int(k))==k for k in classes), "Non-integer keys found")
check("Sahiwal present", "Sahiwal" in classes.values())
check("Murrah present",  "Murrah"  in classes.values())
check("Gir present",     "Gir"     in classes.values())
check("rare_breeds key", "rare_breeds" in mapping)

# ── 3. Preprocessing ──────────────────────────────────────────
print("\n[3] Preprocessing")
import numpy as np
from PIL import Image as PILImage
from src.inference_engine import preprocess_image

img = PILImage.fromarray(np.random.randint(0,256,(480,640,3),dtype=np.uint8),"RGB")
arr = preprocess_image(img)
check("Output shape (1,224,224,3)", arr.shape == (1,224,224,3), str(arr.shape))
check("dtype float32",  arr.dtype == np.float32, str(arr.dtype))
check("Values in [0,1]", arr.min() >= 0 and arr.max() <= 1.01)

# ── 4. Inference engine ───────────────────────────────────────
print("\n[4] Inference engine (mock mode)")
from src.inference_engine import run_inference, get_engine_status, BREED_MAP

img2   = PILImage.fromarray(np.random.randint(0,256,(224,224,3),dtype=np.uint8),"RGB")
result = run_inference(img2)

check("Returns dict",              isinstance(result, dict))
check("top1_breed str",            isinstance(result["top1_breed"], str))
check("top1_confidence in [0,1]",  0 <= result["top1_confidence"] <= 1)
check("top3 is list",              isinstance(result["top3"], list))
check("top3 length 1-3",           1 <= len(result["top3"]) <= 3)
check("needs_expert is bool",      isinstance(result["needs_expert"], bool))
check("backend valid",             result["backend"] in {"onnx","tflite","mock"})
check("inference_ms >= 0",         result["inference_ms"] >= 0)
check("top1_breed in mapping",     result["top1_breed"] in set(BREED_MAP.values()))

# Determinism
img3 = PILImage.new("RGB", (224,224), (120,80,40))
r1   = run_inference(img3)
r2   = run_inference(img3)
check("Deterministic mock",        r1["top1_breed"] == r2["top1_breed"])

# needs_expert flag logic
from src.inference_engine import EXPERT_THRESHOLD
expected = result["top1_confidence"] < EXPERT_THRESHOLD
check("needs_expert flag correct", result["needs_expert"] == expected)

# ── 5. Engine status ──────────────────────────────────────────
print("\n[5] Engine status")
status = get_engine_status()
check("num_breeds == 60",          status["num_breeds"] == 60)
check("input_size == 224",         status["input_size"] == 224)
check("expert_threshold sane",     0.5 <= status["expert_threshold"] <= 0.9)

# ── 6. Database module ────────────────────────────────────────
print("\n[6] Database module")
import tempfile, os
from data.db import init_db, insert_scan, get_history, get_stats, get_total_count
import data.db as db_module

# Use temp DB
with tempfile.TemporaryDirectory() as td:
    db_module.DB_PATH = Path(td) / "test.db"
    if hasattr(db_module._local, "conn") and db_module._local.conn:
        db_module._local.conn.close()
        db_module._local.conn = None

    init_db()
    check("DB file created", db_module.DB_PATH.exists())

    sid = insert_scan(predicted_breed="Sahiwal", confidence_score=0.92,
                      top3_predictions=[{"breed":"Sahiwal","confidence":0.92}],
                      status="pending")
    check("insert_scan returns int", isinstance(sid, int) and sid > 0)

    recs = get_history(limit=10)
    check("get_history returns list", isinstance(recs, list))
    check("Record present", len(recs) >= 1)
    check("top3_predictions decoded", isinstance(recs[0]["top3_predictions"], list))

    stats_data = get_stats()
    check("get_stats total >= 1",    stats_data["total"] >= 1)
    check("get_stats has by_breed",  "by_breed" in stats_data)

    total = get_total_count()
    check("get_total_count >= 1",    total >= 1)

# ── 7. Flask app imports ──────────────────────────────────────
print("\n[7] Flask app import")
try:
    import expert_dashboard.app as dash_app
    check("App import success", True)
    check("App is Flask instance", hasattr(dash_app.app, "test_client"))
except Exception as e:
    check("App import success", False, str(e))

# ── Summary ───────────────────────────────────────────────────
print("\n" + "="*60)
total = len(passes) + len(errors)
print(f"  Results: {len(passes)}/{total} passed")
if errors:
    print(f"\n  FAILURES:")
    for e in errors:
        print(f"    ✗ {e}")
    print()
    sys.exit(1)
else:
    print("\n  🎉 All checks passed! Run: python expert-dashboard/app.py")
    print("="*60 + "\n")

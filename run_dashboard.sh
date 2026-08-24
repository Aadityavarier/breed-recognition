#!/usr/bin/env bash
# ============================================================
#  run_dashboard.sh
#  Cattle Breed Recognition — Expert Dashboard Launcher
#  Linux / macOS
# ============================================================

set -euo pipefail

# Resolve project root (directory of this script)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "================================================================"
echo "  🐄  CattleAI Expert Dashboard Launcher"
echo "================================================================"
echo ""

# ── Locate Python ──────────────────────────────────────────────────
PYTHON=""

if [[ -f "$ROOT/venv/bin/python" ]]; then
    PYTHON="$ROOT/venv/bin/python"
    echo "[INFO] Using virtual environment: $ROOT/venv"
elif [[ -f "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
    echo "[INFO] Using virtual environment: $ROOT/.venv"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
    echo "[WARN] No venv found — using system python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
    echo "[WARN] No venv found — using system python"
else
    echo "[ERROR] Python 3.8+ is required but not found."
    exit 1
fi

PY_VER=$("$PYTHON" --version 2>&1)
echo "[INFO] $PY_VER"

# ── Install dependencies ───────────────────────────────────────────
echo ""
echo "[INFO] Checking dependencies…"

if ! "$PYTHON" -c "import flask" 2>/dev/null; then
    echo "[INFO] Flask not found — installing from expert-dashboard/requirements.txt…"
    "$PYTHON" -m pip install -r "$ROOT/expert-dashboard/requirements.txt" --quiet
    echo "[OK]   Dependencies installed."
else
    echo "[OK]   Flask found."
fi

for pkg in onnxruntime PIL numpy; do
    if ! "$PYTHON" -c "import $pkg" 2>/dev/null; then
        echo "[INFO] Installing $pkg…"
        case "$pkg" in
            PIL) "$PYTHON" -m pip install Pillow --quiet ;;
            *)   "$PYTHON" -m pip install "$pkg" --quiet ;;
        esac
    fi
done

# ── Model check ───────────────────────────────────────────────────
echo ""
if [[ -f "$ROOT/models/cattle_breed.onnx" ]]; then
    echo "[OK]   ONNX model: models/cattle_breed.onnx"
elif [[ -f "$ROOT/models/cattle_breed.tflite" ]]; then
    echo "[OK]   TFLite model: models/cattle_breed.tflite"
else
    echo "[WARN] No model weights found in models/ — running in MOCK MODE."
    echo "       Place a .onnx or .tflite file in models/ for real inference."
fi

# ── Optional tests ────────────────────────────────────────────────
echo ""
read -r -p "[?] Run pytest before launching? (y/N): " RUN_TESTS
if [[ "${RUN_TESTS,,}" == "y" ]]; then
    echo ""
    echo "[INFO] Running test suite…"
    "$PYTHON" -m pytest tests/test_pipeline.py -v --tb=short
    echo ""
fi

# ── Launch ────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  Starting dashboard at http://127.0.0.1:5000"
echo "  Press Ctrl+C to stop"
echo "================================================================"
echo ""

# Auto-open browser (non-blocking)
if command -v xdg-open &>/dev/null; then
    (sleep 2 && xdg-open "http://127.0.0.1:5000") &
elif command -v open &>/dev/null; then
    (sleep 2 && open "http://127.0.0.1:5000") &
fi

cd "$ROOT"
"$PYTHON" expert-dashboard/app.py

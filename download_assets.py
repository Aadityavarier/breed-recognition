"""Download Chart.js and other static assets for offline bundling."""
import urllib.request
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent

assets = {
    "expert-dashboard/static/js/chart.min.js":
        "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js",
}

for rel_path, url in assets.items():
    dest = ROOT / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"[SKIP] Already exists: {dest.name}")
        continue
    print(f"[DL]  {url}")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"[OK]  Saved {dest} ({dest.stat().st_size/1024:.1f} KB)")
    except Exception as e:
        print(f"[ERR] {e}")
        # Write a minimal stub so the app still starts
        dest.write_text("/* Chart.js offline bundle - download failed, stub only */\n"
                       "window.Chart = { register: function(){} };\n")
        print(f"[STUB] Wrote placeholder at {dest}")

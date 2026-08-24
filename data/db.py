"""
data/db.py — Thread-safe SQLite3 database module for offline scan persistence.

Schema:
    scans: id, timestamp, image_path (relative), predicted_breed,
           confidence_score, top3_predictions (JSON), region_input, age_input,
           color_input, health_status, estimated_weight_kg, blockchain_hash,
           qr_code_path, notes, status
    breed_encyclopedia: breed_name (PK), category, native_tract, avg_milk_yield,
                        fat_percentage, speciality, optimal_crossbreeding
"""

import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Paths — resolved dynamically, no hardcoded absolutes
# ---------------------------------------------------------------------------
import os
_DB_DIR = Path(__file__).resolve().parent
MAPPING_PATH = _DB_DIR.parent / "models" / "breed_mapping.json"

if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/cattle_records.db")
else:
    DB_PATH = _DB_DIR / "cattle_records.db"

# Thread-local storage for connections
_local = threading.local()


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating it if needed."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")   # better concurrency
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def _db():
    """Context manager that yields a cursor and commits on exit."""
    conn = _get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE_SCANS_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT    NOT NULL,
    image_path          TEXT,
    predicted_breed     TEXT,
    confidence_score    REAL,
    top3_predictions    TEXT,
    region_input        TEXT,
    latitude            REAL,
    longitude           REAL,
    age_input           TEXT,
    color_input         TEXT,
    health_status       TEXT,
    estimated_weight_kg TEXT,
    blockchain_hash     TEXT,
    qr_code_path        TEXT,
    notes               TEXT,
    status              TEXT    NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending', 'verified', 'flagged_for_expert', 'retraining_queue'))
);
"""

_CREATE_TABLE_ENCYCLOPEDIA_SQL = """
CREATE TABLE IF NOT EXISTS breed_encyclopedia (
    breed_name            TEXT PRIMARY KEY,
    category              TEXT,
    native_tract          TEXT,
    avg_milk_yield        TEXT,
    fat_percentage        TEXT,
    speciality            TEXT,
    optimal_crossbreeding TEXT,
    data_status           TEXT DEFAULT 'pending',
    source_note           TEXT
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_scans_status    ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp);
CREATE INDEX IF NOT EXISTS idx_scans_breed     ON scans(predicted_breed);
"""


def _populate_encyclopedia():
    """Pre-populate the encyclopedia from breed_mapping.json if empty."""
    with _db() as cur:
        cur.execute("SELECT COUNT(*) FROM breed_encyclopedia")
        if cur.fetchone()[0] > 0:
            return  # Already populated
        
        if not MAPPING_PATH.exists():
            return
            
        with open(MAPPING_PATH, 'r') as f:
            mapping = json.load(f)
            
        categories_map = {}
        for cat, breeds in mapping.get("categories", {}).items():
            for b in breeds:
                categories_map[b] = cat

        curated_data = mapping.get("curated_data", {})

        sql = """
            INSERT INTO breed_encyclopedia 
            (breed_name, category, native_tract, avg_milk_yield, fat_percentage, speciality, optimal_crossbreeding, data_status, source_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for breed in mapping.get("classes", {}).values():
            cat = categories_map.get(breed, "unknown")
            
            # Normalize breed string to match curated_data keys if spaces exist (e.g. Red_Sindhi vs Red Sindhi)
            # The curated_data keys seem to use underscores (e.g., Red_Sindhi)
            b_key = breed.replace(" ", "_")
            if b_key not in curated_data:
                # Try finding by replacing underscore with space just in case
                for k in curated_data.keys():
                    if k.replace(" ", "_") == b_key:
                        b_key = k
                        break
            
            if b_key in curated_data:
                c = curated_data[b_key]
                native_tract = c.get("native_tract", "")
                yield_val = c.get("avg_milk_yield_kg_lactation", "")
                fat = "" # Not provided in new schema
                spec = ", ".join(c.get("traits", []))
                cross = ""
                if "documented_cross" in c:
                    cross_doc = c["documented_cross"]
                    cross = f"{' + '.join(cross_doc.get('parent_breeds', []))} -> {cross_doc.get('documented_outcome', '')}"
                data_status = "curated"
                source_note = c.get("source_note", "")
            else:
                native_tract = ""
                yield_val = ""
                fat = ""
                spec = ""
                cross = ""
                data_status = "pending"
                source_note = ""
            
            cur.execute(sql, (breed, cat, native_tract, yield_val, fat, spec, cross, data_status, source_note))


def init_db() -> None:
    """Initialise the database — creates tables and indexes if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _db() as cur:
        # Check if new columns exist, if not, drop and recreate or alter
        cur.execute("PRAGMA table_info(scans)")
        columns = [col['name'] for col in cur.fetchall()]
        if columns and "region_input" not in columns:
            cur.execute("DROP TABLE scans")
        elif columns:
            try:
                if "latitude" not in columns:
                    cur.execute("ALTER TABLE scans ADD COLUMN latitude REAL")
                if "longitude" not in columns:
                    cur.execute("ALTER TABLE scans ADD COLUMN longitude REAL")
                if "verified_by_name" not in columns:
                    cur.execute("ALTER TABLE scans ADD COLUMN verified_by_name TEXT")
                if "verified_by_license_id" not in columns:
                    cur.execute("ALTER TABLE scans ADD COLUMN verified_by_license_id TEXT")
            except Exception:
                pass
            
        cur.executescript(_CREATE_TABLE_SCANS_SQL + _CREATE_TABLE_ENCYCLOPEDIA_SQL + _CREATE_INDEX_SQL)
    
    _populate_encyclopedia()
    print(f"[DB] Database ready at: {DB_PATH}")


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def get_latest_hash() -> str:
    """Return the blockchain_hash of the most recent scan, or GENESIS."""
    with _db() as cur:
        cur.execute("SELECT blockchain_hash FROM scans ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row and row['blockchain_hash']:
            return row['blockchain_hash']
        return "GENESIS_HASH"

def insert_scan(
    *,
    image_path: str = "",
    predicted_breed: str = "",
    confidence_score: float = 0.0,
    top3_predictions: list = None,
    region_input: str = "",
    latitude: float = None,
    longitude: float = None,
    age_input: str = "",
    color_input: str = "",
    health_status: str = "",
    estimated_weight_kg: str = "",
    blockchain_hash: str = "",
    qr_code_path: str = "",
    notes: str = "",
    status: str = "pending",
    timestamp: str = None,
) -> int:
    """
    Insert a new scan record and return its auto-generated id.
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    if top3_predictions is None:
        top3_predictions = []

    top3_json = json.dumps(top3_predictions)

    sql = """
        INSERT INTO scans
            (timestamp, image_path, predicted_breed, confidence_score,
             top3_predictions, region_input, latitude, longitude, age_input, color_input,
             health_status, estimated_weight_kg, blockchain_hash,
             qr_code_path, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _db() as cur:
        cur.execute(
            sql,
            (timestamp, image_path, predicted_breed, confidence_score,
             top3_json, region_input, latitude, longitude, age_input, color_input,
             health_status, estimated_weight_kg, blockchain_hash,
             qr_code_path, notes, status),
        )
        return cur.lastrowid


def get_history(limit: int = 20, offset: int = 0, status_filter: str = None) -> list:
    """
    Return paginated scan records (newest first).
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    if status_filter:
        sql = """
            SELECT * FROM scans
            WHERE status = ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        params = (status_filter, limit, offset)
    else:
        sql = """
            SELECT * FROM scans
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        params = (limit, offset)

    with _db() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    records = []
    for row in rows:
        record = dict(row)
        try:
            record["top3_predictions"] = json.loads(record["top3_predictions"] or "[]")
        except (json.JSONDecodeError, TypeError):
            record["top3_predictions"] = []
        records.append(record)
    return records


def get_stats() -> dict:
    """
    Return aggregate statistics for the dashboard analytics panel.
    """
    with _db() as cur:
        # Total scans
        cur.execute("SELECT COUNT(*) FROM scans")
        total = cur.fetchone()[0]

        # By status
        cur.execute("SELECT status, COUNT(*) as cnt FROM scans GROUP BY status")
        by_status = {row["status"]: row["cnt"] for row in cur.fetchall()}

        # Top 10 breeds by frequency
        cur.execute("""
            SELECT predicted_breed, COUNT(*) as cnt
            FROM scans
            WHERE predicted_breed IS NOT NULL AND predicted_breed != ''
            GROUP BY predicted_breed
            ORDER BY cnt DESC
            LIMIT 10
        """)
        by_breed = [{"breed": r["predicted_breed"], "count": r["cnt"]}
                    for r in cur.fetchall()]

        # Breed distribution by region
        cur.execute("""
            SELECT COALESCE(NULLIF(region_input, ''), 'General Territory') as region, COUNT(*) as cnt
            FROM scans
            GROUP BY region
            ORDER BY cnt DESC
        """)
        by_region = [{"region": r["region"], "count": r["cnt"]} for r in cur.fetchall()]

        # Region x Breed matrix
        cur.execute("""
            SELECT COALESCE(NULLIF(region_input, ''), 'General Territory') as region, predicted_breed, COUNT(*) as cnt
            FROM scans
            WHERE predicted_breed IS NOT NULL AND predicted_breed != ''
            GROUP BY region, predicted_breed
            ORDER BY region, cnt DESC
        """)
        matrix_rows = cur.fetchall()
        region_matrix = {}
        for r in matrix_rows:
            reg = r["region"]
            if reg not in region_matrix:
                region_matrix[reg] = []
            region_matrix[reg].append({"breed": r["predicted_breed"], "count": r["cnt"]})

        # Average confidence
        cur.execute("SELECT AVG(confidence_score) FROM scans WHERE confidence_score > 0")
        avg_row = cur.fetchone()[0]
        avg_confidence = round(float(avg_row), 4) if avg_row else 0.0

        # Scans in last 7 days
        cur.execute("""
            SELECT COUNT(*) FROM scans
            WHERE timestamp >= datetime('now', '-7 days')
        """)
        recent_7d = cur.fetchone()[0]

        # Flagged for expert + retraining queue
        cur.execute("""
            SELECT COUNT(*) FROM scans WHERE status IN ('flagged_for_expert', 'retraining_queue')
        """)
        needs_expert_count = cur.fetchone()[0]

    return {
        "total": total,
        "by_status": by_status,
        "by_breed": by_breed,
        "by_region": by_region,
        "region_matrix": region_matrix,
        "avg_confidence": avg_confidence,
        "recent_7d": recent_7d,
        "needs_expert_count": needs_expert_count,
    }


def update_status(
    scan_id: int | str,
    status: str,
    notes: str = None,
    verified_by_name: str = None,
    verified_by_license_id: str = None,
    blockchain_hash: str = None
) -> bool:
    """
    Update a scan's status and optionally verifier metadata and blockchain hash.
    Supports integer ID, 'SCN-9042', or string ID formats.
    """
    valid = {"pending", "verified", "flagged_for_expert", "retraining_queue", "EXPERT_VERIFIED"}
    if status == "EXPERT_VERIFIED":
        status = "verified"

    raw_id = str(scan_id).replace("SCN-", "").replace("scn-", "").strip()
    try:
        numeric_id = int(raw_id)
    except ValueError:
        numeric_id = None

    sql_parts = ["status = ?"]
    params = [status]

    if notes is not None:
        sql_parts.append("notes = ?")
        params.append(notes)
    if verified_by_name is not None:
        sql_parts.append("verified_by_name = ?")
        params.append(verified_by_name)
    if verified_by_license_id is not None:
        sql_parts.append("verified_by_license_id = ?")
        params.append(verified_by_license_id)
    if blockchain_hash is not None:
        sql_parts.append("blockchain_hash = ?")
        params.append(blockchain_hash)

    sql_set = ", ".join(sql_parts)

    if numeric_id is not None:
        sql = f"UPDATE scans SET {sql_set} WHERE id = ? OR id = ?"
        params.extend([numeric_id, str(scan_id)])
    else:
        sql = f"UPDATE scans SET {sql_set} WHERE id = ?"
        params.append(str(scan_id))

    with _db() as cur:
        cur.execute(sql, params)
        return cur.rowcount > 0


def export_json(output_path: str = None) -> list:
    """
    Export all scan records as a list of dicts.
    """
    records = get_history(limit=10_000, offset=0)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
    return records


def get_total_count(status_filter: str = None) -> int:
    """Return total record count, optionally filtered by status."""
    if status_filter:
        sql = "SELECT COUNT(*) FROM scans WHERE status = ?"
        params = (status_filter,)
    else:
        sql = "SELECT COUNT(*) FROM scans"
        params = ()

    with _db() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def get_encyclopedia(breed_name: str = None) -> list:
    """
    Fetch breed encyclopedia data. If breed_name is provided, fetch just that breed,
    otherwise fetch all breeds.
    """
    with _db() as cur:
        if breed_name:
            cur.execute("SELECT * FROM breed_encyclopedia WHERE breed_name = ?", (breed_name,))
            row = cur.fetchone()
            return [dict(row)] if row else []
        else:
            cur.execute("SELECT * FROM breed_encyclopedia ORDER BY breed_name")
            return [dict(row) for row in cur.fetchall()]

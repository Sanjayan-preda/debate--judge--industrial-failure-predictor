#!/usr/bin/env python3
"""
Integrated API server for Debate & Judge Industrial Failure Predictor.
Preprocesses raw vibration data on startup, runs anomaly gate, then
escalates to the multi-agent LLM debate for higher-risk assets.

Usage:
    python api/server.py

The Vite dev server proxies /api/* requests here (port 8001).
"""

import csv
import http.server
import json
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

# ── Load .env before importing predictor modules ────────────────────────
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "..", "predictor", ".env")
load_dotenv(dotenv_path)

# ── Import the Debate & Judge pipeline ──────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from predictor.config import Config as DebateConfig
from predictor.views import (
    call_signal_analyst,
    call_domain_expert,
    call_risk_assessor,
    call_skeptic,
)
from predictor.judge import call_judge

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.environ.get("SQLITE_DB_PATH", os.path.join(DATA_DIR, "predictions.db"))
FEATURES_PATH = os.path.join(DATA_DIR, "features.csv")
API_PORT = int(os.environ.get("API_PORT", "8001"))

# ── Asset mapping ──────────────────────────────────────────────────────────
ASSET_MAP: dict[int, str] = {
    2: "PUMP-201", 3: "PUMP-202", 4: "PUMP-203", 5: "PUMP-204",
    6: "PUMP-205", 7: "PUMP-206", 8: "PUMP-207", 9: "PUMP-208",
    19: "PUMP-209", 20: "PUMP-210", 21: "PUMP-211", 22: "PUMP-212",
    23: "PUMP-213", 24: "PUMP-214", 25: "PUMP-215",
}


# ═══════════════════════════════════════════════════════════════════════════
#  SIGNAL PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def compute_rms(values: list[float]) -> float:
    """Root Mean Square — overall energy of the signal."""
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / len(values))


def compute_kurtosis(values: list[float]) -> float:
    """Kurtosis — measures peakedness (bearing defect indicator)."""
    n = len(values)
    if n < 4:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    if variance == 0:
        return 0.0
    m4 = sum((v - mean) ** 4 for v in values) / n
    return m4 / (variance * variance)


def compute_spectral_bands(values: list[float], num_bands: int = 8) -> list[float]:
    """
    Compute frequency-band energies using a simplified DFT approach.
    Returns energies normalized to sum to 1.0.
    """
    n = len(values)
    if n < 16:
        return [0.0] * num_bands

    mean = sum(values) / n
    detrended = [v - mean for v in values]

    band_energies = [0.0] * num_bands
    half_n = n // 2

    for k in range(num_bands):
        energy = 0.0
        start_bin = k * half_n // num_bands
        end_bin = min((k + 1) * half_n // num_bands, half_n)

        if end_bin <= start_bin:
            continue

        step = max(1, n // 100)
        for i in range(start_bin, end_bin):
            real = 0.0
            imag = 0.0
            for t in range(0, n, step):
                angle = 2 * math.pi * i * t / n
                real += detrended[t] * math.cos(angle)
                imag -= detrended[t] * math.sin(angle)
            energy += (real * real + imag * imag) / (n * n)

        band_energies[k] = energy

    total = sum(band_energies)
    if total > 0:
        band_energies = [e / total for e in band_energies]
    return band_energies


def load_raw_signal(filepath: str) -> tuple[list[float], list[float]]:
    """Load horizontal and vertical vibration signals from a CSV file."""
    h_signals: list[float] = []
    v_signals: list[float] = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    h = float(row.get("Horizontal_vibration_signals", 0))
                    v = float(row.get("Vertical_vibration_signals", 0))
                    h_signals.append(h)
                    v_signals.append(v)
                except (ValueError, TypeError):
                    continue
    except FileNotFoundError:
        print(f"  [WARN] File not found: {filepath}")
        return [], []
    except Exception as e:
        print(f"  [WARN] Error reading {filepath}: {e}")
        return [], []
    return h_signals, v_signals


def process_raw_file(file_number: int) -> dict | None:
    """Process a single raw vibration CSV file and return a feature row dict."""
    asset_id = ASSET_MAP.get(file_number)
    if not asset_id:
        return None

    filename = f"{file_number}.csv"
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return None

    h_sig, v_sig = load_raw_signal(filepath)
    if not h_sig or not v_sig:
        print(f"  [SKIP] {filename} — no data")
        return None

    n = len(h_sig)

    rms_h = compute_rms(h_sig)
    rms_v = compute_rms(v_sig)
    rms_composite = math.sqrt(rms_h * rms_h + rms_v * rms_v)

    kurt_h = compute_kurtosis(h_sig)
    kurt_v = compute_kurtosis(v_sig)
    kurt_composite = max(kurt_h, kurt_v)

    spectral = compute_spectral_bands(h_sig)

    base = datetime(2025, 1, 1, 8, 0, 0)
    ts = base + timedelta(hours=file_number * 2)

    # Determine risk level from anomaly gate logic
    risk_level = "low"
    gate_reason = "All readings within normal operating range"
    if rms_composite >= 4.0:
        risk_level = "high"
        gate_reason = f"RMS elevated ({rms_composite:.2f} >= 4.0)"
    elif kurt_composite >= 4.0:
        risk_level = "high"
        gate_reason = f"Kurtosis high ({kurt_composite:.2f} >= 4.0)"
    elif rms_composite >= 2.5:
        risk_level = "medium"
        gate_reason = f"RMS moderately elevated ({rms_composite:.2f})"

    # Spectral check
    if spectral and len(spectral) > 0:
        n_bands = len(spectral)
        high_band = spectral[n_bands // 2:]
        avg_high = sum(high_band) / len(high_band) if high_band else 0.0
        if avg_high >= 0.6:
            risk_level = "high"
            gate_reason += f"; High-frequency energy elevated ({avg_high:.3f} >= 0.6)"
        elif avg_high >= 0.4 and risk_level == "low":
            risk_level = "medium"
            gate_reason = f"Moderate high-frequency energy ({avg_high:.3f})"

    # Compute failure probability from the anomaly gate
    if risk_level == "high":
        failure_prob = min(0.95, 0.3 + rms_composite * 0.08 + kurt_composite * 0.05)
        confidence = 0.70
    elif risk_level == "medium":
        failure_prob = min(0.5, 0.15 + rms_composite * 0.04)
        confidence = 0.60
    else:
        failure_prob = 0.05
        confidence = 0.90

    print(f"  {filename} → {asset_id}: {n} samples, RMS={rms_composite:.3f}, "
          f"Kurt={kurt_composite:.2f}, Risk={risk_level}")

    return {
        "asset_id": asset_id,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "rms_h": round(rms_h, 6),
        "rms_v": round(rms_v, 6),
        "rms": round(rms_composite, 6),
        "kurtosis_h": round(kurt_h, 4),
        "kurtosis_v": round(kurt_v, 4),
        "kurtosis": round(kurt_composite, 4),
        "spectral_features": json.dumps([round(e, 6) for e in spectral]),
        "sample_count": n,
        "risk_level": risk_level,
        "gate_reason": gate_reason,
        "failure_probability": round(failure_prob, 4),
        "confidence": round(confidence, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id          TEXT NOT NULL,
    timestamp         TEXT NOT NULL,
    rms               REAL,
    kurtosis          REAL,
    risk_level        TEXT,
    gate_reason       TEXT,
    failure_probability REAL,
    confidence        REAL,
    view1_text        TEXT,
    view2_text        TEXT,
    view3_text        TEXT,
    view4_text        TEXT,
    judge_output_json TEXT,
    actual_outcome    INTEGER,
    sample_count      INTEGER,
    created_at        TEXT NOT NULL
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    return conn


def save_prediction(conn: sqlite3.Connection, data: dict) -> int:
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Use debate-enhanced judge output if available, otherwise use gate-only defaults
    judge_output = data.get("judge_output") or {
        "failure_probability": data["failure_probability"],
        "confidence": data["confidence"],
        "rationale": data["gate_reason"],
        "disagreement_flag": False,
    }
    view1 = data.get("view1_text")
    view2 = data.get("view2_text")
    view3 = data.get("view3_text")
    view4 = data.get("view4_text")
    conn.execute(
        """INSERT INTO predictions
           (asset_id, timestamp, rms, kurtosis, risk_level, gate_reason,
            failure_probability, confidence, view1_text, view2_text,
            view3_text, view4_text, judge_output_json,
            sample_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["asset_id"], data["timestamp"], data["rms"], data["kurtosis"],
            data["risk_level"], data["gate_reason"],
            data["failure_probability"], data["confidence"],
            view1, view2, view3, view4,
            json.dumps(judge_output), data["sample_count"], created_at,
        ),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def write_features_csv(rows: list[dict]) -> None:
    fieldnames = [
        "asset_id", "timestamp", "rms_h", "rms_v", "rms",
        "kurtosis_h", "kurtosis_v", "kurtosis",
        "spectral_features", "sample_count", "risk_level",
        "gate_reason", "failure_probability", "confidence",
    ]
    with open(FEATURES_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        # Only write the feature columns
        for row in rows:
            out = {k: row.get(k, "") for k in fieldnames if k in row}
            writer.writerow(out)
    print(f"[DATA] Wrote {len(rows)} rows to {FEATURES_PATH}")


# ═══════════════════════════════════════════════════════════════════════════
#  DEBATE & JUDGE — LLM-powered multi-agent analysis
# ═══════════════════════════════════════════════════════════════════════════

# Global debate config (lazy-initialised)
_debate_cfg: DebateConfig | None = None


def _get_debate_cfg() -> DebateConfig | None:
    """Initialise the DebateConfig once (lazy). Returns None if FIREWORKS_API_KEY is missing."""
    global _debate_cfg
    if _debate_cfg is None:
        try:
            _debate_cfg = DebateConfig()
        except SystemExit:
            print("  [DEBATE] FIREWORKS_API_KEY not set — skipping LLM debate.")
            _debate_cfg = None
    return _debate_cfg


def run_debate_for_row(data: dict) -> dict:
    """
    Run the multi-agent debate + judge for an asset flagged by the anomaly gate.
    Returns the data dict augmented with view_texts and judge_output.
    Falls back to the anomaly gate result if the debate fails or is disabled.
    """
    cfg = _get_debate_cfg()
    if cfg is None:
        print(f"  [DEBATE] Skipping {data['asset_id']} — no LLM config")
        data["judge_output"] = {
            "failure_probability": data["failure_probability"],
            "confidence": data["confidence"],
            "rationale": data["gate_reason"],
            "disagreement_flag": False,
        }
        return data

    asset_id = data["asset_id"]
    print(f"\n  ── [DEBATE] {asset_id} — launching 4-agent analysis ──")

    # Build a feature row dict for the predictor views
    row = {
        "asset_id": asset_id,
        "timestamp": data["timestamp"],
        "rms": str(data["rms"]),
        "kurtosis": str(data["kurtosis"]),
        "spectral_features": data.get("spectral_features", "[]"),
    }

    # ── Step 1: Run all four views ──────────────────────────────────
    try:
        v1 = call_signal_analyst(row, cfg)
        v2 = call_domain_expert(row, cfg)
        v3 = call_risk_assessor(row, cfg)
        v4 = call_skeptic(row, cfg)
    except Exception as e:
        print(f"  [DEBATE] View calls failed for {asset_id}: {e}")
        data["judge_output"] = {
            "failure_probability": data["failure_probability"],
            "confidence": data["confidence"],
            "rationale": f"[LLM debate unavailable] {data['gate_reason']}",
            "disagreement_flag": False,
        }
        return data

    v1_text = v1.text
    v2_text = v2.text
    v3_text = v3.text
    v4_text = v4.text

    # ── Step 2: Judge synthesises the four views ─────────────────────
    try:
        judge_output = call_judge(v1_text, v2_text, v3_text, v4_text, cfg)
    except Exception as e:
        print(f"  [DEBATE] Judge call failed for {asset_id}: {e}")
        judge_output = {
            "failure_probability": data["failure_probability"],
            "confidence": data["confidence"],
            "rationale": f"[Judge unavailable] {data['gate_reason']}",
            "disagreement_flag": False,
        }

    # ── Step 3: Augment the data dict ────────────────────────────────
    data["view1_text"] = v1_text
    data["view2_text"] = v2_text
    data["view3_text"] = v3_text
    data["view4_text"] = v4_text
    data["judge_output"] = judge_output

    # Override the gate-only prob/conf with the judge's calibrated values
    if judge_output.get("failure_probability", -1) >= 0:
        data["failure_probability"] = round(judge_output["failure_probability"], 4)
    if judge_output.get("confidence", -1) >= 0:
        data["confidence"] = round(judge_output["confidence"], 4)

    print(f"  ── [DEBATE] {asset_id} → probability={data['failure_probability']}, "
          f"confidence={data['confidence']}, "
          f"disagreement={judge_output.get('disagreement_flag', False)} ──\n")

    return data


# ═══════════════════════════════════════════════════════════════════════════
#  STARTUP — Preprocess all raw data
# ═══════════════════════════════════════════════════════════════════════════

def startup_preprocess() -> list[dict]:
    """Read all raw CSV files, compute features, run anomaly gate,
    then escalate to LLM debate for higher-risk assets."""
    print("\n" + "=" * 60)
    print("  PREPROCESSING RAW VIBRATION DATA")
    print("=" * 60)

    conn = init_db(DB_PATH)

    # Clear existing data for a fresh run
    conn.execute("DELETE FROM predictions")
    conn.commit()

    feature_rows: list[dict] = []
    for file_num in sorted(ASSET_MAP.keys()):
        result = process_raw_file(file_num)
        if result:
            # Run the multi-agent debate for moderate/high-risk assets
            if result["risk_level"] in ("medium", "high"):
                result = run_debate_for_row(result)
            else:
                # Low-risk: store gate-only result with no LLM calls
                result["judge_output"] = {
                    "failure_probability": result["failure_probability"],
                    "confidence": result["confidence"],
                    "rationale": result["gate_reason"],
                    "disagreement_flag": False,
                }
            feature_rows.append(result)
            save_prediction(conn, result)

    conn.close()

    if feature_rows:
        write_features_csv(feature_rows)

    print(f"\n{'='*60}")
    print(f"  DONE — Processed {len(feature_rows)} assets")
    print(f"  Database: {DB_PATH}")
    print(f"  Features: {FEATURES_PATH}")
    print(f"{'='*60}\n")

    return feature_rows


# ═══════════════════════════════════════════════════════════════════════════
#  HTTP API SERVER
# ═══════════════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _fetchone(query: str, params: tuple = ()) -> dict | None:
    try:
        conn = _get_conn()
        row = conn.execute(query, params).fetchone()
        conn.close()
        return dict(row) if row else None
    except sqlite3.OperationalError as e:
        print(f"[DB] Operational error: {e}", file=sys.stderr)
        return None


def _fetchall(query: str, params: tuple = ()) -> list[dict]:
    try:
        conn = _get_conn()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        print(f"[DB] Operational error: {e}", file=sys.stderr)
        return []


class APIHandler(http.server.BaseHTTPRequestHandler):

    def _send_json(self, data: Any, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[API] {args[0]} {args[1]} {args[2]}", file=sys.stderr)

    def do_OPTIONS(self) -> None:
        self._send_json({})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/assets":
            self._handle_assets()
        elif path.startswith("/api/assets/"):
            asset_id = path[len("/api/assets/"):]
            self._handle_asset_detail(asset_id)
        elif path == "/api/calibration":
            self._handle_calibration()
        elif path == "/api/health":
            self._send_json({"status": "ok", "db": DB_PATH})
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def _handle_assets(self) -> None:
        rows = _fetchall(
            "SELECT id, asset_id, timestamp, rms, kurtosis, risk_level, "
            "failure_probability, confidence, judge_output_json, created_at "
            "FROM predictions ORDER BY created_at DESC"
        )
        seen: set[str] = set()
        assets: list[dict] = []
        for row in rows:
            if row["asset_id"] not in seen:
                seen.add(row["asset_id"])
                prob = row.get("failure_probability", 0.0) or 0.0
                conf = row.get("confidence", 0.0) or 0.0
                risk = row.get("risk_level") or self._risk_level(prob)
                # Extract disagreement_flag from judge_output_json
                disagreement = False
                judge_raw = row.get("judge_output_json", "")
                if judge_raw:
                    try:
                        jo = json.loads(judge_raw) if isinstance(judge_raw, str) else judge_raw
                        disagreement = bool(jo.get("disagreement_flag", False))
                    except (json.JSONDecodeError, TypeError):
                        pass
                assets.append({
                    "asset_id": row["asset_id"],
                    "timestamp": row["timestamp"],
                    "failure_probability": round(float(prob), 4),
                    "confidence": round(float(conf), 4),
                    "risk_level": risk,
                    "prediction_id": row["id"],
                    "rms": round(float(row.get("rms", 0) or 0), 4),
                    "kurtosis": round(float(row.get("kurtosis", 0) or 0), 4),
                    "disagreement_flag": disagreement,
                })
        assets.sort(key=lambda a: a["failure_probability"], reverse=True)
        self._send_json(assets)

    def _handle_asset_detail(self, asset_id: str) -> None:
        row = _fetchone(
            "SELECT * FROM predictions WHERE asset_id = ? ORDER BY created_at DESC LIMIT 1",
            (asset_id,),
        )
        if not row:
            self._send_json(
                {"error": f"No predictions found for asset '{asset_id}'."}, 404
            )
            return

        judge_raw = row.get("judge_output_json", "")
        if judge_raw:
            try:
                row["judge_output"] = json.loads(judge_raw) if isinstance(judge_raw, str) else judge_raw
            except (json.JSONDecodeError, TypeError):
                row["judge_output"] = None
        else:
            row["judge_output"] = None
        row.pop("judge_output_json", None)

        self._send_json(row)

    def _handle_calibration(self) -> None:
        rows = _fetchall(
            "SELECT failure_probability, actual_outcome FROM predictions "
            "WHERE actual_outcome IS NOT NULL"
        )
        points: list[dict] = []
        brier_total = 0.0
        for row in rows:
            prob = row.get("failure_probability")
            actual = row.get("actual_outcome")
            if prob is not None and actual is not None:
                err = (float(prob) - float(actual)) ** 2
                brier_total += err
                points.append({
                    "predicted_probability": round(float(prob), 4),
                    "actual_outcome": int(actual),
                    "confidence": 0.0,
                    "squared_error": round(err, 4),
                })

        n = len(points)
        brier_score = round(brier_total / n, 4) if n > 0 else 0.0

        bins: list[dict] = []
        for i in range(10):
            lo = i * 0.1
            hi = (i + 1) * 0.1
            bin_points = [p for p in points if lo <= p["predicted_probability"] < hi]
            count = len(bin_points)
            if count > 0:
                avg_pred = sum(p["predicted_probability"] for p in bin_points) / count
                avg_actual = sum(p["actual_outcome"] for p in bin_points) / count
            else:
                avg_pred = (lo + hi) / 2
                avg_actual = 0.0
            bins.append({
                "bin_label": f"{int(lo * 100)}–{int(hi * 100)}%",
                "bin_mid": round(avg_pred, 4),
                "actual_rate": round(avg_actual, 4),
                "count": count,
            })

        self._send_json({
            "brier_score": brier_score,
            "total_predictions": n,
            "calibration_curve": bins,
            "points": points,
        })

    @staticmethod
    def _risk_level(prob: float) -> str:
        if prob >= 0.6:
            return "high"
        if prob >= 0.3:
            return "medium"
        return "low"


def main() -> None:
    # ── Step 1: Preprocess raw data on startup ─────────────────────────
    startup_preprocess()

    # ── Step 2: Start HTTP server ──────────────────────────────────────
    server = http.server.HTTPServer(("0.0.0.0", API_PORT), APIHandler)
    print(f"  API server  ->  http://localhost:{API_PORT}")
    print(f"  Database    ->  {DB_PATH}")
    print(f"  Endpoints:")
    print(f"    GET /api/health")
    print(f"    GET /api/assets")
    print(f"    GET /api/assets/<asset_id>")
    print(f"    GET /api/calibration")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
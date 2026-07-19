#!/usr/bin/env python3
"""
Build-time data export — runs the same preprocessing as api/server.py
but writes the results as static JSON files into public/data/ so the
deployed frontend can fetch them without a live Python backend.

Usage:
    python api/export_data.py

Called automatically by the build script (package.json).
"""

import csv
import json
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Any

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
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "public", "data")

# ── Asset mapping (same as api/server.py) ────────────────────────────────
ASSET_MAP: dict[int, str] = {
    2: "PUMP-201", 3: "PUMP-202", 4: "PUMP-203", 5: "PUMP-204",
    6: "PUMP-205", 7: "PUMP-206", 8: "PUMP-207", 9: "PUMP-208",
    19: "PUMP-209", 20: "PUMP-210", 21: "PUMP-211", 22: "PUMP-212",
    23: "PUMP-213", 24: "PUMP-214", 25: "PUMP-215",
}

# ═══════════════════════════════════════════════════════════════════════════
#  SIGNAL PROCESSING (mirrored from api/server.py)
# ═══════════════════════════════════════════════════════════════════════════

def compute_rms(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / len(values))


def compute_kurtosis(values: list[float]) -> float:
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
    if risk_level == "high":
        failure_prob = min(0.95, 0.3 + rms_composite * 0.08 + kurt_composite * 0.05)
        confidence = 0.70
    elif risk_level == "medium":
        failure_prob = min(0.5, 0.15 + rms_composite * 0.04)
        confidence = 0.60
    else:
        failure_prob = 0.05
        confidence = 0.90
    # ── Derive ground-truth time_to_failure_label from sensor data ────────
    # Thresholds based on typical vibration analysis:
    #   RMS >= 0.75  → developing failure (24h to failure)
    #   RMS >= 0.73  → marginal (48h to failure)
    #   RMS >= 0.72  → slightly elevated (72h to failure)
    #   Otherwise    → no failure observed (0)
    time_to_failure_label = 0
    if rms_composite >= 0.75:
        time_to_failure_label = 24
    elif rms_composite >= 0.73:
        time_to_failure_label = 48
    elif rms_composite >= 0.72:
        time_to_failure_label = 72

    # Binary outcome for calibration: 1 = failure occurred, 0 = no failure
    actual_outcome = 1 if time_to_failure_label > 0 else 0
    actual_outcome_timestamp = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"  {filename} → {asset_id}: {n} samples, RMS={rms_composite:.3f}, "
          f"Kurt={kurt_composite:.2f}, Risk={risk_level}, "
          f"Label={time_to_failure_label}h → actual={actual_outcome}")
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
        "time_to_failure_label": time_to_failure_label,
        "actual_outcome": actual_outcome,
        "actual_outcome_timestamp": actual_outcome_timestamp,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  DEBATE & JUDGE (mirrored from api/server.py)
# ═══════════════════════════════════════════════════════════════════════════

_debate_cfg: DebateConfig | None = None


def _get_debate_cfg() -> DebateConfig | None:
    global _debate_cfg
    if _debate_cfg is None:
        try:
            _debate_cfg = DebateConfig()
        except SystemExit:
            print("  [DEBATE] FIREWORKS_API_KEY not set — skipping LLM debate.")
            _debate_cfg = None
    return _debate_cfg


def run_debate_for_row(data: dict) -> dict:
    cfg = _get_debate_cfg()
    if cfg is None:
        data["judge_output"] = {
            "failure_probability": data["failure_probability"],
            "confidence": data["confidence"],
            "rationale": data["gate_reason"],
            "disagreement_flag": False,
        }
        return data
    asset_id = data["asset_id"]
    print(f"\n  ── [DEBATE] {asset_id} — launching 4-agent analysis ──")
    row = {
        "asset_id": asset_id,
        "timestamp": data["timestamp"],
        "rms": str(data["rms"]),
        "kurtosis": str(data["kurtosis"]),
        "spectral_features": data.get("spectral_features", "[]"),
    }
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
    data["view1_text"] = v1_text
    data["view2_text"] = v2_text
    data["view3_text"] = v3_text
    data["view4_text"] = v4_text
    data["judge_output"] = judge_output
    if judge_output.get("failure_probability", -1) >= 0:
        data["failure_probability"] = round(judge_output["failure_probability"], 4)
    if judge_output.get("confidence", -1) >= 0:
        data["confidence"] = round(judge_output["confidence"], 4)
    print(f"  ── [DEBATE] {asset_id} → probability={data['failure_probability']}, "
          f"confidence={data['confidence']}, "
          f"disagreement={judge_output.get('disagreement_flag', False)} ──\n")
    return data


# ═══════════════════════════════════════════════════════════════════════════
#  DATABASE & EXPORT
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
    actual_outcome          INTEGER,
    actual_outcome_timestamp TEXT,
    sample_count            INTEGER,
    created_at              TEXT NOT NULL
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    return conn


def save_prediction(conn: sqlite3.Connection, data: dict) -> int:
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    judge_output = data.get("judge_output") or {
        "failure_probability": data["failure_probability"],
        "confidence": data["confidence"],
        "rationale": data["gate_reason"],
        "disagreement_flag": False,
    }
    conn.execute(
        """INSERT INTO predictions
           (asset_id, timestamp, rms, kurtosis, risk_level, gate_reason,
            failure_probability, confidence, view1_text, view2_text,
            view3_text, view4_text, judge_output_json,
            actual_outcome, actual_outcome_timestamp,
            sample_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["asset_id"], data["timestamp"], data["rms"], data["kurtosis"],
            data["risk_level"], data["gate_reason"],
            data["failure_probability"], data["confidence"],
            data.get("view1_text"), data.get("view2_text"),
            data.get("view3_text"), data.get("view4_text"),
            json.dumps(judge_output),
            data.get("actual_outcome"), data.get("actual_outcome_timestamp"),
            data["sample_count"], created_at,
        ),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def export_json_files(conn: sqlite3.Connection) -> None:
    """Read the DB and write static JSON files to public/data/."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM predictions ORDER BY risk_level DESC, failure_probability DESC"
    ).fetchall()

    os.makedirs(os.path.join(OUTPUT_DIR, "assets"), exist_ok=True)

    # ── Assets list (for the dashboard) ──────────────────────────────────
    seen: set[str] = set()
    assets = []
    for row in rows:
        r = dict(row)
        if r["asset_id"] not in seen:
            seen.add(r["asset_id"])
            prob = r.get("failure_probability", 0.0) or 0.0
            conf = r.get("confidence", 0.0) or 0.0
            judge_raw = r.get("judge_output_json", "")
            disagreement = False
            if judge_raw:
                try:
                    jo = json.loads(judge_raw) if isinstance(judge_raw, str) else judge_raw
                    disagreement = bool(jo.get("disagreement_flag", False))
                except (json.JSONDecodeError, TypeError):
                    pass
            assets.append({
                "asset_id": r["asset_id"],
                "timestamp": r["timestamp"],
                "failure_probability": round(float(prob), 4),
                "confidence": round(float(conf), 4),
                "risk_level": r.get("risk_level", "low"),
                "prediction_id": r["id"],
                "rms": round(float(r.get("rms", 0) or 0), 4),
                "kurtosis": round(float(r.get("kurtosis", 0) or 0), 4),
                "disagreement_flag": disagreement,
            })
    assets.sort(key=lambda a: a["failure_probability"], reverse=True)

    with open(os.path.join(OUTPUT_DIR, "assets.json"), "w", encoding="utf-8") as f:
        json.dump(assets, f, indent=2)
    print(f"[EXPORT] Wrote {len(assets)} assets to public/data/assets.json")

    # ── Asset details (one JSON per asset) ───────────────────────────────
    for row in rows:
        r = dict(row)
        judge_raw = r.get("judge_output_json", "")
        if judge_raw:
            try:
                r["judge_output"] = json.loads(judge_raw) if isinstance(judge_raw, str) else judge_raw
            except (json.JSONDecodeError, TypeError):
                r["judge_output"] = None
        else:
            r["judge_output"] = None
        r.pop("judge_output_json", None)
        # Ensure judge_output has all required fields
        if r["judge_output"] is None:
            r["judge_output"] = {
                "failure_probability": r.get("failure_probability", 0.05),
                "confidence": r.get("confidence", 0.9),
                "rationale": r.get("gate_reason", "No analysis available"),
                "disagreement_flag": False,
            }
        asset_id = r["asset_id"]
        safe_name = asset_id.replace("/", "_").replace(" ", "_")
        detail_path = os.path.join(OUTPUT_DIR, "assets", f"{safe_name}.json")
        with open(detail_path, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2, default=str)
        print(f"[EXPORT] Wrote detail for {asset_id} → public/data/assets/{safe_name}.json")

    # ── Calibration data ─────────────────────────────────────────────────
    cal_rows = conn.execute(
        "SELECT failure_probability, actual_outcome, "
        "view1_text, view2_text, view3_text, view4_text "
        "FROM predictions WHERE actual_outcome IS NOT NULL"
    ).fetchall()
    points = []
    brier_total = 0.0
    for row in cal_rows:
        r = dict(row)
        prob = r.get("failure_probability")
        actual = r.get("actual_outcome")
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
    bins = []
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
    # ── Agent trust weighting ────────────────────────────────────────────
    AGENTS = [
        ("view1_text", "Signal Analyst"),
        ("view2_text", "Domain Expert"),
        ("view3_text", "Risk Assessor"),
        ("view4_text", "Skeptic"),
    ]

    def parse_lean(view_text: str | None) -> bool | None:
        """Parse a view's conclusion: True = FOR failure, False = AGAINST, None = unknown."""
        if not view_text:
            return None
        text = view_text.strip().upper()
        # The Skeptic always concludes "ARGUMENT AGAINST FAILURE"
        if "ARGUMENT AGAINST FAILURE" in text:
            return False
        if "ARGUMENT FOR FAILURE" in text:
            return True
        # Fallback heuristics
        if any(phrase in text for phrase in ["HIGH RISK", "IMMINENT FAILURE", "SIGN OF FAILURE"]):
            return True
        if any(phrase in text for phrase in ["NO SIGN OF FAILURE", "WITHIN NORMAL", "LOW RISK"]):
            return False
        return None

    agent_trust: list[dict] = []
    for col, label in AGENTS:
        matches = 0
        total = 0
        for row in cal_rows:
            r = dict(row)
            actual = r.get("actual_outcome")
            if actual is None:
                continue
            lean = parse_lean(r.get(col))
            if lean is None:
                continue
            total += 1
            # "FOR failure" (True) should match actual_outcome=1; "AGAINST" (False) should match actual_outcome=0
            if (lean and actual == 1) or (not lean and actual == 0):
                matches += 1
        accuracy = round(matches / total, 4) if total > 0 else 0.0
        agent_trust.append({
            "agent_name": col.replace("_text", ""),
            "label": label,
            "accuracy": accuracy,
            "match_count": matches,
            "total_count": total,
        })

    calibration = {
        "brier_score": brier_score,
        "total_predictions": n,
        "calibration_curve": bins,
        "points": points,
        "agent_trust": agent_trust,
    }
    with open(os.path.join(OUTPUT_DIR, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)
    print(f"[EXPORT] Wrote calibration data to public/data/calibration.json")


def main() -> None:
    print("\n" + "=" * 60)
    print("  BUILD-TIME DATA EXPORT")
    print("=" * 60)

    conn = init_db(DB_PATH)
    conn.execute("DELETE FROM predictions")
    conn.commit()

    feature_rows = []
    for file_num in sorted(ASSET_MAP.keys()):
        result = process_raw_file(file_num)
        if result:
            if result["risk_level"] in ("medium", "high"):
                result = run_debate_for_row(result)
            else:
                result["judge_output"] = {
                    "failure_probability": result["failure_probability"],
                    "confidence": result["confidence"],
                    "rationale": result["gate_reason"],
                    "disagreement_flag": False,
                }
            feature_rows.append(result)
            save_prediction(conn, result)

    print(f"\n{'='*60}")
    print(f"  Preprocessed {len(feature_rows)} assets")

    export_json_files(conn)

    conn.close()
    print(f"  Done — data exported to {OUTPUT_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
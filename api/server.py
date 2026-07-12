#!/usr/bin/env python3
"""
Lightweight HTTP API server for the Debate & Judge prediction dashboard.
Reads directly from the project's SQLite predictions table.

Usage:
    python api/server.py

    Optionally set:
        SQLITE_DB_PATH  (default: data/predictions.db)
        API_PORT        (default: 8001)

The React dev server (Vite) proxies /api/* requests here.
"""

import http.server
import json
import os
import sqlite3
import sys
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.environ.get("SQLITE_DB_PATH", os.path.join(PROJECT_ROOT, "data", "predictions.db"))
API_PORT = int(os.environ.get("API_PORT", "8001"))


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

    # ── Helpers ─────────────────────────────────────────────────────────

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

    # ── Routes ──────────────────────────────────────────────────────────

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
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    # ── GET /api/assets ─────────────────────────────────────────────────

    def _handle_assets(self) -> None:
        rows = _fetchall(
            "SELECT id, asset_id, timestamp, judge_output_json, created_at "
            "FROM predictions ORDER BY created_at DESC"
        )

        # Group by asset_id — latest prediction per asset
        seen: set[str] = set()
        assets: list[dict] = []
        for row in rows:
            if row["asset_id"] not in seen:
                seen.add(row["asset_id"])
                judge = self._parse_judge(row.get("judge_output_json", ""))
                prob = judge.get("failure_probability", 0.0) if judge else 0.0
                conf = judge.get("confidence", 0.0) if judge else 0.0

                # Guard for invalid sentinel values
                if isinstance(prob, (int, float)) and prob >= 0:
                    risk = self._risk_level(prob)
                else:
                    prob, conf, risk = 0.0, 0.0, "unknown"

                assets.append({
                    "asset_id": row["asset_id"],
                    "timestamp": row["timestamp"],
                    "failure_probability": round(prob, 4),
                    "confidence": round(conf, 4),
                    "risk_level": risk,
                    "prediction_id": row["id"],
                })

        # Highest risk first
        assets.sort(key=lambda a: a["failure_probability"], reverse=True)
        self._send_json(assets)

    # ── GET /api/assets/:asset_id ───────────────────────────────────────

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

        # Parse judge_output_json
        judge = self._parse_judge(row.get("judge_output_json", ""))
        row["judge_output"] = judge if judge else None
        del row["judge_output_json"]

        # Safe-guard sentinel values from view text
        for key in ("view1_text", "view2_text", "view3_text", "view4_text"):
            val = row.get(key)
            if val and val.startswith("[ERROR"):
                row[key] = None

        self._send_json(row)

    # ── GET /api/calibration ────────────────────────────────────────────

    def _handle_calibration(self) -> None:
        rows = _fetchall(
            "SELECT judge_output_json, actual_outcome FROM predictions "
            "WHERE actual_outcome IS NOT NULL AND judge_output_json IS NOT NULL "
            "AND judge_output_json != ''"
        )

        points: list[dict] = []
        brier_total = 0.0
        for row in rows:
            judge = self._parse_judge(row.get("judge_output_json", ""))
            prob = judge.get("failure_probability", -1) if judge else -1
            actual = row["actual_outcome"]
            if isinstance(prob, (int, float)) and prob >= 0 and actual is not None:
                err = (prob - actual) ** 2
                brier_total += err
                points.append({
                    "predicted_probability": round(prob, 4),
                    "actual_outcome": actual,
                    "confidence": round(judge.get("confidence", 0), 4) if judge else 0,
                    "squared_error": round(err, 4),
                })

        n = len(points)
        brier_score = round(brier_total / n, 4) if n > 0 else 0.0

        # Build calibration curve bins (10 bins of 0.1 width)
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

    # ── Utilities ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_judge(raw: str) -> dict | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
            return None
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _risk_level(prob: float) -> str:
        if prob >= 0.6:
            return "high"
        if prob >= 0.3:
            return "medium"
        return "low"


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"[FATAL] Database not found at: {DB_PATH}", file=sys.stderr)
        print("  Run the pipeline first: python -m predictor.main --limit 2", file=sys.stderr)
        sys.exit(1)

    server = http.server.HTTPServer(("0.0.0.0", API_PORT), APIHandler)
    print(f"  API server  ->  http://localhost:{API_PORT}")
    print(f"  Database    ->  {DB_PATH}")
    print(f"  Endpoints:")
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
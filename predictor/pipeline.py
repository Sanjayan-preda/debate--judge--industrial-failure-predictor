"""
Core pipeline: load features, run debate + judge, save results.
"""

import csv
import sys
import time
from typing import Iterator

from .config import Config
from .db import init_db, save_prediction, close_db
from .views import (
    call_signal_analyst,
    call_domain_expert,
    call_risk_assessor,
    call_skeptic,
)
from .judge import call_judge


def load_features(path: str) -> list[dict]:
    """
    Read the features CSV and return a list of row-dicts.
    Strips the 'time_to_failure_label' column before returning so that
    the label is NEVER sent to any AI view (prevents label leakage).
    """
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                # Strip whitespace from keys/values
                clean = {k.strip(): v.strip() for k, v in row.items()}
                # Remove the label column — never shown to the AI
                clean.pop("time_to_failure_label", None)
                rows.append(clean)
    except FileNotFoundError:
        print(f"[FATAL] Features file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] Error reading features file: {e}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print(f"[FATAL] Features file is empty: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"[LOAD] Loaded {len(rows)} rows from {path}")
    return rows


def run_debate(row: dict, cfg: Config) -> tuple[str, str, str, str]:
    """
    Run all four view calls for a single feature row.
    Returns (view1_text, view2_text, view3_text, view4_text).
    Because the calls are independent, we make them sequentially here
    (simple, debuggable). A future optimisation could parallelise them.
    """
    # ── Signal Analyst (AMD) ──────────────────────────────────────────
    v1 = call_signal_analyst(row, cfg)

    # ── Domain Expert (Fireworks) ─────────────────────────────────────
    v2 = call_domain_expert(row, cfg)

    # ── Risk Assessor (Fireworks) ─────────────────────────────────────
    v3 = call_risk_assessor(row, cfg)

    # ── Skeptic (AMD) ────────────────────────────────────────────────
    v4 = call_skeptic(row, cfg)

    return v1.text, v2.text, v3.text, v4.text


def process_one_row(
    row: dict,
    idx: int,
    total: int,
    cfg: Config,
    conn,
) -> dict:
    """
    Process a single feature row through the full debate + judge pipeline.
    Returns a summary dict for logging.
    """
    asset_id = row.get("asset_id", "unknown")
    timestamp = row.get("timestamp", "unknown")

    print(f"\n{'='*60}")
    print(f"[ROW {idx}/{total}] asset_id={asset_id}  timestamp={timestamp}")
    print(f"{'='*60}")

    # ── Step 1: Debate — run all four views ──────────────────────────
    print("\n── View calls ──")
    v1_text, v2_text, v3_text, v4_text = run_debate(row, cfg)

    # ── Step 2: Judge ─────────────────────────────────────────────────
    print("\n── Judge ──")
    judge_output = call_judge(v1_text, v2_text, v3_text, v4_text, cfg)

    # ── Step 3: Store ─────────────────────────────────────────────────
    row_id = save_prediction(
        conn,
        asset_id=asset_id,
        timestamp=timestamp,
        view1_text=v1_text,
        view2_text=v2_text,
        view3_text=v3_text,
        view4_text=v4_text,
        judge_output=judge_output,
    )

    # ── Summary for this row ──────────────────────────────────────────
    prob = judge_output.get("failure_probability", "?")
    conf = judge_output.get("confidence", "?")
    flag = judge_output.get("disagreement_flag", "?")
    print(f"\n── Result ──")
    print(f"  DB row ID:    {row_id}")
    print(f"  Probability:  {prob}")
    print(f"  Confidence:   {conf}")
    print(f"  Disagreement: {flag}")
    print(f"  Rationale:    {judge_output.get('rationale', '')[:200]}…")

    return {
        "asset_id": asset_id,
        "timestamp": timestamp,
        "failure_probability": prob,
        "confidence": conf,
        "disagreement_flag": flag,
        "row_id": row_id,
    }


def process_all(
    csv_path: str,
    db_path: str,
    cfg: Config,
    limit: int = 0,
) -> list[dict]:
    """
    Load features, run the full pipeline for every row, and return summaries.
    If limit > 0, only process that many rows (useful for dry-run/testing).
    """
    rows = load_features(csv_path)
    if limit > 0:
        rows = rows[:limit]
        print(f"[LIMIT] Processing first {limit} row(s) only")

    conn = init_db(db_path)
    summaries = []

    start_time = time.time()
    for idx, row in enumerate(rows, start=1):
        summary = process_one_row(row, idx, len(rows), cfg, conn)
        summaries.append(summary)

    elapsed = time.time() - start_time
    close_db(conn)

    # ── Final report ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Rows processed:  {len(summaries)}")
    print(f"  Elapsed time:    {elapsed:.1f}s")
    print(f"  Avg per row:     {elapsed / max(len(summaries), 1):.2f}s")
    print(f"  Output DB:       {db_path}")
    print(f"{'='*60}")

    return summaries
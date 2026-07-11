#!/usr/bin/env python3
"""
Entry point for the Debate & Judge prediction pipeline.

Usage:
    python -m predictor.main                     # uses env vars for paths
    python -m predictor.main --limit 2           # process only 2 rows (test mode)
    python -m predictor.main --csv ./my_data.csv --db ./output.db

Environment variables:
    AMD_ENDPOINT_URL      (required)  Base URL of the AMD GPU endpoint
    AMD_API_KEY           (optional)  API key for AMD endpoint
    AMD_MODEL_NAME        (optional)  Model name on AMD pod
    FIREWORKS_API_KEY     (required)  Fireworks AI API key
    FIREWORKS_VIEW_MODEL  (optional)  Model for Domain Expert & Risk Assessor
    FIREWORKS_JUDGE_MODEL (optional)  Stronger model for Judge
    FEATURES_CSV_PATH     (optional)  Path to input features CSV
    SQLITE_DB_PATH        (optional)  Path to output SQLite database
    MAX_RETRIES           (optional)  API call retry count (default: 3)
    BACKOFF_BASE_SECONDS  (optional)  Backoff base in seconds (default: 2.0)
"""

import argparse
import sys

from dotenv import load_dotenv

from .config import Config
from .pipeline import process_all


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Debate & Judge — Industrial Equipment Failure Predictor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Override FEATURES_CSV_PATH (path to input features CSV)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Override SQLITE_DB_PATH (path to output SQLite database)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N rows (default: all rows)",
    )
    return parser.parse_args(argv)


def main() -> None:
    load_dotenv()  # load .env file if present

    args = parse_args()
    cfg = Config()

    # CLI overrides can supplement env vars
    csv_path = args.csv or cfg.features_csv_path
    db_path = args.db or cfg.sqlite_db_path

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   Debate & Judge — Industrial Failure Predictor        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(cfg)
    print(f"  Input CSV:  {csv_path}")
    print(f"  Output DB:  {db_path}")

    process_all(
        csv_path=csv_path,
        db_path=db_path,
        cfg=cfg,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
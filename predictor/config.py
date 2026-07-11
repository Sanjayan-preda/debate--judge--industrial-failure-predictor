"""
Environment variable loading and configuration.
All secrets and endpoints come from environment — never hardcoded.
"""

import os
import sys
from pathlib import Path

# ── Defaults ──────────────────────────────────────────────────────────
_DEFAULT_AMD_MODEL = "llama-2-7b-chat"
_DEFAULT_FIREWORKS_VIEW_MODEL = "accounts/fireworks/models/llama-v3p1-8b-instruct"
_DEFAULT_FIREWORKS_JUDGE_MODEL = "accounts/fireworks/models/llama-v3p1-70b-instruct"
_DEFAULT_CSV_PATH = "data/features.csv"
_DEFAULT_DB_PATH = "data/predictions.db"


class Config:
    """Immutable configuration loaded from environment variables at startup."""

    def __init__(self):
        # ── AMD endpoint ──────────────────────────────────────────────
        self.amd_endpoint_url = os.environ.get("AMD_ENDPOINT_URL", "").rstrip("/")
        self.amd_api_key = os.environ.get("AMD_API_KEY", "no-key-required")
        self.amd_model = os.environ.get("AMD_MODEL_NAME", _DEFAULT_AMD_MODEL)

        # ── Fireworks AI ──────────────────────────────────────────────
        self.fireworks_api_key = os.environ.get("FIREWORKS_API_KEY", "")
        self.fireworks_view_model = os.environ.get(
            "FIREWORKS_VIEW_MODEL", _DEFAULT_FIREWORKS_VIEW_MODEL
        )
        self.fireworks_judge_model = os.environ.get(
            "FIREWORKS_JUDGE_MODEL", _DEFAULT_FIREWORKS_JUDGE_MODEL
        )

        # ── Data paths ────────────────────────────────────────────────
        self.features_csv_path = os.environ.get(
            "FEATURES_CSV_PATH", _DEFAULT_CSV_PATH
        )
        self.sqlite_db_path = os.environ.get(
            "SQLITE_DB_PATH", _DEFAULT_DB_PATH
        )

        # ── Runtime behaviour ─────────────────────────────────────────
        self.max_retries = int(os.environ.get("MAX_RETRIES", "3"))
        self.backoff_base = float(os.environ.get("BACKOFF_BASE_SECONDS", "2.0"))

        # ── Validate required vars ────────────────────────────────────
        self._validate()

    def _validate(self) -> None:
        missing = []
        if not self.amd_endpoint_url:
            missing.append("AMD_ENDPOINT_URL")
        if not self.fireworks_api_key:
            missing.append("FIREWORKS_API_KEY")
        if missing:
            print(
                f"[ERROR] Missing required environment variable(s): {', '.join(missing)}",
                file=sys.stderr,
            )
            print(
                "  Set them in a .env file or export them before running.",
                file=sys.stderr,
            )
            sys.exit(1)

    def __repr__(self) -> str:
        return (
            f"Config(\n"
            f"  AMD endpoint: {self.amd_endpoint_url}\n"
            f"  AMD model:    {self.amd_model}\n"
            f"  FW view model: {self.fireworks_view_model}\n"
            f"  FW judge model: {self.fireworks_judge_model}\n"
            f"  CSV path:     {self.features_csv_path}\n"
            f"  DB path:      {self.sqlite_db_path}\n"
            f"  Max retries:  {self.max_retries}\n"
            f")"
        )
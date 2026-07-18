"""
Preprocess raw vibration CSV files into engineered features for the pipeline.
Reads each raw signal file (e.g. 2.csv), computes features, and writes
a combined features.csv that the pipeline can consume.

Usage:
    python data/preprocess.py
"""

import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Map raw file numbers to asset IDs
ASSET_MAP = {
    2: "PUMP-201",
    3: "PUMP-202",
    4: "PUMP-203",
    5: "PUMP-204",
    6: "PUMP-205",
    7: "PUMP-206",
    8: "PUMP-207",
    9: "PUMP-208",
    19: "PUMP-209",
    20: "PUMP-210",
    21: "PUMP-211",
    22: "PUMP-212",
    23: "PUMP-213",
    24: "PUMP-214",
    25: "PUMP-215",
}

# ── Signal Processing Helpers ──────────────────────────────────────────


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


def compute_spectral_features(values: list[float]) -> list[float]:
    """
    Compute frequency-band energies using a simple FFT approach.
    Returns energies for 8 frequency bands as a ratio of total energy.
    """
    n = len(values)
    if n < 16:
        return [0.0] * 8

    # Simple DFT for key frequency bins (we don't need full FFT library)
    # We'll use a simplified band energy approach
    # Detrend: subtract mean
    mean = sum(values) / n
    detrended = [v - mean for v in values]

    # Compute power spectrum using FFT approximation
    # We'll compute energies in 8 bands using simplified goertzel-like approach
    bands = 8
    band_energies = [0.0] * bands

    # For each frequency bin k, compute approximate magnitude
    for k in range(bands):
        # Frequency bin k corresponds to normalized frequency k/n
        energy = 0.0
        bin_size = max(1, n // (bands * 4))
        start_bin = k * (n // (bands * 2))
        end_bin = min((k + 1) * (n // (bands * 2)), n // 2)

        if end_bin <= start_bin:
            continue

        for i in range(start_bin, end_bin):
            # Approximate DFT magnitude
            real = 0.0
            imag = 0.0
            step = max(1, n // 100)  # Subsample for speed
            for t in range(0, n, step):
                angle = 2 * math.pi * i * t / n
                real += detrended[t] * math.cos(angle)
                imag -= detrended[t] * math.sin(angle)
            energy += (real * real + imag * imag) / (n * n)

        band_energies[k] = energy

    # Normalize to sum to 1.0
    total = sum(band_energies)
    if total > 0:
        band_energies = [e / total for e in band_energies]

    return band_energies


def load_raw_signal(filepath: str) -> tuple[list[float], list[float]]:
    """Load horizontal and vertical vibration signals from a CSV file."""
    h_signals = []
    v_signals = []
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
    return h_signals, v_signals


def process_file(file_number: int) -> dict | None:
    """
    Process a single raw vibration CSV file and return a feature row dict.
    """
    asset_id = ASSET_MAP.get(file_number)
    if not asset_id:
        print(f"  [SKIP] No asset mapping for file {file_number}")
        return None

    filename = f"{file_number}.csv"
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [SKIP] File not found: {filepath}")
        return None

    print(f"  Processing {filename} → {asset_id} ... ", end="", flush=True)
    h_sig, v_sig = load_raw_signal(filepath)

    if not h_sig or not v_sig:
        print("EMPTY")
        return None

    n = len(h_sig)
    print(f"{n} samples", end=" | ", flush=True)

    # ── Compute features ──────────────────────────────────────────────
    rms_h = compute_rms(h_sig)
    rms_v = compute_rms(v_sig)
    rms_composite = math.sqrt(rms_h * rms_h + rms_v * rms_v)

    kurt_h = compute_kurtosis(h_sig)
    kurt_v = compute_kurtosis(v_sig)
    kurt_composite = max(kurt_h, kurt_v)

    # Use horizontal signal for spectral features (usually richer)
    spectral = compute_spectral_features(h_sig)

    # ── Generate a synthetic timestamp ─────────────────────────────────
    # Base timestamp: 2025-01-01 + offset by file number
    base = datetime(2025, 1, 1, 8, 0, 0)
    ts = base + timedelta(hours=file_number * 2)

    print(f"RMS={rms_composite:.4f} Kurt={kurt_composite:.2f}", end="")

    row = {
        "asset_id": asset_id,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "rms_h": f"{rms_h:.6f}",
        "rms_v": f"{rms_v:.6f}",
        "rms": f"{rms_composite:.6f}",
        "kurtosis_h": f"{kurt_h:.4f}",
        "kurtosis_v": f"{kurt_v:.4f}",
        "kurtosis": f"{kurt_composite:.4f}",
        "spectral_features": json.dumps([round(e, 6) for e in spectral]),
        "sample_count": str(n),
        # Label is unknown for real data — set to 0 (no failure observed)
        "time_to_failure_label": "0",
    }
    print(" ✓")
    return row


def main():
    print("=" * 60)
    print("  VIBRATION DATA PREPROCESSOR")
    print("=" * 60)

    # Process all mapped files
    feature_rows = []
    for file_num in sorted(ASSET_MAP.keys()):
        row = process_file(file_num)
        if row:
            feature_rows.append(row)

    if not feature_rows:
        print("\n[ERROR] No features were generated!")
        sys.exit(1)

    # ── Write combined features.csv ────────────────────────────────────
    output_path = os.path.join(DATA_DIR, "features.csv")
    fieldnames = [
        "asset_id", "timestamp", "rms_h", "rms_v", "rms",
        "kurtosis_h", "kurtosis_v", "kurtosis",
        "spectral_features", "sample_count", "time_to_failure_label",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(feature_rows)

    print(f"\n{'='*60}")
    print(f"  DONE — Wrote {len(feature_rows)} rows to features.csv")
    print(f"  Assets: {', '.join(ASSET_MAP.values())}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
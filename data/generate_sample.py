"""Generate a sample features.csv with 5 rows for testing the pipeline."""

import csv
import json
import os

ROWS = [
    {
        "asset_id": "PUMP-101",
        "timestamp": "2024-11-15T08:00:00Z",
        "rms": 2.34,
        "kurtosis": 3.12,
        "spectral_features": [0.45, 0.32, 0.21, 0.18, 0.15, 0.12, 0.10, 0.08],
        "time_to_failure_label": 120,  # 120 hours until failure (training label)
    },
    {
        "asset_id": "PUMP-101",
        "timestamp": "2024-11-15T09:00:00Z",
        "rms": 4.78,
        "kurtosis": 4.56,
        "spectral_features": [0.62, 0.55, 0.48, 0.42, 0.35, 0.28, 0.20, 0.15],
        "time_to_failure_label": 119,
    },
    {
        "asset_id": "MTR-204",
        "timestamp": "2024-11-14T14:30:00Z",
        "rms": 1.02,
        "kurtosis": 2.88,
        "spectral_features": [0.12, 0.11, 0.10, 0.09, 0.08, 0.08, 0.07, 0.07],
        "time_to_failure_label": None,  # healthy — never failed
    },
    {
        "asset_id": "FAN-037",
        "timestamp": "2024-11-16T06:15:00Z",
        "rms": 6.55,
        "kurtosis": 6.12,
        "spectral_features": [0.88, 0.82, 0.78, 0.71, 0.65, 0.55, 0.42, 0.30],
        "time_to_failure_label": 2,  # very close to failure
    },
    {
        "asset_id": "PUMP-101",
        "timestamp": "2024-11-16T10:00:00Z",
        "rms": 9.23,
        "kurtosis": 8.45,
        "spectral_features": [0.95, 0.92, 0.88, 0.85, 0.79, 0.72, 0.60, 0.45],
        "time_to_failure_label": 0,  # imminent / already failing
    },
]


def main():
    os.makedirs("data", exist_ok=True)
    path = "data/features.csv"

    fieldnames = [
        "asset_id",
        "timestamp",
        "rms",
        "kurtosis",
        "spectral_features",
        "time_to_failure_label",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in ROWS:
            # Serialise spectral_features as JSON string in the CSV
            out = dict(row)
            out["spectral_features"] = json.dumps(row["spectral_features"])
            out["time_to_failure_label"] = (
                "" if row["time_to_failure_label"] is None
                else str(row["time_to_failure_label"])
            )
            writer.writerow(out)

    print(f"✅ Sample features file written to {path}")
    print(f"   {len(ROWS)} rows covering healthy, degrading, and imminent-failure states.")


if __name__ == "__main__":
    main()
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def calculate_psi(expected, actual, bins=10):
    """Calculate PSI using shared quantile bins from the baseline data."""
    expected = pd.Series(expected).dropna().astype(float).to_numpy()
    actual = pd.Series(actual).dropna().astype(float).to_numpy()
    if expected.size == 0 or actual.size == 0:
        raise ValueError("Both baseline and live data must contain numeric values")
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if edges.size < 2:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    expected_counts, _ = np.histogram(expected, bins=edges)
    actual_counts, _ = np.histogram(actual, bins=edges)
    expected_perc = np.maximum(expected_counts / expected.size, 0.0001)
    actual_perc = np.maximum(actual_counts / actual.size, 0.0001)
    return float(np.sum((actual_perc - expected_perc) * np.log(actual_perc / expected_perc)))


def load_feature(path, column):
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Missing monitoring file: {file_path}")
    frame = pd.read_csv(file_path)
    if column not in frame.columns:
        raise ValueError(f"Column '{column}' is missing from {file_path}")
    return frame[column]


def main():
    parser = argparse.ArgumentParser(description="Check population stability index")
    parser.add_argument("--baseline", default="data/clean_features.csv")
    parser.add_argument("--live", default="data/live_predictions_log.csv")
    parser.add_argument("--column", default="total_orders")
    parser.add_argument("--threshold", type=float, default=0.2)
    args = parser.parse_args()
    psi_value = calculate_psi(
        load_feature(args.baseline, args.column),
        load_feature(args.live, args.column),
    )
    print(f"PSI for {args.column}: {psi_value:.4f}")
    if psi_value > args.threshold:
        print("WARNING: Significant data drift detected. Trigger retraining pipeline.")
    else:
        print("Data distribution is stable.")


if __name__ == "__main__":
    main()
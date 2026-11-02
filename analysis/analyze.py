#!/usr/bin/env python3
"""Analyze opted-in exported research data. No upload/network access.
pip install pandas scipy
python analysis/analyze.py path/to/consented-export.csv
"""
import sys
import pandas as pd
from scipy.stats import wilcoxon

REQUIRED = {"participant_id", "condition", "return_latency_ms", "returned"}

def main(path):
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df = df[df["condition"].isin(["treatment", "control"])].copy()
    df = df[df["returned"].astype(str).str.lower().isin(["true", "1"])].copy()
    df["return_latency_ms"] = pd.to_numeric(df["return_latency_ms"], errors="coerce")
    df = df.dropna(subset=["return_latency_ms"])
    df = df[df["return_latency_ms"].between(0, 86_400_000)]
    print("Observed returns by condition (not all assigned sessions):")
    print(df.groupby("condition")["return_latency_ms"].agg(["count", "median", "mean"]) / pd.Series({"count": 1, "median": 1000, "mean": 1000}))
    med = df.groupby(["participant_id", "condition"])["return_latency_ms"].median().unstack()
    if not {"control", "treatment"}.issubset(med.columns):
        print("Insufficient data for within-participant comparison.")
        return
    paired = med[["control", "treatment"]].dropna()
    print(f"Participants with both conditions: {len(paired)}")
    if len(paired) >= 5 and (paired["control"] != paired["treatment"]).any():
        result = wilcoxon(paired["control"], paired["treatment"])
        print(f"Exploratory paired Wilcoxon test: statistic={result.statistic:.3g}, p={result.pvalue:.4g}")
    else:
        print("Insufficient non-tied pairs for inferential test.")
    print("Important: non-return and censoring must be analyzed separately; this is exploratory, not a causal conclusion.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python analysis/analyze.py consented-export.csv")
    main(sys.argv[1])

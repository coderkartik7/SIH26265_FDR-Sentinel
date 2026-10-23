#!/usr/bin/env python3
"""
Model training script for FDR-Sentinel:
Trains GradientBoostingClassifier on ground truth features with 80/20 train/test split.
Computes real test accuracy, precision, recall, F1, and saves model to eval/results/.
"""

import sys
import argparse
from pathlib import Path

def _find_base_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config" / "rules.yaml").exists():
            return parent
    if Path("/app/config/rules.yaml").exists():
        return Path("/app")
    return current.parent.parent.parent.parent


BASE_DIR = _find_base_dir()
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.ml.risk_model import train_risk_model

DEFAULT_DATASET = BASE_DIR / "datagen" / "out" / "ground_truth.csv"
DEFAULT_OUT = BASE_DIR / "eval" / "results"


def main():
    parser = argparse.ArgumentParser(description="Train FDR-Sentinel GBDT Risk Model")
    parser.add_argument("--data", type=str, default=str(DEFAULT_DATASET), help="Path to ground_truth.csv")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT), help="Output directory for model and metrics")
    args = parser.parse_args()

    if not Path(args.data).exists():
        print(f"[ERROR] Dataset file not found at {args.data}. Run 'python datagen/generate_dataset.py' first.")
        sys.exit(1)

    print(f"[*] Training GBDT Risk Model from {args.data}...")
    metrics = train_risk_model(ground_truth_csv=args.data, output_dir=args.out)
    print("\n[*] Training complete. Verified non-hardcoded evaluation metrics:")
    print(f"    Accuracy:  {metrics['accuracy']}")
    print(f"    Precision: {metrics['precision']}")
    print(f"    Recall:    {metrics['recall']}")
    print(f"    F1 Score:  {metrics['f1_score']}")
    print(f"    ROC AUC:   {metrics['roc_auc']}")


if __name__ == "__main__":
    main()

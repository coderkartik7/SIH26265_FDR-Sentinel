import os
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_curve, auc

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
EVAL_RESULTS_DIR = WORKSPACE_ROOT / "eval" / "results"
SUMMARY_FILE = EVAL_RESULTS_DIR / "eval_summary.json"

FOOTER_TEXT = "*Evaluated on synthetic dataset generated with fixed seed=42"

def setup_style():
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.edgecolor"] = "#cbd5e1"
    plt.rcParams["axes.linewidth"] = 0.8

def plot_roc_curve(data):
    y_true = data["y_true"]
    y_scores = data["y_scores"]
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    fig, ax = plt.subplots(figsize=(7, 5.5), dpi=150)
    ax.plot(fpr, tpr, color="#0284c7", lw=2.5, label=f"GBDT + Forensics (AUC = {roc_auc:.3f})")
    ax.plot([0, 1], [0, 1], color="#94a3b8", lw=1.5, linestyle="--", label="Random Classifier (AUC = 0.500)")

    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.05])
    ax.set_xlabel("False Positive Rate (FPR)", fontweight="bold")
    ax.set_ylabel("True Positive Rate (Recall / TPR)", fontweight="bold")
    ax.set_title("FDR-Sentinel: ROC Curve for Anomaly Detection", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="lower right", frameon=True, facecolor="#f8fafc", edgecolor="#cbd5e1")
    ax.grid(True, linestyle=":", alpha=0.6)

    fig.text(0.5, 0.01, FOOTER_TEXT, ha="center", fontsize=8, color="#64748b", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    out_path = EVAL_RESULTS_DIR / "roc_curve.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def plot_confusion_matrix(data):
    cm_dict = data["confusion_matrix"]
    tp = cm_dict["true_positives"]
    fp = cm_dict["false_positives"]
    tn = cm_dict["true_negatives"]
    fn = cm_dict["false_negatives"]

    cm = np.array([[tn, fp], [fn, tp]])
    labels = [["True Negatives\n(Genuine Correct)", "False Positives\n(Genuine Flagged)"],
              ["False Negatives\n(Anomaly Missed)", "True Positives\n(Anomaly Flagged)"]]

    fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=150)
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Document Count", rotation=-90, va="bottom", fontsize=9)

    ax.set(xticks=np.arange(2), yticks=np.arange(2),
           xticklabels=["Genuine (0)", "Anomaly / Dup (1)"],
           yticklabels=["Genuine (0)", "Anomaly / Dup (1)"],
           title="FDR-Sentinel: Confusion Matrix",
           ylabel="Ground Truth Label",
           xlabel="Pipeline Predicted Decision")

    for i in range(2):
        for j in range(2):
            count = cm[i, j]
            text = f"{count}\n\n{labels[i][j]}"
            text_color = "white" if count > (cm.max() / 2) else "#0f172a"
            ax.text(j, i, text, ha="center", va="center", color=text_color, fontsize=9, fontweight="bold")

    fig.text(0.5, 0.01, FOOTER_TEXT, ha="center", fontsize=8, color="#64748b", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    out_path = EVAL_RESULTS_DIR / "confusion_matrix.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def plot_anomaly_breakdown(data):
    breakdown = data.get("category_breakdown", {})
    categories = list(breakdown.keys())
    rates = [breakdown[c]["detection_rate"] * 100 for c in categories]
    counts = [f"{breakdown[c]['detected_count']}/{breakdown[c]['total_count']}" for c in categories]

    # Clean display labels
    labels = [c.replace("_", " ").title() for c in categories]

    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, rates, color="#0ea5e9", edgecolor="#0284c7", height=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Detection / Recall Rate (%)", fontweight="bold")
    ax.set_xlim([0, 115])
    ax.set_title("FDR-Sentinel: Anomaly Detection Rate by Category", fontsize=12, fontweight="bold", pad=12)

    for bar, count, rate in zip(bars, counts, rates):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{rate:.1f}% ({count})", va="center", ha="left", fontsize=8.5, color="#0f172a", fontweight="bold")

    fig.text(0.5, 0.01, FOOTER_TEXT, ha="center", fontsize=8, color="#64748b", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    out_path = EVAL_RESULTS_DIR / "anomaly_breakdown.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def plot_latency_distribution(data):
    lat = data.get("latency_percentiles", {})

    fig, ax = plt.subplots(figsize=(7, 4.8), dpi=150)

    metrics = ["Min", "Median (P50)", "Mean", "P90", "P99", "Max"]
    vals = [
        lat.get("min_ms", 100),
        lat.get("median_p50_ms", 300),
        lat.get("mean_ms", 350),
        lat.get("p90_ms", 600),
        lat.get("p99_ms", 950),
        lat.get("max_ms", 1200)
    ]

    colors = ["#38bdf8", "#0284c7", "#0369a1", "#f59e0b", "#f97316", "#ef4444"]
    x = np.arange(len(metrics))
    bars = ax.bar(x, vals, color=colors, width=0.55, edgecolor="#0f172a", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=9)
    ax.set_ylabel("Processing Time per Document (ms)", fontweight="bold")
    ax.set_title("FDR-Sentinel: Pipeline Processing Latency Profile", fontsize=12, fontweight="bold", pad=12)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 15, f"{h:.0f} ms",
                ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax.set_ylim([0, max(vals) * 1.18])
    fig.text(0.5, 0.01, FOOTER_TEXT, ha="center", fontsize=8, color="#64748b", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    out_path = EVAL_RESULTS_DIR / "latency_distribution.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def main():
    setup_style()
    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(f"Summary file {SUMMARY_FILE} not found. Run eval/run_eval.py first.")

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Generating evaluation charts from computed run results...")
    plot_roc_curve(data)
    plot_confusion_matrix(data)
    plot_anomaly_breakdown(data)
    plot_latency_distribution(data)
    print("All charts successfully generated!")

if __name__ == "__main__":
    main()

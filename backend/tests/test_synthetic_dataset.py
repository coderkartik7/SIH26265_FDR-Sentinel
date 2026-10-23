import csv
import json
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_CSV = BASE_DIR / "datagen" / "out" / "ground_truth.csv"
LEDGER_JSON = BASE_DIR / "datagen" / "out" / "issuer_ledger.json"


def test_ground_truth_dataset_composition():
    assert DATASET_CSV.exists(), "ground_truth.csv must exist"

    with open(DATASET_CSV, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 150, f"Expected 150 FDR records, got {len(reader)}"

    labels = [r["label"] for r in reader]
    assert labels.count("genuine") == 100
    assert labels.count("tampered") == 25
    assert labels.count("duplicate") == 15
    assert labels.count("noisy_genuine") == 10

    # Verify tamper types
    tamper_types = set(r["tamper_type"] for r in reader if r["label"] == "tampered")
    expected_tamper_types = {
        "edited_amount",
        "edited_date",
        "amount_words_mismatch",
        "pasted_region",
        "metadata_edited_after_signing",
        "signature_breaking_edit"
    }
    assert expected_tamper_types.issubset(tamper_types)

    # Verify duplicate types
    dup_types = set(r["duplicate_type"] for r in reader if r["label"] == "duplicate")
    assert "cross_institution_reuse" in dup_types
    assert "post_release_resubmission" in dup_types

    # Verify all generated document files exist on disk
    for r in reader:
        file_path = BASE_DIR / r["file_path"]
        assert file_path.exists(), f"Document file missing: {file_path}"
        assert file_path.stat().st_size > 0


def test_mock_issuer_ledger_generated():
    assert LEDGER_JSON.exists(), "issuer_ledger.json must exist"
    with open(LEDGER_JSON, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    assert len(ledger) > 100
    statuses = set(row["status"] for row in ledger)
    assert "ACTIVE" in statuses
    assert "RELEASED" in statuses

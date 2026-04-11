from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas import (
    validate_metrics_file,
    validate_postquali_predictions_file,
    validate_prequali_predictions_file,
)


def test_metrics_schema() -> None:
    path = Path("data/metrics/metrics_summary.json")
    if not path.exists():
        pytest.skip("metrics_summary.json not found")
    metrics = validate_metrics_file(str(path))
    assert metrics.rounds
    assert "prequali" in metrics.overall
    assert "postquali" in metrics.overall


def test_prequali_predictions_schema() -> None:
    path = _latest_prediction("prequali")
    if path is None:
        pytest.skip("no prequali prediction files")
    preds = validate_prequali_predictions_file(str(path))
    assert preds.mode == "prequali"
    assert len(preds.rows) > 0


def test_postquali_predictions_schema() -> None:
    path = _latest_prediction("postquali")
    if path is None:
        pytest.skip("no postquali prediction files")
    preds = validate_postquali_predictions_file(str(path))
    assert preds.mode == "postquali"
    assert len(preds.rows) > 0


def _latest_prediction(suffix: str) -> Path | None:
    preds_dir = Path("data/predictions")
    if not preds_dir.exists():
        return None
    paths = list(preds_dir.glob(f"round_*_{suffix}_predictions.json"))
    if not paths:
        return None
    return sorted(paths, key=lambda p: p.name)[-1]

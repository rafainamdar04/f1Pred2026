from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


def _parse_json_constant(value: str) -> float:
    if value == "NaN":
        return float("nan")
    if value == "Infinity":
        return float("inf")
    if value == "-Infinity":
        return float("-inf")
    raise ValueError(f"Unsupported JSON constant: {value}")


def _load_json(path: str) -> Any:
    file_path = Path(path)
    try:
        payload = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"JSON file not found: {file_path}") from exc

    payload = re.sub(r'\bNaN\b', 'null', payload)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {file_path}: {exc.msg} (line {exc.lineno}, col {exc.colno})"
        ) from exc


class ModelMetrics(BaseModel):
    ndcg: float
    top3_hit: float
    mae: float
    alpha: float


class RoundMetrics(BaseModel):
    round: int | None = None
    prequali: ModelMetrics
    postquali: ModelMetrics


class MetricsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rounds: list[RoundMetrics]
    overall: dict[str, ModelMetrics]

    @field_validator("rounds")
    @classmethod
    def _require_round_numbers(cls, value: list[RoundMetrics]) -> list[RoundMetrics]:
        missing = [item for item in value if item.round is None]
        if missing:
            raise ValueError("All round entries must include a round number")
        return value


class PredictionRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    season: int
    round: int
    driver_id: str
    constructor_id: str
    score_2026: float
    score_hist: float
    final_score: float
    rationale: str


class PrequaliPredictionRow(PredictionRow):
    pass


class PostqualiPredictionRow(PredictionRow):
    pace_vs_grid: int


class RoundPredictions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round: int
    race_name: str
    mode: str
    alpha: float
    created_at: str | None = None
    rows: list[PredictionRow]


class PrequaliRoundPredictions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round: int
    race_name: str
    mode: str
    alpha: float
    created_at: str | None = None
    rows: list[PrequaliPredictionRow]


class PostqualiRoundPredictions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round: int
    race_name: str
    mode: str
    alpha: float
    created_at: str | None = None
    rows: list[PostqualiPredictionRow]


class ComparisonRow(BaseModel):
    driver_id: str
    prequali_rank: int
    postquali_rank: int
    pace_vs_grid: int
    prequali_score: float
    postquali_score: float


class ComparisonResponse(BaseModel):
    round: int
    race_name: str
    rows: list[ComparisonRow]


def validate_predictions_file(path: str) -> RoundPredictions:
    data = _load_json(path)
    try:
        return RoundPredictions.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Prediction schema validation failed for {path}: {exc}") from exc


def validate_prequali_predictions_file(path: str) -> PrequaliRoundPredictions:
    data = _load_json(path)
    try:
        return PrequaliRoundPredictions.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Prequali schema validation failed for {path}: {exc}") from exc


def validate_postquali_predictions_file(path: str) -> PostqualiRoundPredictions:
    data = _load_json(path)
    try:
        return PostqualiRoundPredictions.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Postquali schema validation failed for {path}: {exc}") from exc


def validate_metrics_file(path: str) -> MetricsSummary:
    data = _load_json(path)
    try:
        return MetricsSummary.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Metrics schema validation failed for {path}: {exc}") from exc

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import (
    validate_metrics_file,
    validate_postquali_predictions_file,
    validate_prequali_predictions_file,
)
from config import settings


CHECKS: list[dict[str, Any]] = []


def _record(name: str, ok: bool, detail: str) -> None:
    CHECKS.append({"name": name, "ok": ok, "detail": detail})


def _print_settings() -> None:
    print("Settings loaded:")
    print(f"  CURRENT_SEASON={settings.CURRENT_SEASON}")
    print(f"  HISTORICAL_YEARS={settings.HISTORICAL_YEARS}")
    print(f"  ALPHA_GRID={settings.ALPHA_GRID}")
    print(f"  XGBOOST_PARAMS={settings.XGBOOST_PARAMS}")
    print(f"  FEATURE_CONSTANTS={settings.FEATURE_CONSTANTS}")
    print(f"  PATHS={settings.PATHS}")


def _scan_for_hardcoded_literals() -> list[str]:
    scripts_dir = Path("scripts")
    if not scripts_dir.exists():
        return ["scripts/ directory not found"]

    forbidden_ints = set(settings.HISTORICAL_YEARS + [settings.CURRENT_SEASON])
    forbidden_strings = {
        settings.PATHS["data"],
        settings.PATHS["models"],
        settings.PATHS["predictions"],
        settings.PATHS["metrics"],
    }

    findings: list[str] = []
    for path in scripts_dir.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(f"{path}: failed to read ({exc})")
            continue

        try:
            import ast

            tree = ast.parse(text)
        except SyntaxError as exc:
            findings.append(f"{path}: syntax error ({exc})")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant):
                continue
            value = node.value
            if isinstance(value, bool):
                continue
            if isinstance(value, int) and value in forbidden_ints:
                findings.append(f"{path}: hardcoded int {value}")
            if isinstance(value, str) and value in forbidden_strings:
                findings.append(f"{path}: hardcoded string '{value}'")

    return findings


def check_settings() -> None:
    try:
        _print_settings()
        findings = _scan_for_hardcoded_literals()
        if findings:
            _record(
                "settings_and_literals",
                False,
                "Hardcoded literals found:\n" + "\n".join(findings),
            )
        else:
            _record("settings_and_literals", True, "No hardcoded literals found in scripts/")
    except Exception as exc:
        _record("settings_and_literals", False, f"Failed: {exc}")


def check_metrics() -> None:
    try:
        metrics = validate_metrics_file("data/metrics/metrics_summary.json")
        print("Metrics summary parsed:")
        print(metrics.model_dump())
        _record("metrics_validation", True, "metrics_summary.json parsed")
    except Exception as exc:
        _record("metrics_validation", False, f"Failed: {exc}")


def _latest_predictions_path(suffix: str) -> Path:
    predictions_dir = Path(settings.PATHS["predictions"])
    if not predictions_dir.exists():
        raise FileNotFoundError(f"Predictions directory not found: {predictions_dir}")

    latest_round = None
    latest_path = None
    for path in predictions_dir.glob(f"round_*_{suffix}_predictions.json"):
        name = path.stem
        parts = name.split("_")
        if len(parts) < 3:
            continue
        try:
            round_num = int(parts[1])
        except ValueError:
            continue
        if latest_round is None or round_num > latest_round:
            latest_round = round_num
            latest_path = path

    if latest_path is None:
        raise FileNotFoundError(f"No {suffix} prediction files found")
    return latest_path


def check_predictions() -> None:
    try:
        latest_pre = _latest_predictions_path("prequali")
        latest_post = _latest_predictions_path("postquali")
        pre = validate_prequali_predictions_file(str(latest_pre))
        post = validate_postquali_predictions_file(str(latest_post))

        pre_top3 = [row.driver_id for row in pre.rows[:3]]
        post_top3 = [row.driver_id for row in post.rows[:3]]
        print(f"Latest prequali predictions: {latest_pre.name}")
        print(f"Driver count: {len(pre.rows)}")
        print(f"Top 3 drivers (prequali): {pre_top3}")
        print(f"Latest postquali predictions: {latest_post.name}")
        print(f"Driver count: {len(post.rows)}")
        print(f"Top 3 drivers (postquali): {post_top3}")
        _record("predictions_validation", True, f"Parsed {latest_pre.name} and {latest_post.name}")
    except Exception as exc:
        _record("predictions_validation", False, f"Failed: {exc}")


def _http_get(url: str) -> tuple[int | None, str | None]:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=5) as resp:
            status = resp.status
            body = resp.read(200).decode("utf-8", errors="replace")
            return status, body
    except Exception as exc:
        return None, str(exc)


def check_http() -> None:
    urls = [
        "http://localhost:8000/health",
        "http://localhost:8000/api/metrics",
        "http://localhost:8000/api/predictions/next/prequali",
        "http://localhost:8000/api/predictions/next/postquali",
        "http://localhost:8000/api/status",
    ]

    all_ok = True
    details: list[str] = []
    for url in urls:
        status, body = _http_get(url)
        if status is None:
            all_ok = False
            details.append(f"{url}: error={body}")
            print(f"{url} -> ERROR: {body}")
        else:
            preview = body.replace("\n", " ")
            print(f"{url} -> {status} {preview}")
            if status >= 400:
                all_ok = False
                details.append(f"{url}: status={status}")

    if all_ok:
        _record("http_checks", True, "All HTTP endpoints returned <400")
    else:
        _record("http_checks", False, "\n".join(details))


def print_summary() -> None:
    print("\nSummary:")
    for check in CHECKS:
        status = "PASS" if check["ok"] else "FAIL"
        print(f"- {check['name']}: {status}")
        if not check["ok"]:
            print(f"  Reason: {check['detail']}")


if __name__ == "__main__":
    print("Running smoke test. Ensure docker-compose is up and API is listening on 8000.\n")
    check_settings()
    check_metrics()
    check_predictions()
    check_http()
    print_summary()

    failed = [c for c in CHECKS if not c["ok"]]
    sys.exit(1 if failed else 0)

"""
End-to-end API and frontend-contract test suite.
Usage: python scripts/test_e2e.py [--base-url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("[FATAL] requests not installed: pip install requests")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Colours ──────────────────────────────────────────────────────────────────
RED   = "\033[91m"
GRN   = "\033[92m"
YLW   = "\033[93m"
BLU   = "\033[94m"
RST   = "\033[0m"
BOLD  = "\033[1m"

def _ok(msg):  print(f"  {GRN}PASS{RST}  {msg}")
def _fail(msg): print(f"  {RED}FAIL{RST}  {msg}"); FAILURES.append(msg)
def _warn(msg): print(f"  {YLW}WARN{RST}  {msg}"); WARNINGS.append(msg)
def _info(msg): print(f"  {BLU}INFO{RST}  {msg}")

FAILURES: list[str] = []
WARNINGS: list[str] = []


# ── HTTP helpers ──────────────────────────────────────────────────────────────
def get(base: str, path: str, expect_status: int = 200) -> dict | None:
    url = f"{base}{path}"
    try:
        r = requests.get(url, timeout=10)
    except requests.ConnectionError:
        _fail(f"Cannot connect to {url} — is the server running?")
        return None
    if r.status_code != expect_status:
        _fail(f"{path} → HTTP {r.status_code} (expected {expect_status})")
        return None
    try:
        return r.json()
    except Exception:
        _fail(f"{path} → response is not valid JSON")
        return None


def require_keys(data: dict, keys: list[str], context: str) -> bool:
    missing = [k for k in keys if k not in data]
    if missing:
        _fail(f"{context}: missing keys {missing}")
        return False
    return True


def require_list(data: Any, key: str, context: str, min_len: int = 1) -> list | None:
    if not isinstance(data, dict) or key not in data:
        _fail(f"{context}: key '{key}' not found")
        return None
    val = data[key]
    if not isinstance(val, list):
        _fail(f"{context}.{key}: expected list, got {type(val).__name__}")
        return None
    if len(val) < min_len:
        _fail(f"{context}.{key}: expected >= {min_len} items, got {len(val)}")
        return None
    return val


# ── Individual checks ─────────────────────────────────────────────────────────
def check_health(base: str) -> None:
    print(f"\n{BOLD}[health]{RST}")
    d = get(base, "/health")
    if d is None:
        return
    if d.get("status") == "ok":
        _ok("/health → ok")
    else:
        _fail(f"/health returned status={d.get('status')}")


def check_status(base: str) -> dict:
    print(f"\n{BOLD}[status]{RST}")
    d = get(base, "/api/status")
    if d is None:
        return {}
    required = ["status", "rounds_completed", "model_version", "jobs"]
    if not require_keys(d, required, "/api/status"):
        return d

    rc = d["rounds_completed"]
    _info(f"rounds_completed = {rc}")
    if not isinstance(rc, int) or rc < 0:
        _fail(f"rounds_completed must be a non-negative int, got {rc!r}")
    elif rc == 0:
        _warn("rounds_completed is 0 — no race data ingested yet?")
    else:
        _ok(f"rounds_completed = {rc}")

    if d.get("model_version") is None:
        _warn("model_version is null — no model files found?")
    else:
        _ok(f"model_version present: {d['model_version'][:19]}")

    return d


def check_calendar(base: str) -> dict:
    print(f"\n{BOLD}[calendar]{RST}")
    d = get(base, "/api/calendar")
    if d is None:
        return {}
    races = require_list(d, "races", "/api/calendar", min_len=1)
    if races is None:
        return d

    _ok(f"{len(races)} races returned")

    required_race_keys = ["round", "name", "date", "is_sprint"]
    missing_any = False
    sprint_rounds = []
    null_date_rounds = []

    for r in races:
        for k in required_race_keys:
            if k not in r:
                _fail(f"calendar race round={r.get('round')}: missing field '{k}'")
                missing_any = True
        if r.get("is_sprint"):
            sprint_rounds.append(r["round"])
        if not r.get("date"):
            null_date_rounds.append(r.get("round"))

    if not missing_any:
        _ok("all races have required fields")
    if sprint_rounds:
        _ok(f"sprint rounds: {sprint_rounds}")
    else:
        _warn("no sprint rounds found in calendar")
    if null_date_rounds:
        _warn(f"rounds with null date: {null_date_rounds}")

    return d


def check_standings(base: str) -> tuple[list, list]:
    print(f"\n{BOLD}[standings]{RST}")
    drivers_data = get(base, "/api/standings/drivers")
    constructors_data = get(base, "/api/standings/constructors")

    drivers = []
    constructors = []

    # Drivers
    if drivers_data is not None:
        drivers = require_list(drivers_data, "drivers", "/api/standings/drivers", min_len=1) or []
        if drivers:
            required = ["position", "driver_id", "driver_name", "constructor_name", "points",
                        "sprint_points", "wins", "podiums"]
            row = drivers[0]
            missing = [k for k in required if k not in row]
            if missing:
                _fail(f"driver standings row missing: {missing}")
            else:
                _ok(f"{len(drivers)} drivers, all required fields present")

            sprint_scorers = [d for d in drivers if d.get("sprint_points", 0) > 0]
            if sprint_scorers:
                _ok(f"{len(sprint_scorers)} drivers have sprint_points > 0")
            else:
                _warn("sprint_points = 0 for all drivers — sprint data may not be ingested")

            # Check leader has points
            leader = min(drivers, key=lambda x: x["position"])
            if leader["points"] == 0:
                _warn(f"Championship leader {leader['driver_name']} has 0 points")
            else:
                _ok(f"Leader: {leader['driver_name']} ({leader['points']} pts)")

    # Constructors
    if constructors_data is not None:
        constructors = require_list(constructors_data, "constructors", "/api/standings/constructors", min_len=1) or []
        if constructors:
            required = ["position", "constructor_id", "constructor_name", "points", "sprint_points", "wins"]
            row = constructors[0]
            missing = [k for k in required if k not in row]
            if missing:
                _fail(f"constructor standings row missing: {missing}")
            else:
                _ok(f"{len(constructors)} constructors, all required fields present")

    return drivers, constructors


def check_predictions_next(base: str) -> tuple[int | None, dict | None, dict | None]:
    print(f"\n{BOLD}[predictions/next]{RST}")
    pre = get(base, "/api/predictions/next/prequali")

    # postquali is only available after qualifying for the upcoming race — treat 404 as expected
    import requests as _req
    _post_resp = _req.get(f"{base}/api/predictions/next/postquali", timeout=10)
    post = _post_resp.json() if _post_resp.ok else None
    if not _post_resp.ok and _post_resp.status_code != 404:
        _fail(f"/api/predictions/next/postquali → HTTP {_post_resp.status_code} (expected 200 or 404)")

    active_round = None

    for label, d in [("prequali", pre), ("postquali", post)]:
        if d is None:
            if label == "postquali":
                _info(f"/api/predictions/next/postquali not yet available (qualifying hasn't happened)")
            else:
                _fail(f"/api/predictions/next/{label} → no response")
            continue
        required = ["round", "race_name", "mode", "rows"]
        if not require_keys(d, required, f"/api/predictions/next/{label}"):
            continue
        rows = d["rows"]
        if not isinstance(rows, list) or len(rows) == 0:
            _fail(f"/api/predictions/next/{label}: rows is empty")
            continue
        row = rows[0]
        row_required = ["driver_id", "constructor_id", "final_score"]
        missing = [k for k in row_required if k not in row]
        if missing:
            _fail(f"/api/predictions/next/{label} row missing: {missing}")
        else:
            _ok(f"/api/predictions/next/{label} → round {d['round']} ({d['race_name']}), {len(rows)} rows, P1={row['driver_id']}")
            if d["mode"] != label:
                _warn(f"/api/predictions/next/{label}: mode field is '{d['mode']}', expected '{label}'")

    if post is not None and "round" in post:
        active_round = post["round"]
    elif pre is not None and "round" in pre:
        active_round = pre["round"]

    # Check prequali and postquali agree on active round
    if pre and post and pre.get("round") != post.get("round"):
        _warn(f"prequali round ({pre.get('round')}) != postquali round ({post.get('round')}) — file mismatch?")

    return active_round, pre, post


def check_predictions_by_round(base: str, rounds_completed: int, active_round: int | None) -> None:
    print(f"\n{BOLD}[predictions by round]{RST}")
    rounds_to_check = list(range(1, (rounds_completed or 0) + 1))
    if active_round and active_round not in rounds_to_check:
        rounds_to_check.append(active_round)

    if not rounds_to_check:
        _warn("No rounds to check (rounds_completed=0 and no active_round)")
        return

    for rn in rounds_to_check:
        for mode in ("prequali", "postquali"):
            # postquali for an upcoming (active) round doesn't exist until after qualifying
            is_upcoming = rn == active_round and rn not in range(1, (rounds_completed or 0) + 1)
            if mode == "postquali" and is_upcoming:
                import requests as _req3
                _r = _req3.get(f"{base}/api/predictions/{rn}/{mode}", timeout=10)
                if _r.status_code == 404:
                    _info(f"/api/predictions/{rn}/postquali not yet available (upcoming race)")
                    continue
            d = get(base, f"/api/predictions/{rn}/{mode}")
            if d is None:
                _fail(f"/api/predictions/{rn}/{mode} → 404 or error")
                continue
            rows = d.get("rows", [])
            if len(rows) < 15:
                _warn(f"/api/predictions/{rn}/{mode}: only {len(rows)} rows (expected ~22)")
            else:
                _ok(f"/api/predictions/{rn}/{mode}: {len(rows)} rows, P1={rows[0].get('driver_id')}")

            # postquali must have grid_position in rationale or pace_vs_grid field
            if mode == "postquali":
                if rows and "pace_vs_grid" not in rows[0]:
                    _warn(f"/api/predictions/{rn}/postquali: 'pace_vs_grid' missing from rows")


def check_race_results(base: str) -> list[int]:
    print(f"\n{BOLD}[race-results]{RST}")
    d = get(base, "/api/race-results")
    if d is None:
        return []
    races = require_list(d, "races", "/api/race-results", min_len=1)
    if not races:
        return []

    result_rounds = []
    for race in races:
        rn = race.get("round")
        result_rounds.append(rn)
        required = ["round", "name", "winner", "podium", "is_sprint", "status"]
        missing = [k for k in required if k not in race]
        if missing:
            _fail(f"/api/race-results round={rn}: missing fields {missing}")
            continue
        if not race["winner"]:
            _fail(f"/api/race-results round={rn}: winner is null")
        else:
            sprint_tag = " (sprint)" if race["is_sprint"] else ""
            _ok(f"Round {rn}: {race['name']} — winner: {race['winner']}{sprint_tag}")

    return result_rounds


def check_metrics(base: str) -> None:
    print(f"\n{BOLD}[metrics]{RST}")
    d = get(base, "/api/metrics")
    if d is None:
        _warn("/api/metrics not available (metrics_summary.json may be missing)")
        return
    required = ["ndcg", "top3_hit", "mae", "alpha"]
    missing = [k for k in required if k not in d]
    if missing:
        _warn(f"/api/metrics: missing fields {missing}")
    else:
        _ok(f"/api/metrics: ndcg={d.get('ndcg')}, top3_hit={d.get('top3_hit')}, alpha={d.get('alpha')}")


def check_consistency(
    status: dict,
    calendar: dict,
    result_rounds: list[int],
    active_round: int | None,
) -> None:
    print(f"\n{BOLD}[cross-endpoint consistency]{RST}")
    rounds_completed = status.get("rounds_completed", 0)
    cal_rounds = [r["round"] for r in calendar.get("races", [])]

    # rounds_completed should match actual result rounds
    if set(result_rounds) != set(range(1, rounds_completed + 1)):
        _warn(
            f"rounds_completed={rounds_completed} but race-results has rounds={sorted(result_rounds)}. "
            f"May indicate sprint-only rounds or data gap."
        )
    else:
        _ok(f"rounds_completed={rounds_completed} consistent with race-results rounds {sorted(result_rounds)}")

    # active round should be rounds_completed + 1
    expected_next = rounds_completed + 1
    if active_round is not None and active_round != expected_next:
        _warn(
            f"active prediction round={active_round} but rounds_completed+1={expected_next}. "
            f"RaceDetail will auto-select round {expected_next}."
        )
    elif active_round == expected_next:
        _ok(f"active prediction round ({active_round}) == rounds_completed+1 ✓")

    # all result rounds should be in calendar
    missing_from_cal = [r for r in result_rounds if r not in cal_rounds]
    if missing_from_cal:
        _fail(f"result rounds {missing_from_cal} not found in calendar")

    # sprint rounds in calendar vs sprint flag in race-results
    sprint_cal = {r["round"] for r in calendar.get("races", []) if r.get("is_sprint")}
    _info(f"sprint rounds per calendar: {sorted(sprint_cal)}")


def check_frontend_contract(base: str, drivers: list, active_round: int | None) -> None:
    """Check that API responses match the exact fields the frontend JS components expect."""
    print(f"\n{BOLD}[frontend contract]{RST}")

    # Home.jsx WDCStandings expects: position, driver_name, constructor_name, points, sprint_points
    if drivers:
        d = drivers[0]
        for field in ("position", "driver_name", "constructor_name", "points", "sprint_points"):
            if field not in d:
                _fail(f"WDCStandings: driver row missing '{field}'")
        _ok("WDCStandings fields satisfied")

    # RaceDetail expects: predictions/next/postquali (or /next fallback) → round, rows[].driver_id
    import requests as _req2
    _nxt_resp = _req2.get(f"{base}/api/predictions/next", timeout=10)
    nxt_pred = _nxt_resp.json() if _nxt_resp.ok else None
    if nxt_pred:
        row = (nxt_pred.get("rows") or [{}])[0]
        for field in ("driver_id", "constructor_id", "final_score"):
            if field not in row:
                _fail(f"OracleCard/RaceDetail postquali row missing '{field}'")
        _ok("OracleCard/RaceDetail postquali fields satisfied")

    # Archive expects: /api/predictions/history → rows with round, driver_id, final_score
    hist = get(base, "/api/predictions/history")
    if hist is None:
        _warn("/api/predictions/history not reachable")
    else:
        rows = hist if isinstance(hist, list) else hist.get("predictions", [])
        if not rows:
            _warn("/api/predictions/history: empty — Archive page will show 'No prediction history yet'")
        else:
            row = rows[0]
            for field in ("round", "driver_id", "final_score"):
                if field not in row:
                    _fail(f"Archive predictions/history row missing '{field}'")
            _ok(f"Archive predictions/history: {len(rows)} rows")

    # WeekendFeed expects calendar race to have is_sprint bool
    cal = get(base, "/api/calendar")
    if cal:
        sprint_races = [r for r in cal.get("races", []) if r.get("is_sprint")]
        if not sprint_races:
            _warn("WeekendFeed: no races have is_sprint=true — sprint timeline step won't render")
        else:
            _ok(f"WeekendFeed: {len(sprint_races)} races have is_sprint=true")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="F1RacePred end-to-end test suite")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"\n{BOLD}{'='*60}{RST}")
    print(f"{BOLD} F1RacePred E2E Test Suite  →  {base}{RST}")
    print(f"{BOLD}{'='*60}{RST}")

    check_health(base)
    status = check_status(base)
    calendar = check_calendar(base)
    drivers, constructors = check_standings(base)
    active_round, pre, post = check_predictions_next(base)
    check_predictions_by_round(base, status.get("rounds_completed", 0), active_round)
    result_rounds = check_race_results(base)
    check_metrics(base)
    check_consistency(status, calendar, result_rounds, active_round)
    check_frontend_contract(base, drivers, active_round)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}{RST}")
    total_issues = len(FAILURES) + len(WARNINGS)
    if not FAILURES and not WARNINGS:
        print(f"{GRN}{BOLD} ALL CHECKS PASSED{RST}")
    else:
        if FAILURES:
            print(f"\n{RED}{BOLD}FAILURES ({len(FAILURES)}):{RST}")
            for f in FAILURES:
                print(f"  {RED}x{RST} {f}")
        if WARNINGS:
            print(f"\n{YLW}{BOLD}WARNINGS ({len(WARNINGS)}):{RST}")
            for w in WARNINGS:
                print(f"  {YLW}!{RST} {w}")

    print(f"\n  {len(FAILURES)} failure(s)  {len(WARNINGS)} warning(s)  {total_issues} total issue(s)")
    print(f"{BOLD}{'='*60}{RST}\n")

    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()

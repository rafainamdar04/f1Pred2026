# F1RacePred Operations Runbook

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ADMIN_API_KEY` | **Yes** | — | 32+ char secret. All admin endpoints require `X-API-Key: <value>` |
| `SCHEDULER_ENABLED` | No | `false` | Set `true` to enable APScheduler auto-jobs. Off by default in Docker. |
| `CURRENT_SEASON` | No | `2026` | Season year |
| `DATABASE_URL` | No | `sqlite:///data/f1ranker.db` | SQLite path |

Minimal production `.env`:
```
ADMIN_API_KEY=<32+ char random string>
SCHEDULER_ENABLED=true
```

---

## Manual Trigger Commands

All commands require `X-API-Key` header. Add `?round=N` to target a specific round; omit to use the next scheduled race.

### Using curl
```bash
BASE=http://localhost:8000
KEY=<your-admin-key>

# Thursday — pre-qualifying predictions
curl -s -X POST "$BASE/api/admin/trigger-job/run_prequali?round=5" -H "X-API-Key: $KEY"

# Saturday — ingest qualifying results
curl -s -X POST "$BASE/api/admin/trigger-job/ingest_quali?round=5" -H "X-API-Key: $KEY"

# Saturday — ingest sprint results (sprint weekends only)
curl -s -X POST "$BASE/api/admin/trigger-job/ingest_sprint?round=5" -H "X-API-Key: $KEY"

# Saturday — post-qualifying predictions (auto-triggered by ingest_quali on success)
curl -s -X POST "$BASE/api/admin/trigger-job/run_postquali?round=5" -H "X-API-Key: $KEY"

# Sunday+3h — ingest race results
curl -s -X POST "$BASE/api/admin/trigger-job/ingest_results?round=5" -H "X-API-Key: $KEY"

# Sunday+3h — score predictions vs actual (auto-triggered by ingest_results on success)
curl -s -X POST "$BASE/api/admin/trigger-job/score_predictions?round=5" -H "X-API-Key: $KEY"

# Check pipeline status (public, no key needed)
curl -s "$BASE/api/status" | python -m json.tool
```

### Job Names Reference

| Job name | When it runs | What it does |
|---|---|---|
| `run_prequali` | Thursday 12:00 UTC | Feature build + pre-quali predictions |
| `ingest_quali` | Saturday +30 min after quali end | Fetch qualifying from FastF1; triggers `run_postquali` |
| `ingest_sprint` | Saturday +90 min after sprint end | Fetch sprint results from FastF1 |
| `run_postquali` | Auto after `ingest_quali` | Post-quali predictions using grid positions |
| `ingest_results` | Sunday +3 h after race end | Fetch race results from FastF1; triggers `score_predictions` |
| `score_predictions` | Auto after `ingest_results` | Evaluate model accuracy; write metrics |
| `retrain_model` | Auto after `ingest_results` | Re-train pre/post-quali XGBoost models |

All ingestion jobs retry 3 times with 15-minute spacing before logging `status=failed`.

---

## 2026 Sprint Race Calendar

| Round | Venue | Race Date | Sprint Ingest After |
|---|---|---|---|
| 2 | China (Shanghai) | 2026-03-15 | 2026-03-14 ~09:00 UTC |
| 4 | USA (Miami) | 2026-05-03 | 2026-05-02 ~21:00 UTC |
| 5 | Canada (Montreal) | 2026-05-24 | 2026-05-23 ~21:00 UTC |
| 9 | Great Britain (Silverstone) | 2026-07-05 | 2026-07-04 ~13:30 UTC |
| 12 | Netherlands (Zandvoort) | 2026-08-23 | 2026-08-22 ~12:30 UTC |
| 16 | Singapore | 2026-10-11 | 2026-10-10 ~11:00 UTC |

Sprint ingest runs 90 minutes after sprint_end_utc. Sprint failure never blocks prediction jobs.

---

## Weekly Check Sequence

### Thursday (pre-qualifying)
1. **12:00 UTC** — `run_prequali` fires automatically (if `SCHEDULER_ENABLED=true`)
2. Check: `GET /api/status` → `jobs.run_prequali.status == "success"`
3. If failed: `POST /api/admin/trigger-job/run_prequali?round=N`

### Saturday (qualifying + optional sprint)
1. **Sprint weekend only**: `ingest_sprint` fires 90 min after sprint end
   - Check: `jobs.ingest_sprint.status == "success"` and `GET /api/standings/drivers/sprints`
   - If failed: `POST /api/admin/trigger-job/ingest_sprint?round=N`
2. **+30 min after qualifying end**: `ingest_quali` fires; on success triggers `run_postquali`
   - Check: `jobs.ingest_quali.status == "success"` and `jobs.run_postquali.status == "success"`
   - If ingest_quali failed: `POST /api/admin/trigger-job/ingest_quali?round=N`
   - If only run_postquali failed: `POST /api/admin/trigger-job/run_postquali?round=N`

### Sunday (race day)
1. **+3 h after race end**: `ingest_results` fires; on success triggers `score_predictions` then `retrain_model`
   - Check: `jobs.ingest_results.status == "success"` and `jobs.score_predictions.status == "success"`
   - If failed: `POST /api/admin/trigger-job/ingest_results?round=N`
2. Verify standings: `GET /api/standings/drivers` — check total points are consistent
3. Verify predictions: `GET /api/predictions/{round}/comparison`

### Monday (data hygiene)
1. `GET /api/status` — confirm all jobs show `status == "success"` for the weekend
2. If `jobs.*.status == "failed"` for any job, check `error_message` and re-trigger manually
3. Review `GET /api/race-results` — confirm race winner and sprint results appear correctly
4. Confirm no duplicate rows: the CSV key is `(season, round, driver_id, session_type)`

---

## Verification Rules (enforced automatically)

| Session | Row count | Points check |
|---|---|---|
| Race (`session_type='R'`) | must be 22 | total = 101 (no FL) or 102 (FL awarded) |
| Sprint (`session_type='S'`) | must be 22 | total = 36 (8+7+6+5+4+3+2+1) |
| Qualifying | 20+ drivers with a grid position | — |

If verification fails, `PipelineRun.status` is set to `"failed"` and the error is visible at `/api/status` under `jobs.<job_name>.error_message`. Data is **not** rolled back — inspect the CSV and re-ingest manually if needed.

---

## Track Isolation Guarantee

**Prediction pipeline reads race rows only (`session_type='R'`).**
Sprint rows (`session_type='S'`) are used exclusively for standings computations. The filter is applied at data load time in `scripts/build_processed_features.py`. No sprint data enters the XGBoost models.

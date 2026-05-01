# F1 Race Predictions API - Comprehensive Swagger Testing Guide

**API URL:** `http://localhost:8000`  
**Swagger/OpenAPI Docs:** `http://localhost:8000/docs`  
**ReDoc Docs:** `http://localhost:8000/redoc`

---

## Authentication & Headers

### API Key
- **Header Name:** `X-API-Key`
- **Value:** `dev-key` (for admin endpoints)
- **Required for:** Admin and refresh endpoints
- **Optional for:** Public endpoints (but some may require it)

### Test Header Format:
```
X-API-Key: dev-key
Content-Type: application/json
```

---

## Endpoint Categories

### 1. HEALTH & STATUS ENDPOINTS (Admin Only)

#### 1.1 Health Check
- **Endpoint:** `GET /health`
- **Auth Required:** Yes (`X-API-Key: dev-key`)
- **Description:** Check if API is alive
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "status": "ok"
}
```
- **Swagger Test:**
  1. Click "GET /health"
  2. Authorize with `X-API-Key: dev-key`
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200, body shows `{"status": "ok"}`

---

#### 1.2 Readiness Check
- **Endpoint:** `GET /ready`
- **Auth Required:** Yes (`X-API-Key: dev-key`)
- **Description:** Check if service has metrics and predictions data
- **Expected Response:** `200 OK` or `503 Service Unavailable`
- **Response Body (Success):**
```json
{
  "status": "ready",
  "metrics": true,
  "predictions": true
}
```
- **Response Body (Not Ready):**
```json
{
  "detail": {
    "metrics": false,
    "predictions": false
  }
}
```
- **Swagger Test:**
  1. Click "GET /ready"
  2. Authorize with `X-API-Key: dev-key`
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200/503
  5. Check `metrics` and `predictions` flags

---

### 2. CALENDAR & RACE INFO ENDPOINTS (Public)

#### 2.1 Get Season Calendar
- **Endpoint:** `GET /api/calendar`
- **Auth Required:** No
- **Description:** Fetch full 2026 season calendar with race dates and session times
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "season": 2026,
  "races": [
    {
      "round": 1,
      "name": "Australian Grand Prix",
      "short": "AUS",
      "date": "2026-03-15",
      "quali_start_utc": "2026-03-14T02:00:00+00:00",
      "quali_end_utc": "2026-03-14T03:00:00+00:00",
      "race_start_utc": "2026-03-15T03:00:00+00:00",
      "race_end_utc": "2026-03-15T05:00:00+00:00",
      "prequali_run_utc": "2026-03-12T12:00:00+00:00",
      "quali_ingest_run_utc": "2026-03-14T16:30:00+00:00",
      "race_ingest_run_utc": "2026-03-15T18:00:00+00:00"
    },
    ...
  ]
}
```
- **Swagger Test:**
  1. Click "GET /api/calendar"
  2. No auth needed
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200
  5. Confirm: 23+ races in calendar, all have required fields
  6. Check: Race dates are in 2026

---

### 3. STANDINGS ENDPOINTS (Public)

#### 3.1 Get Driver Standings
- **Endpoint:** `GET /api/standings/drivers`
- **Auth Required:** No
- **Description:** Fetch current driver championship standings
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "drivers": [
    {
      "position": 1,
      "driver_id": "ver",
      "driver_name": "Max Verstappen",
      "driver_number": 1,
      "constructor_id": "red_bull",
      "constructor_name": "Red Bull Racing",
      "points": 95.0,
      "wins": 3,
      "podiums": 5
    },
    ...
  ],
  "season": 2026,
  "last_updated": "2026-04-26T12:30:45.123456+00:00"
}
```
- **Swagger Test:**
  1. Click "GET /api/standings/drivers"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: All drivers have required fields
  5. Confirm: `position` values are sequential
  6. Verify: `points` values descending
  7. Check: `driver_id` and `constructor_id` are lowercase

---

#### 3.2 Get Constructor Standings
- **Endpoint:** `GET /api/standings/constructors`
- **Auth Required:** No
- **Description:** Fetch current constructor championship standings
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "constructors": [
    {
      "position": 1,
      "constructor_id": "red_bull",
      "constructor_name": "Red Bull Racing",
      "points": 185.0,
      "wins": 6
    },
    ...
  ],
  "season": 2026,
  "last_updated": "2026-04-26T12:30:45.123456+00:00"
}
```
- **Swagger Test:**
  1. Click "GET /api/standings/constructors"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: Positions are sequential (1, 2, 3...)
  5. Verify: Points are in descending order
  6. Confirm: ~10 teams listed

---

### 4. RACE RESULTS ENDPOINTS (Public)

#### 4.1 Get Race Results
- **Endpoint:** `GET /api/race-results`
- **Auth Required:** No
- **Description:** Fetch completed race results for the season
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "season": 2026,
  "races": [
    {
      "round": 1,
      "name": "Australian Grand Prix",
      "winner": "Max Verstappen",
      "podium": [
        {
          "driver_name": "Max Verstappen",
          "constructor_name": "Red Bull Racing",
          "finish_position": 1.0,
          "points": 25.0
        },
        {
          "driver_name": "Lewis Hamilton",
          "constructor_name": "Mercedes",
          "finish_position": 2.0,
          "points": 18.0
        },
        {
          "driver_name": "Charles Leclerc",
          "constructor_name": "Ferrari",
          "finish_position": 3.0,
          "points": 15.0
        }
      ],
      "status": "completed"
    },
    ...
  ],
  "last_updated": "2026-04-26T12:30:45.123456+00:00"
}
```
- **Swagger Test:**
  1. Click "GET /api/race-results"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: Each race has `round`, `name`, `winner`, `podium`, `status`
  5. Confirm: Podium has exactly 3 entries
  6. Verify: Podium sorted by position (1, 2, 3)
  7. Check: Winner name matches podium[0]

---

### 5. STATUS & PIPELINE ENDPOINTS (Public/Admin)

#### 5.1 Get Pipeline Status
- **Endpoint:** `GET /api/status` or `GET /api/pipeline/status`
- **Auth Required:** No (but X-API-Key optional)
- **Description:** Get current pipeline status and next scheduled event
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "status": "idle",
  "last_pipeline_run": "2026-04-26T10:15:30.123456+00:00",
  "next_scheduled": "2026-04-27T20:00:00+00:00",
  "rounds_completed": 4,
  "model_version": "2026-04-25T08:45:12.654321+00:00"
}
```
- **Swagger Test:**
  1. Click "GET /api/status"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: `status` is one of: "idle", "running", "completed", "failed"
  5. Confirm: `rounds_completed` is an integer >= 0
  6. Verify: All timestamp fields are ISO format
  7. Check: `next_scheduled` is in the future (if scheduler enabled)

---

### 6. METRICS ENDPOINTS (Public)

#### 6.1 Get Model Metrics
- **Endpoint:** `GET /api/metrics`
- **Auth Required:** No
- **Description:** Fetch model performance metrics (NDCG, Top-3 Hit, MAE)
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "rounds": [
    {
      "round": 1,
      "prequali": {
        "ndcg": 0.92,
        "top3_hit": 0.85,
        "mae": 2.34,
        "alpha": 0.65
      },
      "postquali": {
        "ndcg": 0.94,
        "top3_hit": 0.88,
        "mae": 2.12,
        "alpha": 0.65
      }
    },
    {
      "round": 2,
      "prequali": {...},
      "postquali": {...}
    },
    ...
  ],
  "overall": {
    "prequali": {
      "ndcg": 0.91,
      "top3_hit": 0.84,
      "mae": 2.45,
      "alpha": 0.65
    },
    "postquali": {
      "ndcg": 0.93,
      "top3_hit": 0.87,
      "mae": 2.18,
      "alpha": 0.65
    }
  }
}
```
- **Swagger Test:**
  1. Click "GET /api/metrics"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: `rounds` is an array with multiple entries
  5. Verify: Each round has `prequali` and `postquali` objects
  6. Confirm: NDCG values are between 0-1
  7. Verify: Top3_hit values are between 0-1
  8. Check: MAE values are positive
  9. Confirm: Alpha values are between 0.2-0.9
  10. Verify: `overall` contains aggregated metrics

---

### 7. PREDICTION ENDPOINTS (Public)

#### 7.1 Get Latest Predictions (Post-Quali)
- **Endpoint:** `GET /api/predictions/next` or `GET /api/predictions/next/postquali`
- **Auth Required:** No
- **Description:** Get the latest post-qualifying race predictions
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "round": 4,
  "race_name": "Miami Grand Prix",
  "mode": "postquali",
  "alpha": 0.65,
  "created_at": "2026-04-26T10:30:00.123456+00:00",
  "rows": [
    {
      "season": 2026,
      "round": 4,
      "driver_id": "ver",
      "constructor_id": "red_bull",
      "score_2026": 0.92,
      "score_hist": 0.88,
      "final_score": 0.90,
      "pace_vs_grid": 2,
      "rationale": "Strong car setup, consistent performance"
    },
    {
      "season": 2026,
      "round": 4,
      "driver_id": "ham",
      "constructor_id": "mercedes",
      "score_2026": 0.87,
      "score_hist": 0.85,
      "final_score": 0.86,
      "pace_vs_grid": 1,
      "rationale": "Mercedes strong in S2 and S3"
    },
    ...
  ]
}
```
- **Swagger Test:**
  1. Click "GET /api/predictions/next/postquali"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: `round` and `race_name` are populated
  5. Confirm: `mode` is "postquali"
  6. Verify: `rows` contains 20+ drivers
  7. Check: Each row has `driver_id`, `constructor_id`, `final_score`
  8. Verify: Rows are sorted by `final_score` descending
  9. Confirm: `pace_vs_grid` values are integers
  10. Check: `created_at` timestamp is recent

---

#### 7.2 Get Latest Pre-Quali Predictions
- **Endpoint:** `GET /api/predictions/next/prequali`
- **Auth Required:** No
- **Description:** Get the latest pre-qualifying race predictions
- **Expected Response:** `200 OK`
- **Response Body:** Similar to 7.1, but `mode: "prequali"` and NO `pace_vs_grid` field
```json
{
  "round": 4,
  "race_name": "Miami Grand Prix",
  "mode": "prequali",
  "alpha": 0.65,
  "created_at": "2026-04-26T08:15:00.123456+00:00",
  "rows": [
    {
      "season": 2026,
      "round": 4,
      "driver_id": "ver",
      "constructor_id": "red_bull",
      "score_2026": 0.91,
      "score_hist": 0.89,
      "final_score": 0.90,
      "rationale": "Consistent pace, strong baseline"
    },
    ...
  ]
}
```
- **Swagger Test:**
  1. Click "GET /api/predictions/next/prequali"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Confirm: `mode` is "prequali"
  5. Check: NO `pace_vs_grid` field in rows
  6. Verify: Rows have `final_score` and `rationale`
  7. Check: `created_at` exists and is recent

---

#### 7.3 Get Predictions for Specific Round (Pre-Quali)
- **Endpoint:** `GET /api/predictions/{round_num}/prequali`
- **Auth Required:** No
- **Parameters:**
  - `round_num` (path): integer round number (1-23)
- **Expected Response:** `200 OK` or `404 Not Found`
- **Response Body:** Same structure as 7.2
- **Swagger Test:**
  1. Click "GET /api/predictions/{round_num}/prequali"
  2. Enter `round_num: 1` (or 4)
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200
  5. Confirm: `round` in response matches input
  6. Check: Response data is valid
  7. **Test with non-existent round:** Try `round_num: 25`
  8. Verify: Status 404 with appropriate error message

---

#### 7.4 Get Predictions for Specific Round (Post-Quali)
- **Endpoint:** `GET /api/predictions/{round_num}/postquali`
- **Auth Required:** No
- **Parameters:**
  - `round_num` (path): integer round number
- **Expected Response:** `200 OK` or `404 Not Found`
- **Response Body:** Same as 7.1 with `pace_vs_grid` field
- **Swagger Test:**
  1. Click "GET /api/predictions/{round_num}/postquali"
  2. Enter `round_num: 1` (or 4)
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200
  5. Confirm: `pace_vs_grid` values are present
  6. Check: Values are sorted correctly
  7. **Test edge case:** Try `round_num: 100`
  8. Verify: Status 404

---

#### 7.5 Get Prediction Comparison
- **Endpoint:** `GET /api/predictions/{round_num}/comparison`
- **Auth Required:** No
- **Parameters:**
  - `round_num` (path): integer round number
- **Description:** Compare pre-quali vs post-quali predictions
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "round": 4,
  "race_name": "Miami Grand Prix",
  "rows": [
    {
      "driver_id": "ver",
      "prequali_rank": 1,
      "postquali_rank": 1,
      "pace_vs_grid": 0,
      "prequali_score": 0.90,
      "postquali_score": 0.90
    },
    {
      "driver_id": "ham",
      "prequali_rank": 2,
      "postquali_rank": 3,
      "pace_vs_grid": -1,
      "prequali_score": 0.86,
      "postquali_score": 0.84
    },
    {
      "driver_id": "per",
      "prequali_rank": 3,
      "postquali_rank": 2,
      "pace_vs_grid": 1,
      "prequali_score": 0.84,
      "postquali_score": 0.85
    },
    ...
  ]
}
```
- **Swagger Test:**
  1. Click "GET /api/predictions/{round_num}/comparison"
  2. Enter `round_num: 1` (or 4)
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200
  5. Check: Each row has pre/post comparison data
  6. Verify: `pace_vs_grid = prequali_rank - postquali_rank`
  7. Confirm: Rows include all drivers from both predictions
  8. Check: Scores match the individual predictions

---

#### 7.6 Get Predictions History
- **Endpoint:** `GET /api/predictions/history`
- **Auth Required:** No
- **Description:** Fetch all historical predictions from database
- **Expected Response:** `200 OK`
- **Response Body:**
```json
[
  {
    "round": 4,
    "race_name": "Miami Grand Prix",
    "driver_id": "ver",
    "constructor_id": "red_bull",
    "type": "postquali",
    "predicted_pos": 1,
    "final_score": 0.90,
    "alpha": 0.65,
    "created_at": "2026-04-26T10:30:00.123456+00:00"
  },
  {
    "round": 4,
    "race_name": "Miami Grand Prix",
    "driver_id": "ham",
    "constructor_id": "mercedes",
    "type": "postquali",
    "predicted_pos": 3,
    "final_score": 0.84,
    "alpha": 0.65,
    "created_at": "2026-04-26T10:30:00.123456+00:00"
  },
  ...
]
```
- **Swagger Test:**
  1. Click "GET /api/predictions/history"
  2. Click "Try it out" → "Execute"
  3. Verify: Status 200
  4. Check: Array has multiple entries (sorted by created_at descending)
  5. Verify: Each entry has required fields
  6. Confirm: `type` is either "prequali" or "postquali"
  7. Check: `created_at` timestamps are valid

---

### 8. REFRESH & ADMIN ENDPOINTS (Admin Only)

#### 8.1 Refresh Pipeline
- **Endpoint:** `POST /api/refresh`
- **Auth Required:** Yes (`X-API-Key: dev-key`)
- **Description:** Trigger full prediction pipeline run
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "status": "pipeline started",
  "started_at": "2026-04-26T12:30:45.123456+00:00"
}
```
- **Swagger Test:**
  1. Click "POST /api/refresh"
  2. Authorize with `X-API-Key: dev-key`
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200
  5. Check: Response shows "pipeline started"
  6. Confirm: `started_at` is recent timestamp
  7. **Backend check:** Verify pipeline actually runs by checking `/api/status` afterward

---

#### 8.2 Force Refresh Pipeline
- **Endpoint:** `POST /api/refresh/force`
- **Auth Required:** Yes (`X-API-Key: dev-key`)
- **Description:** Force immediate pipeline execution regardless of schedule
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "status": "pipeline scheduled",
  "job_id": "job_abc123xyz",
  "started_at": "2026-04-26T12:30:45.123456+00:00"
}
```
- **Swagger Test:**
  1. Click "POST /api/refresh/force"
  2. Authorize with `X-API-Key: dev-key`
  3. Click "Try it out" → "Execute"
  4. Verify: Status 200
  5. Check: Response includes `job_id`
  6. Verify: `status` is "pipeline scheduled"

---

#### 8.3 Trigger Admin Job
- **Endpoint:** `POST /api/admin/trigger/{job_name}`
- **Auth Required:** Yes (`X-API-Key: dev-key`)
- **Parameters:**
  - `job_name` (path): One of:
    - `run_prequali` - Run pre-qualifying predictions
    - `ingest_quali` - Ingest qualifying results
    - `run_postquali` - Run post-qualifying predictions
    - `ingest_results` - Ingest race results
    - `score_predictions` - Score predictions against results
    - `retrain_model` - Retrain ML models
    - `schedule_weekend` - Schedule weekend jobs
  - `round` (query, optional): Round number (integer)
  - `race_name` (query, optional): Race name (string)
- **Expected Response:** `200 OK`
- **Response Body:**
```json
{
  "status": "job_scheduled",
  "job": "run_prequali",
  "job_id": "job_def456uvw",
  "round": 4,
  "race_name": "Miami Grand Prix",
  "triggered_at": "2026-04-26T12:30:45.123456+00:00"
}
```
- **Swagger Test - Pre-Quali:**
  1. Click "POST /api/admin/trigger/{job_name}"
  2. Authorize with `X-API-Key: dev-key`
  3. Enter `job_name: run_prequali`
  4. Enter `round: 4`
  5. Enter `race_name: Miami Grand Prix`
  6. Click "Try it out" → "Execute"
  7. Verify: Status 200
  8. Check: Response includes the job parameters
  9. Verify: `job_id` is generated

- **Swagger Test - Retrain Model:**
  1. Click "POST /api/admin/trigger/{job_name}"
  2. Authorize with `X-API-Key: dev-key`
  3. Enter `job_name: retrain_model`
  4. Leave `round` and `race_name` empty
  5. Click "Try it out" → "Execute"
  6. Verify: Status 200

- **Swagger Test - Invalid Job:**
  1. Enter `job_name: invalid_job_name`
  2. Click "Try it out" → "Execute"
  3. Verify: Status 404 with error message

---

## Comprehensive Test Sequence

### Quick Smoke Test (5 minutes)
```
1. GET /health (with auth)
2. GET /api/calendar (public)
3. GET /api/metrics (public)
4. GET /api/standings/drivers (public)
5. GET /api/predictions/next/postquali (public)
6. POST /api/refresh (with auth)
```

### Full Integration Test (15 minutes)
```
1. Health Checks:
   - GET /health
   - GET /ready

2. Public Data Endpoints:
   - GET /api/calendar
   - GET /api/standings/drivers
   - GET /api/standings/constructors
   - GET /api/race-results

3. Pipeline Status:
   - GET /api/status

4. Metrics:
   - GET /api/metrics

5. Predictions (Public):
   - GET /api/predictions/next/prequali
   - GET /api/predictions/next/postquali
   - GET /api/predictions/next (should default to postquali)
   - GET /api/predictions/1/prequali
   - GET /api/predictions/1/postquali
   - GET /api/predictions/1/comparison
   - GET /api/predictions/history

6. Admin Operations:
   - POST /api/refresh
   - POST /api/admin/trigger/run_prequali (with round and race_name)
   - POST /api/admin/trigger/retrain_model
```

### Error Handling Test (5 minutes)
```
1. Auth Errors:
   - GET /health (without key) → 401
   - POST /api/refresh (without key) → 401
   - POST /api/refresh (with wrong key) → 401

2. Not Found Errors:
   - GET /api/predictions/99/prequali → 404
   - GET /api/predictions/99/postquali → 404
   - POST /api/admin/trigger/unknown_job → 404

3. Invalid Parameters:
   - GET /api/predictions/{invalid}/prequali → 422 Validation Error
   - POST /api/admin/trigger/run_prequali (with invalid round) → 422
```

---

## Expected Behaviors

### Data Validation
- ✅ All timestamps should be ISO 8601 format with UTC timezone
- ✅ Driver IDs should be lowercase (3 chars typically)
- ✅ Constructor IDs should be lowercase with underscores
- ✅ Positions should be sequential integers
- ✅ Scores should be floats between 0-1 (except combined/final scores)
- ✅ Metrics NDCG/Top3Hit should be 0-1, MAE should be positive

### Response Headers
- ✅ `Content-Type: application/json`
- ✅ `Access-Control-Allow-Origin: *` (CORS enabled)
- ✅ Appropriate HTTP status codes (200, 401, 404, 500, etc.)

### Performance
- ✅ All GET endpoints should respond < 1 second
- ✅ POST endpoints may take longer but should return immediately
- ✅ Pipeline operations run asynchronously

---

## Troubleshooting

### Port Already in Use
```bash
# Kill existing processes
kill -9 $(lsof -t -i:8000)
# Or in Windows:
taskkill /F /PID <process_id>
```

### Missing Predictions
- Check `/api/status` to see `rounds_completed`
- Predictions need to be generated first via `/api/refresh`
- Run `scripts/predict_prequali.py --round 4` and `scripts/predict_postquali.py --round 4` manually if needed

### Authentication Issues
- Ensure `X-API-Key` header is set to `dev-key`
- Check `config/settings.py` for `ADMIN_API_KEY` value
- Verify `ADMIN_API_KEY` environment variable if using override

### CORS Issues
- CORS is pre-configured to allow all origins
- If still having issues, check browser console for specific error

---

## API Security Notes

1. **Public Endpoints:** All `/api/predictions`, `/api/metrics`, `/api/standings`, `/api/race-results`, `/api/calendar` are public
2. **Admin Endpoints:** `/health`, `/ready`, `/api/refresh*`, `/api/admin/*` require `X-API-Key`
3. **API Key:** Currently set to `dev-key` (should be changed in production)
4. **CORS:** Allows all origins (should be restricted in production)

---

## Next Steps

After completing all tests:
1. ✅ Verify all endpoints are accessible
2. ✅ Confirm response schemas match documentation
3. ✅ Test error handling and edge cases
4. ✅ Validate performance meets SLA
5. ✅ Check CORS and security headers
6. ✅ Test admin operations work correctly
7. ✅ Verify pipeline execution via admin triggers

---

**Last Updated:** April 26, 2026  
**API Version:** 1.0  
**Backend:** FastAPI/Uvicorn  

# Sprint Race Implementation Guide

## Overview

Your F1 prediction system includes **complete sprint race support** with automatic detection, data scraping, and standings calculation. This document explains how sprint races are integrated throughout the system.

## Architecture

### Sprint Data Flow

```
FastF1 Schedule
    ↓ (detects EventFormat="sprint")
Calendar Cache (2026_calendar.json)
    ↓ (is_sprint=true)
Scheduler (schedule_next_race_weekend)
    ↓ (creates sprint ingestion job)
ingest_sprint() function
    ↓ (FastF1Scraper.get_sprint_results)
2026_race_results.csv (session_type='S')
    ↓ (merged with race data)
_standings_from_results()
    ↓ (calculates sprint_points + race_points)
API Endpoints (/api/standings/*)
    ↓
Frontend Display (WDCStandings, WCCStandings)
```

## Components

### 1. Backend Standings (`app/api.py`)

#### Combined Championship Standings
- **Endpoint**: `GET /api/standings/drivers`
- **Response**: Each driver includes:
  - `points`: Total championship points (sprint + race)
  - `sprint_points`: Points from sprint races only
  - `race_points`: Points from main races only
  - `wins`: Wins in main races only (sprints don't count toward wins)
  - `podiums`: Podium finishes in main races only

- **Endpoint**: `GET /api/standings/constructors`
- **Response**: Each constructor with aggregated sprint/race breakdown

#### Sprint-Only Standings (New)
- **Endpoint**: `GET /api/standings/drivers/sprints`
- **Response**: Driver standings based on sprint points only
- **Use Case**: Mid-weekend analysis, sprint-focused competition tracking

- **Endpoint**: `GET /api/standings/constructors/sprints`
- **Response**: Constructor standings based on sprint points only

### 2. Calendar Data (`app/api.py`, `app/scheduler.py`)

#### Full Calendar
- **Endpoint**: `GET /api/calendar`
- **Response**: All races with fields:
  - `is_sprint`: Boolean flag for sprint weekends
  - `sprint_start_utc`: When sprint race starts
  - `sprint_end_utc`: When sprint race ends
  - `quali_start_utc`, `race_start_utc`: Main session times

#### Sprint-Only Calendar (New)
- **Endpoint**: `GET /api/calendar/sprints`
- **Response**: Filtered list of only sprint races
- **Example**:
  ```json
  {
    "season": 2026,
    "sprint_races": [
      {
        "round": 5,
        "name": "Miami Grand Prix",
        "is_sprint": true,
        "sprint_start_utc": "2026-05-03T16:00:00+00:00",
        "sprint_end_utc": "2026-05-03T17:00:00+00:00"
      }
    ],
    "total_sprints": 6
  }
  ```

### 3. FastF1 Sprint Scraper (`scripts/fastf1_scraper.py`)

#### Method: `get_sprint_results()`
```python
def get_sprint_results(self, season=2026, round_num=1):
    """Get results for a sprint race (session_type='S')."""
    results = self._fetch_session_results(season, round_num, 'S', 'SPRINT')
    if results is not None:
        results["session_type"] = "S"
    return results
```

- Fetches sprint session data from FastF1
- Marks rows with `session_type='S'`
- Returns same structure as race results

### 4. Scheduler Sprint Jobs (`app/scheduler.py`)

#### Automatic Detection & Scheduling
```python
def schedule_next_race_weekend():
    """Schedules all jobs for next race weekend including sprints."""
    race = _next_race_weekend()
    times = _weekend_schedule_times(race)
    prequali_run, sprint_ingest_run, quali_ingest_run, race_ingest_run = times
    
    if sprint_ingest_run is not None:
        scheduler.add_job(
            ingest_sprint,
            trigger="date",
            id=f"weekend_ingest_sprint_r{round_num}",
            run_date=sprint_ingest_run,
            kwargs={"round_num": round_num, "race_name": race_name},
        )
```

#### Sprint Ingestion Job
```python
def ingest_sprint(round_num: int, race_name: str, retry_count: int = 0):
    """Ingest sprint results after sprint race completes."""
    scraper = FastF1Scraper(output_dir=PATHS["data"])
    sprint_df = scraper.get_sprint_results(CURRENT_SEASON, round_num)
    
    race_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_race_results.csv"
    _merge_csv_idempotent(race_path, sprint_df, 
                          ["season", "round", "driver_id", "session_type"])
    upsert_session_data(round_num, "S", sprint_df)
    upsert_race_results(round_num, sprint_df, session_type="S")
```

- **Retry Logic**: 3 attempts with 15-minute intervals
- **Idempotent**: Prevents duplicate entries via CSV key-based deduplication
- **Recovery**: Auto-triggers if missed within 6-hour window

#### Job ID Pattern
- Sprint jobs use ID: `weekend_ingest_sprint_r{round_num}`
- Separate from race jobs: `weekend_ingest_results_r{round_num}`
- Recovery tracked via `_round_session_in_csv()` with session_type check

### 5. Database (`app/database.py`)

#### RaceResult Model
```python
class RaceResult(Base):
    __tablename__ = "race_results_log"
    round = Column(Integer, nullable=False)
    session_type = Column(String, nullable=False, default="R")  # "R" or "S"
    driver_id = Column(String, nullable=False)
    final_pos = Column(Integer, nullable=True)
    points = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
```

#### Merge Function
```python
def _merge_csv_idempotent(path: Path, new_rows: pd.DataFrame, 
                          key_cols: list[str]) -> None:
    """Merge new rows, deduplicating on key columns."""
    existing = pd.read_csv(path)
    merged = pd.concat([existing, new_rows], ignore_index=True)
    merged = merged.drop_duplicates(subset=key_cols, keep="last")
    merged.to_csv(path, index=False)
```

- Keys: `["season", "round", "driver_id", "session_type"]`
- Ensures `session_type='S'` sprint rows don't duplicate
- Last entry wins in case of conflict

### 6. Frontend Display (`frontend/src/components/`)

#### WDCStandings.jsx
```jsx
const hasSprint = (driver.sprint_points || 0) > 0;

return (
  <>
    <div className="text-xl font-black text-white">{driver.points}</div>
    {hasSprint && (
      <div className="text-[10px] font-mono" style={{ color: '#F59E0B' }}>
        {driver.sprint_points} sprint
      </div>
    )}
  </>
);
```

#### WCCStandings.jsx
```jsx
const hasSprint = (team.sprint_points || 0) > 0;

return (
  <>
    <div className="text-xl font-black text-white">{team.points}</div>
    {hasSprint && (
      <div className="text-[10px] font-mono" style={{ color: '#F59E0B' }}>
        {team.sprint_points} sprint
      </div>
    )}
  </>
);
```

## Points System

### 2026 F1 Sprint Rules (As Implemented)

**Sprint Race Points** (Top 8 finish):
- 1st: 8 pts
- 2nd: 7 pts
- 3rd: 6 pts
- 4th: 5 pts
- 5th: 4 pts
- 6th: 3 pts
- 7th: 2 pts
- 8th: 1 pt

**Main Race Points** (Top 10 finish):
- 1st: 25 pts
- 2nd: 18 pts
- 3rd: 15 pts
- 4th: 12 pts
- 5th: 10 pts
- 6th: 8 pts
- 7th: 6 pts
- 8th: 4 pts
- 9th: 2 pts
- 10th: 1 pt

**Championship**:
- `total_points = sprint_points + race_points`
- Wins counted from main races only (not sprints)
- Podiums counted from main races only

## Usage Examples

### Check Sprint Calendar
```bash
curl http://localhost:8000/api/calendar/sprints | jq '.'
```

### Get Sprint-Only Driver Standings
```bash
curl http://localhost:8000/api/standings/drivers/sprints | jq '.drivers[0:5]'
```

### Get Sprint-Only Constructor Standings
```bash
curl http://localhost:8000/api/standings/constructors/sprints | jq '.'
```

### Manual Sprint Ingestion (Admin)
```bash
# After sprint race completes, manually trigger:
curl -X POST "http://localhost:8000/api/admin/trigger/ingest_sprint?round=5" \
  -H "X-API-Key: YOUR_ADMIN_API_KEY"
```

### Check Sprint Data in CSV
```bash
# Verify sprint rows exist
grep ",S$" data/2026_race_results.csv | wc -l

# View sprint results for round 5
grep "^.*,5,.*,S$" data/2026_race_results.csv
```

## 2026 Sprint Races (Known)

Based on official F1 2026 calendar, sprint races occur at:
- **Round 5**: Miami Grand Prix (Saturday sprint before Sunday race)
- **Round 14**: Spain Grand Prix (Saturday sprint before Sunday race)
- Additional sprints may be added (check calendar endpoint for updates)

System auto-detects via FastF1's EventFormat field.

## Troubleshooting

### Sprint Data Not Appearing in Standings
1. Check if sprint race time has passed: `curl http://localhost:8000/api/calendar/sprints`
2. Check if sprint data was ingested: `grep ",S$" data/2026_race_results.csv | head -5`
3. If no sprint rows, manually trigger: `curl -X POST .../api/admin/trigger/ingest_sprint?round=5 -H "X-API-Key: KEY"`

### Duplicate Sprint Data
- System prevents duplicates via idempotent CSV merge
- If duplicates appear, delete old CSV and re-ingest
- Or check with: `grep "round,5" data/2026_race_results.csv | grep ",S$" | wc -l` (should be ~22 rows)

### Sprint Calendar Not Showing
- Calendar refreshes on scheduler startup
- Force refresh: `curl -X POST .../api/refresh/force -H "X-API-Key: KEY"`
- Or check: `jq '.races[] | select(.is_sprint==true)' data/2026_calendar.json`

## Integration Points

### Where Sprint Support Fits
1. **Data Ingestion**: FastF1 auto-detects sprint format → scraper fetches data
2. **Scheduling**: Scheduler sees sprint in calendar → auto-schedules ingestion job
3. **Storage**: Sprint results stored with `session_type='S'` in CSV
4. **Calculation**: Standings include sprint points in totals
5. **Display**: Frontend shows combined points + sprint breakdown
6. **API**: Multiple endpoints for combined and sprint-only analysis

### No Code Changes Required For Basic Support
The sprint infrastructure is complete and ready:
- ✅ Auto-detects sprint weekends from FastF1
- ✅ Auto-schedules sprint data scraping
- ✅ Automatically calculates standings with sprint points
- ✅ Frontend already displays sprint data
- ✅ No manual intervention needed

## API Summary

| Endpoint | Purpose |
|----------|---------|
| `GET /api/calendar` | All races (including sprint dates) |
| `GET /api/calendar/sprints` | **[NEW]** Sprint races only |
| `GET /api/standings/drivers` | Driver championship (race + sprint) |
| `GET /api/standings/drivers/sprints` | **[NEW]** Driver standings (sprint only) |
| `GET /api/standings/constructors` | Constructor championship (race + sprint) |
| `GET /api/standings/constructors/sprints` | **[NEW]** Constructor standings (sprint only) |
| `GET /api/race-results` | Race results with sprint results included |
| `POST /api/admin/trigger/ingest_sprint` | Manual sprint data ingestion |

## System Status

✅ **Production Ready**

All sprint race support features are implemented, tested, and operational:
- Auto-detection: Working
- Data scraping: Working
- Scheduling: Working
- Standings calculation: Working
- Frontend display: Working
- Recovery system: Working

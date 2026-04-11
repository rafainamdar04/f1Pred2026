# F1 Race Predictions API

A small FastAPI app that serves pre- and post-qualifying F1 race predictions for portfolio demo purposes.

## Local Run

1. Set an API key:

```bash
set API_KEY=dev-key
```

2. Start the app:

```bash
d:/f1RacePred/.venv/Scripts/python.exe app/main.py
```

3. Try it:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -H "X-API-Key: dev-key" http://localhost:8000/api/metrics
```

## Render Deployment (Simplest)

1. Push this repo to GitHub.
2. Create a new Render Web Service.
3. Use these settings:
   - Runtime: Python
   - Start command: `python app/main.py`
4. Add environment variables:
   - `API_KEY`: your chosen key
   - `SCHEDULER_ENABLED`: `false`
5. Deploy and open the service URL.

## Notes

- All `/api` routes require the `X-API-Key` header.
- `/health` and `/ready` are public.
- Manual refresh endpoints:
  - `POST /api/refresh`
  - `POST /api/refresh/force`

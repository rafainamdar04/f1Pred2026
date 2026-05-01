from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, select, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.schemas import RoundPredictions, validate_predictions_file
from config.settings import DATABASE_URL, PATHS

Base = declarative_base()


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String, nullable=False, default="pipeline")
    round = Column(Integer, nullable=True)
    pid = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False)
    rounds_completed = Column(Integer, nullable=False, default=0)
    error_message = Column(String, nullable=True)


class PredictionLog(Base):
    __tablename__ = "predictions_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round = Column(Integer, nullable=False)
    race_name = Column(String, nullable=False)
    prediction_type = Column(String, nullable=False, default="post")
    driver_id = Column(String, nullable=False)
    constructor_id = Column(String, nullable=True)
    predicted_pos = Column(Integer, nullable=False, default=0)
    final_score = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class SessionData(Base):
    __tablename__ = "session_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round = Column(Integer, nullable=False)
    session = Column(String, nullable=False)
    driver_id = Column(String, nullable=False)
    position = Column(Integer, nullable=True)
    lap_time = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class RaceResult(Base):
    __tablename__ = "race_results_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round = Column(Integer, nullable=False)
    driver_id = Column(String, nullable=False)
    final_pos = Column(Integer, nullable=True)
    points = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round = Column(Integer, nullable=False)
    top3_hit_rate = Column(Float, nullable=False)
    ndcg = Column(Float, nullable=False)
    mae = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

Base.metadata.create_all(_engine)


def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    with _engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        columns = {row[1] for row in rows}
        if column_name in columns:
            return
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
        conn.commit()


_ensure_column("pipeline_runs", "job_name", "job_name TEXT NOT NULL DEFAULT 'pipeline'")
_ensure_column("pipeline_runs", "round", "round INTEGER")
_ensure_column("pipeline_runs", "pid", "pid INTEGER")
_ensure_column("predictions_log", "prediction_type", "prediction_type TEXT NOT NULL DEFAULT 'post'")
_ensure_column("predictions_log", "constructor_id", "constructor_id TEXT")
_ensure_column("predictions_log", "predicted_pos", "predicted_pos INTEGER NOT NULL DEFAULT 0")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _count_rounds_completed() -> int:
    predictions_dir = Path(PATHS["predictions"])
    if not predictions_dir.exists():
        return 0
    return len(list(predictions_dir.glob("round_*_postquali_predictions.json")))


def log_job_start(job_name: str, round_num: int | None = None) -> int:
    with SessionLocal() as session:
        run = PipelineRun(
            job_name=job_name,
            round=round_num,
            started_at=_utcnow(),
            finished_at=None,
            status="running",
            rounds_completed=_count_rounds_completed(),
            error_message=None,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return int(run.id)


def log_job_finish(
    run_id: int,
    status: str,
    error_message: str | None = None,
    rounds_completed: int | None = None,
) -> None:
    with SessionLocal() as session:
        run = session.get(PipelineRun, run_id)
        if run is None:
            raise ValueError(f"Pipeline run not found: {run_id}")

        run.status = status
        run.rounds_completed = rounds_completed if rounds_completed is not None else _count_rounds_completed()
        run.error_message = error_message
        if status == "running":
            run.finished_at = None
        else:
            run.finished_at = _utcnow()

        session.commit()


def log_pipeline_start() -> int:
    return log_job_start("pipeline", None)


def log_pipeline_finish(
    run_id: int,
    status: str,
    rounds_completed: int,
    error_message: str | None = None,
) -> None:
    log_job_finish(
        run_id=run_id,
        status=status,
        rounds_completed=rounds_completed,
        error_message=error_message,
    )


def _parse_created_at(payload: dict) -> datetime:
    value = payload.get("created_at")
    if not value:
        return _utcnow()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return _utcnow()


def log_predictions(round_predictions: RoundPredictions, prediction_type: str = "post", created_at: datetime | None = None) -> None:
    created_ts = created_at or _utcnow()
    logs = [
        PredictionLog(
            round=row.round,
            race_name=round_predictions.race_name,
            prediction_type=prediction_type,
            driver_id=row.driver_id,
            constructor_id=getattr(row, "constructor_id", None),
            predicted_pos=index + 1,
            final_score=row.final_score,
            alpha=round_predictions.alpha,
            created_at=created_ts,
        )
        for index, row in enumerate(round_predictions.rows)
    ]

    with SessionLocal() as session:
        session.query(PredictionLog).filter(
            PredictionLog.round == round_predictions.round,
            PredictionLog.prediction_type == prediction_type,
        ).delete()
        session.bulk_save_objects(logs)
        session.commit()


def log_predictions_from_file(path: Path, prediction_type: str) -> None:
    if not path.exists():
        return
    model = validate_predictions_file(str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {}
    created_at = _parse_created_at(payload)
    log_predictions(model, prediction_type=prediction_type, created_at=created_at)


def upsert_session_data(round_num: int, session_type: str, frame) -> None:
    if frame is None or len(frame) == 0:
        return

    with SessionLocal() as session:
        session.query(SessionData).filter(
            SessionData.round == round_num,
            SessionData.session == session_type,
        ).delete()

        rows = []
        for _, row in frame.iterrows():
            position = row.get("grid_position") if session_type == "Q" else row.get("finish_position")
            lap_time = row.get("q3_time") or row.get("q2_time") or row.get("q1_time")
            rows.append(
                SessionData(
                    round=round_num,
                    session=session_type,
                    driver_id=str(row.get("driver_id", "")),
                    position=int(position) if position is not None and str(position) != "nan" else None,
                    lap_time=str(lap_time) if lap_time is not None and str(lap_time) != "nan" else None,
                    created_at=_utcnow(),
                )
            )

        session.bulk_save_objects(rows)
        session.commit()


def upsert_race_results(round_num: int, frame) -> None:
    if frame is None or len(frame) == 0:
        return

    with SessionLocal() as session:
        session.query(RaceResult).filter(RaceResult.round == round_num).delete()
        rows = []
        for _, row in frame.iterrows():
            final_pos = row.get("finish_position")
            points = row.get("points")
            rows.append(
                RaceResult(
                    round=round_num,
                    driver_id=str(row.get("driver_id", "")),
                    final_pos=int(final_pos) if final_pos is not None and str(final_pos) != "nan" else None,
                    points=float(points) if points is not None and str(points) != "nan" else None,
                    created_at=_utcnow(),
                )
            )
        session.bulk_save_objects(rows)
        session.commit()


def log_model_metrics(round_num: int, top3_hit_rate: float, ndcg: float, mae: float, alpha: float) -> None:
    with SessionLocal() as session:
        session.query(ModelMetric).filter(ModelMetric.round == round_num).delete()
        session.add(
            ModelMetric(
                round=round_num,
                top3_hit_rate=top3_hit_rate,
                ndcg=ndcg,
                mae=mae,
                alpha=alpha,
                created_at=_utcnow(),
            )
        )
        session.commit()


def update_pipeline_pid(run_id: int, pid: int) -> None:
    with SessionLocal() as session:
        run = session.get(PipelineRun, run_id)
        if run is not None:
            run.pid = pid
            session.commit()


def scan_orphaned_pipelines() -> None:
    """Mark 'running' rows as 'orphaned' if their PID is no longer alive."""
    import psutil

    with SessionLocal() as session:
        rows = session.query(PipelineRun).filter(PipelineRun.status == "running").all()
        for row in rows:
            if row.pid is None or not psutil.pid_exists(row.pid):
                row.status = "orphaned"
                row.finished_at = _utcnow()
                row.error_message = "Process not found on startup"
        session.commit()

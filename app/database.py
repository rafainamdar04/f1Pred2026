from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

from app.schemas import RoundPredictions
from config.settings import PATHS

Base = declarative_base()


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
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
    driver_id = Column(String, nullable=False)
    final_score = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


_project_root = Path(__file__).resolve().parents[1]
_db_path = _project_root / PATHS["data"] / "f1ranker.db"
_engine = create_engine(
    f"sqlite:///{_db_path}",
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

Base.metadata.create_all(_engine)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def log_pipeline_start() -> int:
    with SessionLocal() as session:
        run = PipelineRun(
            started_at=_utcnow(),
            finished_at=None,
            status="running",
            rounds_completed=0,
            error_message=None,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return int(run.id)


def log_pipeline_finish(
    run_id: int,
    status: str,
    rounds_completed: int,
    error_message: str | None = None,
) -> None:
    with SessionLocal() as session:
        run = session.get(PipelineRun, run_id)
        if run is None:
            raise ValueError(f"Pipeline run not found: {run_id}")

        run.status = status
        run.rounds_completed = rounds_completed
        run.error_message = error_message
        if status == "running":
            run.finished_at = None
        else:
            run.finished_at = _utcnow()

        session.commit()


def log_predictions(round_predictions: RoundPredictions) -> None:
    created_at = _utcnow()
    logs = [
        PredictionLog(
            round=row.round,
            race_name=round_predictions.race_name,
            driver_id=row.driver_id,
            final_score=row.final_score,
            alpha=round_predictions.alpha,
            created_at=created_at,
        )
        for row in round_predictions.rows
    ]

    with SessionLocal() as session:
        session.bulk_save_objects(logs)
        session.commit()

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.analytics.reporting import build_dashboard_metrics, comparative_study_stats
from backend import schemas

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=schemas.DashboardMetricsOut)
def get_metrics(db: Session = Depends(get_db)):
    return build_dashboard_metrics(db)


@router.get("/comparison", response_model=schemas.ComparisonStatsOut)
def get_comparison(db: Session = Depends(get_db)):
    """R3 evidence endpoint: AI-driven (treatment) vs traditional (control) comparison."""
    return comparative_study_stats(db)

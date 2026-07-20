from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.analytics.reporting import build_dashboard_metrics
from backend import schemas

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=schemas.DashboardMetricsOut)
def get_metrics(db: Session = Depends(get_db)):
    return build_dashboard_metrics(db)

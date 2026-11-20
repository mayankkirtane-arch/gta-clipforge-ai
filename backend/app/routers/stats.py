from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.stats_service import get_dashboard_stats, get_system_status
from ..schemas.stats import DashboardStats, SystemStatus

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    return get_dashboard_stats(db)

@router.get("/system", response_model=SystemStatus)
def system_status(db: Session = Depends(get_db)):
    return get_system_status(db)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database import get_db
from app import models

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ТОП ДОМОВ
@router.get("/top-buildings")
def top_buildings(db: Session = Depends(get_db)):
    results = (
        db.query(
            models.Building.id.label("id"),
            models.Building.address.label("address"),
            func.count(models.Report.id).label("reports_count")
        )
        .outerjoin(models.Report, models.Building.id == models.Report.building_id)
        .group_by(models.Building.id, models.Building.address)
        .order_by(func.count(models.Report.id).desc())
        .limit(10)
        .all()
    )

    return [
        {
            "id": r.id,
            "address": r.address,
            "reports_count": r.reports_count
        }
        for r in results
    ]


# СТАТИСТИКА ПО СЕРЬЕЗНОСТИ
@router.get("/severity-stats")
def severity_stats(db: Session = Depends(get_db)):
    results = (
        db.query(
            models.Report.severity.label("severity"),
            func.count(models.Report.id).label("count")
        )
        .group_by(models.Report.severity)
        .all()
    )

    return [
        {"severity": r.severity, "count": r.count}
        for r in results
    ]


# ЖАЛОБЫ ПО ДНЯМ
@router.get("/reports-by-day")
def reports_by_day(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)

    results = (
        db.query(
            func.date(models.Report.created_at).label("date"),
            func.count(models.Report.id).label("count")
        )
        .filter(models.Report.created_at >= since)
        .group_by(func.date(models.Report.created_at))
        .order_by(func.date(models.Report.created_at))
        .all()
    )

    return [
        {"date": str(r.date), "count": r.count}
        for r in results
    ]

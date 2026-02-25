from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building, Report, NeighborHelp
from app import schemas
from datetime import datetime, timedelta

router = APIRouter(prefix="/buildings", tags=["buildings"])


def calculate_building_status(reports: list) -> str:
    if not reports:
        return "green"

    score = 0

    for r in reports:
        if r.severity == "high":
            score += 3
        elif r.severity == "medium":
            score += 1

    # 🔴 RED
    if score >= 45:
        return "red"

    # 🟠 ORANGE
    if score >= 25:
        return "orange"

    # 🟡 YELLOW
    if score >= 10:
        return "yellow"

    # 🟢 ЗЕЛЁНЫЙ
    return "green"



@router.get("/")
def get_buildings(db: Session = Depends(get_db)):
    buildings = db.query(Building).all()
    result = []

    for b in buildings:
        reports = db.query(Report).filter(
            Report.building_id == b.id
        ).all()

        status = calculate_building_status(reports)

        # 🔵 ДОБАВЛЯЕМ ПОДСЧЁТ ПОМОЩИ
        help_count = db.query(NeighborHelp).filter(
            NeighborHelp.building_id == b.id,
            NeighborHelp.status == "open"
        ).count()

        result.append({
            "id": b.id,
            "lat": b.lat,
            "lng": b.lng,
            "address": getattr(b, "address", None),
            "status": status,
            "positive_count": getattr(b, "positive_count", 0),
            "help_count": help_count,   # 🔵 ВОТ ЭТО НОВОЕ
        })

    return result


@router.post("/", response_model=schemas.BuildingOut)
def create_building(
    payload: schemas.BuildingCreate,
    db: Session = Depends(get_db),
):
    b = Building(
        lat=payload.lat,
        lng=payload.lng,
    )

    if hasattr(Building, "address") and payload.address is not None:
        b.address = payload.address

    if hasattr(Building, "status") and payload.status is not None:
        b.status = payload.status

    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.patch("/{building_id}/position", response_model=schemas.BuildingOut)
def update_building_position(
    building_id: int,
    payload: schemas.BuildingUpdate,
    db: Session = Depends(get_db),
):
    b = db.query(Building).filter(
        Building.id == building_id
    ).first()

    if not b:
        raise HTTPException(status_code=404, detail="Building not found")

    if payload.lat is not None:
        b.lat = payload.lat
    if payload.lng is not None:
        b.lng = payload.lng

    db.commit()
    db.refresh(b)
    return b

@router.post("/{building_id}/confirm-positive")
def confirm_positive(building_id: int, db: Session = Depends(get_db)):
    b = db.query(Building).filter(
        Building.id == building_id
    ).first()

    if not b:
        raise HTTPException(status_code=404, detail="Building not found")

    b.positive_count = (b.positive_count or 0) + 1

    db.commit()
    db.refresh(b)

    return {
        "id": b.id,
        "positive_count": b.positive_count
    }
    
@router.post("/{building_id}/confirm-positive")
def confirm_positive(building_id: int, db: Session = Depends(get_db)):

    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Ограничение: не чаще чем раз в 24 часа
    if building.last_positive_at:
        if datetime.utcnow() - building.last_positive_at < timedelta(hours=24):
            raise HTTPException(
                status_code=400,
                detail="Вы уже подтверждали норму за последние 24 часа"
            )

    building.positive_count += 1
    building.last_positive_at = datetime.utcnow()

    db.commit()
    db.refresh(building)

    return {"success": True}   
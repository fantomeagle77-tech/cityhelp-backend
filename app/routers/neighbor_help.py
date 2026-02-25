from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import hashlib
from datetime import datetime
from app.models import HelpResponse
from app.models import NeighborHelp

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/help", tags=["neighbor_help"])


@router.post("/", response_model=schemas.NeighborHelpOut)
def create_help(payload: schemas.NeighborHelpCreate, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    raw = f"{ip}-{payload.building_id}"
    user_hash = hashlib.sha256(raw.encode()).hexdigest()

    active_count = db.query(NeighborHelp).filter(
        NeighborHelp.building_id == payload.building_id,
        NeighborHelp.status == "open"
    ).count()

    if active_count >= 3:
        raise HTTPException(
            status_code=400,
            detail="У дома уже слишком много активных заявок"
        )

    help_item = models.NeighborHelp(
        building_id=payload.building_id,
        category=payload.category,   # ← ВОТ ЭТО ОБЯЗАТЕЛЬНО
        title=payload.title,
        description=payload.description,
        contact=payload.contact,
        user_hash=user_hash
    )

    db.add(help_item)
    db.commit()
    db.refresh(help_item)

    return help_item


@router.get("/", response_model=List[schemas.NeighborHelpOut])
def get_help(building_id: int = None, db: Session = Depends(get_db)):
    query = db.query(models.NeighborHelp)

    if building_id:
        query = query.filter(models.NeighborHelp.building_id == building_id)

    return query.order_by(models.NeighborHelp.id.desc()).all()


@router.post("/{help_id}/close")
def close_help(help_id: int, db: Session = Depends(get_db)):
    item = db.query(models.NeighborHelp).filter(models.NeighborHelp.id == help_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    item.status = "closed"
    db.commit()

    return {"status": "closed"}
    
@router.post("/{help_id}/respond")
def respond_to_help(help_id: int, request: Request, db: Session = Depends(get_db)):

    user_hash = request.headers.get("X-User-Hash")

    if not user_hash:
        raise HTTPException(status_code=400, detail="No user hash")

    existing = db.query(HelpResponse).filter(
        HelpResponse.help_id == help_id,
        HelpResponse.responder_hash == user_hash
    ).first()

    if existing:
        return {"message": "already responded"}

    response = HelpResponse(
        help_id=help_id,
        responder_hash=user_hash
    )

    db.add(response)
    db.commit()

    return {"message": "ok"}
    
@router.get("/{help_id}/responses")
def get_responses(help_id: int, db: Session = Depends(get_db)):
    count = db.query(HelpResponse).filter(
        HelpResponse.help_id == help_id
    ).count()

    return {"count": count}
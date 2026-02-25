from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import hashlib

from app import models, schemas
from app.database import get_db
from datetime import datetime, timedelta

from fastapi import UploadFile, File, Form
import os
import uuid

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/", response_model=schemas.ReportOut)
def create_report(
    request: Request,
    building_id: int = Form(...),
    category: schemas.ReportCategory = Form(...),
    severity: schemas.ReportSeverity = Form(...),
    periodicity: schemas.ReportPeriodicity = Form(...),
    text: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    b = db.query(models.Building).filter(
        models.Building.id == building_id
    ).first()

    if not b:
        raise HTTPException(status_code=404, detail="Building not found")

    # простой user_hash (анонимно, стабильно)
    ip = request.client.host
    raw = f"{ip}-{building_id}"
    user_hash = hashlib.sha256(raw.encode()).hexdigest()

    # Проверка 1 жалоба в 24 часа
    since = datetime.utcnow() - timedelta(hours=24)
    
    # Дополнительный лимит: максимум 3 жалобы в сутки с одного IP (в целом)
    daily_count = db.query(models.Report).filter(
        models.Report.user_hash == user_hash,
        models.Report.created_at >= since
    ).count()

    if daily_count >= 3:
        raise HTTPException(
            status_code=429,
            detail="Слишком много жалоб за сутки с вашего IP"
        )
    
    existing = db.query(models.Report).filter(
        models.Report.building_id == building_id,
        models.Report.user_hash == user_hash,
        models.Report.created_at >= since
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Вы уже оставляли жалобу за последние 24 часа"
        )
    
    # Проверка антифлуда (60 секунд)
    last_report = db.query(models.Report).filter(
        models.Report.user_hash == user_hash
    ).order_by(models.Report.created_at.desc()).first()

    if last_report:
        delta = datetime.utcnow() - last_report.created_at
        if delta.total_seconds() < 60:
            raise HTTPException(
                status_code=429,
                detail="Слишком часто. Подождите минуту."
            )
    
    image_path = None

    if image:
        if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(status_code=400, detail="Разрешены только изображения")

        contents = image.file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5MB)")

        image.file.seek(0)
        
        os.makedirs("uploads", exist_ok=True)

        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_location = os.path.join("uploads", filename)

        with open(file_location, "wb") as f:
            f.write(image.file.read())

        image_path = f"/uploads/{filename}"
    
    report = models.Report(
        building_id=building_id,
        category=category,
        text=text,
        severity=severity,
        periodicity=periodicity,  # ✅ ВАЖНО
        user_hash=user_hash,              # ✅ ВАЖНО
        image_path=image_path  # ← ДОБАВЛЕНО
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@router.get("/buildings/{building_id}/reports", response_model=List[schemas.ReportOut])
def get_reports_by_building(building_id: int, db: Session = Depends(get_db)):

    reports = db.query(models.Report).filter(
        models.Report.building_id == building_id
    ).order_by(models.Report.id.desc()).all()

    now = datetime.utcnow()

    for report in reports:
        # Авто-устаревание только для open
        if report.status == "open":
            if now - report.created_at > timedelta(days=30):
                report.status = "outdated"

    db.commit()

    for report in reports:
        confirmations_count = db.query(models.ReportConfirmation).filter(
            models.ReportConfirmation.report_id == report.id
        ).count()

        report.confirmations = confirmations_count
    
    for report in reports:
        problem_count = db.query(models.ReportConfirmation).filter(
            models.ReportConfirmation.report_id == report.id,
            models.ReportConfirmation.type == "problem"
        ).count()

        resolved_count = db.query(models.ReportConfirmation).filter(
            models.ReportConfirmation.report_id == report.id,
            models.ReportConfirmation.type == "resolved"
        ).count()

        report.problem_confirmations = problem_count
        report.resolved_confirmations = resolved_count
    
    now = datetime.utcnow()

    for report in reports:
        if report.status == "open":
            # Последнее подтверждение проблемы
            last_problem_confirm = db.query(models.ReportConfirmation).filter(
                models.ReportConfirmation.report_id == report.id,
                models.ReportConfirmation.type == "problem"
            ).order_by(models.ReportConfirmation.created_at.desc()).first()

            last_activity = report.created_at

            if last_problem_confirm:
                last_activity = last_problem_confirm.created_at

            if now - last_activity > timedelta(days=30):
                report.status = "outdated"
                db.commit()
    
    return reports


@router.post("/{report_id}/confirm-problem")
def confirm_problem(report_id: int, request: Request, db: Session = Depends(get_db)):

    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    ip = request.client.host
    user_hash = hashlib.sha256(f"{ip}-{report.building_id}".encode()).hexdigest()

    existing = db.query(models.ReportConfirmation).filter(
        models.ReportConfirmation.report_id == report_id,
        models.ReportConfirmation.user_hash == user_hash,
        models.ReportConfirmation.type == "problem"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Вы уже подтверждали проблему")

    confirmation = models.ReportConfirmation(
        report_id=report_id,
        user_hash=user_hash,
        type="problem"
    )

    db.add(confirmation)
    db.commit()

    count = db.query(models.ReportConfirmation).filter(
        models.ReportConfirmation.report_id == report_id,
        models.ReportConfirmation.type == "problem"
    ).count()
    
    # Авто-поднятие серьёзности
    if report.status == "open":
        if count >= 5 and report.severity == "medium":
            report.severity = "high"
            db.commit()
        elif count >= 3 and report.severity == "low":
            report.severity = "medium"
            db.commit()

    return {"confirmations": count}

@router.post("/{report_id}/confirm-resolved")
def confirm_resolved(report_id: int, request: Request, db: Session = Depends(get_db)):

    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != "open":
        raise HTTPException(status_code=400, detail="Жалоба уже закрыта")

    ip = request.client.host
    user_hash = hashlib.sha256(f"{ip}-{report.building_id}".encode()).hexdigest()

    existing = db.query(models.ReportConfirmation).filter(
        models.ReportConfirmation.report_id == report_id,
        models.ReportConfirmation.user_hash == user_hash,
        models.ReportConfirmation.type == "resolved"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Вы уже подтверждали решение")

    confirmation = models.ReportConfirmation(
        report_id=report_id,
        user_hash=user_hash,
        type="resolved"
    )

    db.add(confirmation)
    db.commit()

    count = db.query(models.ReportConfirmation).filter(
        models.ReportConfirmation.report_id == report_id,
        models.ReportConfirmation.type == "resolved"
    ).count()

    if count >= 3:
        report.status = "resolved"
        db.commit()

    return {
        "confirmations": count,
        "status": report.status
    }

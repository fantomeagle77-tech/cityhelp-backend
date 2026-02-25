from sqlalchemy.orm import Session
from app import models

def create_report(db: Session, report_data, building_id, user_hash):
    report = models.Report(
        building_id=building_id,
        category=report_data.category,
        text=report_data.text,
        severity=report_data.severity,
        periodicity=report_data.periodicity,
        user_hash=user_hash
    )
    db.add(report)
    db.commit()
    return report
    
def create_building(db: Session, lat: float, lng: float, address: str):
    building = models.Building(lat=lat, lng=lng, address=address)
    db.add(building)
    db.flush()          # ← ВАЖНО
    db.commit()
    db.refresh(building)
    return building

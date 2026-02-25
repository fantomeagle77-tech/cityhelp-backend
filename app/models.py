from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base
from sqlalchemy import Column, String

class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    address = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    positive_count = Column(Integer, default=0)
    last_positive_at = Column(DateTime, nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), index=True)
    category = Column(String, nullable=False)
    text = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    periodicity = Column(String, nullable=False)
    user_hash = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default="open", nullable=False)
    image_path = Column(String, nullable=True)  # ← НОВОЕ ПОЛЕ
    
class ReportConfirmation(Base):
    __tablename__ = "report_confirmations"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    user_hash = Column(String)
    type = Column(String)  # "problem" или "resolved"
    created_at = Column(DateTime, default=datetime.utcnow)
    category = Column(String, default="other")

Index("idx_report_user_time", Report.user_hash, Report.created_at)
Index("idx_report_building_time", Report.building_id, Report.created_at)

class NeighborHelp(Base):
    __tablename__ = "neighbor_help"

    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), index=True)

    title = Column(String, nullable=False)
    category = Column(String, nullable=False, default="other")  # ← ВОТ ЭТО
    description = Column(String, nullable=False)

    contact = Column(String, nullable=True)

    status = Column(String, default="open", nullable=False)  # open / closed
    user_hash = Column(String, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class HelpResponse(Base):
    __tablename__ = "help_responses"

    id = Column(Integer, primary_key=True, index=True)
    help_id = Column(Integer, ForeignKey("neighbor_help.id"))
    responder_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
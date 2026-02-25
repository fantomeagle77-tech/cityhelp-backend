from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS
# =====================================================

class ReportCategory(str, Enum):
    yard = "yard"
    road = "road"
    trashinyard = "trashinyard"
    utiltrash = "utiltrash"
    noise = "noise"
    JKH = "JKH"
    water = "water"
    heating = "heating"
    electricity = "electricity"
    gas = "gas"
    parking = "parking"
    other = "other"
    


class ReportSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ReportPeriodicity(str, Enum):
    rare = "rare"
    often = "often"
    always = "always"


# =====================================================
# BUILDINGS
# =====================================================

class BuildingCreate(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None


class BuildingUpdate(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class BuildingOut(BaseModel):
    id: int
    lat: float
    lng: float
    address: Optional[str] = None
    status: Optional[str] = None  # red / orange / yellow / green

    class Config:
        from_attributes = True


# =====================================================
# REPORTS
# =====================================================

class ReportCreate(BaseModel):
    building_id: int
    category: ReportCategory
    severity: ReportSeverity
    periodicity: ReportPeriodicity
    text: str = Field(min_length=5, max_length=1000)


class ReportOut(BaseModel):
    id: int
    building_id: int
    category: ReportCategory
    severity: ReportSeverity
    periodicity: ReportPeriodicity
    text: str
    user_hash: str
    created_at: datetime
    confirmations: int = 0
    status: str   # open / resolved / outdated
    problem_confirmations: int = 0
    resolved_confirmations: int = 0
    image_path: Optional[str] = None  # ← НОВОЕ ПОЛЕ

    class Config:
        from_attributes = True
        orm_mode = True
        
# =====================================================
# NEIGHBOR HELP
# =====================================================

class NeighborHelpCreate(BaseModel):
    building_id: int
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=2000)
    contact: Optional[str] = None
    category: str

class NeighborHelpOut(BaseModel):
    id: int
    building_id: int
    title: str
    description: str
    contact: Optional[str]
    status: str
    created_at: datetime
    category: Optional[str] = "other"

    class Config:
        from_attributes = True
        orm_mode = True        
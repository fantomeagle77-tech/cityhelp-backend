from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import buildings, reports
from app.routers import analytics
from app.routers import neighbor_help

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()
app.include_router(neighbor_help.router)

os.makedirs("uploads", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS: обязательно для фронта на localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(buildings.router)
app.include_router(reports.router)
app.include_router(analytics.router)


@app.get("/")
def health():
    return {"ok": True}

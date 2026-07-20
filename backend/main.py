from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db, SessionLocal
from backend import seed_data
from backend.routers import consent, learners, quests, gameplay, dashboard

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_data.seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="SkillSphere - AI-Driven Adaptive Gamified Training Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consent.router)
app.include_router(learners.router)
app.include_router(quests.router)
app.include_router(gameplay.router)
app.include_router(dashboard.router)


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

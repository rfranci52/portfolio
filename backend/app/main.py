from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, ensure_dirs
from app.db import init_db
from app.routes import contact, projects
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    init_db()
    seed()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects.router)
app.include_router(contact.router)


@app.get("/api/health")
def health():
    return {"ok": True}

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models import CompareRequest, CompareResponse, PlayerOut
from app.services.compare import compare_players, list_players

app = FastAPI(
    title="Fantasy Football Recommender",
    description="Who Do I Start? — compare weekly adjusted projections",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Fantasy Football Recommender API",
        "docs": "/docs",
        "health": "/health",
        "players": "/players",
        "compare": "POST /compare",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/players", response_model=list[PlayerOut])
def get_players(
    db: DbSession,
    position: str | None = None,
) -> list[PlayerOut]:
    return list_players(db, position=position)


@app.post("/compare", response_model=CompareResponse)
def compare(request: CompareRequest, db: DbSession) -> CompareResponse:
    return compare_players(db, request)

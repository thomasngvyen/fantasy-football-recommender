from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sleeper_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    position: Mapped[str] = mapped_column(String(10))  # QB, RB, WR, TE, K, D, DST
    team: Mapped[Optional[str]] = mapped_column(String(10))
    base_projection: Mapped[float] = mapped_column(Float, insert_default=0.0)

    matchups: Mapped[List["Matchup"]] = relationship(back_populates="player")
    projections: Mapped[List["Projection"]] = relationship(back_populates="player")


class Matchup(Base):
    __tablename__ = "matchups"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "week", "season", name="uq_matchup_player_week_season"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    week: Mapped[int] = mapped_column(Integer)
    season: Mapped[int] = mapped_column(Integer)
    opponent: Mapped[str] = mapped_column(String(10), index=True)
    is_home: Mapped[bool] = mapped_column(Boolean, insert_default=True)
    is_dome: Mapped[bool] = mapped_column(Boolean, insert_default=False)
    game_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    player: Mapped["Player"] = relationship(back_populates="matchups")
    weather: Mapped[Optional["Weather"]] = relationship(
        back_populates="matchup",
        uselist=False,
        cascade="all, delete-orphan",
    )
    projection: Mapped[Optional["Projection"]] = relationship(
        back_populates="matchup",
        uselist=False,
        cascade="all, delete-orphan",
    )


class TeamMatchupStats(Base):
    """Weekly team ranks consumed by compute_adjusted_projection."""

    __tablename__ = "team_matchup_stats"
    __table_args__ = (
        UniqueConstraint(
            "team", "week", "season", name="uq_team_stats_team_week_season"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team: Mapped[str] = mapped_column(String(10), index=True)
    week: Mapped[int] = mapped_column(Integer)
    season: Mapped[int] = mapped_column(Integer)
    pass_defense_rank: Mapped[int] = mapped_column(Integer)
    run_defense_rank: Mapped[int] = mapped_column(Integer)
    total_offense_rank: Mapped[int] = mapped_column(Integer)
    points_allowed_pass_avg: Mapped[Optional[float]] = mapped_column(Float)
    points_allowed_run_avg: Mapped[Optional[float]] = mapped_column(Float)


class Weather(Base):
    __tablename__ = "weather"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matchup_id: Mapped[int] = mapped_column(
        ForeignKey("matchups.id", ondelete="CASCADE"), unique=True, index=True
    )
    wind_mph: Mapped[float] = mapped_column(Float, insert_default=0.0)
    temp_f: Mapped[Optional[float]] = mapped_column(Float)
    precip_mm: Mapped[float] = mapped_column(Float, insert_default=0.0)
    is_rain: Mapped[bool] = mapped_column(Boolean, insert_default=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=_utc_now
    )

    matchup: Mapped["Matchup"] = relationship(back_populates="weather")


class Projection(Base):
    __tablename__ = "projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    matchup_id: Mapped[int] = mapped_column(
        ForeignKey("matchups.id", ondelete="CASCADE"), unique=True, index=True
    )
    week: Mapped[int] = mapped_column(Integer)
    season: Mapped[int] = mapped_column(Integer)
    adjusted_points: Mapped[float] = mapped_column(Float)
    breakdown_json: Mapped[dict] = mapped_column(JSON)

    player: Mapped["Player"] = relationship(back_populates="projections")
    matchup: Mapped["Matchup"] = relationship(back_populates="projection")

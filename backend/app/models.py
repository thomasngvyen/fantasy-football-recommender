from pydantic import BaseModel, Field, model_validator

class ProjectionBreakdown(BaseModel):
    base_projection: float = Field(..., description="Base projection")
    home_advantage_modifier: float = Field(..., description="Home advantage modifier")
    defense_rank_modifier: float = Field(..., description="Defense rank modifier")
    total_offense_rank_modifier: float = Field(..., description="Total offense rank modifier")
    weather_modifier: float = Field(..., description="Weather modifier")
    final_projection: float = Field(..., description="Final projection")
    weather_notes: str | None = Field(None, description="Weather notes")

class ComparePlayerResult(BaseModel):
    sleeper_id: str = Field(..., description="Sleeper ID")
    name: str = Field(..., description="Player name")
    position: str = Field(..., description="Player position")
    team: str | None = Field(None, description="Player team")
    opponent: str | None = Field(None, description="Opponent")
    adjusted_points: float = Field(..., description="Adjusted points")
    breakdown: ProjectionBreakdown
    explanation: str = Field(..., description="Explanation")

class CompareRequest(BaseModel):
    player_a_id: str = Field(..., description="Player A ID")
    player_b_id: str = Field(..., description="Player B ID")  
    week: int = Field(..., ge = 1, le = 18, description="Week of the season")
    season: int = Field(..., ge = 2020, le = 2035, description="Season")

    @model_validator(mode = "after")
    def validate_player_ids(self) -> "CompareRequest":
        if self.player_a_id == self.player_b_id:
            raise ValueError("Player A and Player B cannot be the same")
        return self

class CompareResponse(BaseModel):
    week: int = Field(..., description="Week of the season")
    season: int = Field(..., description="Season")
    winner: ComparePlayerResult
    loser: ComparePlayerResult
    margin_of_victory: float = Field(..., description="Margin of victory")
    recommendation: str = Field(..., description="Recommendation")

class PlayerOut(BaseModel):
    sleeper_id: str = Field(..., description="Sleeper ID")
    name: str = Field(..., description="Player name")
    position: str = Field(..., description="Player position")
    team: str | None = Field(None, description="Player team")


class WeekScheduleOut(BaseModel):
    week: int
    game_count: int
    teams_playing: int
    teams_on_bye: list[str]
    has_schedule: bool = True

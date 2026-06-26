PLAYERS: list[dict] = [
    {
        "id": 1,
        "name": "Patrick Mahomes",
        "position": "QB",
        "team": "KC",
        "projected_points": 22.4,
    },
    {
        "id": 2,
        "name": "Josh Allen",
        "position": "QB",
        "team": "BUF",
        "projected_points": 24.1,
    },
    {
        "id": 3,
        "name": "Christian McCaffrey",
        "position": "RB",
        "team": "SF",
        "projected_points": 18.7,
    },
    {
        "id": 4,
        "name": "Saquon Barkley",
        "position": "RB",
        "team": "PHI",
        "projected_points": 17.2,
    },
    {
        "id": 5,
        "name": "Tyreek Hill",
        "position": "WR",
        "team": "MIA",
        "projected_points": 16.8,
    },
    {
        "id": 6,
        "name": "CeeDee Lamb",
        "position": "WR",
        "team": "DAL",
        "projected_points": 15.9,
    },
    {
        "id": 7,
        "name": "Travis Kelce",
        "position": "TE",
        "team": "KC",
        "projected_points": 12.3,
    },
    {
        "id": 8,
        "name": "Mark Andrews",
        "position": "TE",
        "team": "BAL",
        "projected_points": 10.1,
    },
]

_PLAYERS_BY_ID = {player["id"]: player for player in PLAYERS}


def get_player(player_id: int) -> dict | None:
    return _PLAYERS_BY_ID.get(player_id)

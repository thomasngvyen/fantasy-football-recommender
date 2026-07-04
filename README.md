# Fantasy Football Recommender

**Who do I start?** A full-stack fantasy football decision tool that compares two players at the same position and recommends a starter based on adjusted weekly projections. The app blends Sleeper roster data, matchup context, home-field advantage, and weather into a transparent point breakdown you can trust on Sunday morning.

---

## Features

- **Head-to-head compare** — Pick two players (QB, RB, WR, TE, K, or DST) and get a clear start/sit recommendation with margin of victory.
- **Projection engine** — Multiplicative modifiers for home field, defensive matchup, opponent offense (DST), and weather, with a full breakdown per player.
- **Live player list** — Roster-filtered dropdowns from the Sleeper API (active NFL players only, depth-chart limits applied).
- **Smart base projections** — Prior-season Sleeper averages for skill players; defense ranks from fixture data for DST; backup QB downgrade for depth-chart QB2+.
- **Weekly sync pipeline** — One command seeds players, matchups, weather, and cached projections into SQLite for fast API responses.
- **Schedule fixtures** — Week 1–17 JSON schedules for offline matchup building and multi-week sync.
- **Interactive API docs** — FastAPI Swagger UI at `/docs` for exploring endpoints.
- **Test coverage** — Pytest suite covering projections, compare logic, weather parsing, roster filters, and HTTP integration tests.

---

## Tech Stack

| Layer | Technologies |
|-------|----------------|
| **Frontend** | React 19, TypeScript, Vite 8 |
| **Backend** | Python 3, FastAPI, Uvicorn, Pydantic |
| **Database** | SQLite via SQLAlchemy 2 |
| **External APIs** | [Sleeper API](https://docs.sleeper.com/) (players, stats, NFL state), [OpenWeather](https://openweathermap.org/api) (optional, 5-day forecast) |
| **Testing** | pytest, FastAPI TestClient |

---

## Getting Started

### Prerequisites

- **Python 3.11+** (3.14 tested)
- **Node.js 18+** and npm
- **Git**
- *(Optional)* OpenWeather API key for weather-adjusted projections

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/your-username/fantasy_football_recommender.git
cd fantasy_football_recommender
```

**2. Set up the backend**

```bash
cd backend
python -m pip install -r requirements.txt
```

**3. Configure environment variables**

Copy the example file and edit as needed:

```bash
cp .env.example .env
```

Or create `backend/.env` manually (this file is gitignored — never commit secrets):

```env
# Required for defaults; "live" uses Sleeper + fixture data
DATA_MODE=live

# SQLite database path (relative to backend/ when running from there)
DATABASE_URL=sqlite:///./fantasy.db

# Comma-separated origins allowed by CORS (Vite dev server)
CORS_ORIGINS=http://localhost:5173

# Optional — enables weather modifiers during sync
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

**4. Set up the frontend**

```bash
cd ../frontend
npm install
```

**5. Seed the database**

From the `backend/` directory, run a full sync before using the app. This pulls players from Sleeper, loads defense ranks, builds matchups, and caches projections.

```bash
cd ../backend
python scripts/sync_week.py --week 1 --season 2026 --stats-season 2025
```

> **Note:** OpenWeather only forecasts ~5 days ahead. Weather rows for distant weeks will populate closer to kickoff. Use `--no-weather` to skip weather during bulk syncs.

**Sync all weeks (1–17)**

```bash
python scripts/sync_week.py --all-weeks --season 2026 --stats-season 2025 --no-weather
```

This seeds players and defense stats on week 1, then rebuilds matchups and projections for every week. Omit `--no-weather` to fetch forecasts when games fall inside OpenWeather’s 5-day window.

Manual loop (PowerShell):

```powershell
1..17 | ForEach-Object {
  python scripts/sync_week.py --week $_ --season 2026 --matchups-only
  python scripts/sync_week.py --week $_ --season 2026 --projections-only
}
```

### Run the development servers

You need **two terminals** — backend first, then frontend.

**Terminal 1 — API (port 8000)**

```bash
cd backend
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000  
- Swagger docs: http://127.0.0.1:8000/docs  

**Terminal 2 — Frontend (port 5173)**

```bash
cd frontend
npm run dev
```

- App: http://localhost:5173  

The Vite dev server proxies `/health`, `/players`, and `/compare` to the backend. No extra frontend env is required for local development.

### Run tests

```bash
cd backend
python -m pytest -v

cd ../frontend
npm test
npm run build
```

### Docker Compose

```bash
docker compose up --build
```

- API: http://localhost:8000  
- Frontend: http://localhost:8080  

Run a sync inside the backend container before comparing players in Docker.

### Useful sync flags

| Flag | Purpose |
|------|---------|
| `--week N` | Target NFL week |
| `--all-weeks` | Sync a range of weeks (default 1–17) |
| `--weeks-start` / `--weeks-end` | Range for `--all-weeks` |
| `--season YYYY` | Target season |
| `--stats-season YYYY` | Season for Sleeper per-game averages (e.g. prior year) |
| `--matchups-only` | Rebuild matchups only |
| `--projections-only` | Recompute cached projections only |
| `--no-weather` | Skip OpenWeather fetch |
| `--no-projections` | Skip projection step during full sync |

---

## Project Structure

```text
fantasy_football_recommender/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI routes
│   │   ├── models.py               # Pydantic request/response schemas
│   │   ├── config.py               # Environment settings
│   │   ├── db/
│   │   │   ├── tables.py           # SQLAlchemy models
│   │   │   ├── session.py          # DB engine & sessions
│   │   │   └── seed.py             # Seed players & defense stats
│   │   ├── fixtures/
│   │   │   ├── defense_ranks.json  # Team defense ranks & DST baselines
│   │   │   ├── stadiums.json       # Dome/outdoor stadium metadata
│   │   │   └── week{N}_schedule.json
│   │   └── services/
│   │       ├── sleeper_client.py   # Sleeper API + roster filtering
│   │       ├── base_projections.py # Season averages & DST baselines
│   │       ├── projection.py       # Modifier engine
│   │       ├── recommendation.py   # Orchestrates weekly projections
│   │       ├── matchup_builder.py  # Schedule → matchup rows
│   │       ├── compare.py          # Compare API logic
│   │       └── weather_client.py   # OpenWeather integration
│   ├── scripts/
│   │   └── sync_week.py            # End-to-end weekly sync CLI
│   ├── tests/                      # Pytest suite
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.tsx                 # Compare UI
    │   ├── App.css
    │   └── api/
    │       ├── client.ts           # API client
    │       └── types.ts            # Shared TypeScript types
    ├── vite.config.ts              # Dev proxy to backend
    └── package.json
```

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/players?position=QB` | List rosterable players (live from Sleeper) |
| `GET` | `/schedule/weeks` | List schedule metadata (bye weeks, game counts) |
| `GET` | `/schedule/weeks/{week}` | Schedule info for one week |
| `POST` | `/compare` | Compare two players for a given week/season |

Example compare request:

```json
{
  "player_a_id": "4881",
  "player_b_id": "6797",
  "week": 1,
  "season": 2026
}
```

Projections are read from the local database. Run `sync_week.py` before comparing if you see missing matchup or projection errors.


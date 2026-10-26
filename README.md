# MarketMind United Nations Data

Microservice for consuming, normalizing, and persisting demographic data from the
**UN Population Data Portal API** (REST/JSON, `https://population.un.org/dataportalapi/uiapi/v1`).

## What it does

- Proxies the portal's indicator and location lists (`/remote/*`) so callers can find `un_indicator_id` and `location_id`
- Keeps an internal catalog of the indicators MarketMind needs, each mapped to its `un_indicator_id`
- Collects yearly observations per country, one request per indicator per year
- Persists raw JSON responses for auditability and normalized observations for consumption
- Exposes stored series, freshness and a stale-refresh pass over REST, with full traceability (`ingestion_run_id`, `undata_request_id`)

## What it does NOT do

- Does NOT calculate MOS, Rank Order Centroid weights or TOPSIS
- Does NOT use LLMs
- Does NOT know about Semantic Layer or MarketMind final rules
- Does NOT calculate Market Readiness Score dimensions

## Architecture

```text
app/
  api/routes/         # FastAPI route handlers (no business logic)
  core/               # Config, logging, exceptions
  domain/             # Enums, entities
  clients/            # UNDataClient (httpx.Client, retry policy in app/utils/retry.py)
  services/           # UNDataService (orchestration)
  repositories/       # Database persistence layer
  db/models/          # SQLAlchemy ORM models
  schemas/            # Pydantic request/response schemas
  utils/              # Normalization, time utilities
tests/                # Pytest test suite
alembic/              # Database migrations
```

The service is **synchronous** end to end: route handlers are plain `def`, the database is
reached through SQLAlchemy `Session` over psycopg2, and the upstream API through
`httpx.Client`. There is no asyncio in the request path.

## Indicators

`POST /indicators/catalog/seed` registers the four entries of `SEED_INDICATORS`
(`app/services/undata_service.py`). The `un_indicator_id` values were confirmed against the
live portal (`GET /remote/indicators`).

| Code | Name | `un_indicator_id` | Unit | Dimension |
|------|------|-------------------|------|-----------|
| `TOTAL_POPULATION` | Total Population | 49 | persons | market_population_potential |
| `MEDIAN_AGE` | Median Age | 67 | years | target_age_fit |
| `NET_MIGRATION` | Net Migration (absolute count) | 65 | persons | demographic_readiness |
| `POPULATION_GROWTH` | Population Growth Rate (annual %) | 51 | percentage | demographic_readiness |

Each catalog entry also carries the portal's query defaults: `variant_id=4` (Medium),
`age_id=188` (Total), `sex_id=3` (Both sexes), `category_id=0`.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ and Poetry (for local development)

### Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Services:

- **API**: `http://localhost:${APP_PORT}` (8002 in `.env.example`; the container listens on 8000)
- **Swagger**: `http://localhost:8002/docs`
- **PostgreSQL 16**: `localhost:${DATABASE_EXTERNAL_PORT}` (5435 in `.env.example`)

Migrations run automatically when the container starts (`alembic upgrade head`).

### Run locally

```bash
poetry install
cp .env.example .env            # set DATABASE_HOST=localhost
docker compose up postgres -d
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### pgAdmin

pgAdmin was consolidated into `marketmind-scoring` (single instance pointing at
all 5 services' databases). See `marketmind-scoring/README.md`.

## Environment Variables

| Variable | Default in code | Description |
|---|---|---|
| `APP_NAME` | `marketmind-united-nations-data` | Service name |
| `APP_PORT` | — | Host port mapped by `docker-compose.yml` only (8002 in `.env.example`); the app itself does not read it |
| `DATABASE_HOST` | `localhost` | PostgreSQL host (`postgres` in `.env.example`) |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_EXTERNAL_PORT` | — | Host port for Postgres in `docker-compose.yml` (5435 in `.env.example`) |
| `DATABASE_NAME` | `marketmind_united_nations_data` | Database name |
| `DATABASE_USER` | `marketmind` | Database user |
| `DATABASE_PASSWORD` | `marketmind_password` | Database password |
| `DATABASE_SSL_MODE` | `disable` | `disable`, `require` or `verify-full` (Azure needs at least `require`) |
| `UNDATA_API_BASE_URL` | `https://population.un.org/dataportalapi/uiapi/v1` | UN Population Data Portal API |
| `DEFAULT_TIMEOUT` | `60` | HTTP timeout (seconds), same in every collector |
| `DEFAULT_RETRIES` | `5` | Attempts per call, same in every collector |
| `DEFAULT_BACKOFF` | `2` | First wait (seconds); doubles per attempt, with jitter, capped at 60 s |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints

### Health & Version

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness: is the process up (no DB access) |
| `GET` | `/health` | Readiness: health check + DB connectivity |
| `GET` | `/version` | Service version |

### Remote (proxy to the UN portal)

| Method | Path | Description |
|---|---|---|
| `GET` | `/remote/indicators` | List the portal's indicators (find `un_indicator_id`) |
| `GET` | `/remote/locations` | List the portal's locations (find `location_id`, e.g. 724 = Spain) |

### Data Management

| Method | Path | Description |
|---|---|---|
| `POST` | `/dataflows/register` | Register dataflow metadata (e.g. `WPP2024`) |
| `GET` | `/dataflows` | List dataflows |
| `POST` | `/datastructures/register` | Register dimensions/codes of a dataflow |
| `GET` | `/datastructures` | List datastructures |

### Indicators

| Method | Path | Description |
|---|---|---|
| `POST` | `/indicators/catalog` | Register/update indicator catalog entries |
| `GET` | `/indicators/catalog` | List indicator catalog |
| `POST` | `/indicators/catalog/seed` | Seed the 4 default MarketMind indicators |
| `POST` | `/indicators/collect` | Collect indicators for a country/location and year range |
| `GET` | `/observations/series` | Read one indicator's stored values for one country (`country`, `indicator_code`, optional `limit`) |
| `GET` | `/freshness` | What is stored and when it was last checked (`country`, `indicator`, `stale_after_days`, `only_stale`) |
| `POST` | `/maintenance/refresh-stale` | Collect again every country whose last check is older than `stale_after_days` (default 90); `limit`, `fail_if_incomplete`, `years_back` (default 10) |

### Audit

| Method | Path | Description |
|---|---|---|
| `GET` | `/requests/{id}` | Get request + observations |
| `GET` | `/runs/{id}` | Get ingestion run details |

Consumers (e.g. `marketmind-scoring`) read this service over HTTP (`/observations/series`,
`/freshness`); they do not connect to its database.

## How to Collect

### Step 1: Find the location id

```bash
curl http://localhost:8002/remote/locations
```

### Step 2: Seed the catalog

```bash
curl -X POST http://localhost:8002/indicators/catalog/seed
```

To add or change an entry by hand:

```bash
curl -X POST http://localhost:8002/indicators/catalog \
  -H "Content-Type: application/json" \
  -d '{
    "indicators": [{
      "indicator_code": "TOTAL_POPULATION",
      "indicator_name": "Total Population",
      "category": "total_population",
      "expected_unit": "persons",
      "marketmind_dimension": "market_population_potential",
      "un_indicator_id": 49
    }]
  }'
```

### Step 3: Collect

```bash
curl -X POST http://localhost:8002/indicators/collect \
  -H "Content-Type: application/json" \
  -d '{
    "country": "ES",
    "location_id": 724,
    "start_year": 2015,
    "end_year": 2025,
    "indicator_codes": ["TOTAL_POPULATION", "MEDIAN_AGE"]
  }'
```

One `ingestion_run` is recorded per indicator, and one `undata_request` per indicator the portal
answered. The response carries the successful ones in `data.ingestion_run_ids` and
`data.undata_request_ids`, next to `data.observations`, `data.errors` and `data.indicators_failed`.
When no indicator got an answer the call answers 503 (portal down) or 502.

### Step 4: Read back, check freshness, refresh

```bash
curl "http://localhost:8002/observations/series?country=ES&indicator_code=TOTAL_POPULATION&limit=3"

curl "http://localhost:8002/freshness?country=ES&stale_after_days=90&only_stale=true"

curl -X POST http://localhost:8002/maintenance/refresh-stale \
  -H "Content-Type: application/json" \
  -d '{"stale_after_days": 90, "fail_if_incomplete": true}'
```

The refresh replays each country's successful collections (location id and every indicator),
so the service never has to keep a country-to-location mapping of its own.

## Running Tests

```bash
pytest                 # unit tests, all external calls mocked
pytest -v --cov=app
```

## Running Migrations

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "description"
```

## Linting & Type Checking

```bash
ruff check .
black .
mypy .
```

## UN Portal API Behaviour and Limitations

- The portal returns **one year per call**, so a series of 11 years is 11 requests per indicator.
- A year that fails is logged and skipped; the collection fails only when **no** year got an answer. That keeps "the source is down" an error (worth retrying) while "one year in the middle is missing" is not. A year the portal answers with 404 did get an answer: it has no data.
- Response times can be slow for large year ranges; prefer the range you need and `/maintenance/refresh-stale` over blanket re-collection.

## Collection rules (the same in every MarketMind collector)

- **Retries** (`app/utils/retry.py`): 408, 429, any 5xx, timeouts and network errors are retried, up to
  `DEFAULT_RETRIES` attempts, waiting `DEFAULT_BACKOFF` seconds doubled per attempt, with jitter, capped at
  60 s; a `Retry-After` header is honoured up to the same cap. Other 4xx are never retried.
- **HTTP status**: `422` when the request names an indicator the catalog does not have, or one without a
  `un_indicator_id` (the only caller error, refused before anything is collected); `503` when the source
  stayed down through every attempt; `502` when the source answered with something unusable.
- **A collection that got nothing raises**: if no requested indicator got an answer, `/indicators/collect`
  answers `503` (every failure transient) or `502`.
- **What counts as a check**: one `undata_requests` row per (country, indicator) that got an answer from the
  source -- data, or a definitive "no data". Failed indicators get a `failed` run and no request row. Run
  statuses are `running`, `success` and `failed`; there is no `partial`.
- **One value per period**: a new collection replaces the periods it brings, and `/observations/series`
  returns one row per period -- the latest collection's; within one collection, the largest value.
- **Timestamps**: timezone-aware UTC everywhere (`app/utils/time.py`).
- **Refresh**: each stale country is replayed with every indicator from all of its successful runs, over
  the Core's window (`years_back` = 10: from ten years ago to this year); it counts as refreshed only when
  every indicator got an answer.

## Database

PostgreSQL 16, UUID primary keys, UTC timestamps, JSONB payloads, Alembic migrations. Raw
responses are never overwritten; each call generates new history.

| Table | Purpose |
|---|---|
| `ingestion_runs` | One row per indicator collected (status, timing, request payload) |
| `undata_requests` | One row per (country, indicator) the portal answered -- the checks |
| `raw_api_responses` | Raw JSON responses |
| `undata_dataflows` | Registered dataflow metadata |
| `undata_datastructures` | Registered dimensions/codes |
| `undata_indicators_catalog` | Internal indicator registry |
| `undata_observations` | Normalized yearly observations |

Migration `002_create_readonly_role` creates a `marketmind_readonly` Postgres role. It is
legacy: it dates from when `marketmind-scoring` read this database directly. Collectors are
now read over HTTP, so nothing uses the role; the migration is kept only so existing
databases keep a linear revision history (technical debt).

## Tech Stack

- Python 3.12, FastAPI, Pydantic v2
- httpx (`httpx.Client`, synchronous)
- SQLAlchemy 2.0 (sync, psycopg2), Alembic
- PostgreSQL 16
- Docker + Docker Compose, Poetry, Pytest

## Team

Final project (TFM) for the *Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa* — **EBIS Business Techschool**. The whole system and how to run it: [marketmind-ai](https://github.com/Market-Mind-AI/marketmind-ai).

- **Miguel Antonio Blanco Salcedo** — [@mikews93](https://github.com/mikews93)
- **Álvaro Augusto De Marco Neto** — [@ironeto](https://github.com/ironeto)

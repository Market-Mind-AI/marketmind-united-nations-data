# MarketMind United Nations Data

Microservice for consuming, normalizing, and persisting United Nations Data (UNdata) via SDMX/SOAP API.

## What it does

- Discovers and registers UNdata datasets/dataflows
- Stores SDMX Query XML obtained from the UNdata SDMX Browser
- Executes SOAP/XML queries against the UNdata API
- Persists raw XML/JSON responses for auditability
- Normalizes demographic and social observations
- Delivers clean, traceable data ready for the MarketMind Core

## What it does NOT do

- Does NOT calculate MOS, Entropy Weight, or TOPSIS
- Does NOT use LLMs
- Does NOT know about Semantic Layer or MarketMind final rules
- Does NOT calculate Market Readiness Score dimensions

## Architecture

```
app/
  api/routes/         # FastAPI route handlers (no business logic)
  core/               # Config, logging, exceptions
  domain/             # Enums, entities
  clients/            # UNDataClient (httpx, SOAP, retry)
  services/           # UNDataService (orchestration)
  repositories/       # Database persistence layer
  db/models/          # SQLAlchemy ORM models
  schemas/            # Pydantic request/response schemas
  utils/              # XML, SDMX, normalization utilities
tests/                # Pytest test suite
alembic/              # Database migrations
```

## Priority Indicators

| Category | Description |
|---|---|
| Total Population | Total resident population |
| Urban Population | Urban area population |
| Urban Population % | Percentage of urban population |
| Population by Age | Age group breakdown |
| Working Age Population | 15-64 age group |
| Population Growth | Annual growth rate |
| Population Density | Population per km² |
| Migration | Net migration (if available) |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Poetry (for local development)

### Run with Docker

```bash
# Copy environment variables
cp .env.example .env

# Start all services
docker compose up --build
```

Services:
- **API**: http://localhost:8000
- **Swagger**: http://localhost:8000/docs

### Run locally

```bash
# Install dependencies
poetry install

# Start PostgreSQL (via Docker or locally)
docker compose up postgres -d

# Run migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --port 8000
```

### Access pgAdmin

pgAdmin was consolidated into `marketmind-scoring` (single instance pointing at
all 5 services' databases). See `marketmind-scoring/README.md`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `marketmind-united-nations-data` | Service name |
| `APP_ENV` | `local` | Environment |
| `APP_PORT` | `8000` | API port |
| `DATABASE_HOST` | `postgres` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_NAME` | `marketmind_united_nations_data` | Database name |
| `DATABASE_USER` | `marketmind` | Database user |
| `DATABASE_PASSWORD` | `marketmind_password` | Database password |
| `UNDATA_SOAP_URL` | `http://data.un.org/ws/NSIStdV20Service.asmx` | UNdata SOAP endpoint |
| `DEFAULT_TIMEOUT` | `60` | HTTP timeout (seconds) |
| `DEFAULT_RETRIES` | `3` | Number of retries |
| `DEFAULT_BACKOFF` | `2` | Backoff multiplier |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints

### Health & Version

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check + DB connectivity |
| `GET` | `/version` | Service version |

### SDMX Queries

| Method | Path | Description |
|---|---|---|
| `POST` | `/sdmx-queries` | Register an SDMX Query XML |
| `GET` | `/sdmx-queries` | List registered queries |
| `POST` | `/execute-query` | Execute a registered query |
| `POST` | `/execute-raw-query` | Execute an inline SDMX query |

### Data Management

| Method | Path | Description |
|---|---|---|
| `POST` | `/dataflows/register` | Register UNdata dataflows |
| `GET` | `/dataflows` | List dataflows |
| `POST` | `/datastructures/register` | Register dimensions/codelists |
| `GET` | `/datastructures` | List datastructures |

### Indicators

| Method | Path | Description |
|---|---|---|
| `POST` | `/indicators/catalog` | Register indicator catalog |
| `GET` | `/indicators/catalog` | List indicator catalog |
| `POST` | `/indicators/collect` | Collect indicators for a country |

### Audit

| Method | Path | Description |
|---|---|---|
| `GET` | `/requests/{id}` | Get request + observations |
| `GET` | `/runs/{id}` | Get ingestion run details |

## How to Use the UNdata SDMX Browser

1. Go to the [UNdata SDMX Browser](http://data.un.org/SdmxBrowser/start)
2. Select a dataset (e.g., Population)
3. Configure filters (country, time period, indicator)
4. Click "View SDMX Query"
5. Copy the XML query

## How to Register and Execute a Query

### Step 1: Register the SDMX Query

```bash
curl -X POST http://localhost:8000/sdmx-queries \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Total Population Spain",
    "description": "Query for total population in Spain",
    "dataset_id": "UN_POPULATION",
    "dataflow_id": "DF_POPULATION",
    "indicator_code": "TOTAL_POPULATION",
    "country": "ES",
    "soap_method": "GetCompactData",
    "sdmx_query_xml": "<QueryMessage xmlns=\"http://www.SDMX.org/resources/SDMXML/schemas/v2_0/message\">...</QueryMessage>"
  }'
```

### Step 2: Execute the Query

```bash
curl -X POST http://localhost:8000/execute-query \
  -H "Content-Type: application/json" \
  -d '{"query_id": "QUERY_UUID_FROM_STEP_1"}'
```

### Step 3: Register Indicators in the Catalog

```bash
curl -X POST http://localhost:8000/indicators/catalog \
  -H "Content-Type: application/json" \
  -d '{
    "indicators": [{
      "indicator_code": "TOTAL_POPULATION",
      "indicator_name": "Total Population",
      "category": "total_population",
      "expected_unit": "persons",
      "marketmind_dimension": "market_population_potential",
      "sdmx_query_id": "QUERY_UUID_FROM_STEP_1"
    }]
  }'
```

### Step 4: Collect Indicators

```bash
curl -X POST http://localhost:8000/indicators/collect \
  -H "Content-Type: application/json" \
  -d '{
    "country": "ES",
    "start_period": "2020",
    "end_period": "2026",
    "indicator_codes": ["TOTAL_POPULATION"]
  }'
```

## Running Tests

```bash
pytest
pytest -v --cov=app
```

## Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Check current revision
alembic current

# Generate a new migration
alembic revision --autogenerate -m "description"
```

## Linting & Type Checking

```bash
ruff check .
black .
mypy .
```

## UNdata API Limitations

- The UNdata API uses SDMX 2.0 with SOAP Web Services
- Not all datasets are available via API
- Rate limits may apply (be defensive with retries and backoff)
- Response times can be slow for large datasets
- XML responses may vary in structure between datasets
- Some datasets may require manual SDMX query construction via the Browser

## Best Practices for Rate Limiting

- Use `DEFAULT_RETRIES=3` and `DEFAULT_BACKOFF=2` for exponential backoff
- Add delays between batch requests
- Monitor `ingestion_runs` for failed requests
- Cache dataflow/datastructure metadata locally
- Avoid parallel requests to the same dataset

## Database

- PostgreSQL 16
- UUID primary keys
- UTC timestamps
- JSONB for normalized payloads
- TEXT for raw XML
- Full audit trail (never overwrites old data)
- Alembic migrations

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic v2
- httpx
- lxml + xmltodict
- SQLAlchemy 2.x
- Alembic
- PostgreSQL 16
- Docker + Docker Compose
- Poetry
- Pytest

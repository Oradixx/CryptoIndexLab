# CryptoIndexLab

A microservices web application where users create and monitor custom cryptocurrency indexes — weighted baskets of coins tracked over time with historical performance charts.

![Index detail page: allocation, candlestick chart with an indicator, and window statistics](docs/images/index-detail.png)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Oradixx/CryptoIndexLab?quickstart=1)

Built as a school project to learn containerization, service isolation, and Docker Compose orchestration (Containerization Technologies course, ESILV, March 2026). The project was first hosted on the school's Gitea; this repository is a mirror with the full commit history.

## Features

- **User accounts** — register, log in, and manage a personal session with JWT-based authentication.
- **Custom indexes** — create named indexes composed of multiple crypto assets with custom weights (e.g. 50% BTC, 30% ETH, 20% SOL).
- **Full CRUD** — edit index name, description, and composition; delete indexes you no longer need.
- **Historical performance** — each index gets a daily performance series computed from real market data (CoinGecko API), displayed as an interactive chart.
- **Technical indicators** — overlay SMA, EMA, RSI, MACD, and Bollinger Bands on the performance chart.
- **Index comparison** — compare your indexes against each other or against individual cryptos (BTC, ETH, etc.) on a normalized base-100 chart.
- **User isolation** — each user only sees and manages their own indexes.
- **Dockerized stack** — the entire app runs with a single `docker compose up` command.

## Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Frontend | Vanilla JavaScript (ES6 modules) | Single-page app with client-side routing |
| Reverse proxy | Traefik v3.6 | Single entry point on port 80, routes to the frontend via Docker labels |
| Frontend server | Nginx 1.27.5 (unprivileged Alpine) | Serves static files and proxies API calls |
| Charts | Lightweight Charts 4.2 | TradingView charting library |
| Backend APIs | Python 3.12 + FastAPI | Two independent microservices |
| Databases | PostgreSQL 16 (Alpine) | One dedicated instance per API |
| Market data | CoinGecko API | Historical daily prices with in-memory cache |
| Containerization | Docker + Docker Compose | Multi-stage builds, non-root users, healthchecks |
| CI/CD | GitHub Actions (originally Gitea Actions) | Build, Trivy vulnerability scan, optional Docker Hub push |

## Architecture

```mermaid
graph TB
    Browser([Browser])

    subgraph Docker Compose
        Traefik["traefik<br/><small>reverse proxy · port 80</small>"]
        Frontend["frontend<br/><small>Nginx · port 8080</small>"]

        subgraph Authentication
            API1["api1<br/><small>FastAPI · port 8001</small>"]
            DB1[("db1<br/><small>PostgreSQL<br/>crypto_auth</small>")]
        end

        subgraph Business Logic
            API2["api2<br/><small>FastAPI · port 8002</small>"]
            DB2[("db2<br/><small>PostgreSQL<br/>crypto_index</small>")]
        end
    end

    CoinGecko([CoinGecko API])

    Browser -->|HTTP| Traefik
    Traefik -->|all requests| Frontend
    Frontend -->|/api1/*| API1
    Frontend -->|/api2/*| API2
    API1 -->|SQL| DB1
    API2 -->|SQL| DB2
    API2 -->|token validation| API1
    API2 -->|market data| CoinGecko
```

### Communication Rules

The services follow strict separation — this is a key part of the project:

| Path | Allowed | How |
|------|---------|-----|
| frontend → api1 | Yes | Nginx reverse proxy (`/api1/*`) |
| frontend → api2 | Yes | Nginx reverse proxy (`/api2/*`) |
| api1 → db1 | Yes | Direct SQL connection (SQLAlchemy) |
| api2 → db2 | Yes | Direct SQL connection (SQLAlchemy) |
| api2 → api1 | Yes | HTTP call to `/me` for token validation |
| api1 → db2 | **No** | api1 has no credentials or connection string for db2 |
| api2 → db1 | **No** | api2 has no credentials or connection string for db1 |
| db1 ↔ db2 | **No** | Databases have no awareness of each other |

Each API only receives the `DATABASE_URL` for its own database. There is no shared database, no shared schema, and no direct database-to-database link. Cross-service communication happens exclusively through HTTP APIs.

The isolation is also enforced at the **network level**: each database sits on its own Docker network, shared only with its API.

| Network | Services |
|---------|----------|
| `frontend-net` | traefik, frontend, api1, api2 |
| `api1-db-net` | api1, db1 |
| `api2-db-net` | api2, db2 |

So api1 cannot even resolve `db2`, and the frontend cannot reach either database.

### Service Overview

| Service | Role | Port |
|---------|------|------|
| `traefik` | Reverse proxy, routes every request to the frontend | 80 (dashboard on 8080) |
| `frontend` | SPA served by Nginx, proxies API calls to backends | 8080 (internal, behind Traefik) |
| `api1` | User registration, login, JWT token management | 8001 |
| `api2` | Index CRUD, market data retrieval, performance calculation | 8002 |
| `db1` | PostgreSQL database dedicated to api1 (users table) | internal |
| `db2` | PostgreSQL database dedicated to api2 (indexes + assets tables) | internal |

## Getting Started

### Try it in the browser (no install)

Click **Open in GitHub Codespaces** above. GitHub starts a cloud machine with Docker, the stack starts automatically (`docker compose up`, about 2 minutes the first time), and the app opens on the forwarded port 80. If it does not open by itself, go to the **Ports** tab and open port 80. Codespaces uses the free monthly quota of your own GitHub account.

### Run it locally

**Prerequisites**

- [Docker](https://www.docker.com/) and Docker Compose (included with Docker Desktop)
- Git

**Installation**

```bash
# 1. Clone the repository
git clone https://github.com/Oradixx/CryptoIndexLab.git
cd CryptoIndexLab

# 2. Create your environment file
cp .env.example .env          # Linux / macOS
Copy-Item .env.example .env   # PowerShell (Windows)

# 3. Start the full stack
docker compose up --build -d

# 4. Wait for all services to be healthy
docker compose ps
```

Once all services show `healthy`, open **http://localhost** in your browser (Traefik listens on port 80; its dashboard is on http://localhost:8080 — insecure mode, for local development only).

### Frontend Hot Reload (Development)

To edit frontend files without rebuilding the container:

```bash
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
```

This bind-mounts `frontend/src/` into the Nginx container. Edit files locally and refresh the browser to see changes.

### Stopping

```bash
docker compose down            # stops containers, keeps database volumes
docker compose down -v         # stops containers AND deletes database volumes
```

## Docker Orchestration

The stack is defined in `docker-compose.yaml` and includes 6 services (traefik, frontend, api1, api2, db1, db2) on three bridge networks (see [Communication Rules](#communication-rules)).

**Startup order** is managed with healthchecks:
1. `db1` and `db2` start first (PostgreSQL readiness check via `pg_isready`)
2. `api1` starts after `db1` is healthy
3. `api2` starts after both `db2` and `api1` are healthy
4. `frontend` starts after both `api1` and `api2` are healthy

**Persistence**: database data is stored in named Docker volumes (`db1-data`, `db2-data`) so data survives container restarts.

**Image hardening**:
- Pinned base images (no `latest` tags)
- Multi-stage builds for Python APIs (builder + lean runtime)
- Non-root execution: Nginx runs as `nginx` user, APIs run as `appuser` (uid 10001)
- Healthchecks defined in each Dockerfile for portability
- Service-level `.dockerignore` files to minimize build contexts
- `pip check` during build to catch broken dependencies early
- No packaging tools in the runtime images: pip, setuptools and wheel are removed after the dependencies are installed

## Environment Variables

All variables are defined in `.env.example` with sensible defaults. Copy it to `.env` before running.

### Frontend

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| `FRONTEND_PORT` | frontend | Not used anymore: the UI is served by Traefik on port 80 | `3000` |
| `FRONTEND_PUBLIC_API1_URL` | frontend | Browser-facing URL for api1 (proxied by Nginx) | `/api1` |
| `FRONTEND_PUBLIC_API2_URL` | frontend | Browser-facing URL for api2 (proxied by Nginx) | `/api2` |

### API1 — Authentication Service

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| `API1_PORT` | api1 | Host port for the auth API | `8001` |
| `API1_LOG_LEVEL` | api1 | Logging level | `info` |
| `API1_JWT_SECRET` | api1 | Secret key for signing tokens | `change_me_for_dev_only` |
| `API1_TOKEN_TTL_SECONDS` | api1 | Token expiration time | `3600` |
| `API1_DATABASE_URL` | api1 | PostgreSQL connection string for db1 | `postgresql+psycopg2://crypto_user:crypto_pass@db1:5432/crypto_auth` |
| `API1_DB_INIT_MAX_ATTEMPTS` | api1 | Max retries for DB connection at startup | `10` |
| `API1_DB_INIT_RETRY_DELAY_SECONDS` | api1 | Delay between DB init retries | `2` |

### API2 — Crypto Index Service

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| `API2_PORT` | api2 | Host port for the index API | `8002` |
| `API2_LOG_LEVEL` | api2 | Logging level | `info` |
| `API2_DATABASE_URL` | api2 | PostgreSQL connection string for db2 | `postgresql+psycopg2://crypto_user:crypto_pass@db2:5432/crypto_index` |
| `API2_DB_INIT_MAX_ATTEMPTS` | api2 | Max retries for DB connection at startup | `10` |
| `API2_DB_INIT_RETRY_DELAY_SECONDS` | api2 | Delay between DB init retries | `2` |
| `API2_MARKET_DATA_BASE_URL` | api2 | CoinGecko API base URL | `https://api.coingecko.com/api/v3` |
| `API2_MARKET_DATA_TIMEOUT_SECONDS` | api2 | Timeout for CoinGecko requests | `10` |
| `API2_MARKET_DATA_CURRENCY` | api2 | Currency for price data | `usd` |
| `API2_MARKET_DATA_DAYS` | api2 | Days of historical data to fetch | `365` |
| `API2_MARKET_DATA_CACHE_TTL_SECONDS` | api2 | Cache duration for market data | `300` |
| `API2_MARKET_DATA_API_KEY` | api2 | Optional CoinGecko API key for higher rate limits | *(empty)* |
| `API2_AUTH_API1_ME_URL` | api2 | Internal URL to validate tokens via api1 | `http://api1:8001/me` |
| `API2_AUTH_TIMEOUT_SECONDS` | api2 | Timeout for token validation calls | `5` |

### Databases

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| `DB1_NAME` | db1 | Database name for api1 | `crypto_auth` |
| `DB1_USER` | db1 | Database user for api1 | `crypto_user` |
| `DB1_PASSWORD` | db1 | Database password for api1 | `crypto_pass` |
| `DB2_NAME` | db2 | Database name for api2 | `crypto_index` |
| `DB2_USER` | db2 | Database user for api2 | `crypto_user` |
| `DB2_PASSWORD` | db2 | Database password for api2 | `crypto_pass` |

> **Note**: Inside Docker, services use internal hostnames (`api1`, `api2`, `db1`, `db2`), not `localhost`. The `FRONTEND_PUBLIC_*` URLs are browser-facing paths proxied by Nginx.

## API Endpoints

### API1 — Authentication (`/api1`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| POST | `/register` | Create a new user account | No |
| POST | `/login` | Log in and receive a bearer token | No |
| GET | `/me` | Get current user info | Yes |

### API2 — Crypto Indexes (`/api2`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/assets/available` | List supported crypto symbols | Yes |
| GET | `/indexes` | List current user's indexes | Yes |
| POST | `/indexes` | Create a new index | Yes |
| GET | `/indexes/{id}` | Get index details with composition | Yes |
| PUT | `/indexes/{id}` | Update index name/description/assets | Yes |
| DELETE | `/indexes/{id}` | Delete an index | Yes |
| GET | `/indexes/{id}/performance` | Get historical performance series | Yes |
| GET | `/market/history/{symbol}` | Get daily price history for a crypto | Yes |

## Demo Walkthrough

Here is the typical user flow to demonstrate the application:

1. **Register** — go to the register page, enter an email, name, and password. The account is created via api1.

2. **Log in** — use your credentials on the login page. A JWT token is stored in the browser for authenticated requests.

3. **Create an index** — from the dashboard, open the create form. Pick a name (e.g. "My Top 3"), optionally add a description, then add assets with weights:
   - BTC — 50%
   - ETH — 30%
   - SOL — 20%
   - Weights must add up to 100%.

4. **View your indexes** — the dashboard lists all your saved indexes with a quick summary of their composition.

5. **Inspect performance** — click on an index to see its detail page:
   - Composition breakdown (assets and weights)
   - Historical performance chart computed from real CoinGecko data
   - Toggle technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
   - Compare with other indexes or individual cryptos on a normalized chart

6. **Edit an index** — update the name, description, or change the asset allocation.

7. **Delete an index** — remove an index you no longer want (with confirmation).

## CI/CD

The project uses GitHub Actions (`.github/workflows/ci.yaml`). The workflow was written for Gitea Actions, which uses the same syntax; it was moved unchanged.

**Pipeline steps**:
1. Build Docker images for `frontend`, `api1`, and `api2`
2. Scan each image with [Trivy](https://trivy.dev/) — fails on MEDIUM, HIGH, or CRITICAL vulnerabilities
3. Push images to Docker Hub (only on `main` branch with credentials)

**Image naming**: `docker.io/<namespace>/cryptoindexlab-<service>:<tag>`

**Required repository secrets** for Docker Hub push:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Without credentials, the pipeline still builds and scans but skips the push step.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Docker engine not running (Windows named pipe error) | Start Docker Desktop and wait until it's fully ready, then retry |
| Services not healthy yet | Run `docker compose ps` and wait — healthchecks take a few seconds |
| A backend fails to start | Check logs: `docker compose logs api1` or `docker compose logs api2` |
| Database connection errors | Make sure `.env` exists and matches `.env.example` defaults |
| CoinGecko rate limiting | Add a free API key in `API2_MARKET_DATA_API_KEY` or wait a few minutes |
| Need a fresh start | `docker compose down -v` then `docker compose up --build -d` |
| Port conflict | Free ports 80 and 8080 (Traefik), or change `API1_PORT` / `API2_PORT` in `.env` |

## Project Structure

```
CryptoIndexLab/
├── frontend/                   # Nginx + vanilla JS single-page app
│   ├── src/
│   │   ├── index.html
│   │   ├── styles.css
│   │   ├── js/
│   │   │   ├── main.js         # App init, routing, state
│   │   │   ├── router.js       # Client-side route definitions
│   │   │   ├── services/       # API clients (auth, indexes, session)
│   │   │   └── views/          # View components (login, dashboard, etc.)
│   │   └── vendor/             # Third-party libs (Lightweight Charts)
│   ├── nginx/default.conf      # Nginx config with API proxying
│   └── Dockerfile
├── api1/                       # Authentication microservice
│   ├── src/
│   │   ├── main.py
│   │   ├── core/               # Config, security, dependencies
│   │   ├── db/                 # Database setup
│   │   ├── models/             # SQLAlchemy models (User)
│   │   ├── routes/             # FastAPI endpoints
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── services/           # Business logic (AuthService)
│   └── Dockerfile
├── api2/                       # Crypto index microservice
│   ├── src/
│   │   ├── main.py
│   │   ├── core/               # Config, symbol mapping, dependencies
│   │   ├── db/                 # Database setup
│   │   ├── models/             # SQLAlchemy models (Index, IndexAsset)
│   │   ├── routes/             # FastAPI endpoints
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # Business logic + CoinGecko provider
│   └── Dockerfile
├── docs/                       # Additional documentation
│   └── architecture.md
├── docker-compose.yaml         # Production-like stack definition
├── docker-compose.dev.yaml     # Dev override (frontend hot reload)
├── .env.example                # Environment variable template
├── .github/workflows/ci.yaml   # CI/CD pipeline
└── AUTHORS.md                  # Team members
```

## Authors

See [AUTHORS.md](AUTHORS.md).

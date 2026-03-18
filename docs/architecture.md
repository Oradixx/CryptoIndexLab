# Architecture

This document describes how CryptoIndexLab is structured as a microservices application and how the services interact.

## Services

### frontend

- **Tech**: Nginx 1.27.5 (unprivileged Alpine image) serving a vanilla JavaScript SPA.
- **Role**: serves the web UI and acts as a reverse proxy for backend APIs.
- **Routing**: Nginx forwards `/api1/*` to `api1:8001` and `/api2/*` to `api2:8002`, so the browser never talks to backend containers directly. This avoids CORS configuration entirely.
- **Auth**: the frontend stores a JWT token in localStorage and attaches it as a `Bearer` header on every authenticated request.

### api1 — Authentication Service

- **Tech**: Python 3.12, FastAPI, SQLAlchemy 2.0, Uvicorn.
- **Role**: manages user accounts and identity.
- **Endpoints**: `POST /register`, `POST /login`, `GET /me`, `GET /health`.
- **Database**: connects only to `db1` (`crypto_auth`). Stores a single `users` table.
- **Token management**: uses a simple JWT-style token mechanism with configurable TTL. Passwords are hashed before storage.

### api2 — Crypto Index Service

- **Tech**: Python 3.12, FastAPI, SQLAlchemy 2.0, Uvicorn, httpx.
- **Role**: handles all business logic around crypto indexes.
- **Endpoints**: full CRUD on indexes, available assets list, market history, index performance.
- **Database**: connects only to `db2` (`crypto_index`). Stores `indexes` and `index_assets` tables.
- **Token validation**: api2 does not manage users itself. When a request comes in with a bearer token, api2 calls `api1 /me` over HTTP to verify the token and get the user identity. This keeps auth logic centralized in api1.
- **Market data**: fetches historical prices from the CoinGecko API with in-memory caching (default 5-minute TTL) to avoid hitting rate limits.

### db1 and db2

- **Tech**: PostgreSQL 16 (Alpine).
- **Role**: dedicated, isolated databases — one per API service.
- **Persistence**: data is stored in Docker named volumes (`db1-data`, `db2-data`).
- **No cross-access**: db1 and db2 have no link, no shared schema, and no replication. Each API only has connection credentials for its own database.

## Service Isolation

This is a core requirement of the project. The isolation is enforced at the configuration level:

```
frontend ──proxy──▶ api1 ──SQL──▶ db1
                      ▲
frontend ──proxy──▶ api2 ──SQL──▶ db2
                    │
                    └──HTTP──▶ api1 (token validation)
                    └──HTTP──▶ CoinGecko (market data)
```

**What is allowed:**
- frontend → api1 (Nginx proxy)
- frontend → api2 (Nginx proxy)
- api1 → db1 (SQL, via `API1_DATABASE_URL`)
- api2 → db2 (SQL, via `API2_DATABASE_URL`)
- api2 → api1 (HTTP, for token validation via `API2_AUTH_API1_ME_URL`)
- api2 → CoinGecko (HTTP, external market data)

**What is NOT allowed:**
- api1 → db2 (api1 has no credentials for db2)
- api2 → db1 (api2 has no credentials for db1)
- db1 ↔ db2 (no replication, no foreign data wrapper, no shared network alias)
- frontend → db1 or db2 (databases are not exposed on host ports)

## Docker Compose Orchestration

All services run on a single bridge network (`cryptoindexlab-net`). Service isolation is enforced by application configuration (each service only has the connection strings it needs), not by separate Docker networks.

### Startup Order

Docker Compose healthchecks enforce a safe startup sequence:

1. **db1** and **db2** start first — they report healthy when `pg_isready` succeeds
2. **api1** waits for db1 to be healthy before starting
3. **api2** waits for both db2 and api1 to be healthy
4. **frontend** waits for both api1 and api2 to be healthy

This means a single `docker compose up` brings everything up in the right order without race conditions.

### Image Build Strategy

All three application services use hardened Docker images:

- **Pinned base images** — no `:latest` tags, all versions are locked
- **Multi-stage builds** (api1, api2) — a builder stage installs Python dependencies, the runtime stage only copies the virtual environment and application code
- **Non-root users** — Nginx runs as `nginx`, APIs run as `appuser` (uid 10001)
- **Healthchecks in Dockerfiles** — health behavior is portable even outside Compose
- **Lean build contexts** — `.dockerignore` per service keeps the build context small

## Data Model

### db1 — crypto_auth

```
users
├── id            UUID (primary key)
├── email         VARCHAR(255), unique, indexed
├── hashed_password VARCHAR(255)
├── name          VARCHAR(100), nullable
└── created_at    TIMESTAMP (server default: now)
```

### db2 — crypto_index

```
indexes
├── id            UUID (primary key)
├── name          VARCHAR(100)
├── description   VARCHAR(500), nullable
├── user_id       VARCHAR(100), nullable
└── created_at    TIMESTAMP (server default: now)

index_assets
├── id            INTEGER (primary key, autoincrement)
├── index_id      VARCHAR(36), FK → indexes.id (cascade delete)
├── symbol        VARCHAR(10)
├── weight        FLOAT
└── UNIQUE(index_id, symbol)
```

## Request Flow Examples

### User creates an index

1. Browser sends `POST /api2/indexes` with bearer token and index payload
2. Nginx forwards the request to `api2:8002/indexes`
3. api2 extracts the bearer token and calls `GET http://api1:8001/me` to validate it
4. api1 checks the token, returns user info (or 401)
5. api2 validates the index payload (name, assets, weights summing to 100%)
6. api2 inserts the index and assets into db2
7. api2 returns the created index to the browser

### User views index performance

1. Browser sends `GET /api2/indexes/{id}/performance` with bearer token
2. api2 validates the token via api1 (same as above)
3. api2 fetches historical prices for each asset in the index from CoinGecko (or from cache)
4. api2 computes the weighted daily performance series
5. api2 returns the performance data to the browser
6. The frontend renders the chart using Lightweight Charts

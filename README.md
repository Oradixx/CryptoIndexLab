# CryptoIndexLab

CryptoIndexLab is a school microservices project to build a web app where users can create and monitor custom cryptocurrency indexes.

## Problem Solved

Most simple crypto tools only track single assets. CryptoIndexLab focuses on user-defined indexes (custom baskets of coins with weights) to support portfolio-style tracking and experimentation.

## Architecture Overview

- `frontend`: MVP web app (login, register, dashboard, create-index form) connected to backend APIs.
- `api1`: users/authentication service (accounts, login, identity endpoints).
- `api2`: crypto index business service (index creation and management logic).
- `db1`: dedicated database for `api1`.
- `db2`: dedicated database for `api2`.

The repository currently provides a clean microservices foundation. Authentication and crypto index business logic are being implemented incrementally.

## API1 Current Scope

`api1` now exposes a minimal FastAPI authentication service backed by its dedicated PostgreSQL database (`db1`):

- `GET /health`
- `POST /register`
- `POST /login`
- `GET /me`

Passwords are hashed before storage, `/me` is protected with a simple bearer token mechanism, and the users table is auto-created at service startup (basic schema bootstrap before introducing migrations).

## API2 Current Scope

`api2` now exposes a FastAPI business service for custom crypto indexes backed by its dedicated PostgreSQL database (`db2`):

- `GET /health`
- `GET /assets/available`
- `GET /indexes`
- `GET /indexes/{index_id}`
- `POST /indexes`
- `PUT /indexes/{index_id}`
- `DELETE /indexes/{index_id}`
- `GET /market/history/{symbol}`
- `GET /indexes/{index_id}/performance`

Indexes and index assets are now persisted (`Index` + `IndexAsset` tables), while `/assets/available` remains a controlled internal list of supported symbols.
Indexes are now user-owned: authenticated index endpoints return only the current user's resources and reject cross-user access.
`api2` can now fetch daily historical crypto prices (about 1 year) through a dedicated market-data service, with symbol mapping, response normalization, and lightweight in-memory caching for repeated requests.
Supported market-history symbols include `BTC`, `ETH`, `SOL`, `XRP`, `DOGE` (plus `ADA` and `BNB`).
Saved indexes can now return a historical performance series (normalized base value, daily points, and simple return summary) to power future frontend charts.
User-owned indexes now support full CRUD updates: owners can edit index name/composition and delete indexes, while cross-user edit/delete access is rejected.
`api2` remains decoupled from `api1` database by validating bearer tokens through the `api1` identity endpoint.

## Frontend Current Scope

The frontend now provides the first usable MVP flow:

- Login page (`api1` `/login` + `/me`)
- Register page (`api1` `/register`)
- Authenticated dashboard with list of saved indexes (`api2` `/indexes`)
- Create-index page with asset/weight form validation (`api2` `/assets/available` + `/indexes`)
- Dedicated index list view with quick summaries (`api2` `/indexes`)
- Index detail view with composition and historical performance section (`api2` `/indexes/{index_id}` + `/indexes/{index_id}/performance`)
- Index edit flow to update name/assets/weights (`api2` `PUT /indexes/{index_id}`)
- Index delete action with confirmation (`api2` `DELETE /indexes/{index_id}`)
- Simple built-in line chart (SVG) for demo-friendly performance visualization

Authentication state is handled client-side with a stored bearer token.
Frontend sends authenticated requests to protected `api2` index endpoints so each user only sees and accesses their own indexes.
By default, frontend nginx proxies `/api1/*` to `api1` and `/api2/*` to `api2`, so the browser can call backend services without extra CORS configuration.

## Isolation Rules (Target)

- `api1` writes only to `db1`.
- `api2` writes only to `db2`.
- Services communicate through API calls, not shared databases.
- Databases remain isolated per backend service.

## Deployment Goal

The final goal is a deployable Docker-based microservices app that can be started and tested by the professor with Docker Compose.

# CryptoIndexLab

CryptoIndexLab is a school microservices project to build a web app where users can create and monitor custom cryptocurrency indexes.

## Problem Solved

Most simple crypto tools only track single assets. CryptoIndexLab focuses on user-defined indexes (custom baskets of coins with weights) to support portfolio-style tracking and experimentation.

## Architecture Overview

- `frontend`: web UI placeholder for authentication and index management flows.
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

`api2` now exposes a first FastAPI business skeleton for custom crypto indexes using in-memory/mock data:

- `GET /health`
- `GET /assets/available`
- `GET /indexes`
- `GET /indexes/{index_id}`
- `POST /indexes`

This milestone validates the index domain shape (name, assets, weights, future owner linkage) before integrating real persistence, price feeds, and performance calculations.

## Isolation Rules (Target)

- `api1` writes only to `db1`.
- `api2` writes only to `db2`.
- Services communicate through API calls, not shared databases.
- Databases remain isolated per backend service.

## Deployment Goal

The final goal is a deployable Docker-based microservices app that can be started and tested by the professor with Docker Compose.

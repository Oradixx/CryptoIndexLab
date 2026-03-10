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

This first commit provides the project foundation only. Full authentication and crypto index business logic will be implemented in later iterations.

## Isolation Rules (Target)

- `api1` writes only to `db1`.
- `api2` writes only to `db2`.
- Services communicate through API calls, not shared databases.
- Databases remain isolated per backend service.

## Deployment Goal

The final goal is a deployable Docker-based microservices app that can be started and tested by the professor with Docker Compose.

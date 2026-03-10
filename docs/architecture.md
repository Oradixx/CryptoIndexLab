# Architecture Note

## Service Responsibilities

- `frontend`: user-facing web application.
- `api1`: user management and authentication service.
- `api2`: crypto index business service.
- `db1`: isolated datastore for `api1`.
- `db2`: isolated datastore for `api2`.

## Isolation Rules

1. `api1` must only access `db1`.
2. `api2` must only access `db2`.
3. Any cross-domain communication must happen via HTTP APIs between services.
4. Services run in isolated containers and communicate through the internal Docker network.

## Evolution Plan

- Add schema migrations and persistence models for each backend.
- Implement auth flows in `api1` and index domain logic in `api2`.
- Replace frontend placeholder with full UI connected to both APIs.

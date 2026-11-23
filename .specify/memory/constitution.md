<!--
Sync Impact Report:
- Version change: 1.0.0 -> 1.1.0
- Additions: Explicit Alignment with Project Architecture Decision Records (ADRs) and Agent Directives (AGENTS.md / CLAUDE.md)
  1. Formalized State Machine & Audit Trail invariant: Non-negotiable transitions (UNASSIGNED -> ASSIGNED -> PICKED_UP -> IN_TRANSIT -> DELIVERED -> COMPLETED), mandatory POD evidence before completion, immutable history (soft-delete only).
  2. ACID Resource Booking & Concurrency Guard: Strict transactional locking on truck and driver schedules to eliminate race conditions between multiple dispatchers (TRN-02).
  3. Clean Layered Architecture: Strict presentation (FastAPI/Jinja2), business domain (Service), data persistence (Repository/SQLAlchemy) separation.
  4. Non-negotiable Security & Observability: Session-based cookie auth, no plain text secrets, standard Python logging (print() strictly forbidden).
- Technology Stack: Python 3.11+ (FastAPI), SQLAlchemy, Jinja2/Bootstrap 5, SQLite / SQL Server 2022 / PostgreSQL, pytest.
- Governance: Constitution supersedes all code; operationalized via AGENTS.md and CLAUDE.md.
-->

# Freight Transportation System Constitution

## Core Principles

### I. Layered Architecture & Separation of Concerns
Every component must follow a clean layered architecture:
- **Presentation / API Layer**: FastAPI routers handle HTTP requests, validate input via Pydantic schemas, and return Jinja2 templates or structured JSON. No business logic or SQL queries are allowed in this layer.
- **Service Layer**: Pure business logic orchestrator (validating truck capacity, driver availability, state transitions). Does not handle direct HTTP requests or raw SQL.
- **Data Access Layer (Repository / DAO)**: Handles all database operations using SQLAlchemy or parameterized queries. Direct string concatenation of SQL is strictly forbidden.
- **Model / Schema Layer**: Declares database models and data validation contracts.

### II. State Machine Integrity & Immutable Audit Trail
The lifecycle of a transport order follows an explicit state machine:
`UNASSIGNED` ➔ `ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED`.
- State transitions must not skip intermediate stages (e.g., cannot jump from `UNASSIGNED` directly to `DELIVERED`).
- Any truck or driver once associated with a transactional record must never be deleted (`soft-delete` only; historical audit trails are preserved).
- Proof of delivery (POD file: PDF/JPG/PNG) and actual delivery timestamp are mandatory before marking `DELIVERED` and closing as `COMPLETED`.

### III. Strict Concurrency & ACID Booking
Truck and driver scheduling must be protected against race conditions:
- When multiple dispatchers attempt to assign the same truck or driver to overlapping time windows, only one transaction must succeed; other concurrent requests must fail gracefully with a conflict notification.
- Booking operations must execute in an atomic transaction; partial bookings (e.g., truck booked but driver failed) are prohibited.

### IV. Test-Driven Verification (TDD)
Automated testing is non-negotiable for business rules (BR-06 to BR-09, BR-15 to BR-17):
- Unit and integration tests using `pytest` must cover critical paths: overweight rejection, schedule conflict rejection, state transition guardrails, and concurrent dispatching.
- Tests must pass cleanly (`pytest`) before any feature is declared complete.

### V. Security, Observability & Simplicity
- **Security**: No secrets or credentials committed to source code or environment files. Session/Authentication handling must be centralized.
- **Observability**: Use standard Python `logging` (`logger.info`, `logger.error`). `print()` statements are forbidden in production code. Never log sensitive personal data.
- **Simplicity**: Do not over-engineer with unnecessary microservices or distributed queues unless explicitly specified.

## Technology Stack & Constraints

- **Backend**: Python 3.11+ (FastAPI)
- **Frontend / UI**: Jinja2 Templates + Bootstrap 5 (or responsive HTML/CSS/JS)
- **Database**: SQLite (local development / testing) / SQL Server 2022 / PostgreSQL
- **ORM / Data Access**: SQLAlchemy Core/ORM with transaction management
- **Documentation**: Automatic OpenAPI 3.0 (Swagger UI at `/docs`)
- **Validation**: Pydantic v2 schemas

## Development Workflow & Quality Gates

1. **Specification**: Features start with clear specs defining preconditions, inputs, and acceptance criteria.
2. **Review & Planning**: Technical designs must identify state changes, locking strategies, and schema updates.
3. **Automated Testing**: Test suites must be maintained alongside implementation code.
4. **Git Standards**: Feature branches with Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`).

## Governance

- This Constitution serves as the single source of truth for engineering practices, design standards, and architecture guardrails.
- Any architectural change or deviation from these principles requires an amendment to this document with justification.
- The `AGENTS.md` and `CLAUDE.md` files operationalize these constitutional rules for AI agents and developers working in this repository.

**Version**: 1.1.0 | **Ratified**: 2026-11-23 | **Last Amended**: 2026-11-23

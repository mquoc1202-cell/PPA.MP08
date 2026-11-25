<!--
Sync Impact Report:
- Version change: 1.2.0 -> 1.2.1
- Modified Principles:
  - Principle VI: Unified Precision UI/UX Design System (BMW Design DNA & GSAP)
    - Enforced strict Cross-Page Visual & Interaction Parity between the Login Terminal (/login) and the Main Operations Dashboard (/dashboard).
    - Prescribed identical luminous surface treatment (linear-gradient 145deg, pure white to soft slate #f8fafc), hairline structural borders (#e2e8f0), absolute zero border-radius (0px), and BMW Connected Drive typographic tracking across both viewports.
    - Standardized telemetry node representations, system status tags (ISO 27001, online pills), and coordinated GSAP motion choreography (power2.out, 0.25-0.35s).
- Deferred Intents:
  - Direct template refactoring of src/templates/dashboard/index.html (deferred per speckit-constitution Scope Guard). Suggested follow-up: /speckit-specify or /speckit-implement.
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

### VI. Unified Precision UI/UX Design System (BMW Design DNA & GSAP)
All web interfaces (Login, Dashboard, Dispatch, Management) must strictly adhere to the unified visual and interaction rules, with complete cross-page parity between the Login Terminal (`/login`) and the Main Operations Dashboard (`/dashboard`):
- **Cross-Page Visual Parity**:
  - The architectural aesthetic established on `/login` (luminous gradient cards `linear-gradient(145deg, #ffffff 0%, #f8fafc 100%)`, crisp hairline borders `#e2e8f0`, and ambient micro-shadows) must be mirrored across `/dashboard` KPI stat cards, telemetry graphs, and table containers.
  - No interface element may deviate from the shared visual DNA; moving from `/login` to `/dashboard` must feel like entering the same continuous operating environment.
- **Geometry & Border Radius**: Absolute zero border radius (`border-radius: 0 !important;`) applied universally across cards, buttons, form inputs, badges, and modals. Curved or bubbly corners are strictly prohibited.
- **Typography Hierarchy**: Dual hierarchy inspired by BMW Connected Drive:
  - Headings / KPI metrics: Geometric, bold/medium (`font-weight: 700` or `600`), uppercase/technical tracking.
  - Body copy / labels: Clean, highly legible, light/regular (`font-weight: 300` or `400`), fallback Inter / system-ui.
- **Luminous Precision Palette**:
  - Primary Brand & Action: Electric Corporate Blue `#1c69d4` (Hover: `#0653b6`).
  - Dark Surface & Header Accent: Deep Navy `#1a2129`.
  - Canvas & Background: Soft, glare-reducing off-white `#f8f9fa`.
  - Surface & Card: Pure white `#ffffff` with crisp hairline borders `#e2e8f0` and subtle elevation shadows.
  - System Badges: Active/Success (`#22c55e`), Warning/Assigned (`#f59e0b`), In Transit (`#1c69d4`), Inactive (`#6c757d`), Danger/Issue (`#dc2626`).
- **Iconography**: Exclusively use Bootstrap Icons 1.11+ (`<i class="bi bi-..."></i>`). Arbitrary emoji or disparate icon styles are prohibited.
- **GSAP Motion & Micro-interactions**:
  - All button hover, card reveal, telemetry animations, and entrance transitions must use GSAP Core with GPU acceleration (`transform`, `opacity`).
  - Standard duration: `0.2s` - `0.35s` with `power2.out` easing.
  - Coordinated entrance: Staggered reveal for KPI metrics, counter tweens for telemetry data, scaleX animations for capacity bars.
  - Reduced Motion: Respect user `prefers-reduced-motion` settings.
- **Template Inheritance & Role Rendering**:
  - Every page must inherit from `templates/base.html` or dedicated authenticated layout with global `theme.css`.
  - Dispatch actions are restricted to `DSP`; `SAL` and `MGR` roles receive read-only interfaces.
  - Empty states must provide structured feedback with `<i class="bi bi-inbox fs-2">` and descriptive guidance.

## Technology Stack & Constraints

- **Backend**: Python 3.11+ (FastAPI)
- **Frontend / UI**: Jinja2 Templates + Bootstrap 5 + `src/static/css/theme.css` + GSAP 3.12 + Bootstrap Icons 1.11+
- **Database**: SQLite (local development / testing) / SQL Server 2022 / PostgreSQL
- **ORM / Data Access**: SQLAlchemy Core/ORM with transaction management
- **Documentation**: Automatic OpenAPI 3.0 (Swagger UI at `/docs`)
- **Validation**: Pydantic v2 schemas
- **Testing**: pytest + pytest-asyncio + httpx (TestClient)

## Development Workflow & Quality Gates

1. **Specification**: Features start with clear specs defining preconditions, inputs, UI wireframes, and acceptance criteria.
2. **Review & Planning**: Technical designs must identify state changes, locking strategies, and schema updates.
3. **UI/UX Design System Gate**: Every new or refactored view must be audited against Principle VI (0px radius, typography weights, color tokens, GSAP micro-interactions, empty states, and Login-Dashboard parity) before release.
4. **Automated Testing**: Test suites must be maintained alongside implementation code.
5. **Git Standards**: Feature branches with Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`).

## Governance

- This Constitution serves as the single source of truth for engineering practices, design standards, and architecture guardrails.
- Any architectural change or deviation from these principles requires an amendment to this document with justification.
- The `AGENTS.md`, `frontend/DESIGN.md`, and `CLAUDE.md` files operationalize these constitutional rules for AI agents and developers working in this repository.

**Version**: 1.2.1 | **Ratified**: 2026-11-23 | **Last Amended**: 2026-11-25

# UX Requirements Quality Checklist: Dispatch & Dashboard Management

**Purpose**: Validate requirement quality, completeness, clarity, and cross-page synchronization with Login and Design System under Constitution Principle VI.
**Created**: 2026-11-25
**Feature**: [003-trip-dispatch-and-conflict-management/spec.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/spec.md)
**Governance**: [Constitution Principle VI](file:///d:/PPA.MP08_GROUP3/.specify/memory/constitution.md)

**Review Ownership**: This checklist is a reviewer-owned requirements-quality review artifact. Mark an item `[x]` only when the reviewer determines the requirements-quality criterion is satisfied.
**Marker Semantics**: `[x]` means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.

## Cross-Page Synchronization & Token Alignment

- [ ] CHK001 Are zero-border-radius (`0px`) requirements strictly aligned across KPI cards, tables, modal dialogs, and action bars matching the Login page? [Consistency, Constitution Principle VI]
- [ ] CHK002 Are color tokens (Primary `#1c69d4`, Accent `#1a2129`, Canvas `#f8f9fa`, Surface `#ffffff`, Border `#e2e8f0`) identical to the Login theme specification? [Consistency, Constitution Principle VI]
- [ ] CHK003 Are system status badges (`ACTIVE`, `ASSIGNED`, `IN_TRANSIT`, `DELIVERED`, `ISSUE`) explicitly mapped to standardized token colors? [Clarity, Constitution Principle VI]

## Typography & Data Presentation

- [ ] CHK004 Is the dual typography hierarchy (Bold 700 KPI metrics + Light 300 data labels) specified for all dashboard telemetry widgets? [Completeness, Constitution Principle VI]
- [ ] CHK005 Are table column headers and alignment rules (e.g. actions right-aligned `text-end`) documented with specific CSS conventions? [Clarity, AGENTS.md §3.4]

## Motion & Interactive Feedback

- [ ] CHK006 Are GSAP reveal animations (staggered row entrance, number count-up, progress bar fill) defined with explicit easing and durations? [Completeness, Constitution Principle VI]
- [ ] CHK007 Are hover elevations and interactive click-states on table rows and action buttons synchronized with base button micro-interactions? [Consistency, Constitution Principle VI]
- [ ] CHK008 Are reduced-motion fallbacks documented for heavy dashboard animations? [Coverage, Non-Functional]

## Empty States & Role-Based UI Permissions

- [ ] CHK009 Are empty state requirements (icon `<i class="bi bi-inbox fs-2">` + descriptive message) specified for unassigned trips, empty schedules, and filter misses? [Completeness, Edge Case]
- [ ] CHK010 Are role-based permission rendering rules (buttons visible only for `DSP`, read-only for `SAL`/`MGR`) explicitly specified for all mutation actions? [Coverage, Spec §FR-05]
- [ ] CHK011 Are conflict modal dialog requirements specified with explicit trip codes, start/end times, and conflict reasons? [Completeness, Spec §FR-07]

## Notes

- Mark items `[x]` only after review confirms the requirement-quality criterion is satisfied
- Leave items unchecked when they still require clarification, correction, or reviewer evaluation
- `/speckit-implement` reads checklist checkbox state as a gate and must not modify markers
- Items are numbered sequentially for easy reference

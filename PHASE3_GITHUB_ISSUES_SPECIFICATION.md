# PHASE 3 GITHUB ISSUES - SPECIFICATION & CREATION PLAN

**Date:** January 28, 2026  
**Status:** READY FOR CREATION  
**Total Issues:** 5 (1 P0 + 4 P1 + multiple subtasks)

---

## ISSUE #45: PHASE 3a - Expand Investigation Data Model (P0 BLOCKER)

**Title:** Phase 3a - Expand Investigation Data Model & Event Schema

**Type:** Task / Epic

**Priority:** P0 (Blocks all downstream work)

**Estimated Effort:** 10-12 hours

**Description:**

## Objective

Extend the current minimal Investigation data model to support comprehensive root cause analysis workflows. Define the Event schema that will link multiple signal sources (git, CI, logs, metrics, traces) to investigations.

## Current State

The Investigation model is incomplete:
- ~224 lines in `src/models/investigation.py`
- Only basic fields: id, title, status
- Missing: root cause, timeline, component tracking, relationships
- No Event schema defined
- Event linking service is basic (342 lines)

## Requirements

### Investigation Model Expansion
Add these core fields to Investigation:

```python
class Investigation(BaseModel):
    # Existing fields (keep)
    id: str  # UUID
    title: str
    description: str
    status: enum [open, in_progress, resolved, closed]
    
    # New fields (REQUIRED)
    impact_severity: enum [critical, high, medium, low]
    detected_at: datetime
    started_at: datetime
    resolved_at: datetime
    root_cause: str (optional, 2000 char limit)
    remediation: str (optional, 2000 char limit)
    lessons_learned: str (optional, 2000 char limit)
    
    # Component & service tracking
    component_affected: str  # "auth-service", "api-gateway", etc.
    service_affected: str  # "production", "staging", etc.
    tags: [str]  # Searchable tags
    
    # Relationships
    event_ids: [str]  # Links to events
    related_investigation_ids: [str]  # Cross-references
    
    # Ownership & workflow
    created_by: str  # User ID
    assigned_to: str  # User ID (optional)
    priority: enum [p0, p1, p2, p3]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime  # Soft delete
```

### Event Schema (NEW)

Create new Event model to support multiple signal sources:

```python
class Event(BaseModel):
    # Identity
    id: str  # UUID
    timestamp: datetime  # When event occurred
    source: enum [git, ci, logs, metrics, traces, manual]
    
    # Content
    event_type: str  # "commit", "build_failure", "error_spike", "deployment", etc.
    data: dict  # Source-specific payload
    
    # Severity & classification
    severity: enum [critical, high, medium, low, info]
    tags: [str]
    
    # Relationships
    investigation_ids: [str]  # Links to investigations
    source_id: str  # External ID (commit hash, build ID, etc.)
    
    # Metadata
    parsed_at: datetime  # When we parsed it
    linked_at: datetime  # When linked to investigation
    metadata: dict  # Additional context
    
    # Soft delete
    deleted_at: datetime  # null = active
```

### Sub-Task 45a: Update Investigation Store

**Effort:** 4 hours

- [ ] Expand Investigation table schema in SQLite
- [ ] Add columns: impact_severity, detected_at, started_at, resolved_at, root_cause, remediation, lessons_learned, component_affected, service_affected, tags, event_ids, created_by, assigned_to, priority
- [ ] Create migration script: `migrations/001_expand_investigation_model.sql`
- [ ] Update `src/store/investigation_store.py` methods:
  - [ ] `create_investigation()` - accept new fields
  - [ ] `update_investigation()` - handle new fields
  - [ ] `get_investigation()` - fetch with related data
  - [ ] Add `get_by_component()` - filter by component_affected
  - [ ] Add `get_by_priority()` - filter by priority
  - [ ] Add `get_by_severity()` - filter by impact_severity

### Sub-Task 45b: Create Event Store

**Effort:** 4 hours

- [ ] Create `src/store/event_store.py` (following repository pattern)
- [ ] Implement SQLite table: `events` with fields from Event model
- [ ] Implement methods:
  - [ ] `create_event(event: Event) -> str` - returns event ID
  - [ ] `get_event(event_id: str) -> Event`
  - [ ] `get_events_by_investigation(investigation_id: str) -> List[Event]`
  - [ ] `get_events_by_source(source: str) -> List[Event]`
  - [ ] `get_events_by_timestamp(start: datetime, end: datetime) -> List[Event]`
  - [ ] `link_event_to_investigation(event_id: str, investigation_id: str) -> bool`
  - [ ] `delete_event(event_id: str)` - soft delete

### Sub-Task 45c: Update Event Linker Service

**Effort:** 2-3 hours

- [ ] Enhance `src/services/event_linker.py` to:
  - [ ] Accept Event objects (not just git/CI specific)
  - [ ] Implement event deduplication (same source_id = same event)
  - [ ] Add timestamp-based linking (find investigations within time window)
  - [ ] Add component-based linking (match component_affected)
  - [ ] Add tag-based linking (semantic matching)
  - [ ] Return confidence score for each link
  - [ ] Log linking decisions for debugging

### Sub-Task 45d: Write 25+ Tests

**Effort:** 2-3 hours

- [ ] Create `tests/test_investigation_model_expanded.py`
  - [ ] Test Investigation model with all new fields
  - [ ] Test field validation (severity enum, timestamps, etc.)
  - [ ] Test soft deletes
  - [ ] Test field length limits (root_cause, remediation, etc.)

- [ ] Create `tests/test_event_model.py`
  - [ ] Test Event model creation with all fields
  - [ ] Test source enum validation
  - [ ] Test severity enum validation
  - [ ] Test event_type validation

- [ ] Create `tests/test_event_store.py`
  - [ ] Test CRUD operations
  - [ ] Test query by source, timestamp, component
  - [ ] Test event-investigation linking
  - [ ] Test soft deletes
  - [ ] Performance test: query 1000+ events in <100ms

- [ ] Create `tests/test_event_linker_enhanced.py`
  - [ ] Test event deduplication
  - [ ] Test timestamp-based linking
  - [ ] Test component-based linking
  - [ ] Test confidence score calculation
  - [ ] Test linking with missing fields

**Acceptance Criteria:**

- [ ] Investigation model expanded with 12 new fields
- [ ] Event model created with 10+ fields
- [ ] Both models validated with tests
- [ ] Event store implemented (CRUD + 4 query methods)
- [ ] Event linker enhanced for multiple linking strategies
- [ ] 25+ new tests, all passing
- [ ] Database migration script created
- [ ] Backward compatibility: old investigations still work
- [ ] Documentation: Update `docs/schema.md` with new models
- [ ] Performance: Query 1000+ investigations/events in <100ms

**Success Metrics:**

- All 25+ tests passing (100%)
- Database migration executes cleanly
- No breaking changes to existing API
- Event linking confidence score >80% for git events
- <100ms query time for 1000+ records

---

## ISSUE #46: PHASE 3b - Advanced Connectors & Resilience (P1 BLOCKER)

**Title:** Phase 3b - Advanced Event Connectors & Resilience Patterns

**Type:** Task / Epic

**Priority:** P1 (Blocks API completeness)

**Estimated Effort:** 12-15 hours

**Description:**

## Objective

Extend connector support beyond git & CI to include logs, metrics, and traces. Implement enterprise-grade resilience patterns (retry, circuit breaker, exponential backoff, dead letter queues).

## Current State

Current connectors are basic:
- `src/connectors/git_connector.py` - 61 lines (minimal)
- `src/connectors/ci_connector.py` - 52 lines (minimal)
- No logs/metrics/traces connectors
- No resilience patterns (retry, circuit breaker, etc.)
- No monitoring/alerting for connector failures

## Requirements

### Sub-Task 46a: Build Logs Connector (3-4 hours)

**Target:** Ingest structured logs from JSON log stream or log aggregator (ELK, Splunk, etc.)

- [ ] Create `src/connectors/logs_connector.py`
- [ ] Implement:
  - [ ] `fetch_logs(start: datetime, end: datetime, filter: str) -> List[LogEvent]`
  - [ ] Parse JSON logs into Event schema
  - [ ] Classify severity from log level
  - [ ] Extract error context (stack traces, user actions)
  - [ ] Handle pagination (large log sets)

- [ ] Tests:
  - [ ] Parse sample JSON logs
  - [ ] Extract errors correctly
  - [ ] Handle truncated/malformed logs gracefully

### Sub-Task 46b: Build Metrics Connector (3-4 hours)

**Target:** Ingest metrics from monitoring system (Prometheus, Datadog, CloudWatch)

- [ ] Create `src/connectors/metrics_connector.py`
- [ ] Implement:
  - [ ] `fetch_metrics(start: datetime, end: datetime, metric_name: str) -> List[MetricEvent]`
  - [ ] Detect anomalies (spike detection, threshold violations)
  - [ ] Classify severity based on magnitude/impact
  - [ ] Extract correlated metrics (CPU+memory spike = system issue)
  - [ ] Cache metric queries (time-range based)

- [ ] Tests:
  - [ ] Detect CPU/memory spikes
  - [ ] Classify disk full as critical
  - [ ] Extract multiple correlated metrics

### Sub-Task 46c: Build Traces Connector (3-4 hours)

**Target:** Ingest distributed traces from APM (Jaeger, Datadog APM, etc.)

- [ ] Create `src/connectors/traces_connector.py`
- [ ] Implement:
  - [ ] `fetch_traces(start: datetime, end: datetime, service: str) -> List[TraceEvent]`
  - [ ] Detect slow traces (latency anomalies)
  - [ ] Extract error traces (exceptions in spans)
  - [ ] Correlate service dependencies (if A slow → B slow?)
  - [ ] Sample traces (extract representative subset)

- [ ] Tests:
  - [ ] Detect slow traces (>1000ms)
  - [ ] Extract exception details
  - [ ] Correlate services

### Sub-Task 46d: Implement Resilience Patterns (3-4 hours)

**Create:** `src/connectors/resilience.py`

- [ ] Implement `RetryPolicy` class:
  - [ ] Exponential backoff (1s → 2s → 4s → 8s with jitter)
  - [ ] Max retries: 5
  - [ ] Idempotency key handling

- [ ] Implement `CircuitBreaker` class:
  - [ ] States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing)
  - [ ] Failure threshold: 5 consecutive failures
  - [ ] Reset timeout: 60 seconds
  - [ ] Fast-fail when OPEN

- [ ] Implement `DeadLetterQueue` (DLQ):
  - [ ] Store failed events for manual replay
  - [ ] Persist to SQLite: `event_dlq` table
  - [ ] Admin endpoint to review/replay DLQ

- [ ] Add monitoring:
  - [ ] Track retry counts per connector
  - [ ] Alert if circuit breaker opens
  - [ ] Log all failures with context

- [ ] Tests:
  - [ ] Test exponential backoff timing
  - [ ] Test circuit breaker state transitions
  - [ ] Test DLQ persistence & replay
  - [ ] Simulate connector failures, verify resilience

### Sub-Task 46e: Enhance Connector Base Class (2 hours)

**Update:** `src/connectors/base_connector.py` (new)

- [ ] Create abstract base class with:
  - [ ] Built-in retry logic (uses RetryPolicy)
  - [ ] Built-in circuit breaker (ConnectorBreaker instance)
  - [ ] Built-in DLQ (sends failures to queue)
  - [ ] Standard error handling
  - [ ] Logging/metrics
  - [ ] Rate limiting (configurable QPS)

- [ ] All connectors inherit from this

### Sub-Task 46f: Update Git & CI Connectors (2 hours)

- [ ] Refactor `git_connector.py` to use base class
- [ ] Refactor `ci_connector.py` to use base class
- [ ] Add resilience patterns
- [ ] Add monitoring/alerting
- [ ] Update tests

**Acceptance Criteria:**

- [ ] 3 new connectors: logs, metrics, traces
- [ ] Each connector parses events into Event schema
- [ ] Resilience patterns: retry, circuit breaker, DLQ
- [ ] All connectors inherit from base class
- [ ] 30+ new tests, all passing
- [ ] Admin endpoints for DLQ management
- [ ] Monitoring: circuit breaker state, retry counts
- [ ] Performance: Each connector <500ms for 100 events

**Success Metrics:**

- All 30+ tests passing
- Circuit breaker opens after 5 failures
- Exponential backoff: 1s, 2s, 4s, 8s timing verified
- DLQ persists and replays successfully
- Connector failures don't crash main application
- <500ms latency per connector per 100 events

---

## ISSUE #47: PHASE 3c - Investigation Canvas UI (P1 BLOCKER)

**Title:** Phase 3c - Investigation Canvas UI (React/Vue Frontend)

**Type:** Task / Epic

**Priority:** P1 (Blocks user workflows)

**Estimated Effort:** 15-20 hours

**Description:**

## Objective

Build the Investigation Canvas UI—a visual workspace where engineers can conduct root cause analysis by combining events, timelines, and notes.

## Requirements

### Sub-Task 47a: UI Framework Setup (2 hours)

- [ ] Choose framework: React or Vue (recommend React for larger team)
- [ ] Setup project structure:
  - [ ] `frontend/` directory (separate from backend)
  - [ ] Build tooling: Vite or Webpack
  - [ ] ESLint + Prettier configuration
  - [ ] Unit testing: Jest + React Testing Library
  - [ ] E2E testing: Cypress or Playwright

### Sub-Task 47b: Core Components (5-6 hours)

**Investigation Header Component:**
- [ ] Title, status, severity badge, timestamps
- [ ] Assigned to, created by, priority selector
- [ ] Edit/save buttons

**Timeline Component:**
- [ ] Vertical timeline of events
- [ ] Each event: timestamp, source (git/CI/logs/metrics), type, details
- [ ] Color-coded by severity (red=critical, orange=high, etc.)
- [ ] Hover: show full event details
- [ ] Click: select event → show in detail pane

**Event Details Pane:**
- [ ] Source-specific details
- [ ] Raw data (JSON viewer)
- [ ] Copy event ID / external link
- [ ] "Link to investigation" button

**Notes/Annotation Panel:**
- [ ] Rich text editor for root cause, remediation, lessons learned
- [ ] Timestamp each note
- [ ] Track who wrote what
- [ ] Markdown support

**Relationships Panel:**
- [ ] Related investigations
- [ ] Related events (show multiple)
- [ ] Filter/search in relationships

### Sub-Task 47c: Canvas Layout (3-4 hours)

**Main Canvas View:**
- [ ] 4-pane layout (responsive):
  1. Investigation header (top)
  2. Timeline + Events (left, 40%)
  3. Event details (center-right, 30%)
  4. Notes/annotations (right, 30%)
  5. Footer: Tags, metadata

- [ ] Responsive design (works on tablets, mobile graceful degradation)
- [ ] Keyboard shortcuts (arrow keys = timeline navigation, Ctrl+S = save)

### Sub-Task 47d: Data Integration (3-4 hours)

- [ ] Connect to backend API:
  - [ ] `GET /api/investigations/{id}` - fetch investigation
  - [ ] `GET /api/investigations/{id}/events` - fetch linked events
  - [ ] `PUT /api/investigations/{id}` - save investigation updates
  - [ ] `POST /api/investigations/{id}/notes` - save notes

- [ ] Implement loading states, error handling
- [ ] Add optimistic UI updates
- [ ] Cache investigation data (10-min TTL)

### Sub-Task 47e: Features (3-4 hours)

- [ ] **Search/Filter:**
  - [ ] Filter events by source (git/CI/logs/metrics)
  - [ ] Filter by severity
  - [ ] Search by text in event details
  - [ ] Search in notes

- [ ] **Export:**
  - [ ] Export investigation as PDF (with timeline, notes)
  - [ ] Export as Markdown (for documentation)
  - [ ] Export as JSON (raw data)

- [ ] **Collaboration:**
  - [ ] Show "Last updated by X at Y"
  - [ ] Real-time updates (WebSocket or polling)
  - [ ] Lock investigation to prevent concurrent edits (optional for MVP)

### Sub-Task 47f: Testing (2 hours)

- [ ] Unit tests for all components
- [ ] Integration tests (API calls)
- [ ] E2E test: Load investigation → scroll timeline → edit notes → save

**Acceptance Criteria:**

- [ ] Canvas layout renders correctly
- [ ] All 6 core components functional
- [ ] API integration working
- [ ] 20+ tests, all passing
- [ ] Responsive on desktop/tablet
- [ ] Mobile graceful degradation
- [ ] Export to PDF/Markdown/JSON working
- [ ] Performance: Canvas loads in <1s

**Success Metrics:**

- All 20+ tests passing
- Canvas loads investigation in <1s
- Timeline renders 100+ events smoothly
- PDF export completes in <5s
- Mobile UI usable (not pixel-perfect)

---

## ISSUE #48: PHASE 3d - API Completion (P1 BLOCKER)

**Title:** Phase 3d - Complete Investigation & Event APIs

**Type:** Task / Epic

**Priority:** P1 (Enables all frontend features)

**Estimated Effort:** 10-12 hours

**Description:**

## Objective

Extend the API with full CRUD, search, filter, and analytics endpoints for investigations and events.

## Current API State

Current API is minimal:
- Basic CRUD for investigations
- No search/filter
- No pagination
- No analytics
- No event APIs

## Requirements

### Investigation API Endpoints

**CRUD Operations:**
- [x] `POST /api/investigations` - Create (exists)
- [x] `GET /api/investigations/{id}` - Get (exists)
- [x] `PUT /api/investigations/{id}` - Update (exists)
- [x] `DELETE /api/investigations/{id}` - Delete (exists)

**List & Search:**
- [ ] `GET /api/investigations?page=1&per_page=20` - List with pagination
- [ ] `GET /api/investigations?status=open&priority=p0` - Filter by status, priority
- [ ] `GET /api/investigations?severity=critical` - Filter by severity
- [ ] `GET /api/investigations?component=auth-service` - Filter by component
- [ ] `GET /api/investigations?assigned_to=user123` - Filter by assignee
- [ ] `GET /api/investigations/search?q=memory+leak` - Full-text search
- [ ] `GET /api/investigations/by-date-range?start=2026-01-20&end=2026-01-28` - Date range
- [ ] `GET /api/investigations/stats` - Summary stats (count by status, severity, etc.)

**Advanced:**
- [ ] `POST /api/investigations/{id}/link-event` - Link event to investigation
- [ ] `DELETE /api/investigations/{id}/unlink-event/{event_id}` - Unlink event
- [ ] `GET /api/investigations/{id}/events` - Get linked events
- [ ] `POST /api/investigations/{id}/close` - Close investigation
- [ ] `POST /api/investigations/{id}/reopen` - Reopen investigation

### Event API Endpoints

**CRUD Operations:**
- [ ] `POST /api/events` - Create event
- [ ] `GET /api/events/{id}` - Get event
- [ ] `PUT /api/events/{id}` - Update event
- [ ] `DELETE /api/events/{id}` - Delete (soft delete) event

**List & Search:**
- [ ] `GET /api/events?page=1&per_page=50` - List with pagination
- [ ] `GET /api/events?source=git&per_page=50` - Filter by source
- [ ] `GET /api/events?severity=critical&per_page=50` - Filter by severity
- [ ] `GET /api/events?investigation_id={id}` - Get events for investigation
- [ ] `GET /api/events/by-date-range?start=2026-01-20&end=2026-01-28` - Date range
- [ ] `GET /api/events/search?q=deploy` - Full-text search

### Analytics Endpoints

- [ ] `GET /api/analytics/investigation-timeline` - Timeline of investigations (e.g., 10 per day)
- [ ] `GET /api/analytics/severity-distribution` - Pie chart: critical, high, medium, low counts
- [ ] `GET /api/analytics/mttr` - Mean time to resolution by severity
- [ ] `GET /api/analytics/sources` - Events by source (git, CI, logs, etc.)
- [ ] `GET /api/analytics/components` - Investigations by component

### Admin Endpoints

- [ ] `GET /api/admin/dlq` - View Dead Letter Queue
- [ ] `POST /api/admin/dlq/{id}/retry` - Retry failed event
- [ ] `DELETE /api/admin/dlq/{id}` - Delete DLQ entry
- [ ] `GET /api/admin/circuit-breaker-status` - Status of all circuit breakers
- [ ] `POST /api/admin/circuit-breaker/{connector}/reset` - Manually reset circuit breaker

### Implementation Tasks

**Sub-Task 48a: Implement Search (3 hours)**
- [ ] Add full-text search using SQLite FTS (Full-Text Search)
- [ ] Index: title, description, root_cause, remediation, tags
- [ ] Update `investigation_store.py` with search method
- [ ] Update `event_store.py` with search method
- [ ] Performance: <100ms for search across 10,000 records

**Sub-Task 48b: Implement Filters (2 hours)**
- [ ] Add query parameter parsing
- [ ] Support multiple filters combined (AND logic)
- [ ] Validate filter values (e.g., status enum)
- [ ] Tests for each filter

**Sub-Task 48c: Implement Pagination (2 hours)**
- [ ] Add `page` and `per_page` parameters
- [ ] Add response headers: X-Total-Count, X-Page, X-Per-Page
- [ ] Default: page=1, per_page=20 (max 100)

**Sub-Task 48d: Implement Analytics (2 hours)**
- [ ] Add analytics methods to stores
- [ ] Calculate statistics efficiently (use SQL aggregates)
- [ ] Cache results (5-min TTL) for expensive queries
- [ ] Add tests

**Sub-Task 48e: API Documentation (1 hour)**
- [ ] Update `docs/api_events.md` with all new endpoints
- [ ] Include request/response examples
- [ ] Include error codes and messages
- [ ] Add OpenAPI/Swagger spec (optional for MVP)

**Acceptance Criteria:**

- [ ] 25+ API endpoints implemented
- [ ] All endpoints return proper status codes
- [ ] All endpoints include pagination where applicable
- [ ] Search performance: <100ms
- [ ] Filter performance: <50ms
- [ ] Analytics performance: <500ms
- [ ] 30+ API tests, all passing
- [ ] API documentation complete
- [ ] Error messages are helpful
- [ ] Rate limiting in place (100 req/min per token)

**Success Metrics:**

- All 30+ API tests passing
- Search <100ms for 10k records
- Analytics queries <500ms
- No N+1 query problems
- Proper HTTP status codes (200, 400, 404, 500, etc.)
- Rate limiting working

---

## ISSUE #49: PHASE 3e - Security & Observability (P1/Optional)

**Title:** Phase 3e - Security Hardening & Production Observability

**Type:** Task / Epic

**Priority:** P1/Optional (Nice-to-have for MVP)

**Estimated Effort:** 10-15 hours

**Description:**

## Objective

Harden security posture and implement production-grade observability (OpenTelemetry, Prometheus, alerts).

## Sub-Task 49a: Security Red Team (4 hours)

- [ ] SQL injection testing → Verify parameterized queries work
- [ ] XSS testing (frontend) → Verify HTML escaping
- [ ] CSRF protection → Verify token validation
- [ ] Authorization testing → Verify RBAC works
- [ ] Data exposure → Verify sensitive data not logged/returned
- [ ] Dependency scanning → Check for CVEs in packages

## Sub-Task 49b: OpenTelemetry Integration (4 hours)

- [ ] Add OpenTelemetry SDKs
- [ ] Instrument all API endpoints with traces
- [ ] Instrument database queries
- [ ] Export traces to Jaeger (locally) or vendor (Datadog, NewRelic)
- [ ] Add performance spans around slow operations
- [ ] Tests: Verify traces are exported

## Sub-Task 49c: Prometheus Metrics (3 hours)

- [ ] Add Prometheus client
- [ ] Expose metrics endpoint: `/metrics`
- [ ] Add key metrics:
  - [ ] Request count (by endpoint, status)
  - [ ] Request duration (p50, p95, p99)
  - [ ] Database query count
  - [ ] Circuit breaker state
  - [ ] Event queue depth
- [ ] Tests: Verify metrics are exposed

## Sub-Task 49d: Alerting Rules (2 hours)

- [ ] Create alert rules (Prometheus AlertManager or vendor):
  - [ ] Alert if error rate >1% in 5min window
  - [ ] Alert if p99 latency >1s
  - [ ] Alert if circuit breaker open
  - [ ] Alert if DLQ depth >1000
- [ ] Configure notification (email, Slack)

**Acceptance Criteria:**

- [ ] All security tests pass
- [ ] OpenTelemetry traces exported successfully
- [ ] Prometheus metrics exposed
- [ ] Alerting rules configured and tested
- [ ] No high-severity CVEs in dependencies

---

## CREATION SEQUENCE

**Recommended Order (Dependency Chain):**

1. **#45 (Phase 3a)** - Data Model (REQUIRED, no dependencies)
2. **#46 (Phase 3b)** - Connectors (depends on #45 Event schema)
3. **#48 (Phase 3d)** - API (depends on #45 data, #46 connectors)
4. **#47 (Phase 3c)** - UI (depends on #48 API)
5. **#49 (Phase 3e)** - Security (can be parallel, no hard dependency)

**Parallel Execution Possible:**

- #45 & #46 can start together (Event schema in #45 enables #46)
- #48 & #47 can start after #45 (API needs data model, UI needs API)
- #49 can start after #45 (security testing of expanded model)

**Recommended Parallelism:**

```
Week 1:
  Sprint 1: #45 (Phase 3a) + #46 (Phase 3b)
Week 2:
  Sprint 2: #46 (finish) + #48 (Phase 3d API)
Week 3:
  Sprint 3: #47 (Phase 3c UI) + #49 (Security/Observability)
Week 4:
  Sprint 4: Finish all + integration testing + Phase 3 closure
```

**Estimated Total Duration: 40-50 hours of focused engineering time**

---

## GITHUB ISSUE TEMPLATES

Use these to create issues:

### Issue #45 Template

```
## Summary
Phase 3a - Expand Investigation Data Model & Event Schema

## Priority
P0 - Blocks all downstream Phase 3 work

## Effort
10-12 hours

## Description
[Use full description above]

## Acceptance Criteria
- [ ] Investigation model expanded (12 new fields)
- [ ] Event model created (10+ fields)
- [ ] Event store CRUD + 4 query methods
- [ ] Event linker enhanced
- [ ] 25+ tests passing
- [ ] Database migration created
- [ ] Backward compatible
- [ ] Documentation updated

## Success Metrics
- 25+ tests: 100% passing
- Database migration: clean execution
- Query performance: <100ms for 1000+ records
- Event linking confidence: >80%

## Assignee
[TBD]

## Labels
phase-3, P0, data-model, backend
```

### Issue #46 Template

```
## Summary
Phase 3b - Advanced Event Connectors & Resilience Patterns

## Priority
P1 - Blocks API and connector features

## Effort
12-15 hours

## Depends On
#45 (Phase 3a - Event Schema)

## Description
[Use full description above]

## Acceptance Criteria
- [ ] 3 new connectors: logs, metrics, traces
- [ ] Resilience patterns: retry, circuit breaker, DLQ
- [ ] Base connector class with built-in resilience
- [ ] 30+ tests passing
- [ ] Admin endpoints for DLQ
- [ ] Performance: <500ms per connector per 100 events

## Assignee
[TBD]

## Labels
phase-3, P1, connectors, backend, resilience
```

[Similar templates for #47, #48, #49...]


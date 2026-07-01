# OCI CLI — Developer Reference

This file is the authoritative entry point for anyone (human or AI) picking up
this codebase. Read it before touching anything.

---

## What this project is

Oracle Cloud Infrastructure CLI (`oci-cli`). A Python 3.6+ command-line tool
that wraps the OCI REST API. Users run `oci <service> <resource> <verb>`
commands (e.g. `oci db database list`).

The project has two distinct layers:

| Layer | Location | Who writes it |
|---|---|---|
| Auto-generated CLI commands | `services/<service>/src/.../generated/` | OracleSDKGenerator — **never edit** |
| Hand-written extensions | `services/<service>/src/.../<service>_cli_extended.py` | Us |
| Async Repository packages | `packages/` | Us — new pattern, see below |

---

## Repo layout

```
oci-cli/
├── src/
│   └── oci_cli/          # Core CLI framework (cli_util, cli_root, custom_types …)
├── services/             # 168 OCI service modules (one per service)
│   ├── database/
│   ├── core/             # Compute + VCN (called "core" in OCI)
│   ├── identity/
│   ├── object_storage/
│   └── …
├── packages/             # NEW — standalone async data-access packages
│   └── database/         # First package; see Architecture below
├── tests/                # Integration test suite (VCR-based)
├── setup.py              # Single package install for the whole CLI
├── requirements.txt      # Pinned deps for CI
└── tox.ini               # Test matrix
```

---

## Architecture: the `packages/` pattern

### Why it exists

The generated CLI calls OCI SDK clients synchronously, inline inside Click
command handlers. That makes the code hard to test, impossible to compose, and
blocks the event loop for long-running operations.

The `packages/` layer introduces a clean **async Repository** abstraction that:
- Owns all OCI SDK calls (one executor thread pool per repo instance)
- Translates OCI `ServiceError` into typed domain exceptions
- Handles pagination automatically
- Is fully testable with stdlib `unittest.mock` — no network required

### Package structure (packages/database as the template)

```
packages/database/
├── __init__.py           # Public API: re-exports Repository, AsyncDatabaseRepository,
│                         #   DatabaseDetails, DatabaseSummary, and all exceptions
├── repository.py         # Abstract base: Repository[T, S] with 5 async methods
├── async_repository.py   # AsyncDatabaseRepository — concrete OCI implementation
├── models.py             # DatabaseSummary (list), DatabaseDetails (get/create/update)
├── exceptions.py         # RepositoryError hierarchy
└── tests/
    └── test_async_repository.py   # 16 unit tests — run without network
```

### Repository interface (repository.py)

```python
class Repository(ABC, Generic[T, S]):
    async def get(self, resource_id: str) -> T: ...
    async def list(self, compartment_id: str, **filters) -> list[S]: ...
    async def create(self, compartment_id: str, details: dict) -> T: ...
    async def update(self, resource_id: str, details: dict) -> T: ...
    async def delete(self, resource_id: str) -> None: ...
```

All new resource repositories must implement this interface.

### Exception hierarchy (exceptions.py)

```
RepositoryError
├── ResourceNotFoundError   ← OCI 404
├── ResourceConflictError   ← OCI 409
└── RepositoryOperationError ← everything else
```

### Usage pattern

```python
import asyncio, oci
from packages.database import AsyncDatabaseRepository

config = oci.config.from_file()

async def main():
    async with AsyncDatabaseRepository(config) as repo:
        # list with automatic pagination
        dbs = await repo.list("ocid1.compartment.oc1..")
        # get full details
        db  = await repo.get("ocid1.database.oc1..")
        # delete (OCI is async — resource moves to TERMINATING)
        await repo.delete("ocid1.database.oc1..")

asyncio.run(main())
```

### How async works under the hood

OCI Python SDK has **no native async support**. Every `AsyncXxxRepository`
wraps each SDK call with:

```python
loop.run_in_executor(executor, functools.partial(sdk_fn, *args, **kwargs))
```

This offloads the blocking HTTP call to a `ThreadPoolExecutor` (default 4
workers, configurable via `workers=` kwarg) so the caller can `await` it.

---

## How to run tests

### Unit tests (no network, no OCI account)

```bash
# From repo root
python -m unittest packages.database.tests.test_async_repository -v
```

### Full integration tests (need OCI credentials + tenancy)

```bash
pip install -r requirements.txt
# Set env vars: OCI_CLI_PROFILE, COMPARTMENT_ID, etc.
python -m pytest services/database/tests/integ/ -v
```

### Lint / type check (future — not wired yet)

```bash
python -m mypy packages/ --strict
python -m flake8 packages/
```

---

## Key decisions (ADRs)

### ADR-1: ThreadPoolExecutor over aiohttp

We wrap synchronous OCI SDK calls rather than rewriting HTTP calls with
aiohttp. Reason: OCI SDK handles signing, retry logic, circuit-breaking, and
region resolution. Replicating all that in aiohttp would be a maintenance
burden. The executor approach is a thin compatibility shim, not an architectural
commitment.

### ADR-2: Generic Repository[T, S] with two type params

`T` = full detail model (from get/create/update), `S` = summary model (from
list). OCI list operations return pruned summaries, not full objects. Using two
type params makes the distinction explicit and prevents callers from assuming
list items have all fields.

### ADR-3: Context manager is optional

`open()` / `close()` are public. `async with` calls them implicitly. This lets
long-lived server processes keep a repo open for the lifetime of the process
without a context manager.

### ADR-4: Pagination is hidden

`list()` follows `next_page` tokens automatically and returns a flat list.
Callers that need streaming pagination (very large result sets) can pass
`limit=N` in filters to get a single page.

---

## Roadmap

See `packages/ROADMAP.md` for the full 8-week plan leading to the
infrastructure phase.

---

## Adding a new resource repository

1. Create `packages/<service>/` mirroring `packages/database/` layout.
2. Add `exceptions.py` and `models.py` (reuse existing ones if the service
   shares error semantics).
3. Subclass `Repository[DetailType, SummaryType]` in `async_repository.py`.
4. Implement all 5 abstract methods; call `self._call(client.sdk_method, ...)`.
5. Write unit tests using `unittest.mock` — patch `_call` with `_passthrough_call`
   or `_raising_call` helpers (see `packages/database/tests/` for the pattern).
6. Export public names from `__init__.py`.
7. Add the package to `packages/ROADMAP.md` marking it done.

---

## OCI SDK notes

- Installed version: `oci==2.180.0` (pinned in setup.py)
- Useful modules: `oci.pagination`, `oci.wait_until`, `oci.waiter`,
  `oci.work_requests`, `oci.exceptions.ServiceError`
- `oci.wait_until(client, response, 'lifecycle_state', 'AVAILABLE')` polls
  until the resource reaches a target state — use this inside waiter helpers.
- Every OCI list response has `.next_page` (str or None) and `.data` (list).

---

## Branch naming convention

`claude/<short-description>-<ticket-id>`

Current active branch: `claude/async-repository-database-8ir5va`

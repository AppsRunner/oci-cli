# packages/ — 8-Week Roadmap (Infrastructure Phase)

**Start date:** 2026-07-01  
**Infrastructure phase target:** 2026-08-26  
**Branch convention:** `claude/<description>-<id>`  

Status legend: ✅ Done · 🔄 In progress · ⬜ Not started

---

## Overview

```
Week 1-2  │ Database package (AsyncDatabase, AutonomousDB, DbSystem, Backup)
Week 3    │ Waiter utilities (cross-package polling)
Week 4    │ Compute package (Instance, Image, VnicAttachment)
Week 5    │ Networking package (VCN, Subnet, SecurityList)
Week 6    │ Identity package (Compartment, User, Group)
Week 7    │ CLI integration (wire repos into Click commands)
Week 8    │ Infrastructure phase prep (packaging, CI, docs)
```

---

## Week 1 (2026-07-01 → 2026-07-07): Database Package Foundation ✅

**Branch:** `claude/async-repository-database-8ir5va`

| Deliverable | File | Status |
|---|---|---|
| Abstract `Repository[T, S]` base class | `packages/database/repository.py` | ✅ |
| `AsyncDatabaseRepository` (Database objects) | `packages/database/async_repository.py` | ✅ |
| `DatabaseSummary` / `DatabaseDetails` models | `packages/database/models.py` | ✅ |
| Exception hierarchy | `packages/database/exceptions.py` | ✅ |
| 16 unit tests | `packages/database/tests/test_async_repository.py` | ✅ |

---

## Week 2 (2026-07-07 → 2026-07-14): Expand Database Package ⬜

**Branch:** `claude/database-autonomous-dbsystem-<id>`

Extend `packages/database/` with three more repository classes. All follow the
same pattern as `AsyncDatabaseRepository`.

| Deliverable | OCI Client method prefix | Key filters for `list()` |
|---|---|---|
| `AsyncAutonomousDatabaseRepository` | `*_autonomous_database` | `lifecycle_state`, `display_name` |
| `AsyncDbSystemRepository` | `*_db_system` | `lifecycle_state`, `availability_domain` |
| `AsyncBackupRepository` | `*_backup` | `database_id`, `db_system_id` |

**Also add:**
- `packages/database/waiter.py` — `wait_for_state(repo, resource_id, target, timeout_s=1200)` using `oci.wait_until`
- Tests for each new repository class

**Definition of done:** all new classes pass unit tests, `__init__.py` exports updated.

---

## Week 3 (2026-07-14 → 2026-07-21): Cross-Package Utilities ⬜

**Branch:** `claude/packages-core-utilities-<id>`

Create `packages/core/` — shared utilities consumed by all packages.

```
packages/core/
├── __init__.py
├── base_repository.py     # Move shared _call / _translate logic here
├── waiter.py              # Generic wait_for_state using oci.wait_until
├── pagination.py          # _paginate(client_fn, **kwargs) generator
├── factory.py             # RepositoryFactory.from_config(config) -> repos
└── tests/
    └── test_waiter.py
    └── test_factory.py
```

**Key design: `BaseAsyncRepository`**

Move `_call`, `_translate_service_error`, `open()`, `close()`, and the
context-manager logic from `AsyncDatabaseRepository` into
`packages/core/base_repository.py`. All future repository classes inherit from
it. Refactor `packages/database/async_repository.py` to use it.

**`RepositoryFactory`** constructs all known repos from a single OCI config
dict. Consumers create one factory, then call `.database()`, `.compute()`, etc.

```python
async with RepositoryFactory.from_config(oci.config.from_file()) as f:
    db  = await f.database().get("ocid1.database…")
    inst = await f.compute().get("ocid1.instance…")
```

**Definition of done:** `packages/database` refactored to use `core`, all 16
existing tests still pass, factory can instantiate a DatabaseRepository.

---

## Week 4 (2026-07-21 → 2026-07-28): Compute Package ⬜

**Branch:** `claude/packages-compute-<id>`

OCI compute lives in `oci.core.ComputeClient`.

```
packages/compute/
├── __init__.py
├── repository.py           # Abstract ComputeRepository
├── async_repository.py     # AsyncInstanceRepository, AsyncImageRepository
├── models.py               # InstanceSummary, InstanceDetails, ImageSummary
├── exceptions.py           # Reuse or extend core exceptions
└── tests/
    └── test_async_repository.py
```

| Class | OCI client | get | list | create | update | delete |
|---|---|---|---|---|---|---|
| `AsyncInstanceRepository` | `ComputeClient` | `get_instance` | `list_instances` | `launch_instance` | `update_instance` | `terminate_instance` |
| `AsyncImageRepository` | `ComputeClient` | `get_image` | `list_images` | `create_image` | `update_image` | `delete_image` |

**Models needed:**
- `InstanceSummary` — id, compartment_id, display_name, lifecycle_state, shape, availability_domain
- `InstanceDetails` — above + image_id, metadata, shape_config, source_details, time_created
- `ImageSummary` — id, compartment_id, display_name, lifecycle_state, operating_system

**Definition of done:** both repository classes, full unit test coverage.

---

## Week 5 (2026-07-28 → 2026-08-04): Networking Package ⬜

**Branch:** `claude/packages-networking-<id>`

OCI networking (VCN, subnets, security lists) lives in `oci.core.VirtualNetworkClient`.

```
packages/networking/
├── __init__.py
├── async_repository.py     # AsyncVcnRepository, AsyncSubnetRepository,
│                           # AsyncSecurityListRepository
├── models.py               # VcnSummary, SubnetSummary, SecurityListSummary + Detail types
└── tests/
```

| Class | Key list filters |
|---|---|
| `AsyncVcnRepository` | `display_name`, `lifecycle_state` |
| `AsyncSubnetRepository` | `vcn_id`, `availability_domain`, `lifecycle_state` |
| `AsyncSecurityListRepository` | `vcn_id`, `lifecycle_state` |

**Note:** SecurityList update is a full-replace (PUT), not a partial patch.
The `update()` method must accept `ingress_security_rules` and
`egress_security_rules` lists in `details`.

**Definition of done:** all three classes with unit tests.

---

## Week 6 (2026-08-04 → 2026-08-11): Identity Package ⬜

**Branch:** `claude/packages-identity-<id>`

OCI identity lives in `oci.identity.IdentityClient`.

```
packages/identity/
├── __init__.py
├── async_repository.py     # AsyncCompartmentRepository, AsyncUserRepository,
│                           # AsyncGroupRepository
├── models.py
└── tests/
```

| Class | Notes |
|---|---|
| `AsyncCompartmentRepository` | `list()` takes optional `parent_compartment_id` for tree traversal |
| `AsyncUserRepository` | `create()` requires `name` + `description`; no `delete` (deactivate instead) |
| `AsyncGroupRepository` | includes `add_user(group_id, user_id)` / `remove_user(group_id, user_id)` extra methods |

**Definition of done:** all three classes with unit tests.

---

## Week 7 (2026-08-11 → 2026-08-18): CLI Integration ⬜

**Branch:** `claude/cli-integration-async-repos-<id>`

Wire the async repos into existing CLI commands. Start with database, which has
the most complex extended commands.

**Pattern for Click + asyncio:**

```python
import asyncio
from packages.database import AsyncDatabaseRepository

@database_cli.database_group.command(name='list-async')
@click.pass_context
def list_databases_async(ctx, **kwargs):
    config = ctx.obj['config']
    async def _run():
        async with AsyncDatabaseRepository(config) as repo:
            return await repo.list(kwargs['compartment_id'])
    results = asyncio.run(_run())
    cli_util.render_response(results, ctx)
```

**What to wire first:**
1. `oci db database list` → `AsyncDatabaseRepository.list()`
2. `oci db database get` → `AsyncDatabaseRepository.get()`
3. `oci db autonomous-database list` → `AsyncAutonomousDatabaseRepository.list()`

**What NOT to touch yet:** create/update/delete — these need work-request
polling (waiter) which comes from `packages/core/waiter.py`.

**Definition of done:** 3 list/get commands use repo layer, existing unit tests
for `database_cli_extended.py` still pass.

---

## Week 8 (2026-08-18 → 2026-08-26): Infrastructure Phase Prep ⬜

**Branch:** `claude/infra-phase-prep-<id>`

The final week makes everything deployable and handover-ready.

### 8a. Make packages independently installable

Add `packages/database/setup.py`:

```python
setup(
    name='oci-cli-database-repository',
    version='0.1.0',
    packages=['packages.database'],
    install_requires=['oci>=2.180.0'],
    python_requires='>=3.8',
)
```

Same for `packages/compute`, `packages/networking`, `packages/identity`.

### 8b. CI wiring

Update `tox.ini` with a new environment:

```ini
[testenv:packages]
deps = oci
commands = python -m unittest discover -s packages -p "test_*.py" -v
```

### 8c. Type annotations

Run `mypy packages/ --strict` and fix all errors. Add `py.typed` markers.

### 8d. Final documentation pass

- Update `CLAUDE.md` with any decisions made during Weeks 2-7
- Each package gets its own one-page `README.rst`
- `packages/ROADMAP.md` (this file) updated with final status

### 8e. Handover checklist

- [ ] All unit tests pass: `python -m unittest discover -s packages`
- [ ] `mypy packages/ --strict` exits 0
- [ ] `CLAUDE.md` reflects actual architecture
- [ ] Branch for each week merged to master
- [ ] No direct `oci.database.DatabaseClient` calls remain in wired CLI commands

---

## Risk log

| Risk | Likelihood | Mitigation |
|---|---|---|
| OCI SDK version bump breaks models | Medium | Pin `oci==2.180.0` in each package setup.py |
| ThreadPoolExecutor deadlock under high concurrency | Low | Each repo instance owns its own executor; don't share |
| Click + asyncio version incompatibility | Low | Use `asyncio.run()` (Python 3.7+), not deprecated `get_event_loop()` |
| Waiter timeout on slow OCI environments | Medium | Make `timeout_s` a parameter with a generous default (1200s) |

---

## Dependency map

```
packages/core          ← no internal deps
packages/database      ← packages/core
packages/compute       ← packages/core
packages/networking    ← packages/core
packages/identity      ← packages/core
CLI integration        ← packages/database, packages/compute, packages/networking
```

Each package depends only on `packages/core` and `oci` SDK — never on each other.

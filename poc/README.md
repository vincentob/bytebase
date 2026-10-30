# Permission fixtures

This directory migrates the role definitions and permission checks from
`rg/bytebase/poc`. It uses the same locally built application image as the root
Compose file, with a separate container, volume, and loopback port. It does not
mount `~/.bytebase/data` or read credentials from the former infrastructure repo.

## Add custom roles to the running application

```sh
make up
make roles-sync
```

`roles-sync` runs inside the application container. It prompts for an existing
admin email and password, or uses `BYTEBASE_ADMIN_TOKEN` from the caller's
environment. The token is never written to a file. The command upserts only the
four role definitions in [roles.yaml](roles.yaml); it preserves users, projects,
and their IAM bindings. Rerun it after changing those definitions.

| Identity | Workspace binding | Project binding | Access |
| --- | --- | --- | --- |
| Admin | `roles/workspaceAdmin` | Existing owner bindings as needed | Manage roles and IAM |
| Dev | `roles/pocbase` | `roles/pocdeveloper`, Sandbox only | Read, direct DDL/DML, submit issues |
| Leader | `roles/pocbase` | `roles/pocsubmitter` | Submit issues; no standing SQL or rollout creation |
| Temporary reader | Existing base binding | Time-scoped `roles/pocquery` | SELECT, info and explain until expiry |

Assign these bindings through the admin UI or the deployment configuration. Remove
broader overlapping grants from a restricted account when adopting this policy:
IAM grants are additive. In particular, the built-in `workspaceMember` grants
administrative reads that `pocbase` deliberately omits. Synchronizing role
definitions does not change an account's existing memberships.

## Run the isolated checks

Host prerequisites are Python 3 with venv support, Node.js, PNPM, Docker Compose,
and Make. The application itself still needs only its one Docker image.

```sh
make poc:browser-deps
make poc:up
make poc:seed
make poc:test
make poc:stop
```

The fixture UI is at `http://127.0.0.1:17880`. Random passwords for
`owner@permission-poc.invalid`, `dev@permission-poc.invalid`, and
`leader@permission-poc.invalid` are stored in `.state/accounts.yaml` with mode
`600`. This file and all generated artifacts are ignored by Git and Docker builds.

| Command | Behavior |
| --- | --- |
| `make poc:up` | Rebuild the root image and start the isolated application. |
| `make poc:seed` | Check the test container's ownership label, create its two fixture databases, then provision users, roles and project IAM. |
| `make poc:api-test` | Seed, then check management API denial, Sandbox DDL/DML, Prod isolation, issue submission, rollout denial, and read-grant expiry. |
| `make poc:browser-test` | Run the three browser checks against existing fixtures. |
| `make poc:test` | Seed and run both API/SQL and browser checks. |
| `make poc:unit` | Test the role matrix, role-only synchronization, private credential storage, and SQL permission-denied responses. |
| `make poc:go-test` | Cross-compile the existing PoC Go tests and run them in a Linux container with networking disabled. |
| `make poc:check` | Run the upstream frontend formatter and full gate. |
| `make poc:status` | Show the isolated container status. |
| `make poc:stop` | Stop the isolated stack; retain its fixture volume. |

The isolated seed owns its fixture workspace and replaces its IAM to reproduce
the test matrix. Run it only through the fixture Make commands. The daily
application's `roles-sync` command does not call that seed.

The fixture PostgreSQL process is Bytebase's embedded server, reached over its
Unix socket on port `8082`. `init.sql` creates the `poc` login and the
`sandbox_poc`/`prod_poc` databases inside the isolated volume. It never initializes
tables in Bytebase's `bb` metadata database. API checks treat an HTTP 200 response
containing SQL `permissionDenied` as a denial, and verify that no data was returned.
The five-second temporary grant is revoked in `finally` after checking expiration
with the same login token.

## Migration map

| Former component | Current location |
| --- | --- |
| Source patch | Already integrated in commit `b7cb46c04`; no second patch application is needed. |
| Role definitions inside `scripts/poc/api.py` | `poc/roles.yaml`, shared by seeding and role synchronization. |
| Fixture API and SQL checks | `scripts/poc/api.py` |
| Browser tests and configuration | `poc/tests/permissions.spec.mjs`, `poc/playwright.config.mjs` |
| Fixture schema | `poc/fixtures/init.sql` |
| Lifecycle helpers | `poc/Makefile`, `scripts/poc/manage.py`, `scripts/poc/settings.py` |
| Workspace/project policy, aliases and expiring grants | `deploy/terraform/`, including the five provider-mocked tests. |
| Clone/apply-patch and separate Vite startup | Replaced by building this checkout's embedded-frontend image. |

Former passwords, tokens, Terraform state, plans, browser artifacts, and database
volumes are not copied. Existing deployments need their own credentials and an
explicit policy plan; see [deployment instructions](../deploy/terraform/README.md).

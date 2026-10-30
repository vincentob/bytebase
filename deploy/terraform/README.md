# Bytebase deployment policy

This module migrates the environment, user, project, instance, GitOps identity,
SQL review, and IAM configuration from `rg/bytebase`. The checked-in
[config.yaml](config.yaml) is a sanitized example using reserved `.invalid` URLs
and example email addresses. No existing infrastructure state or credentials are
included. Terraform never runs as part of `make up`.

## Usage

Create the four custom roles first with `make roles-sync` from the repository
root. Configure this module's YAML with the intended Bytebase URL, owners,
members, instance connections, environments and SQL review rules. Supply the
provider credentials through `TF_VAR_bytebase_service_account` and
`TF_VAR_bytebase_service_key`. `TF_VAR_db_passwords` and `TF_VAR_user_passwords`
are maps keyed by the YAML instance/user IDs. They are marked sensitive. Optional
Cloudflare Access credentials use `TF_VAR_cf_access_client_id` and
`TF_VAR_cf_access_client_secret`; no Access headers are sent when the ID is empty.

From the repository root:

```sh
make terraform:init
make terraform:validate
make terraform:test
make terraform:plan QUIET=1
# The owner reviews the plan and runs this in a terminal:
make terraform:apply
```

`plan` saves `deploy/terraform/plan.tfplan`. `QUIET=1` prints only a summary of
resource addresses, actions and changed field names; `ARGS=` passes extra plan
arguments. `apply` requires a saved plan and terminal confirmation, applies
exactly that plan, then removes it. Agents must not run apply. Saved plans may
contain secrets and are ignored by Git and Docker. Import existing resources
into a separately managed state before using this module for an existing
installation; an empty state does not adopt existing resources automatically.

## Policy behavior

- Dev is bound to `pocbase` at workspace scope and `pocdeveloper` only in the
  Sandbox project. Leader is bound to `pocbase` and `pocsubmitter`, without standing
  SQL or rollout permissions. Admin uses `workspaceAdmin`.
- `allowed_environments` prevents placing a production connection in a
  Sandbox-only project. `instance_aliases` creates a separate Bytebase
  registration using the source connection settings and password, preserving
  existing CI instance targets. It does not create or copy a physical database.
- Workspace/project IAM is authoritative: the YAML owners, members, approved
  grants and CI identities form the entire policy. Review membership removals in
  the plan before the owner applies it.
- GitOps check/deploy/baseline identities preserve the former stage and OIDC
  subject constraints. The `dbops_config` output is the interface to the separately
  maintained dbops repositories.

## Expiring read access

Add an owner-approved record under a project's `query_grants`:

```yaml
query_grants:
  incident-123:
    member: user:leader@example.com
    approved_by: user:owner@example.com
    reason: "INC-123 inspect order state"
    approved_at: "2026-10-30T10:00:00Z"
    expires_at: "2026-10-30T11:00:00Z"
    database: projects/example/instances/example-prod/databases/app
    schema: public
    tables: [orders]
```

Replace the timestamps with the actual approval window. The member must already
hold a project submitter binding (`pocsubmitter`, or the legacy
`projectDeveloper`). The approver must be one of that project's owners. A reason
and UTC timestamps are required, approval cannot be in the future, and expiry
must be later than approval and at most eight hours away. The approver field is
an audit record of manual review, not an independent approval mechanism.

Each record produces a separate `pocquery` binding with an absolute expiry.
Replanning does not extend it. A database scope must refer to a managed instance
in the same project; schema/table scopes require a database. Quotes, backslashes,
newlines, and empty scope names are rejected. Expiry and data access are enforced
by Bytebase on each request. Broader existing grants remain additive.

The five tests in [tests/access.tftest.hcl](tests/access.tftest.hcl) use a mocked
provider and do not contact Bytebase: Dev isolation, Leader approval requirements,
CI connection preservation, expiring scoped grants, and invalid grant rejection.

<p align="center">
  <a href="https://docs.bytebase.com/get-started/self-host-vs-cloud" target="_blank">⚙️ Install</a> •
  <a href="https://docs.bytebase.com">📚 Docs</a> •
  <a href="https://www.bytebase.com/contact-us/">🙋‍♀️ Book Demo</a>
</p>

![banner](https://raw.githubusercontent.com/bytebase/bytebase/main/docs/assets/banner.jpg)

## What is Bytebase?

Bytebase is the open-source database governance platform. It acts as a single control plane between your users — humans and AI agents — and your databases, governing change management, access control, and compliance so every change and query is reviewed, controlled, and recorded.

![middleware](https://raw.githubusercontent.com/bytebase/bytebase/main/docs/assets/middleware.svg)

It replaces the disparate tools stitched across migration scripts, SQL clients, and ticketing systems, unifying database operations in a single platform.

<p align="center">
  <img alt="venn" src="https://raw.githubusercontent.com/bytebase/bytebase/main/docs/assets/venn.svg" width="480" />
</p>

## Supported Databases and Integrations

Bytebase supports PostgreSQL, MySQL, SQL Server, Oracle, MongoDB, Redis, MariaDB, TiDB, Snowflake, ClickHouse, Spanner, OceanBase, and [more](https://docs.bytebase.com/introduction/supported-databases) — plus [integrations](https://www.bytebase.com/integrations/) spanning IaC, AI, identity providers, collaboration, ITSM, log streaming, and secret managers.

![integrations](https://raw.githubusercontent.com/bytebase/bytebase/main/docs/assets/integrations.webp)

## Key Features

### Change Management

- **GUI-Based Workflow**: Request, review, deploy, and rollback changes through a web console
- **GitOps Integration**: Native GitHub/GitLab integration for database-as-code workflows
- **SQL Review**: 200+ lint rules to enforce SQL standards and best practices

### Access Control

- **Fine-Grained RBAC**: Project and workspace-level roles and permissions
- **Just-in-Time Access**: Time-boxed database access grants with automatic revocation
- **Dynamic Data Masking**: Column-level masking applied based on user role at query time

### Compliance

- **Audit Logging**: Complete audit trail of all database activities
- **Codified Policy**: Manage policies as code via Terraform Provider and API
- **Data Classification**: Identify and tag sensitive data across your databases

### AI

- **MCP Server**: Connect AI agents and IDEs to Bytebase through the Model Context Protocol
- **Text-to-SQL**: Generate and refine queries in the SQL Editor with AI assistance
- **Page Agent**: Built-in AI assistant that guides or executes workflows from plain language requests

## Quick Start

### Docker

```bash
docker run --init \
  --name bytebase \
  --publish 8080:8080 \
  --volume ~/.bytebase/data:/var/opt/bytebase \
  bytebase/bytebase:latest
```

### Kubernetes

```bash
helm install bytebase bytebase/bytebase
```

Visit [http://localhost:8080](http://localhost:8080) and follow the setup wizard.

## Documentation

- [Installation Guide](https://docs.bytebase.com/get-started/self-host-vs-cloud)
- [Tutorials](https://docs.bytebase.com/tutorials)
- [Terraform Provider](https://registry.terraform.io/providers/bytebase/bytebase)
- [API Reference](https://api.bytebase.com)

## Use Cases

### For Development Teams

- Implement database schema version control
- Automate database deployments through CI/CD pipelines
- Collaborate on database changes with review workflows

### For DBAs

- Centralize database management across all environments
- Enforce organization-wide SQL standards and policies
- Monitor and audit all database activities

### For Security Teams

- Control data access with column-level permissions
- Implement data masking for sensitive information
- Maintain compliance with audit trails

## Community & Support

- [Twitter](https://twitter.com/Bytebase)
- [Issue Tracker](https://github.com/bytebase/bytebase/issues)
- [FAQ](https://docs.bytebase.com/faq)

## Contributing

We welcome contributions!

### Permission PoC with Docker Compose

The repository's `docker-compose.yml` builds a single Bytebase image from the
current checkout. Like the official Docker image, it embeds the frontend and
PostgreSQL and mounts `~/.bytebase/data` at `/var/opt/bytebase`. The default HTTP
port is `8088`. Docker Engine with the Compose plugin and Make are required;
Node.js, Go, and PNPM run inside the build stages.

```bash
# First start on a server: use the URL users will actually visit.
BYTEBASE_EXTERNAL_URL=http://your-server:8088 make up

# After editing code, rebuild and restart with the same external URL.
BYTEBASE_EXTERNAL_URL=http://your-server:8088 make up

make status
make logs
make down
```

`make up` builds the local image, recreates the `bytebase` container with an init
process, removes obsolete containers from this Compose project, and waits for its
health check. Docker reuses unchanged build layers.
`make build` builds without starting the container; `make validate` checks the
Compose configuration. Stop any existing `bytebase` container before switching to
this Compose setup.

The bind mount uses the home directory of the user running Compose. Metadata,
users, roles, and settings live in `~/.bytebase/data/pgdata` and survive rebuilds
and `make down`. An empty directory starts a new workspace. Data from the previous
Compose setup's separate PostgreSQL volume is not automatically migrated into
this directory.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BYTEBASE_EXTERNAL_URL` | `http://localhost:8088` | Public URL, including the port when needed. |
| `BYTEBASE_BIND_ADDRESS` | `0.0.0.0` | Host address for HTTP; use `127.0.0.1` for a local reverse proxy. |
| `BYTEBASE_PORT` | `8088` | Published HTTP port; also update the external URL when changing it. |
| `GIT_COMMIT` | Current commit via Make, otherwise `local` | Revision recorded in the built image. |

After `make build`, the same image can also run directly:

```bash
docker run --rm --init \
  --name bytebase \
  --publish 8088:8080 \
  --volume ~/.bytebase/data:/var/opt/bytebase \
  bytebase-permission-poc:local \
  --external-url http://your-server:8088
```

The frontend build enables `BB_PERMISSION_POC=1`; the backend uses the
`embed_frontend,docker,permission_poc` build tags. The image sets
`BB_PERMISSION_POC_CONTAINER=1` to listen on the container's network interface.
The profile guard permits Docker's embedded metadata database while retaining the
self-hosted development requirement and the isolated loopback database check for
external metadata. The standard Docker build retains its production tags and
disables the permission PoC by default.

Custom role definitions and IAM bindings are managed through the standard
Bytebase UI and APIs. Deployment-specific configuration and initialization are
maintained by the infrastructure repository.

```bash
# Setup a postgres database with user bbdev and database bbdev
export PG_URL=postgresql://bbdev@localhost/bbdev

# Start backend
alias r='go build -ldflags "-w -s" -p=16 -o ./bytebase-build/bytebase ./backend/bin/server/main.go && ./bytebase-build/bytebase --port 8080 --data . --debug'

# Start frontend
alias y="pnpm --dir frontend i && pnpm --dir frontend dev"
```

## Comparisons

- [Bytebase vs Liquibase](https://www.bytebase.com/blog/bytebase-vs-liquibase/)
- [Bytebase vs Flyway](https://www.bytebase.com/blog/bytebase-vs-flyway/)
- [Bytebase vs Jira](https://www.bytebase.com/blog/use-jira-for-database-change/)
- [Bytebase vs DBeaver](https://www.bytebase.com/blog/bytebase-vs-dbeaver/)
- [Bytebase vs DataGrip](https://www.bytebase.com/blog/bytebase-vs-datagrip/)
- [Bytebase vs Navicat](https://www.bytebase.com/blog/bytebase-vs-navicat/)
- [Bytebase vs CloudBeaver](https://www.bytebase.com/blog/bytebase-vs-cloudbeaver/)

<a href="https://www.star-history.com/?repos=bytebase%2Fbytebase%2Cliquibase%2Fliquibase%2Cflyway%2Fflyway%2Cdbeaver%2Fcloudbeaver&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=bytebase/bytebase%2Cliquibase/liquibase%2Cflyway/flyway%2Cdbeaver/cloudbeaver&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=bytebase/bytebase%2Cliquibase/liquibase%2Cflyway/flyway%2Cdbeaver/cloudbeaver&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=bytebase/bytebase%2Cliquibase/liquibase%2Cflyway/flyway%2Cdbeaver/cloudbeaver&type=date&legend=top-left" />
 </picture>
</a>

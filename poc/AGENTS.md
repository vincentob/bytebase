# Permission fixture ownership

- Read `README.md` before running the fixture suite.
- Tests and seeding must use `poc/compose.yaml`, its labeled container, its dedicated
  metadata volume and its loopback API port. Never point fixture code or SQL at an
  existing deployment or mount `~/.bytebase/data` into the fixture stack.
- The daily deployment's `roles-sync` operation may update the configured role
  definitions only; it must preserve users and all workspace/project IAM bindings.
- Never print or commit `.state/accounts.yaml`, `.state/database.yaml`, tokens,
  database dumps, or browser traces containing session information.
- Keep the root single-container deployment independent of the fixture lifecycle.

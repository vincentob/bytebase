"""Contracts for role synchronization and fixture authorization boundaries."""

from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import api
from settings import ROOT, role_definitions


class PermissionFixtureTest(unittest.TestCase):
    def test_developer_and_leader_keep_distinct_permissions(self):
        roles = role_definitions()
        self.assertEqual(set(roles), {"pocbase", "pocsubmitter", "pocquery", "pocdeveloper"})
        self.assertEqual(set(roles["pocbase"]["permissions"]), {
            "bb.settings.getWorkspaceProfile", "bb.settings.getEnvironment",
        })
        submit = set(roles["pocsubmitter"]["permissions"])
        query = set(roles["pocquery"]["permissions"])
        self.assertIn("bb.issues.create", submit)
        self.assertFalse(submit & {"bb.sql.select", "bb.sql.ddl", "bb.sql.dml", "bb.rollouts.create"})
        self.assertEqual(set(roles["pocdeveloper"]["permissions"]), submit | query | {"bb.sql.ddl", "bb.sql.dml"})

    def test_all_permissions_exist_in_this_version(self):
        known = set(re.findall(r'Permission\s*=\s*"([^"]+)"', (ROOT / "backend/common/permission/permission.go").read_text()))
        for role in role_definitions().values():
            self.assertFalse(set(role["permissions"]) - known)

    def test_role_sync_never_modifies_membership(self):
        class Owner:
            def __init__(self):
                self.requests = []

            def request(self, *args):
                self.requests.append(args)

        owner = Owner()
        api.sync_roles(owner)
        self.assertEqual(len(owner.requests), 4)
        for method, path, role in owner.requests:
            self.assertEqual(method, "PATCH")
            self.assertTrue(path.startswith("/v1/roles/"))
            self.assertIn("allowMissing=true", path)
            self.assertNotIn("members", role)

    def test_developer_has_no_production_binding(self):
        with patch.object(api, "credentials", return_value={r: {"email": r + "@example.com"} for r in ["owner", "dev", "leader"]}):
            production = api.bindings_for("poc-prod")
            sandbox = api.bindings_for("poc-sandbox")
        self.assertFalse(any("user:dev@example.com" in b["members"] for b in production))
        self.assertTrue(any(b["role"] == "roles/pocdeveloper" and "user:dev@example.com" in b["members"] for b in sandbox))

    def test_credentials_are_private_and_stable(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(api, "STATE", Path(directory)), patch.object(api, "state_directory"):
            first = api.credentials()
            self.assertEqual(first, api.credentials())
            self.assertEqual((Path(directory) / "accounts.yaml").stat().st_mode & 0o777, 0o600)

    def test_query_permission_denied_inside_http_200(self):
        class Denied:
            last_status = 200

            def request(self, *args):
                return {"results": [{"permissionDenied": True}]}

        api.query(Denied(), "poc-prod", "prod_poc", "SELECT 1", (403,))

    def test_query_does_not_treat_success_as_denial(self):
        class Allowed:
            last_status = 200

            def request(self, *args):
                return {"results": [{"rows": [[1]]}]}

        with self.assertRaises(RuntimeError):
            api.query(Allowed(), "poc-prod", "prod_poc", "SELECT 1", (403,))

    def test_schema_readiness_waits_for_the_fixture_table(self):
        class Owner:
            reads = 0

            def request(self, method, path, body=None, statuses=(200,)):
                if method == "POST":
                    return {}
                self.reads += 1
                return {} if self.reads == 1 else {"schemas": [{"name": "public", "tables": [{"name": "permission_fixture"}]}]}

        owner = Owner()
        with patch.object(api.time, "sleep"):
            api.wait_database_metadata(owner, "poc-sandbox", "sandbox_poc")
        self.assertEqual(owner.reads, 2)


if __name__ == "__main__":
    unittest.main()

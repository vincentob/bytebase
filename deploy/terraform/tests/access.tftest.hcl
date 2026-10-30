# Every run plans against a mocked provider; no live API or database is used.
mock_provider "bytebase" {
  override_during = plan

  mock_resource "bytebase_project" {
    defaults = { name = "projects/mock" }
  }
  mock_resource "bytebase_workload_identity" {
    defaults = { email = "mock@mock.workload.bytebase.com" }
  }
}

variables {
  bytebase_service_account = "mock@service.bytebase.com"
  bytebase_service_key     = "mock"
  cf_access_client_id      = "mock"
  cf_access_client_secret  = "mock"
  db_passwords = {
    rusgaas-20101-sandbox   = "mock"
    rusgaas-20101-prod-test = "mock"
    grant-test              = "mock"
    unsafe-scope            = "mock"
    forbidden-prod          = "mock"
  }
  user_passwords = {
    test-dev    = "mock"
    test-leader = "mock"
    test-dba    = "mock"
  }
}

run "developer_isolation" {
  command = plan

  assert {
    condition = alltrue([
      for role, members in local.project_iam["rusgaas-20101"] :
      !contains(members, "user:test-dev@example.com")
    ])
    error_message = "The developer must have no membership in the CI/production project."
  }
  assert {
    condition     = contains(local.project_iam["rusgaas-20101-sandbox"]["roles/pocdeveloper"], "user:test-dev@example.com")
    error_message = "The developer needs SELECT/DDL/DML in the sandbox project."
  }
  assert {
    condition = alltrue([
      for _, inst in local.instances : inst.environment == "sandbox"
      if inst.project == "rusgaas-20101-sandbox"
    ]) && length([for _, inst in local.instances : inst if inst.project == "rusgaas-20101-sandbox"]) > 0
    error_message = "The developer project must contain sandbox connections only."
  }
  assert {
    condition = alltrue([
      for role, members in local.config.workspace_iam :
      role == "roles/pocbase" || !contains(members, "user:test-dev@example.com")
    ])
    error_message = "Workspace-level access must not bypass the developer's project boundary."
  }
}

run "leader_requires_approval" {
  command = plan

  assert {
    condition = alltrue(flatten([
      for project, bindings in local.project_iam : [
        for role, members in bindings :
        role == "roles/pocsubmitter" || !contains(members, "user:test-leader@example.com")
      ]
    ]))
    error_message = "The leader may submit issues but must not have standing SQL, owner or rollout permissions."
  }
  assert {
    condition     = alltrue([for _, grants in local.query_grants : length(grants) == 0])
    error_message = "The checked-in configuration must not pre-approve a query grant."
  }
  assert {
    condition = alltrue([
      for role, members in local.config.workspace_iam :
      role == "roles/pocbase" || !contains(members, "user:test-leader@example.com")
    ])
    error_message = "Workspace-level access must not bypass the leader's approval requirement."
  }
}

run "preserve_ci_connections" {
  command = plan

  assert {
    condition = local.gitops_instances["rusgaas-20101"] == {
      sandbox = "projects/rusgaas-20101/instances/rusgaas-20101-sandbox"
      prod    = "projects/rusgaas-20101/instances/rusgaas-20101-prod-test"
    }
    error_message = "The existing dbops stage targets must remain unchanged."
  }
  assert {
    condition     = local.instance_password_keys["rusgaas-20101-sandbox-dev"] == "rusgaas-20101-sandbox"
    error_message = "The additional sandbox registration must reuse its source credential."
  }
  assert {
    condition     = local.instances["rusgaas-20101-sandbox-dev"].host == local.instances["rusgaas-20101-sandbox"].host
    error_message = "The development connection must point at the existing sandbox."
  }
}

run "expiring_read_grants" {
  command = plan

  variables {
    config_file = "tests/fixtures/query-grants.yaml"
  }

  assert {
    condition = length([
      for binding in bytebase_iam_policy.project["grant-test"].iam_policy[0].binding : binding
      if binding.role == "roles/pocquery"
    ]) == 2
    error_message = "Every approved grant must produce a separate read-only binding."
  }
  assert {
    condition = alltrue([
      for binding in bytebase_iam_policy.project["grant-test"].iam_policy[0].binding :
      one(binding.condition).expire_timestamp == "2026-01-01T01:00:00Z"
      if binding.role == "roles/pocquery"
    ])
    error_message = "All query grants must retain their fixed expiration; later plans must not renew access."
  }
  assert {
    condition = alltrue([
      for binding in bytebase_iam_policy.project["grant-test"].iam_policy[0].binding :
      one(binding.condition).database == "projects/grant-test/instances/grant-test/databases/casino" &&
      one(binding.condition).schema == "public" &&
      one(binding.condition).tables == toset(["orders"])
      if binding.role == "roles/pocquery" && contains(binding.members, "user:leader@example.com")
    ])
    error_message = "Database/schema/table scope must be preserved in the actual IAM binding."
  }
}

run "reject_invalid_grants" {
  command = plan

  variables {
    config_file = "tests/fixtures/invalid-grants.yaml"
  }

  expect_failures = [
    bytebase_iam_policy.project["unapproved"],
    bytebase_iam_policy.project["too-long"],
    bytebase_iam_policy.project["no-reason"],
    bytebase_iam_policy.project["non-member"],
    bytebase_iam_policy.project["unscoped-table"],
    bytebase_iam_policy.project["cross-project"],
    bytebase_iam_policy.project["unsafe-scope"],
    bytebase_iam_policy.project["future-approval"],
    bytebase_iam_policy.project["invalid-time"],
    bytebase_instance.this["forbidden-prod"],
  ]
}

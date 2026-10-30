resource "bytebase_project" "this" {
  for_each = local.projects

  resource_id = each.key
  title       = each.value.title

  enforce_issue_title         = try(each.value.settings.enforce_issue_title, false)
  enforce_sql_review          = try(each.value.settings.enforce_sql_review, true)
  require_issue_approval      = try(each.value.settings.require_issue_approval, false)
  require_plan_check_no_error = try(each.value.settings.require_plan_check_no_error, true)
  allow_request_role          = try(each.value.settings.allow_request_role, false)
}

## Authoritative per project: owners and members from config.yaml plus the CI identities.
locals {
  project_iam_base = {
    for k, p in local.projects : k => merge(
      { "roles/projectOwner" = p.owners },
      contains(keys(local.gitops_projects), k) ? {
        "roles/projectOwner"       = concat(p.owners, ["workloadIdentity:${bytebase_workload_identity.baseline[k].email}"])
        "roles/projectDeveloper"   = ["workloadIdentity:${bytebase_workload_identity.check[k].email}"]
        "roles/gitopsServiceAgent" = ["workloadIdentity:${bytebase_workload_identity.deploy[k].email}"]
      } : {},
    )
  }

  # Merge `members` (role => principals) into the base bindings role by role.
  project_iam = {
    for k, base in local.project_iam_base : k => {
      for role in distinct(concat(keys(base), keys(try(local.projects[k].members, {})))) :
      role => distinct(concat(try(base[role], []), try(local.projects[k].members[role], [])))
    }
  }
}

resource "bytebase_iam_policy" "project" {
  for_each = local.projects

  parent     = bytebase_project.this[each.key].name
  depends_on = [bytebase_user.this]

  iam_policy {
    dynamic "binding" {
      for_each = local.project_iam[each.key]
      content {
        role    = binding.key
        members = binding.value
      }
    }

    # Keep temporary read grants separate from permanent bindings of the same role.
    dynamic "binding" {
      for_each = local.query_grants[each.key]
      content {
        role    = "roles/pocquery"
        members = [binding.value.member]

        condition {
          expire_timestamp = binding.value.expires_at
          database         = try(binding.value.database, null)
          schema           = try(binding.value.schema, null)
          tables           = try(binding.value.tables, null)
        }
      }
    }
  }

  lifecycle {
    precondition {
      condition = alltrue([
        for _, grant in local.query_grants[each.key] : try(
          contains(each.value.owners, grant.approved_by) &&
          length(trimspace(grant.reason)) > 0 &&
          startswith(grant.member, "user:") &&
          (contains(try(each.value.members["roles/pocsubmitter"], []), grant.member) || contains(try(each.value.members["roles/projectDeveloper"], []), grant.member)) &&
          can(regex("Z$", grant.approved_at)) &&
          can(regex("Z$", grant.expires_at)) &&
          timecmp(grant.approved_at, plantimestamp()) <= 0 &&
          timecmp(grant.approved_at, grant.expires_at) < 0 &&
          timecmp(grant.expires_at, timeadd(grant.approved_at, "8h")) <= 0,
          false,
        )
      ])
      error_message = "Query grants in ${each.key} require a submitter user, an owner approver, a reason, and UTC approval/expiry timestamps no more than 8 hours apart; approval cannot be in the future."
    }

    precondition {
      condition = alltrue([
        for _, grant in local.query_grants[each.key] : try(
          (try(grant.database, null) == null ?
            try(grant.schema, null) == null && length(try(grant.tables, [])) == 0 :
            can(regex("^projects/${each.key}/instances/[^/]+/databases/[^/]+$", grant.database)) &&
            contains([for k, inst in local.instances : k if inst.project == each.key], split("/", grant.database)[3])
          ) &&
          alltrue([for name in concat(
            try(grant.schema, null) == null ? [] : [grant.schema],
            try(grant.tables, []),
            try(grant.database, null) == null ? [] : [grant.database],
          ) : length(trimspace(name)) > 0 && !can(regex("[\"\\\\\\n\\r]", name))]),
          false,
        )
      ])
      error_message = "Scoped query grants in ${each.key} must name a managed database in that project; schema/tables require a database, and scope names cannot contain quotes, backslashes or newlines."
    }
  }
}

resource "bytebase_iam_policy" "workspace" {
  depends_on = [bytebase_user.this]

  iam_policy {
    dynamic "binding" {
      for_each = local.config.workspace_iam
      content {
        role    = binding.key
        members = binding.value
      }
    }
  }
}

## GitOps per project: Bytebase workload identities trusted for the dbops repo's GitLab OIDC
## tokens. The dbops repository itself (tool, CI, SQL) is maintained there through merge
## requests; Terraform only publishes what its dbops.yaml must contain (output dbops_config).

locals {
  repo_path = { for k, p in local.gitops_projects : k => "${p.gitops.namespace}/${p.gitops.repo}" }

  # Stage list as dbops.yaml expects it.
  gitops_stages = {
    for k, p in local.gitops_projects : k => [
      for env in p.gitops.stages : {
        environment = env
        manual      = contains(try(p.gitops.manual_stages, ["prod"]), env)
      }
    ]
  }

  # GitLab OIDC "sub" claims: project_path:<path>:ref_type:<type>:ref:<ref>
  wi_subjects = {
    for k, path in local.repo_path : k => {
      check    = "project_path:${path}:*"
      deploy   = "project_path:${path}:ref_type:branch:ref:main"
      baseline = "project_path:${path}:ref_type:branch:ref:main"
    }
  }
}

resource "bytebase_workload_identity" "check" {
  for_each = local.gitops_projects

  workload_identity_id = "${each.key}-ci-check"
  title                = "${each.value.title} CI check"
  parent               = bytebase_project.this[each.key].name

  workload_identity_config {
    provider_type     = "GITLAB"
    issuer_url        = local.config.gitlab_url
    allowed_audiences = [local.config.bytebase_url]
    subject_pattern   = local.wi_subjects[each.key].check
  }

  # Import (provider 3.23.0) does not read these back; both are derived from the project
  # key and never change, so ignoring them keeps an imported identity from being replaced.
  lifecycle {
    ignore_changes = [parent, workload_identity_id]
  }
}

resource "bytebase_workload_identity" "deploy" {
  for_each = local.gitops_projects

  workload_identity_id = "${each.key}-ci-deploy"
  title                = "${each.value.title} CI deploy"
  parent               = bytebase_project.this[each.key].name

  workload_identity_config {
    provider_type     = "GITLAB"
    issuer_url        = local.config.gitlab_url
    allowed_audiences = [local.config.bytebase_url]
    subject_pattern   = local.wi_subjects[each.key].deploy
  }

  lifecycle {
    ignore_changes = [parent, workload_identity_id]

    # dbops.yaml maps each stage to exactly one instance.
    precondition {
      condition     = alltrue([for env, keys in local.gitops_instance_keys[each.key] : length(keys) <= 1])
      error_message = "GitOps project ${each.key} has more than one instance in an environment: ${jsonencode(local.gitops_instance_keys[each.key])}"
    }
  }
}

## Baseline creates revisions, which only project owners may do.
resource "bytebase_workload_identity" "baseline" {
  for_each = local.gitops_projects

  workload_identity_id = "${each.key}-ci-baseline"
  title                = "${each.value.title} CI baseline"
  parent               = bytebase_project.this[each.key].name

  workload_identity_config {
    provider_type     = "GITLAB"
    issuer_url        = local.config.gitlab_url
    allowed_audiences = [local.config.bytebase_url]
    subject_pattern   = local.wi_subjects[each.key].baseline
  }

  lifecycle {
    ignore_changes = [parent, workload_identity_id]
  }
}

## What each dbops repository's dbops.yaml must contain; copy it there by MR when it changes.
locals {
  dbops_config = {
    for k, _ in local.gitops_projects : k => {
      bytebase_url = local.config.bytebase_url
      audience     = local.config.bytebase_url
      project      = bytebase_project.this[k].name
      identities = {
        check    = bytebase_workload_identity.check[k].email
        deploy   = bytebase_workload_identity.deploy[k].email
        baseline = bytebase_workload_identity.baseline[k].email
      }
      stages    = local.gitops_stages[k]
      instances = local.gitops_instances[k]
    }
  }
}

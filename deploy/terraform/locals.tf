locals {
  config = yamldecode(file("${path.module}/${var.config_file}"))

  environments = local.config.environments
  projects     = local.config.projects
  users        = try(local.config.users, {})

  # Reuse connection settings for a separately authorized Bytebase registration.
  # Aliases only reference primary entries, so connection inheritance cannot cycle.
  instance_aliases = try(local.config.instance_aliases, {})
  instances = merge(local.config.instances, {
    for k, alias in local.instance_aliases : k => merge(local.config.instances[alias.source], {
      project = alias.project
    })
  })
  instance_password_keys = merge(
    { for k, _ in local.config.instances : k => k },
    { for k, alias in local.instance_aliases : k => alias.source },
  )

  # Expiration is an absolute timestamp supplied by the owner, never timestamp()+TTL.
  query_grants = { for k, p in local.projects : k => try(p.query_grants, {}) }

  # Projects that own a GitLab dbops repository.
  gitops_projects = { for k, p in local.projects : k => p if try(p.gitops, null) != null }

  # Instance per project and environment, used as rollout targets in dbops.yaml.
  # { project => { env => "projects/<p>/instances/<i>" } }
  gitops_instance_keys = {
    for pk, p in local.gitops_projects : pk => {
      for env in p.gitops.stages : env => [
        for ik, inst in local.instances : ik if inst.project == pk && inst.environment == env
      ]
    }
  }
  gitops_instances = {
    for pk, envs in local.gitops_instance_keys : pk => {
      for env, keys in envs : env => "projects/${pk}/instances/${keys[0]}" if length(keys) > 0
    }
  }
}

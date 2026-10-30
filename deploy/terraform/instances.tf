## Project-owned instances: only members of that project can see them.
resource "bytebase_instance" "this" {
  for_each = local.instances

  resource_id   = each.key
  title         = each.key
  engine        = each.value.engine
  parent        = bytebase_project.this[each.value.project].name
  environment   = bytebase_environment.this[each.value.environment].name
  external_link = try(each.value.external_link, null)

  data_sources {
    id       = "admin"
    type     = "ADMIN"
    host     = each.value.host
    port     = tostring(each.value.port)
    username = each.value.username
    password = lookup(var.db_passwords, local.instance_password_keys[each.key], "")
    database = try(each.value.database, null)
    use_ssl  = try(each.value.use_ssl, false)
  }

  lifecycle {
    precondition {
      condition     = contains(try(local.projects[each.value.project].allowed_environments, keys(local.environments)), each.value.environment)
      error_message = "Environment ${each.value.environment} is not allowed in project ${each.value.project}."
    }

    precondition {
      condition     = !contains(keys(local.config.instances), each.key) || !contains(keys(local.instance_aliases), each.key)
      error_message = "Instance alias ${each.key} must not shadow a primary instance."
    }

    precondition {
      condition     = contains(keys(var.db_passwords), local.instance_password_keys[each.key])
      error_message = "Missing instance ${local.instance_password_keys[each.key]} in TF_VAR_db_passwords."
    }
  }
}

resource "bytebase_review_config" "default" {
  resource_id = local.config.sql_review.id
  title       = local.config.sql_review.title
  enabled     = true
  resources   = [for k, _ in local.environments : bytebase_environment.this[k].name]

  dynamic "rules" {
    for_each = local.config.sql_review.rules
    content {
      type   = rules.value.type
      engine = rules.value.engine
      level  = rules.value.level
    }
  }
}

## Environments are a workspace-wide list; each resource upserts only its own entry.
resource "bytebase_environment" "this" {
  for_each = local.environments

  resource_id = each.key
  title       = each.value.title
  order       = each.value.order

  color {
    red   = each.value.color.red
    green = each.value.color.green
    blue  = each.value.color.blue
  }
}

## End users from config.yaml `users` (key => email/title). The initial password comes from
## TF_VAR_user_passwords; later changes made by the user are kept.
resource "bytebase_user" "this" {
  for_each = local.users

  email    = each.value.email
  title    = each.value.title
  password = lookup(var.user_passwords, each.key, null)

  lifecycle {
    ignore_changes = [password]

    precondition {
      condition     = contains(keys(var.user_passwords), each.key)
      error_message = "Missing user ${each.key} in TF_VAR_user_passwords."
    }
  }
}

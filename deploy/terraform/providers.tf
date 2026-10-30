provider "bytebase" {
  url             = local.config.bytebase_url
  service_account = var.bytebase_service_account
  service_key     = var.bytebase_service_key

  dynamic "custom_header" {
    for_each = var.cf_access_client_id == "" ? {} : {
      "CF-Access-Client-Id"     = var.cf_access_client_id
      "CF-Access-Client-Secret" = var.cf_access_client_secret
    }
    content {
      name  = custom_header.key
      value = custom_header.value
    }
  }
}

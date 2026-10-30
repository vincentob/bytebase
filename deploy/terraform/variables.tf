## Credentials are supplied through TF_VAR_* environment variables.

variable "config_file" {
  description = "YAML configuration relative to the module; tests use isolated fixtures"
  type        = string
  default     = "config.yaml"
}

variable "bytebase_service_account" {
  description = "Bytebase service account email (workspace admin)"
  type        = string
  default     = ""

  validation {
    condition     = var.bytebase_service_account != ""
    error_message = "bytebase_service_account is not set. Set the matching TF_VAR_* environment variable before planning."
  }
}

variable "bytebase_service_key" {
  description = "Bytebase service account key"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.bytebase_service_key != ""
    error_message = "bytebase_service_key is not set. Set the matching TF_VAR_* environment variable before planning."
  }
}

variable "cf_access_client_id" {
  description = "Cloudflare Access service token client id"
  type        = string
  sensitive   = true
  default     = ""

}

variable "cf_access_client_secret" {
  description = "Cloudflare Access service token client secret"
  type        = string
  sensitive   = true
  default     = ""

}

variable "db_passwords" {
  description = "Instance key => admin password, from TF_VAR_db_passwords"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "user_passwords" {
  description = "User key => initial login password, from TF_VAR_user_passwords"
  type        = map(string)
  sensitive   = true
  default     = {}
}

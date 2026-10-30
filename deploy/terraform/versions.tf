terraform {
  required_version = ">= 1.9.0"

  required_providers {
    bytebase = {
      source  = "bytebase/bytebase"
      version = "~> 3.23"
    }
  }
}

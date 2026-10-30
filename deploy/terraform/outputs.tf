output "dbops_config" {
  description = "dbops.yaml content per GitOps project; copy into the dbops repo by MR when it changes"
  value       = { for k, c in local.dbops_config : k => yamlencode(c) }
}

output "workload_identities" {
  description = "Bytebase workload identity emails used by the dbops CI"
  value = {
    for k, _ in local.gitops_projects : k => {
      check    = bytebase_workload_identity.check[k].email
      deploy   = bytebase_workload_identity.deploy[k].email
      baseline = bytebase_workload_identity.baseline[k].email
    }
  }
}

output "rollout_instances" {
  description = "Bytebase instance per GitOps project and environment"
  value       = local.gitops_instances
}

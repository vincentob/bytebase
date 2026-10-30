# Deployment policy

- Read `README.md` and the repository instructions before changing this module.
- Never run `terraform apply` or `make apply`; the owner applies a reviewed saved plan.
- Review plans with `make plan QUIET=1`. Do not print credentials or plan values.
- Tests must use the mocked provider. Do not use an existing Bytebase instance or
  database as a test fixture.
- Keep committed example URLs and identities sanitized. Do not copy credentials,
  Terraform state or saved plans from the source infrastructure repository.

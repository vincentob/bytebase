SHELL := /bin/bash
.DEFAULT_GOAL := help

C_RESET := \033[0m
C_BOLD := \033[1m
C_CYAN := \033[36m
C_GREEN := \033[32m
C_YELLOW := \033[33m
C_RED := \033[31m

ifneq ($(strip $(NO_COLOR)),)
C_RESET :=
C_BOLD :=
C_CYAN :=
C_GREEN :=
C_YELLOW :=
C_RED :=
else ifneq ($(shell test -t 1 && printf 1),1)
C_RESET :=
C_BOLD :=
C_CYAN :=
C_GREEN :=
C_YELLOW :=
C_RED :=
endif

INFO = printf "$(C_GREEN)[INFO]$(C_RESET)  %s\n" >&2
WARN = printf "$(C_YELLOW)[WARN]$(C_RESET)  %s\n" >&2
ERROR = printf "$(C_RED)[ERROR]$(C_RESET) %s\n" >&2

# ---------- vars ----------
# A wrapper that injects credentials replaces terraform here, e.g. TF := scripts/tf.sh
TF      ?= terraform
PYTHON  ?= python3
# Matches the repo-wide *.tfplan ignore rule.
PLAN    := plan.tfplan
# Repo-root scripts/, relative to this directory.
SCRIPTS ?= ../../scripts
TFPLAN_TABLE := $(SCRIPTS)/terraform/tfplan_table.py

# ---------- help ----------
# `##@ Group` starts a group, `target: ## desc` documents a target.
define HELP_AWK
/^##@/ { h = sprintf("%s%s%s%s", (n++ ? "\n" : ""), b, substr($$0, 5), r); next }
/^[a-zA-Z0-9_.-]+:.*## / {
  if (h != "") { print h; h = "" }
  printf "  %s%-20s%s %s\n", c, substr($$0, 1, index($$0, ":") - 1), r, substr($$0, index($$0, "## ") + 3)
}
endef
export HELP_AWK

##@ Terraform
.PHONY: init validate plan apply
init: ## Install providers and modules
	@$(INFO) "terraform init"
	@$(TF) init -input=false
validate: ## Check formatting and validate the configuration
	@terraform fmt -check -recursive >/dev/null || { $(ERROR) "terraform fmt needed: run make fmt"; exit 1; }
	@$(TF) validate >/dev/null
	@$(INFO) "configuration valid"
plan: validate ## Plan into plan.tfplan: native output, then a summary table (QUIET=1 table only, ARGS=extra flags)
	@$(INFO) "terraform plan -> $(PLAN)"
	@$(TF) plan -input=false -out=$(PLAN) $(ARGS) $(if $(QUIET),>/dev/null)
	@$(PYTHON) -B $(TFPLAN_TABLE) $(PLAN)
apply: ## [owner] Show the plan saved by make plan, apply it after typing yes, then delete it
	@[ -f $(PLAN) ] || { $(ERROR) "$(PLAN) not found: run make plan first"; exit 1; }
	@[ -t 0 ] || { $(ERROR) "make apply needs an interactive terminal"; exit 1; }
	@$(PYTHON) -B $(TFPLAN_TABLE) $(PLAN)
	@$(WARN) "applying $(PLAN) (owner only)"
	@read -r -p "Type yes to apply: " answer; [ "$$answer" = yes ] || { $(WARN) "aborted, nothing applied"; exit 1; }
	@$(TF) apply -input=false $(PLAN)
	@rm -f $(PLAN)
	@$(INFO) "applied; $(PLAN) removed"

##@ Tools
.PHONY: fmt test help
fmt: ## Format Terraform files
	@terraform fmt -recursive
test: ## Verify isolation and expiry with a mocked provider; no live API calls
	@$(INFO) "Testing deployment policy with a mocked provider"
	@terraform test -no-color
help: ## Show this help
	@awk -v b="$(C_BOLD)" -v c="$(C_CYAN)" -v r="$(C_RESET)" "$$HELP_AWK" $(firstword $(MAKEFILE_LIST))

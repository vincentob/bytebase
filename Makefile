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

COMPOSE := docker compose -f docker-compose.yml
COMPOSE_EXEC_FLAGS := $(shell test -t 0 || printf '%s' '-T')
SCRIPTS := scripts
export GIT_COMMIT := $(shell git rev-parse HEAD 2>/dev/null || printf local)

NAMESPACES := poc terraform
NS_DIR_poc := poc
NS_DIR_terraform := deploy/terraform
ns_targets = $(shell sed -nE 's/^([a-zA-Z0-9_.-]+):.*\#\# .*/\1/p' $(1)/Makefile)

define ns_rule
.PHONY: $(1)\:$(2)
$(1)\:$(2):
	@$$(MAKE) --no-print-directory -C $$(NS_DIR_$(1)) $(2)
endef
$(foreach n,$(NAMESPACES),$(foreach t,$(filter-out help,$(call ns_targets,$(NS_DIR_$(n)))),$(eval $(call ns_rule,$(n),$(t)))))

define HELP_AWK
BEGIN { if (ns != "") h = sprintf("\n%s%s%s", b, ns, r) }
/^##@/ { if (ns == "") h = sprintf("%s%s%s%s", (n++ ? "\n" : ""), b, substr($$0, 5), r); next }
/^[a-zA-Z0-9_.-]+:.*## / {
  t = substr($$0, 1, index($$0, ":") - 1)
  if (ns != "" && t == "help") next
  t = (ns != "" ? ns ":" : "") t
  if (h != "") { print h; h = "" }
  printf "  %s%-26s%s %s\n", c, t, r, substr($$0, index($$0, "## ") + 3)
}
endef
export HELP_AWK

##@ Compose
.PHONY: build up status logs down
build: validate ## Build the permission PoC image from the current source
	@$(INFO) "Building the permission PoC image"
	@$(COMPOSE) build bytebase

up: validate ## Rebuild the image and recreate Bytebase; preserve ~/.bytebase/data
	@$(INFO) "Building and starting the permission PoC"
	@$(COMPOSE) up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300 bytebase

status: ## Show container status
	@$(COMPOSE) ps

logs: ## Follow Bytebase logs
	@$(COMPOSE) logs --follow --tail=100 bytebase

down: ## Stop Bytebase and preserve ~/.bytebase/data
	@$(INFO) "Stopping Bytebase; the mounted data directory is preserved"
	@$(COMPOSE) down --remove-orphans

##@ Roles
.PHONY: roles-sync
roles-sync: ## Synchronize the four custom roles; preserve users and IAM bindings
	@$(INFO) "Synchronizing custom roles with the running Bytebase instance"
	@$(COMPOSE) exec $(COMPOSE_EXEC_FLAGS) --env BYTEBASE_ADMIN_TOKEN bytebase python3 /opt/bytebase/scripts/poc/manage.py roles

##@ Tools
.PHONY: validate tfplan-test help
validate: ## Validate Compose configuration without printing credentials
	@$(COMPOSE) config --quiet

tfplan-test: ## Test the Terraform plan summary renderer
	@python3 -B -m unittest discover -s $(SCRIPTS)/terraform -p 'test_tfplan_table.py'

help: ## Show available commands
	@awk -v b="$(C_BOLD)" -v c="$(C_CYAN)" -v r="$(C_RESET)" "$$HELP_AWK" $(firstword $(MAKEFILE_LIST))
	@$(foreach n,$(NAMESPACES),awk -v b="$(C_BOLD)" -v c="$(C_CYAN)" -v r="$(C_RESET)" -v ns=$(n) "$$HELP_AWK" $(NS_DIR_$(n))/Makefile;)

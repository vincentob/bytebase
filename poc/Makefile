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

PYTHON := $(CURDIR)/.venv/bin/python
SCRIPTS := ../scripts/poc
POC := $(PYTHON) -B $(SCRIPTS)/manage.py
COMPOSE := docker compose -f compose.yaml

define HELP_AWK
/^##@/ { h = sprintf("%s%s%s%s", (n++ ? "\n" : ""), b, substr($$0, 5), r); next }
/^[a-zA-Z0-9_.-]+:.*## / {
  if (h != "") { print h; h = "" }
  printf "  %s%-20s%s %s\n", c, substr($$0, 1, index($$0, ":") - 1), r, substr($$0, index($$0, "## ") + 3)
}
endef
export HELP_AWK

##@ Permission fixtures
.PHONY: up seed status stop api-test browser-test test
up: ## Build the local image and start one isolated test container
	@$(MAKE) --no-print-directory -C .. build
	@$(COMPOSE) up -d --wait --wait-timeout 300
seed: deps ## Create isolated users, roles, projects and SQL fixtures
	@$(INFO) "Seeding the isolated permission fixtures"
	@$(POC) seed
status: ## Show isolated test container status
	@$(COMPOSE) ps
stop: ## Stop the isolated stack and preserve its test volume
	@$(COMPOSE) down
api-test: deps ## Verify API, SQL, rollout and expiring read permissions
	@$(POC) api-test
browser-test: deps ## Verify the three role-specific browser flows
	@$(POC) browser-test
test: deps ## Seed fixtures, verify APIs and SQL, then run browser checks
	@$(POC) test

##@ Tools
.PHONY: deps browser-deps unit go-test check help
deps: ## Install Python dependencies in the local virtual environment
	@test -x $(PYTHON) || python3 -m venv .venv
	@$(PYTHON) -m pip install --quiet --disable-pip-version-check --no-cache-dir -r requirements.txt
browser-deps: ## Install frontend dependencies and Playwright Chromium
	@pnpm --dir ../frontend install --frozen-lockfile
	@pnpm --dir ../frontend exec playwright install chromium
unit: deps ## Check role synchronization and fixture permission contracts
	@$(PYTHON) -B -m unittest discover -s $(SCRIPTS) -p 'test_*.py' -v
go-test: deps ## Run existing PoC Go tests in an isolated Linux container
	@$(POC) go-test
check: ## Run the repository frontend format and full validation gate
	@pnpm --dir ../frontend fix
	@pnpm --dir ../frontend test
help: ## Show permission fixture commands
	@awk -v b="$(C_BOLD)" -v c="$(C_CYAN)" -v r="$(C_RESET)" "$$HELP_AWK" $(firstword $(MAKEFILE_LIST))

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
export GIT_COMMIT := $(shell git rev-parse HEAD 2>/dev/null || printf local)

define HELP_AWK
/^##@/ { h = sprintf("%s%s%s%s", (n++ ? "\n" : ""), b, substr($$0, 5), r); next }
/^[a-zA-Z0-9_.-]+:.*## / {
  if (h != "") { print h; h = "" }
  printf "  %s%-20s%s %s\n", c, substr($$0, 1, index($$0, ":") - 1), r, substr($$0, index($$0, "## ") + 3)
}
endef
export HELP_AWK

##@ Compose
.PHONY: build up status logs down
build: validate ## Build the permission PoC image from the current source
	@$(INFO) "Building the permission PoC image"
	@$(COMPOSE) build bytebase

up: validate ## Rebuild the image and recreate Bytebase; preserve data volumes
	@$(INFO) "Building and starting the permission PoC"
	@$(COMPOSE) up -d --build --force-recreate --wait --wait-timeout 300 bytebase

status: ## Show container status
	@$(COMPOSE) ps

logs: ## Follow Bytebase logs
	@$(COMPOSE) logs --follow --tail=100 bytebase

down: ## Stop the stack and preserve data volumes
	@$(INFO) "Stopping the stack; data volumes are preserved"
	@$(COMPOSE) down

##@ Tools
.PHONY: validate help
validate: ## Validate Compose configuration without printing credentials
	@$(COMPOSE) config --quiet

help: ## Show available commands
	@awk -v b="$(C_BOLD)" -v c="$(C_CYAN)" -v r="$(C_RESET)" "$$HELP_AWK" $(firstword $(MAKEFILE_LIST))

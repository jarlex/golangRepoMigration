SHELL := /usr/bin/env bash

CSV ?= ./migration.csv
BASE_DIR ?= ./repos
GHE_HOST ?=
PREPARE_PROTOCOL ?= ssh
STOP_ON_ERROR ?= true

PREPARE_EXTRA_FLAGS :=
ifeq ($(PREPARE_PROTOCOL),https)
PREPARE_EXTRA_FLAGS += --https
endif

.PHONY: prepare-repos push-repos

prepare-repos:
	@./scripts/prepare_repos.sh --csv "$(CSV)" --base-dir "$(BASE_DIR)" --ghe-host "$(GHE_HOST)" $(PREPARE_EXTRA_FLAGS)

push-repos:
	@./scripts/push_repos.sh --csv "$(CSV)" --base-dir "$(BASE_DIR)" --stop-on-error "$(STOP_ON_ERROR)"

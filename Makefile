# Cross-tool test targets (Codex, Cursor, CI, humans without Claude slash commands)
.PHONY: smoke integration e2e verify help

ENV ?= dev
export ENV


help:
	@echo "Targets: smoke | integration | e2e | verify"
	@echo "Example: make smoke ENV=dev"

smoke:
	pytest tests/smoke -m smoke -ra

integration:
	pytest tests/integration -m integration -ra

e2e:
	pytest tests/e2e -m e2e -ra

verify: smoke integration e2e

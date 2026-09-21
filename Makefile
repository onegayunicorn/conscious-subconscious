# conscious-subconscious — developer task runner
#
# Targets are intentionally thin wrappers so that every step can also be run
# by hand. Anything that needs an optional dependency says so in its error.

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin
PY     := $(BIN)/python

.DEFAULT_GOAL := help
.PHONY: help venv install install-dev lint fmt typecheck test test-golden coverage \
        build clean simulate demo report audit sbom web-install web-build web-test \
        site-build verify docker docker-compose-up k8s-validate locales-sync preflight

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Create the local virtual environment
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip

install: venv ## Install the core package (no optional extras)
	$(PY) -m pip install -e .

install-dev: venv ## Install core + api + dev extras
	$(PY) -m pip install -e ".[api,dev]"
	@echo "Run 'make install-devices' or 'make install-science' for optional extras."

install-devices: venv ## Install hardware driver extras
	$(PY) -m pip install -e ".[devices]"

install-science: venv ## Install numerical/plotting extras
	$(PY) -m pip install -e ".[science]"

lint: ## Ruff lint
	$(PY) -m ruff check src tests tools

fmt: ## Ruff format + autofix
	$(PY) -m ruff check --fix src tests tools
	$(PY) -m ruff format src tests tools

typecheck: ## mypy on the core package
	$(PY) -m mypy

test: ## Run the test suite
	$(PY) -m pytest

test-golden: ## Run only the golden reference-run tests
	$(PY) -m pytest -m golden

coverage: ## Test suite with coverage report
	$(PY) -m pytest --cov --cov-report=term-missing

simulate: ## Baseline vs focused vs intermittent comparison
	$(PY) -m conscious_subconscious.sim.cli compare

demo: ## Short focused demo with a printed report
	$(PY) -m conscious_subconscious.sim.cli run --scenario focused --report

report: ## Write a Markdown report to out/report.md
	@mkdir -p out
	$(PY) -m conscious_subconscious.sim.cli run --scenario intermittent --report --out out/report.md

audit: ## Run the hardening self-audit
	$(PY) -m conscious_subconscious.hardening.cli --root .

sbom: ## Generate a CycloneDX-style SBOM
	$(PY) tools/gen_sbom.py --out sbom.json

locales-sync: ## Validate that every locale has the keys English defines
	$(PY) tools/check_locales.py

build: clean ## Build sdist + wheel into dist/
	$(PY) -m build

build-all: ## Build every platform artefact and write deploy/out/manifest.json
	$(PY) tools/build_platforms.py --all

web-install: ## Install web workspace dependencies
	cd apps/console && npm install

web-build: ## Type-check and build the web console
	cd apps/console && npm run build

web-test: ## Run web unit tests
	cd apps/console && npm test

site-build: ## Build the marketing/docs site
	cd apps/site && npm install && npm run build

verify: lint typecheck test web-test web-build audit locales-sync ## Everything CI runs locally

docker: ## Build the service container image
	docker build -f deploy/docker/Dockerfile -t conscious-subconscious:0.1.0 .

docker-compose-up: ## Start the local stack
	docker compose -f deploy/docker/docker-compose.yml up --build

k8s-validate: ## Dry-run the Kubernetes manifests (requires kubectl)
	kubectl apply --dry-run=client -f deploy/k8s/ -R

preflight: ## Show tool availability for the current machine
	$(PY) tools/preflight.py

clean: ## Remove build and cache artefacts
	@$(PY) -c "import shutil,pathlib; \
[shutil.rmtree(p, ignore_errors=True) for p in \
 [pathlib.Path(x) for x in ('build','dist','out','.pytest_cache','.mypy_cache','.ruff_cache','.coverage','htmlcov','sbom.json')]]"

.PHONY: verify test smoke docker-smoke help

PYTHON ?= python
ARTIFACTS := artifacts

help:
	@echo "Targets: verify | test | smoke | docker-smoke"

verify:
	$(PYTHON) scripts/verify_release.py
	$(PYTHON) -m pytest

test:
	$(PYTHON) -m pytest

smoke:
	$(PYTHON) $(ARTIFACTS)/non_oracle_defer_simulation_2026_05.py --seed 20260501 --n_seeds 3 --out $(ARTIFACTS)/out/smoke.json --bootstrap_iterations 200

docker-smoke:
	cd $(ARTIFACTS) && docker build -t airi-defer-sim:latest .
	mkdir -p $(ARTIFACTS)/out
	docker run --rm -v "$$(pwd)/$(ARTIFACTS)/out:/app/out" airi-defer-sim:latest \
		$(PYTHON) non_oracle_defer_simulation_2026_05.py --seed 20260501 --n_seeds 1 --out out/smoke_docker.json

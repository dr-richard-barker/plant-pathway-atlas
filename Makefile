.PHONY: all test maps cache clean

all: maps cache test

maps:
	.venv/bin/python scripts/compile_maps.py

cache:
	.venv/bin/python scripts/build_ortholog_cache.py

test:
	.venv/bin/pytest tests

clean:
	rm -rf .pytest_cache maps/svg/*.svg catalog/sidecars/*.json

.PHONY: all test maps cache zenodo site abai clean serve

all: maps cache zenodo site abai test

maps:
	.venv/bin/python scripts/compile_maps.py

cache:
	.venv/bin/python scripts/build_ortholog_cache.py

zenodo:
	.venv/bin/python scripts/prepare_zenodo.py

site:
	.venv/bin/python scripts/build_site.py

abai:
	.venv/bin/python scripts/run_abai_qc_screen.py

test:
	.venv/bin/pytest tests

serve:
	python3 -m http.server 8080 --directory docs

clean:
	rm -rf .pytest_cache maps/svg/*.svg maps/sbgn/*.sbgn catalog/sidecars/*.json

.PHONY: test
test:
	python -m unittest discover tests

.PHONY: fix
fix:
	python -m ruff format
	python -m ruff check --fix
	python -m mypy .

.PHONY: check
check:
	python -m ruff format --check
	python -m ruff check
	python -m mypy .


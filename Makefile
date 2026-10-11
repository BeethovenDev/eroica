# EROICA developer shortcuts. Works on any platform with GNU make.
.PHONY: install test lint type check fmt build clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

type:
	mypy

check: lint type test

fmt:
	ruff check --fix .
	ruff format .

build:
	python -m build

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

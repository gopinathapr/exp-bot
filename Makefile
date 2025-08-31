# Makefile for Expense Bot Testing

.PHONY: test test-unit test-integration test-coverage install-test-deps clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  test              - Run all tests with coverage"
	@echo "  test-unit         - Run only unit tests"
	@echo "  test-integration  - Run only integration tests"
	@echo "  test-coverage     - Run tests and generate detailed coverage report"
	@echo "  install-test-deps - Install testing dependencies"
	@echo "  clean             - Clean test artifacts"
	@echo "  help              - Show this help message"

# Install test dependencies
install-test-deps:
	pip install -r requirements-test.txt

# Run all tests
test:
	python run_tests.py

# Run unit tests only
test-unit:
	python run_tests.py --type unit

# Run integration tests only
test-integration:
	python run_tests.py --type integration

# Run tests with detailed coverage
test-coverage:
	pytest test_bot.py test_integration.py \
		--cov=bot \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		-v

# Clean test artifacts
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Quick test run (no coverage)
test-quick:
	python run_tests.py --no-coverage

# Install dependencies and run tests
test-all:
	make install-test-deps
	make test

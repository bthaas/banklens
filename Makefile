.PHONY: install run test test-fast demo-files check-env

install:
	python3 -m pip install -r requirements.txt

check-env:
	@if [ -z "$$OPENAI_API_KEY" ]; then echo "OPENAI_API_KEY is not set"; exit 1; fi
	@if [ -z "$$FLASK_SECRET_KEY" ]; then echo "FLASK_SECRET_KEY is not set"; exit 1; fi

run: check-env
	python3 app.py

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q

test-fast:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -k "not slow"

demo-files:
	@echo "Demo CSV files:"
	@ls -1 demo_data

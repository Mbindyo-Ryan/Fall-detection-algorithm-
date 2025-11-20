PYTHON ?= python3
APP_FILE ?= app_auth.py
DIST_DIR ?= dist

.PHONY: help install run run-debug seed-db setup-test-data test-video train-ml train-cnn lint package-release clean

help:
	@echo "Available targets:"
	@echo "  make install             # Install Python dependencies"
	@echo "  make run                 # Start the Flask dashboard"
	@echo "  make run-debug           # Start Flask with debugger on"
	@echo "  make seed-db             # Populate the database with dummy data"
	@echo "  make setup-test-data     # Organize fall/no-fall videos"
	@echo "  make test-video VIDEO=... [GROUND=0|1]"
	@echo "  make train-ml            # Train the classical ML classifier"
	@echo "  make train-cnn           # Train the CNN validator"
	@echo "  make package-release     # Bundle app, models, docs, and guides"
	@echo "  make clean               # Remove build artifacts"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run:
	FLASK_ENV=production $(PYTHON) $(APP_FILE)

run-debug:
	FLASK_ENV=development $(PYTHON) $(APP_FILE)

seed-db:
	$(PYTHON) scripts/generate_dummy_data.py

setup-test-data:
	$(PYTHON) scripts/setup_test_data.py --setup-folders

test-video:
	@if [ -z "$(VIDEO)" ]; then echo "Missing VIDEO path. Usage: make test-video VIDEO=path/to/file.mp4 [GROUND=0|1]"; exit 1; fi
	@if [ -z "$(GROUND)" ]; then \
		$(PYTHON) scripts/test_fall_videos.py --video "$(VIDEO)"; \
	else \
		$(PYTHON) scripts/test_fall_videos.py --video "$(VIDEO)" --ground-truth $(GROUND); \
	fi

train-ml:
	$(PYTHON) scripts/train_classifier.py

train-cnn:
	$(PYTHON) scripts/train_cnn_validator.py

lint:
	$(PYTHON) -m flake8 app_auth.py detection_skeleton.py scripts/*.py

package-release:
	$(PYTHON) tools/package_release.py --output $(DIST_DIR)/care-system-release.zip

clean:
	rm -rf $(DIST_DIR) __pycache__ */__pycache__ .pytest_cache


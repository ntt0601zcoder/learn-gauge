.PHONY: clean install run fresh

# Python version
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
PYTHON_VENV := $(VENV_BIN)/python
PIP_VENV := $(VENV_BIN)/pip

# Remove hsmh_model module
clean:
	@echo "Removing hsmh_model module..."
	@if [ -f $(PIP_VENV) ]; then \
		$(PIP_VENV) uninstall -y hsmh_model || true; \
		echo "hsmh_model module removed."; \
	else \
		echo "Virtual environment not found. Skipping..."; \
	fi

# Create virtual environment and install dependencies
install:
	@if [ ! -d $(VENV) ]; then \
		echo "Creating new virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@echo "Installing dependencies..."
	$(PIP_VENV) install --upgrade pip
	$(PIP_VENV) install -r requirements.txt
	@echo "Installation completed."

# Run Django development server
run:
	@echo "Starting Django development server..."
	$(PYTHON_VENV) manage.py runserver

# Clean, install, and run (fresh start)
fresh: install run


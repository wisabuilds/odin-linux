PREFIX ?= /usr/local
APP_DIR = $(PREFIX)/share/odin-linux
BIN_DIR = $(PREFIX)/bin
DESKTOP_DIR = $(PREFIX)/share/applications
ICON_DIR = $(PREFIX)/share/icons/hicolor/scalable/apps

.PHONY: all install uninstall test run udev clean

all:
	@echo "Odin Linux"
	@echo "Commands:"
	@echo "  make run        - Run locally from current directory"
	@echo "  make install    - Install to $(PREFIX) (use sudo for system-wide)"
	@echo "  make uninstall  - Remove installation"
	@echo "  make udev       - Install udev rules for Download Mode"

run:
	./bin/odin-linux

install:
	./install.sh

uninstall:
	./uninstall.sh

udev:
	sudo ./setup_udev_rules.sh

test:
	python3 -m py_compile odin_linux/app.py
	@echo "✔ Syntax validation passed."

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info

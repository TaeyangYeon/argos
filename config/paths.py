"""
Centralized path management for the Argos vision algorithm design system.

This module provides absolute paths for all project directories and files,
ensuring consistent file system access throughout the application.
"""

from pathlib import Path

# All paths are absolute, derived from this file's location
PROJECT_ROOT = Path(__file__).parent.parent

# Core directories
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Configuration files
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Test directories
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
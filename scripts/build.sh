#!/bin/bash
# Argos Build Script (macOS / Linux)
# Usage: ./scripts/build.sh

set -e

echo "======================================"
echo "  Argos Build Script"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.11+."
    exit 1
fi

PYTHON=python3
echo "Python: $($PYTHON --version)"

# Move to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "Project root: $PROJECT_ROOT"

# Install dependencies
echo ""
echo "Installing dependencies..."
$PYTHON -m pip install -r requirements.txt pyinstaller --quiet

# Generate assets if missing
if [ ! -f "assets/icon.png" ]; then
    echo "Generating placeholder assets..."
    $PYTHON scripts/generate_assets.py
fi

# Run PyInstaller
echo ""
echo "Building with PyInstaller..."
$PYTHON -m PyInstaller argos.spec --noconfirm --clean

# Check output
echo ""
if [ -f "dist/Argos" ] || [ -d "dist/Argos.app" ]; then
    echo "======================================"
    echo "  BUILD SUCCESS"
    echo "======================================"
    echo "Output: dist/"
    ls -la dist/
else
    echo "======================================"
    echo "  BUILD FAILED"
    echo "======================================"
    exit 1
fi

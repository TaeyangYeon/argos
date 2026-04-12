# Argos

AI-powered vision algorithm design agent for automated inspection system development.

## Description

Argos is an intelligent agent that automatically designs vision algorithms for alignment and inspection tasks. It takes OK/NG sample images, ROI specifications, and inspection objectives to generate optimized algorithms with detailed parameters for various vision libraries (Keyence, Cognex, Halcon, MIL).

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Testing

```bash
pytest
```

## Features

- Automated align algorithm design (Pattern Matching, Caliper, Feature-based)
- Inspection algorithm optimization with multi-candidate evaluation
- Library-agnostic parameter output for major vision platforms
- AI-powered feasibility analysis and technology level recommendations
- Modern PyQt6 user interface with dark theme
- Secure local API key storage

## Requirements

- Python 3.11+
- OpenCV
- PyQt6
- NumPy

## Project Structure

```
argos/
├── core/          # Core algorithms and engines
├── ui/            # User interface components
├── config/        # Configuration and settings
├── tests/         # Test suites
├── logs/          # Application logs
└── output/        # Analysis results
```

## Development Status

This project is currently in development. See PROGRESS.md for detailed status.

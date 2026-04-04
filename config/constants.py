"""
Constants for the Argos vision algorithm design system.

This module centralizes all magic numbers and string literals used throughout
the system, following the DRY principle and making configuration changes easier.
"""

# Supported image formats
SUPPORTED_FORMATS = [".bmp", ".png", ".tiff", ".tif", ".jpg", ".jpeg"]

# Image validation
MIN_IMAGE_WIDTH = 64
MIN_IMAGE_HEIGHT = 64
MIN_ROI_AREA_RATIO = 0.01   # ROI must be at least 1% of image area

# SLA thresholds
DEFAULT_SCORE_THRESHOLD = 70.0
DEFAULT_MARGIN_WARNING = 15.0
DEFAULT_W1 = 0.5             # OK pass rate weight
DEFAULT_W2 = 0.5             # NG detect rate weight

# NG sample warnings
NG_MINIMUM_RECOMMENDED = 3
NG_ABSOLUTE_MINIMUM = 1

# AI Provider
AI_TIMEOUT_SECONDS = 30
AI_RETRY_COUNT = 2

# Align strategy names
ALIGN_STRATEGY_PATTERN = "Pattern Matching"
ALIGN_STRATEGY_CALIPER = "Caliper"
ALIGN_STRATEGY_FEATURE = "Feature-based"
ALIGN_STRATEGY_CONTOUR = "Contour-based"
ALIGN_STRATEGY_BLOB = "Blob Detection"

# Feasibility labels
APPROACH_RULE_BASED = "Rule-based"
APPROACH_EDGE_LEARNING = "Edge Learning"
APPROACH_DEEP_LEARNING = "Deep Learning"

# Noise level labels
NOISE_LOW = "Low"
NOISE_MEDIUM = "Medium"
NOISE_HIGH = "High"
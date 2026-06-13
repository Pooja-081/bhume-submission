# BhuMe Engineering Take-Home Submission

## Overview
This project solves a cadastral map alignment problem where official land plot boundaries are slightly shifted from their true positions on satellite imagery.

The goal is to correct these spatial drifts and estimate confidence for each correction.

---

## Approach

### 1. Data Loading
- Loaded village GeoJSON plots using the provided `bhume.load()` utility
- Converted geometries from EPSG:4326 to EPSG:32643 for meter-based computation

### 2. Control Point Extraction
- Used example truth plots to compute displacement vectors
- Built a set of (official centroid → true centroid shift) samples

### 3. Spatial Correction Model
- Applied Inverse Distance Weighting (IDW) interpolation
- Estimated local shift for each plot centroid based on nearby control samples
- Applied shift using Shapely geometry translation

### 4. Confidence Estimation
- Confidence is derived from nearest control distance
- Smooth decay function used to reflect uncertainty:
  - closer control points → higher confidence
  - distant regions → lower confidence

### 5. Output Generation
- Converted geometries back to EPSG:4326
- Generated final predictions.geojson using `write_predictions()`

---

## Key Improvements Over Baseline
- Stabilized IDW interpolation (avoids division instability)
- Smooth confidence calibration instead of fixed thresholds
- Better spatial consistency across plots
- Robust CRS handling

---

## Results (Local Evaluation)
- Median IoU: ~0.999 (on example truths)
- Centroid error: ~0.1 m
- 100% plots improved over baseline

---

## Files
- `improved_v3.py` → main solution script
- `predictions.geojson` → final output
- `transcripts/` → AI-assisted development logs

---

## Tools Used
- Python (GeoPandas, Shapely, NumPy)
- Bhume Starter Kit utilities
- ChatGPT (for debugging and iterative improvement)

---

## Notes
This solution prioritizes:
- Spatial correctness
- Robustness across plots
- Interpretable confidence scoring

Rather than overfitting to example truths, it focuses on generalizable correction logic.

AI tools used:
- ChatGPT for debugging and model improvement
- Iterative development of IDW + hybrid model
- Confidence tuning discussion and fixes

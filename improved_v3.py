import geopandas as gpd
import numpy as np
from shapely.affinity import translate
from pathlib import Path

from bhume import load, score, write_predictions

VILLAGE = "data/34855_vadnerbhairav_chandavad_nashik"

# --------------------------------------------------
# Load data
# --------------------------------------------------

village = load(VILLAGE)

truths = village.example_truths
plots = village.plots

truths_u = truths.to_crs("EPSG:32643")
plots_u = plots.to_crs("EPSG:32643")

# --------------------------------------------------
# Build control points
# --------------------------------------------------

samples = []

for pn in truths_u.index:
    if pn not in plots_u.index:
        continue

    official = plots_u.loc[pn].geometry.centroid
    truth = truths_u.loc[pn].geometry.centroid

    samples.append((
        official.x,
        official.y,
        truth.x - official.x,
        truth.y - official.y
    ))

print(f"Loaded {len(samples)} truth control points")

# --------------------------------------------------
# HYBRID SHIFT MODEL (IDW + GLOBAL + KNN BLEND)
# --------------------------------------------------

def hybrid_shift(x, y, k=5):

    if len(samples) == 0:
        return 0.0, 0.0, float("inf")

    # compute all distances
    dlist = []
    for sx, sy, dx, dy in samples:
        d = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
        dlist.append((d, dx, dy))

    # sort by distance
    dlist.sort(key=lambda z: z[0])
    nearest_dist = dlist[0][0]

    # take k nearest
    nearest = dlist[:k]

    # weights (stable IDW)
    eps = 1e-6
    weights = []
    dxs = []
    dys = []

    for d, dx, dy in nearest:
        d = max(d, 1.0)  # stability floor
        w = 1.0 / ((d + eps) ** 2)

        weights.append(w)
        dxs.append(dx)
        dys.append(dy)

    wsum = sum(weights)

    idw_dx = sum(w * v for w, v in zip(weights, dxs)) / wsum
    idw_dy = sum(w * v for w, v in zip(weights, dys)) / wsum

    # GLOBAL fallback (mean shift)
    all_dx = np.mean([s[2] for s in samples])
    all_dy = np.mean([s[3] for s in samples])

    # adaptive blending
    alpha = np.exp(-nearest_dist / 3000)

    dx = alpha * idw_dx + (1 - alpha) * all_dx
    dy = alpha * idw_dy + (1 - alpha) * all_dy

    return dx, dy, nearest_dist

# --------------------------------------------------
# APPLY MODEL
# --------------------------------------------------

preds = plots_u.copy()

new_geoms = []
confidences = []
statuses = []
notes = []

for geom in preds.geometry:

    c = geom.centroid

    dx, dy, nearest = hybrid_shift(c.x, c.y)

    shifted = translate(geom, xoff=dx, yoff=dy)

    new_geoms.append(shifted)

    # --------------------------------------------------
    # REALISTIC CONFIDENCE MODEL (important for AUC)
    # --------------------------------------------------

    conf = np.exp(-nearest / 2500)
    conf = 1 / (1 + np.exp(-10 * (conf - 0.5)))  # smooth calibration

    if conf < 0.5:
        status = "flagged"
    else:
        status = "corrected"

    confidences.append(conf)
    statuses.append(status)

    notes.append(
        f"HYBRID dx={dx:.2f} dy={dy:.2f} nearest={nearest:.0f}m"
    )

preds["geometry"] = new_geoms

# --------------------------------------------------
# BACK TO WGS84
# --------------------------------------------------

preds = preds.to_crs("EPSG:4326")

preds["status"] = statuses
preds["confidence"] = confidences
preds["method_note"] = notes

preds = preds[
    ["plot_number", "status", "confidence", "method_note", "geometry"]
]

# --------------------------------------------------
# SAVE
# --------------------------------------------------

outfile = write_predictions(
    Path(VILLAGE) / "predictions_hybrid_v3.geojson",
    preds
)

print("\nSaved:", outfile)
print()

print(score(preds, village))
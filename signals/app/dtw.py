"""
Dynamic Time Warping — matches live signal trajectories against historical
pre-crisis windows to find the closest analog.

Pure Python O(n*m) DP implementation. No numpy required.
"""
from __future__ import annotations

import math


def dtw_distance(x: list[float], y: list[float]) -> float:
    """
    Compute DTW distance between two time series.
    Uses Euclidean (L2) point distance with standard DP warping path.
    Returns 0.0 for identical series, higher for more dissimilar.
    """
    n, m = len(x), len(y)
    if n == 0 or m == 0:
        return float("inf")

    cost = [[float("inf")] * (m + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = (x[i - 1] - y[j - 1]) ** 2
            cost[i][j] = d + min(cost[i - 1][j], cost[i][j - 1], cost[i - 1][j - 1])

    return math.sqrt(cost[n][m])


def dtw_distance_normalized(x: list[float], y: list[float]) -> float:
    """DTW distance normalized by path length (max of series lengths)."""
    raw = dtw_distance(x, y)
    path_len = max(len(x), len(y))
    if path_len == 0:
        return float("inf")
    return raw / math.sqrt(path_len)


def find_similar_windows(
    current_window: list[float],
    historical_windows: list[dict],
    top_k: int = 3,
) -> list[dict]:
    """
    Compare a live signal window against stored historical pre-crisis windows.

    Each entry in historical_windows should have:
      - "crisis_name": str
      - "crisis_type": str
      - "region": str
      - "severity_series": list[float]
      - "lag_days": int  (days from peak severity to crisis peak)

    Returns top-k matches sorted by DTW distance (ascending), each with:
      - "crisis_name", "crisis_type", "region", "lag_days"
      - "dtw_distance": float (normalized)
      - "similarity": float  (1 / (1 + dtw_distance), range 0–1)
    """
    if not current_window or not historical_windows:
        return []

    scored: list[dict] = []
    for hw in historical_windows:
        series = hw.get("severity_series", [])
        if not series:
            continue
        dist = dtw_distance_normalized(current_window, series)
        scored.append({
            "crisis_name": hw["crisis_name"],
            "crisis_type": hw["crisis_type"],
            "region": hw["region"],
            "lag_days": hw.get("lag_days", 0),
            "dtw_distance": round(dist, 4),
            "similarity": round(1.0 / (1.0 + dist), 4),
        })

    scored.sort(key=lambda m: m["dtw_distance"])
    return scored[:top_k]

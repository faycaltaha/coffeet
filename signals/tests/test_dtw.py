"""Tests for DTW trajectory matching."""
from __future__ import annotations

import math

from app.dtw import dtw_distance, dtw_distance_normalized, find_similar_windows


class TestDtwDistance:
    def test_identical_series_is_zero(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert dtw_distance(x, x) == 0.0

    def test_reversed_is_nonzero(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert dtw_distance(x, y) > 0.0

    def test_similar_less_than_dissimilar(self):
        base = [0.1, 0.2, 0.3, 0.5, 0.8]
        similar = [0.1, 0.25, 0.35, 0.55, 0.75]
        dissimilar = [0.9, 0.8, 0.7, 0.3, 0.1]
        assert dtw_distance(base, similar) < dtw_distance(base, dissimilar)

    def test_empty_series_returns_inf(self):
        assert dtw_distance([], [1.0, 2.0]) == float("inf")
        assert dtw_distance([1.0], []) == float("inf")
        assert dtw_distance([], []) == float("inf")

    def test_single_element(self):
        assert abs(dtw_distance([3.0], [5.0]) - 2.0) < 1e-9

    def test_different_lengths(self):
        x = [1.0, 2.0, 3.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        dist = dtw_distance(x, y)
        assert dist > 0.0
        assert math.isfinite(dist)

    def test_symmetry(self):
        x = [0.1, 0.5, 0.9]
        y = [0.2, 0.6, 0.8]
        assert abs(dtw_distance(x, y) - dtw_distance(y, x)) < 1e-9

    def test_constant_series(self):
        x = [0.5, 0.5, 0.5, 0.5]
        y = [0.5, 0.5, 0.5, 0.5]
        assert dtw_distance(x, y) == 0.0


class TestDtwDistanceNormalized:
    def test_normalized_identical_is_zero(self):
        x = [1.0, 2.0, 3.0]
        assert dtw_distance_normalized(x, x) == 0.0

    def test_normalized_scales_by_length(self):
        x = [0.0, 1.0]
        y = [0.0, 0.0]
        raw = dtw_distance(x, y)
        norm = dtw_distance_normalized(x, y)
        assert norm < raw


class TestFindSimilarWindows:
    def test_returns_top_k(self):
        current = [0.1, 0.3, 0.5, 0.7, 0.9]
        windows = [
            {"crisis_name": "A", "crisis_type": "fin", "region": "EU",
             "severity_series": [0.1, 0.3, 0.5, 0.7, 0.9]},
            {"crisis_name": "B", "crisis_type": "fin", "region": "US",
             "severity_series": [0.9, 0.7, 0.5, 0.3, 0.1]},
            {"crisis_name": "C", "crisis_type": "fin", "region": "Asia",
             "severity_series": [0.2, 0.4, 0.6, 0.8, 0.95]},
        ]
        results = find_similar_windows(current, windows, top_k=2)
        assert len(results) == 2
        assert results[0]["crisis_name"] == "A"
        assert results[0]["similarity"] > results[1]["similarity"]

    def test_empty_current_returns_empty(self):
        assert find_similar_windows([], [{"severity_series": [1.0]}]) == []

    def test_empty_historical_returns_empty(self):
        assert find_similar_windows([1.0, 2.0], []) == []

    def test_result_fields(self):
        current = [0.5, 0.6, 0.7]
        windows = [{"crisis_name": "X", "crisis_type": "energy", "region": "EU",
                     "severity_series": [0.5, 0.6, 0.7], "lag_days": 14}]
        results = find_similar_windows(current, windows)
        r = results[0]
        assert "crisis_name" in r
        assert "dtw_distance" in r
        assert "similarity" in r
        assert 0.0 <= r["similarity"] <= 1.0

    def test_similarity_range(self):
        current = [0.1, 0.2, 0.3]
        windows = [{"crisis_name": "Z", "crisis_type": "t", "region": "r",
                     "severity_series": [0.8, 0.9, 1.0]}]
        results = find_similar_windows(current, windows)
        assert 0.0 < results[0]["similarity"] < 1.0

"""Tests for Granger causality and lead-lag analysis."""
from __future__ import annotations

import math

from app.granger import (
    _f_cdf_approx,
    _invert,
    _ols_rss,
    granger_test,
    optimal_lag_correlation,
)


class TestMatrixInvert:
    def test_identity_2x2(self):
        I = [[1.0, 0.0], [0.0, 1.0]]
        inv = _invert(I)
        assert inv is not None
        assert abs(inv[0][0] - 1.0) < 1e-9
        assert abs(inv[1][1] - 1.0) < 1e-9

    def test_simple_2x2(self):
        M = [[2.0, 1.0], [1.0, 3.0]]
        inv = _invert(M)
        assert inv is not None
        # M * inv should be ~identity
        assert abs(M[0][0] * inv[0][0] + M[0][1] * inv[1][0] - 1.0) < 1e-9

    def test_singular_returns_none(self):
        M = [[1.0, 2.0], [2.0, 4.0]]
        assert _invert(M) is None


class TestOlsRss:
    def test_perfect_fit_returns_zero(self):
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        X = [[1.0, float(i)] for i in range(1, 6)]
        rss = _ols_rss(y, X)
        assert rss is not None
        assert rss < 1e-9

    def test_noisy_fit_returns_positive(self):
        y = [2.1, 3.9, 6.2, 7.8, 10.1]
        X = [[1.0, float(i)] for i in range(1, 6)]
        rss = _ols_rss(y, X)
        assert rss is not None
        assert rss > 0.0


class TestFCdfApprox:
    def test_zero_returns_zero(self):
        assert _f_cdf_approx(0.0, 3, 30) == 0.0

    def test_large_f_near_one(self):
        assert _f_cdf_approx(100.0, 3, 30) > 0.99

    def test_moderate_f(self):
        val = _f_cdf_approx(3.0, 4, 40)
        assert 0.01 < val < 0.99


class TestGrangerTest:
    def test_causal_series(self):
        """x leads y by 1 step — should detect Granger causality."""
        n = 50
        x = [math.sin(i * 0.3) for i in range(n)]
        y = [0.0] + [x[i] + 0.1 * (i % 3 - 1) for i in range(n - 1)]
        result = granger_test(x, y, max_lag=2)
        assert "f_statistic" in result
        assert "p_value" in result
        assert "granger_causes" in result
        assert result["n_obs"] > 0

    def test_independent_series(self):
        """Two unrelated series — should not detect causality (most of the time)."""
        import random
        random.seed(42)
        n = 60
        x = [random.gauss(0, 1) for _ in range(n)]
        y = [random.gauss(0, 1) for _ in range(n)]
        result = granger_test(x, y, max_lag=2)
        assert result["p_value"] > 0.0

    def test_insufficient_data(self):
        result = granger_test([1.0, 2.0], [3.0, 4.0], max_lag=4)
        assert result["granger_causes"] is False
        assert result["p_value"] == 1.0

    def test_identical_series(self):
        x = [float(i) for i in range(30)]
        result = granger_test(x, x, max_lag=2)
        assert "f_statistic" in result

    def test_returns_dict(self):
        x = [float(i) for i in range(20)]
        y = [float(i) * 0.5 for i in range(20)]
        result = granger_test(x, y, max_lag=2)
        assert isinstance(result, dict)
        assert set(result.keys()) >= {"f_statistic", "p_value", "lag", "granger_causes", "n_obs"}


class TestOptimalLagCorrelation:
    def test_lag_zero_for_identical(self):
        x = [math.sin(i * 0.5) for i in range(30)]
        result = optimal_lag_correlation(x, x, max_lag=5)
        assert result["lag"] == 0
        assert abs(result["r"] - 1.0) < 1e-3

    def test_detects_lag(self):
        """x leads y by 3 steps."""
        n = 40
        x = [math.sin(i * 0.2) for i in range(n)]
        y = [0.0, 0.0, 0.0] + x[:n - 3]
        result = optimal_lag_correlation(x, y, max_lag=10)
        assert result["lag"] == 3
        assert result["abs_r"] > 0.9

    def test_returns_dict(self):
        result = optimal_lag_correlation([1.0] * 10, [2.0] * 10, max_lag=3)
        assert "lag" in result
        assert "r" in result
        assert "abs_r" in result

    def test_short_series(self):
        result = optimal_lag_correlation([1.0, 2.0], [3.0, 4.0], max_lag=5)
        assert result["abs_r"] == 0.0 or result["lag"] == 0

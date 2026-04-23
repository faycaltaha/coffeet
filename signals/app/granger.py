"""
Granger causality testing — determines whether one signal category
statistically predicts another (or a crisis proxy) beyond its own history.

Pure Python implementation using OLS via normal equations.
No numpy/scipy required.
"""
from __future__ import annotations

import math


def _dot(a: list[float], b: list[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def _mat_vec(M: list[list[float]], v: list[float]) -> list[float]:
    return [_dot(row, v) for row in M]


def _transpose(M: list[list[float]]) -> list[list[float]]:
    if not M:
        return []
    rows, cols = len(M), len(M[0])
    return [[M[r][c] for r in range(rows)] for c in range(cols)]


def _mat_mul(A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
    rows_a, cols_b = len(A), len(B[0])
    cols_a = len(A[0])
    result = [[0.0] * cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += A[i][k] * B[k][j]
    return result


def _invert(M: list[list[float]]) -> list[list[float]] | None:
    """Invert a square matrix via Gauss-Jordan elimination. Returns None if singular."""
    n = len(M)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(M)]

    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        for j in range(2 * n):
            aug[col][j] /= scale
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(2 * n):
                aug[row][j] -= factor * aug[col][j]

    return [row[n:] for row in aug]


def _ols_rss(y: list[float], X: list[list[float]]) -> float | None:
    """Fit OLS: y = X @ beta + e. Return residual sum of squares."""
    Xt = _transpose(X)
    XtX = _mat_mul(Xt, X)
    XtX_inv = _invert(XtX)
    if XtX_inv is None:
        return None
    Xty = _mat_vec(Xt, y)
    beta = _mat_vec(XtX_inv, Xty)
    y_hat = _mat_vec(X, beta)
    return sum((yi - yhi) ** 2 for yi, yhi in zip(y, y_hat))


def _f_cdf_approx(f_val: float, df1: int, df2: int) -> float:
    """
    Approximate CDF of F-distribution using the normal approximation
    (Fisher's z-transform). Good enough for df2 > 10.
    """
    if f_val <= 0:
        return 0.0
    z = (
        (1.0 - 2.0 / (9 * df2)) * (f_val * df1 / df2) ** (1.0 / 3)
        - (1.0 - 2.0 / (9 * df1))
    ) / math.sqrt(2.0 / (9 * df1) + 2.0 / (9 * df2) * (f_val * df1 / df2) ** (2.0 / 3))
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def granger_test(
    x: list[float],
    y: list[float],
    max_lag: int = 4,
) -> dict:
    """
    Test whether x Granger-causes y.

    Restricted model:  y(t) = a0 + a1*y(t-1) + ... + ap*y(t-p)
    Unrestricted model: y(t) = a0 + a1*y(t-1) + ... + ap*y(t-p)
                                   + b1*x(t-1) + ... + bp*x(t-p)

    Returns {
        "f_statistic": float,
        "p_value": float,
        "lag": int,
        "granger_causes": bool,  (p < 0.10)
        "n_obs": int,
    }
    Returns None if insufficient data or singular matrix.
    """
    n = len(x)
    if n != len(y) or n < max_lag + max_lag + 2:
        return {"f_statistic": 0.0, "p_value": 1.0, "lag": max_lag,
                "granger_causes": False, "n_obs": n}

    T = n - max_lag
    y_dep = y[max_lag:]

    X_restricted: list[list[float]] = []
    X_unrestricted: list[list[float]] = []

    for t in range(max_lag, n):
        row_r = [1.0]  # intercept
        row_u = [1.0]
        for lag in range(1, max_lag + 1):
            row_r.append(y[t - lag])
            row_u.append(y[t - lag])
        for lag in range(1, max_lag + 1):
            row_u.append(x[t - lag])
        X_restricted.append(row_r)
        X_unrestricted.append(row_u)

    rss_r = _ols_rss(y_dep, X_restricted)
    rss_u = _ols_rss(y_dep, X_unrestricted)

    if rss_r is None or rss_u is None or rss_u < 1e-15:
        return {"f_statistic": 0.0, "p_value": 1.0, "lag": max_lag,
                "granger_causes": False, "n_obs": T}

    df1 = max_lag
    df2 = T - 2 * max_lag - 1
    if df2 < 1:
        return {"f_statistic": 0.0, "p_value": 1.0, "lag": max_lag,
                "granger_causes": False, "n_obs": T}

    f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)
    p_value = 1.0 - _f_cdf_approx(f_stat, df1, df2)
    p_value = max(0.0, min(1.0, p_value))

    return {
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_value, 4),
        "lag": max_lag,
        "granger_causes": p_value < 0.10,
        "n_obs": T,
    }


def optimal_lag_correlation(
    x: list[float],
    y: list[float],
    max_lag: int = 30,
) -> dict:
    """
    Find the lag k (in data points) that maximizes |Pearson r| between
    x(t-k) and y(t). Useful for determining optimal lead time.

    Returns {"lag": int, "r": float, "abs_r": float}
    """
    n = min(len(x), len(y))
    best = {"lag": 0, "r": 0.0, "abs_r": 0.0}

    for k in range(0, min(max_lag + 1, n - 5)):
        x_lagged = x[:n - k] if k > 0 else x[:n]
        y_target = y[k:n] if k > 0 else y[:n]
        m = len(x_lagged)
        if m < 5:
            break
        mx = sum(x_lagged) / m
        my = sum(y_target) / m
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x_lagged, y_target))
        den_x = math.sqrt(sum((xi - mx) ** 2 for xi in x_lagged))
        den_y = math.sqrt(sum((yi - my) ** 2 for yi in y_target))
        if den_x < 1e-12 or den_y < 1e-12:
            continue
        r = num / (den_x * den_y)
        if abs(r) > best["abs_r"]:
            best = {"lag": k, "r": round(r, 4), "abs_r": round(abs(r), 4)}

    return best

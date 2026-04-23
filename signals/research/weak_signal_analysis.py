"""
Weak Signal Analysis — Historical Pre-Crisis Pattern Study

Runs DTW, Granger causality, and lead-time analysis on synthetic signal data
derived from known historical crisis precursors. Generates 5 PNG charts.

Usage:
    cd signals/
    python -m research.weak_signal_analysis
"""
from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from app.dtw import dtw_distance_normalized, find_similar_windows
from app.granger import granger_test, optimal_lag_correlation

OUT_DIR = Path(__file__).parent / "charts"
OUT_DIR.mkdir(exist_ok=True)

random.seed(42)
np.random.seed(42)

# ── Palette ───────────────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    "geopolitical": "#e74c3c",
    "energy":       "#e67e22",
    "financial":    "#3498db",
    "economic":     "#2ecc71",
    "humanitarian": "#9b59b6",
    "news":         "#95a5a6",
    "supply_chain": "#1abc9c",
    "trade":        "#f39c12",
    "seismic":      "#c0392b",
    "climate":      "#27ae60",
    "conflict":     "#8e44ad",
}

CRISIS_COLORS = {
    "geopolitical":  "#e74c3c",
    "financial":     "#3498db",
    "energy":        "#e67e22",
    "supply_chain":  "#1abc9c",
    "natural_disaster": "#27ae60",
}

# ── Synthetic pre-crisis signal profiles ─────────────────────────────────────
#
# Each entry describes what signal categories elevated (and when, relative to
# crisis onset at day 0). Severity in 0-1. Based on public post-mortems.

CRISIS_PRECURSORS = [
    {
        "name": "2007-2009 Financial Crisis",
        "type": "financial",
        "region": "Global",
        "impact_score": 10.0,
        "lead_days": 90,
        "signals": {
            "financial":    {"start": -90, "peak": -30, "peak_severity": 0.9, "noise": 0.08},
            "economic":     {"start": -75, "peak": -45, "peak_severity": 0.7, "noise": 0.06},
            "news":         {"start": -60, "peak": -20, "peak_severity": 0.6, "noise": 0.10},
            "trade":        {"start": -45, "peak": -15, "peak_severity": 0.5, "noise": 0.07},
        },
        "annotation": "Credit default swaps & housing indicators\nrose 60-90 days before Lehman collapse",
    },
    {
        "name": "2022 Russia-Ukraine War",
        "type": "geopolitical",
        "region": "Europe",
        "impact_score": 9.5,
        "lead_days": 90,
        "signals": {
            "geopolitical": {"start": -90, "peak": -7,  "peak_severity": 0.95, "noise": 0.07},
            "energy":       {"start": -60, "peak": -14, "peak_severity": 0.80, "noise": 0.06},
            "news":         {"start": -45, "peak": -5,  "peak_severity": 0.75, "noise": 0.10},
            "conflict":     {"start": -30, "peak": -3,  "peak_severity": 0.90, "noise": 0.05},
            "economic":     {"start": -21, "peak": -7,  "peak_severity": 0.55, "noise": 0.08},
        },
        "annotation": "Military buildup & ACLED conflict events\nbegan escalating 90 days before invasion",
    },
    {
        "name": "2020 COVID Supply Chain",
        "type": "supply_chain",
        "region": "Global",
        "impact_score": 10.0,
        "lead_days": 60,
        "signals": {
            "news":         {"start": -60, "peak": -20, "peak_severity": 0.70, "noise": 0.09},
            "humanitarian": {"start": -45, "peak": -14, "peak_severity": 0.80, "noise": 0.07},
            "supply_chain": {"start": -30, "peak": -7,  "peak_severity": 0.90, "noise": 0.06},
            "financial":    {"start": -25, "peak": -10, "peak_severity": 0.75, "noise": 0.08},
            "trade":        {"start": -21, "peak": -7,  "peak_severity": 0.65, "noise": 0.07},
        },
        "annotation": "ReliefWeb & RSS news spikes preceded\nfactory shutdown cascade by ~30 days",
    },
    {
        "name": "2022 European Energy Crisis",
        "type": "energy",
        "region": "Europe",
        "impact_score": 8.5,
        "lead_days": 90,
        "signals": {
            "energy":       {"start": -90, "peak": -14, "peak_severity": 0.95, "noise": 0.05},
            "geopolitical": {"start": -80, "peak": -30, "peak_severity": 0.75, "noise": 0.07},
            "financial":    {"start": -45, "peak": -21, "peak_severity": 0.65, "noise": 0.09},
            "economic":     {"start": -30, "peak": -14, "peak_severity": 0.60, "noise": 0.08},
        },
        "annotation": "EIA gas storage & Nord Stream flows showed\nabnormal depletion 90 days before crisis peak",
    },
    {
        "name": "2023 Red Sea Shipping Crisis",
        "type": "supply_chain",
        "region": "Middle East",
        "impact_score": 7.0,
        "lead_days": 45,
        "signals": {
            "geopolitical": {"start": -45, "peak": -10, "peak_severity": 0.80, "noise": 0.06},
            "conflict":     {"start": -35, "peak": -7,  "peak_severity": 0.85, "noise": 0.05},
            "supply_chain": {"start": -21, "peak": -5,  "peak_severity": 0.88, "noise": 0.06},
            "news":         {"start": -30, "peak": -3,  "peak_severity": 0.70, "noise": 0.08},
            "trade":        {"start": -14, "peak": -2,  "peak_severity": 0.60, "noise": 0.07},
        },
        "annotation": "ACLED Houthi attacks preceded AIS anomalies\n& shipping cost surge by 2-3 weeks",
    },
    {
        "name": "2022 Sri Lanka Financial Collapse",
        "type": "financial",
        "region": "South Asia",
        "impact_score": 7.0,
        "lead_days": 90,
        "signals": {
            "economic":     {"start": -90, "peak": -30, "peak_severity": 0.80, "noise": 0.06},
            "financial":    {"start": -75, "peak": -21, "peak_severity": 0.85, "noise": 0.07},
            "humanitarian": {"start": -45, "peak": -14, "peak_severity": 0.75, "noise": 0.08},
            "news":         {"start": -30, "peak": -7,  "peak_severity": 0.65, "noise": 0.09},
            "trade":        {"start": -60, "peak": -35, "peak_severity": 0.55, "noise": 0.07},
        },
        "annotation": "IMF debt indicators & currency depreciation\nformed 90-day warning window",
    },
]


def _build_signal_series(start_day: int, peak_day: int, peak_severity: float,
                          noise: float, n_days: int = 90) -> np.ndarray:
    """Asymmetric Gaussian-shaped signal ramp with additive noise."""
    days = np.arange(-n_days, 1)
    center = peak_day
    sigma_left = abs(center - start_day) / 2.5
    sigma_right = abs(center) / 1.5
    series = np.zeros(n_days + 1)
    for i, d in enumerate(days):
        if d < start_day:
            series[i] = 0.02 * peak_severity
        elif d <= center:
            sigma = sigma_left if sigma_left > 0 else 1
            series[i] = peak_severity * math.exp(-((d - center) ** 2) / (2 * sigma ** 2))
        else:
            sigma = sigma_right if sigma_right > 0 else 1
            series[i] = peak_severity * math.exp(-((d - center) ** 2) / (2 * sigma ** 2))
        series[i] = max(0.0, min(1.0, series[i] + np.random.normal(0, noise)))
    return series


# ── Chart 1: Pre-crisis signal timelines ─────────────────────────────────────

def chart_precursor_timelines():
    n = len(CRISIS_PRECURSORS)
    fig, axes = plt.subplots(n, 1, figsize=(14, n * 2.8))
    fig.suptitle("Weak Signal Patterns Before Historical Crises\n"
                 "(synthetic daily severity, 0-1 scale, t=0 = crisis onset)",
                 fontsize=13, fontweight="bold", y=0.99)

    for ax, crisis in zip(axes, CRISIS_PRECURSORS):
        days = np.arange(-crisis["lead_days"], 1)
        for cat, params in crisis["signals"].items():
            series = _build_signal_series(
                params["start"], params["peak"], params["peak_severity"],
                params["noise"], n_days=crisis["lead_days"],
            )
            ax.plot(days, series, label=cat, color=CATEGORY_COLORS.get(cat, "#555"),
                    linewidth=1.8, alpha=0.85)

        ax.axvline(0, color="#c0392b", linewidth=1.2, linestyle="--", alpha=0.7)
        ax.fill_betweenx([0, 1], -14, 0, alpha=0.06, color="#c0392b")
        ax.set_xlim(-crisis["lead_days"], 8)
        ax.set_ylim(-0.02, 1.05)
        ax.set_title(f"{crisis['name']}  (impact score: {crisis['impact_score']}/10)",
                     fontsize=9.5, fontweight="bold", loc="left")
        ax.annotate(crisis["annotation"], xy=(0.97, 0.72), xycoords="axes fraction",
                    ha="right", va="top", fontsize=7.5, color="#555",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))
        ax.set_ylabel("Severity", fontsize=8)
        ax.legend(fontsize=7, loc="upper left", ncol=3, framealpha=0.5)
        ax.tick_params(labelsize=8)
        if ax != axes[-1]:
            ax.set_xticklabels([])

    axes[-1].set_xlabel("Days before crisis onset", fontsize=9)
    plt.tight_layout(rect=[0, 0, 1, 0.975])
    out = OUT_DIR / "1_precursor_timelines.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ── Chart 2: DTW similarity matrix ───────────────────────────────────────────

def chart_dtw_similarity_matrix():
    """How similar are pre-crisis signal trajectories across different crises?"""
    # Build 30-day composite severity windows per crisis (aggregate all categories)
    windows = []
    for crisis in CRISIS_PRECURSORS:
        n = 30
        composite = np.zeros(n + 1)
        for params in crisis["signals"].values():
            s = _build_signal_series(params["start"], params["peak"],
                                     params["peak_severity"], params["noise"], n_days=n)
            composite += s
        composite = np.clip(composite / len(crisis["signals"]), 0, 1)
        windows.append(composite.tolist())

    names = [c["name"].replace("20", "'").replace(" / ", "/") for c in CRISIS_PRECURSORS]
    n = len(windows)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            d = dtw_distance_normalized(windows[i], windows[j])
            matrix[i][j] = 1.0 / (1.0 + d)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0.4, vmax=1.0)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8.5)
    ax.set_yticklabels(names, fontsize=8.5)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center",
                    fontsize=8, color="black" if matrix[i][j] < 0.75 else "white",
                    fontweight="bold" if i == j else "normal")
    plt.colorbar(im, ax=ax, shrink=0.7, label="DTW Similarity (1 = identical trajectory)")
    ax.set_title("DTW Trajectory Similarity Matrix\n"
                 "30-day pre-crisis composite signal windows",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    out = OUT_DIR / "2_dtw_similarity_matrix.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ── Chart 3: Granger causality between signal categories ─────────────────────

def chart_granger_causality():
    """
    Leading indicator analysis: for each crisis, compute the cross-correlation
    between each early-warning signal category and the primary outcome signal.
    Shows (1) peak correlation strength and (2) optimal lead time (days ahead).
    This replaces raw Granger p-values, which are uninformative on smooth
    synthetic ramps due to shared autoregressive structure.
    """
    crisis_names_short = [
        "Financial\nCrisis '08",
        "Russia-\nUkraine War",
        "COVID\nSupply Chain",
        "EU Energy\nCrisis",
        "Red Sea\nShipping",
        "Sri Lanka\nCollapse",
    ]

    # Collect all cause categories
    all_causes_order: list[str] = []
    for crisis in CRISIS_PRECURSORS:
        for c in crisis["signals"]:
            if c not in all_causes_order:
                all_causes_order.append(c)

    n_crises = len(CRISIS_PRECURSORS)
    n_cats = len(all_causes_order)

    corr_matrix = np.full((n_crises, n_cats), np.nan)   # peak |r| values
    lead_matrix = np.full((n_crises, n_cats), np.nan)   # optimal lead days

    for ci, crisis in enumerate(CRISIS_PRECURSORS):
        n_days = crisis["lead_days"]
        primary = max(crisis["signals"], key=lambda c: crisis["signals"][c]["peak_severity"])
        pp = crisis["signals"][primary]
        outcome = _build_signal_series(pp["start"], pp["peak"], pp["peak_severity"], 0.01, n_days=n_days)

        for ji, cat in enumerate(all_causes_order):
            if cat not in crisis["signals"] or cat == primary:
                continue
            p = crisis["signals"][cat]
            series = _build_signal_series(p["start"], p["peak"], p["peak_severity"], 0.01, n_days=n_days)
            lag_result = optimal_lag_correlation(series.tolist(), outcome.tolist(),
                                                  max_lag=min(45, n_days // 2))
            corr_matrix[ci, ji] = lag_result["abs_r"]
            lead_matrix[ci, ji] = lag_result["lag"]

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

    # Left: correlation strength heatmap
    ax = axes[0]
    masked_corr = np.ma.masked_invalid(corr_matrix)
    cmap = plt.cm.YlOrRd.copy()
    cmap.set_bad("#eeeeee")
    im = ax.imshow(masked_corr, cmap=cmap, vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(n_cats))
    ax.set_xticklabels([c.replace("_", "\n") for c in all_causes_order], fontsize=8.5)
    ax.set_yticks(range(n_crises))
    ax.set_yticklabels(crisis_names_short, fontsize=8.5)
    ax.set_title("Predictive Correlation Strength (|r|)\nBetween early signal and primary outcome",
                 fontsize=10, fontweight="bold")
    ax.set_xlabel("Signal category (leading indicator)", fontsize=9)
    ax.set_ylabel("Crisis", fontsize=9)

    for i in range(n_crises):
        for j in range(n_cats):
            if not np.isnan(corr_matrix[i, j]):
                r = corr_matrix[i, j]
                lag = int(lead_matrix[i, j])
                ax.text(j, i, f"{r:.2f}\n+{lag}d", ha="center", va="center", fontsize=7.5,
                        color="white" if r > 0.70 else "black", fontweight="bold" if r > 0.80 else "normal")
            else:
                ax.text(j, i, "—", ha="center", va="center", fontsize=9, color="#bbb")

    plt.colorbar(im, ax=ax, shrink=0.8, label="|Pearson r| at optimal lag")

    # Right: average lead time per category across crises (bubble size = avg |r|)
    ax2 = axes[1]
    cat_leads = []
    cat_corrs = []
    cat_counts = []
    for j, cat in enumerate(all_causes_order):
        vals = [(lead_matrix[i, j], corr_matrix[i, j])
                for i in range(n_crises) if not np.isnan(lead_matrix[i, j])]
        if vals:
            avg_lead = np.mean([v[0] for v in vals])
            avg_corr = np.mean([v[1] for v in vals])
            cat_leads.append(avg_lead)
            cat_corrs.append(avg_corr)
            cat_counts.append(len(vals))
        else:
            cat_leads.append(0)
            cat_corrs.append(0)
            cat_counts.append(0)

    xpos = np.arange(n_cats)
    bar_colors = [CATEGORY_COLORS.get(c, "#888") for c in all_causes_order]
    bars = ax2.bar(xpos, cat_leads, color=bar_colors, alpha=0.85, edgecolor="white")

    # Overlay correlation dots
    ax2b = ax2.twinx()
    ax2b.scatter(xpos, cat_corrs, s=[c * 80 for c in cat_counts],
                 color=[CATEGORY_COLORS.get(c, "#555") for c in all_causes_order],
                 edgecolors="white", linewidths=1.5, zorder=5, alpha=0.9)
    ax2b.set_ylim(0, 1.2)
    ax2b.set_ylabel("Avg |r| correlation (●, size = # crises observed)", fontsize=8.5, color="#555")
    ax2b.tick_params(axis="y", labelcolor="#555")

    ax2.set_xticks(xpos)
    ax2.set_xticklabels([c.replace("_", "\n") for c in all_causes_order], fontsize=8.5)
    ax2.set_ylabel("Avg lead time ahead of primary outcome (days)", fontsize=9)
    ax2.set_title("Leading Indicator Summary\nAvg lead time (bars) & avg |r| correlation (dots)",
                  fontsize=10, fontweight="bold")

    for bar, lead in zip(bars, cat_leads):
        if lead > 0:
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                     f"{lead:.0f}d", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    out = OUT_DIR / "3_leading_indicators.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ── Chart 4: Optimal lead times per crisis type ───────────────────────────────

def chart_lead_times():
    """How many days before a crisis do each signal type show peak correlation?"""
    lead_data: dict[str, dict[str, int]] = {}

    for crisis in CRISIS_PRECURSORS:
        crisis_type = crisis["type"]
        n_days = crisis["lead_days"]
        cats = list(crisis["signals"].keys())
        if len(cats) < 2:
            continue

        # Use the first category as the "crisis proxy" (highest impact)
        proxy_cat = max(cats, key=lambda c: crisis["signals"][c]["peak_severity"])
        proxy_params = crisis["signals"][proxy_cat]
        proxy = _build_signal_series(proxy_params["start"], proxy_params["peak"],
                                      proxy_params["peak_severity"], 0.02, n_days=n_days)

        leads: dict[str, int] = {}
        for cat, params in crisis["signals"].items():
            if cat == proxy_cat:
                continue
            series = _build_signal_series(params["start"], params["peak"],
                                           params["peak_severity"], 0.02, n_days=n_days)
            lag_result = optimal_lag_correlation(series.tolist(), proxy.tolist(), max_lag=min(45, n_days // 2))
            leads[cat] = lag_result["lag"]

        lead_data[crisis["name"]] = leads

    fig, ax = plt.subplots(figsize=(13, 6))
    crises_list = list(lead_data.keys())
    n_crises = len(crises_list)
    all_cats = sorted({cat for leads in lead_data.values() for cat in leads})
    x = np.arange(n_crises)
    width = 0.8 / max(len(all_cats), 1)

    for i, cat in enumerate(all_cats):
        vals = [lead_data[c].get(cat, 0) for c in crises_list]
        offset = (i - len(all_cats) / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width * 0.9,
                       label=cat, color=CATEGORY_COLORS.get(cat, "#888"), alpha=0.82)

    ax.set_xticks(x)
    ax.set_xticklabels([c["name"] for c in CRISIS_PRECURSORS if c["name"] in crises_list],
                        rotation=20, ha="right", fontsize=8.5)
    ax.set_ylabel("Optimal lead time (days)", fontsize=10)
    ax.set_title("Optimal Signal Lead Times Before Each Crisis Type\n"
                 "(how many days before the crisis proxy does each signal category peak?)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right", ncol=3)
    ax.axhline(7, color="red", linestyle="--", linewidth=0.8, alpha=0.6, label="_7-day horizon")
    ax.axhline(30, color="orange", linestyle="--", linewidth=0.8, alpha=0.6, label="_30-day horizon")
    ax.annotate("7d", xy=(n_crises - 0.5, 8), fontsize=7.5, color="red")
    ax.annotate("30d", xy=(n_crises - 0.5, 31), fontsize=7.5, color="orange")
    plt.tight_layout()
    out = OUT_DIR / "4_lead_times.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ── Chart 5: Risk score decomposition ─────────────────────────────────────────

def chart_risk_decomposition():
    """Break down the v2 composite risk score for a simulated 'active' region."""
    from app.risk_engine import _compute_risk_score, _classify_alert_tier, _lead_time_probability

    # Simulate 3 regions at different alert stages
    scenarios = [
        {
            "label": "Europe (Energy Crisis\nRe-escalation)",
            "z_scores": {"energy": 3.2, "geopolitical": 2.1, "economic": 1.4},
            "dtw_similarity": 0.78,
            "granger_confidence": 0.82,
            "correlation_strength": 0.71,
            "lag_samples": [12, 18, 21, 14, 9, 7, 25, 30, 16],
        },
        {
            "label": "Middle East (Conflict\nShipping Risk)",
            "z_scores": {"conflict": 2.8, "geopolitical": 2.4, "supply_chain": 1.9, "news": 1.3},
            "dtw_similarity": 0.65,
            "granger_confidence": 0.61,
            "correlation_strength": 0.58,
            "lag_samples": [7, 14, 21, 5, 9, 12, 30, 45],
        },
        {
            "label": "South Asia (Debt\nStress Early Warning)",
            "z_scores": {"financial": 1.6, "economic": 1.2},
            "dtw_similarity": 0.42,
            "granger_confidence": 0.35,
            "correlation_strength": 0.44,
            "lag_samples": [30, 45, 60, 75, 90, 50, 35],
        },
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    fig.suptitle("v2 Risk Score Decomposition by Region\n"
                 "Component weights: z-score 35% | DTW 25% | Granger 20% | Correlation 20%",
                 fontsize=11, fontweight="bold")

    comp_colors = ["#e74c3c", "#3498db", "#2ecc71", "#e67e22"]
    comp_names = ["Z-score\nelevation\n(35%)", "DTW\nsimilarity\n(25%)",
                  "Granger\nconfidence\n(20%)", "Corr.\nstrength\n(20%)"]

    for ax, sc in zip(axes, scenarios):
        score, conf_low, conf_high = _compute_risk_score(
            sc["z_scores"], sc["dtw_similarity"],
            sc["granger_confidence"], sc["correlation_strength"]
        )
        p_7d = _lead_time_probability(sc["lag_samples"], 7)
        p_30d = _lead_time_probability(sc["lag_samples"], 30)
        p_90d = _lead_time_probability(sc["lag_samples"], 90)
        tier = _classify_alert_tier(p_7d, p_30d, p_90d)

        # Compute component values
        from statistics import mean
        elevated = [z for z in sc["z_scores"].values() if z >= 1.0]
        z_comp = min(1.0, mean(elevated) / 4.0) if elevated else 0.0
        components = [
            z_comp * 0.35 * 100,
            sc["dtw_similarity"] * 0.25 * 100,
            sc["granger_confidence"] * 0.20 * 100,
            min(1.0, sc["correlation_strength"]) * 0.20 * 100,
        ]

        bars = ax.barh(comp_names, components, color=comp_colors, alpha=0.82, height=0.55)
        ax.set_xlim(0, 35)
        for bar, val in zip(bars, components):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", fontsize=9, fontweight="bold")

        tier_colors = {"critical": "#c0392b", "warning": "#e67e22",
                       "watch": "#f1c40f", "informational": "#3498db", "none": "#95a5a6"}
        tc = tier_colors.get(tier, "#555")

        ax.set_title(f"{sc['label']}\n"
                     f"Risk Score: {score:.0f}  [{conf_low:.0f}–{conf_high:.0f}]",
                     fontsize=9.5, fontweight="bold")
        ax.set_xlabel("Score contribution (out of 100)", fontsize=8.5)

        # Annotate probabilities
        prob_text = (f"P(7d): {p_7d:.0%}  P(30d): {p_30d:.0%}  P(90d): {p_90d:.0%}\n"
                     f"Alert tier: {tier.upper()}")
        ax.text(0.5, -0.22, prob_text, transform=ax.transAxes, ha="center",
                fontsize=8.5, color=tc, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=tc, alpha=0.12))

        ax.tick_params(axis="y", labelsize=8.5)

    plt.tight_layout(rect=[0, 0.02, 1, 0.93])
    out = OUT_DIR / "5_risk_decomposition.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ── Chart 6: Signal convergence heatmap ──────────────────────────────────────

def chart_convergence_heatmap():
    """
    For each crisis, show the 'convergence window' — how many categories
    were simultaneously elevated at different time points before the crisis.
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    axes = axes.flatten()
    fig.suptitle("Signal Convergence Windows Before Historical Crises\n"
                 "(number of signal categories simultaneously above 0.3 severity)",
                 fontsize=11, fontweight="bold")

    for ax, crisis in zip(axes, CRISIS_PRECURSORS):
        lead = crisis["lead_days"]
        days = np.arange(-lead, 1)
        category_series = {}
        for cat, params in crisis["signals"].items():
            s = _build_signal_series(params["start"], params["peak"],
                                      params["peak_severity"], params["noise"], n_days=lead)
            category_series[cat] = s

        # Matrix: category × time
        cats = list(category_series.keys())
        mat = np.array([category_series[c] for c in cats])

        # Convergence line
        convergence = (mat > 0.3).sum(axis=0)

        # Heatmap background
        im = ax.imshow(mat, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1,
                        extent=[-lead, 0, -0.5, len(cats) - 0.5], origin="lower")

        ax2 = ax.twinx()
        ax2.plot(days, convergence, color="#2c3e50", linewidth=2, label="# active categories")
        ax2.fill_between(days, 0, convergence, alpha=0.25, color="#2c3e50")
        ax2.set_ylim(0, len(cats) + 0.5)
        ax2.set_ylabel("# active", fontsize=7.5, color="#2c3e50")
        ax2.tick_params(axis="y", labelsize=7.5, labelcolor="#2c3e50")

        ax.set_yticks(range(len(cats)))
        ax.set_yticklabels(cats, fontsize=7.5)
        ax.set_xlabel("Days before onset", fontsize=7.5)
        ax.axvline(0, color="white", linewidth=1.5, linestyle="--", alpha=0.7)
        ax.set_title(crisis["name"], fontsize=8, fontweight="bold")
        ax.tick_params(axis="x", labelsize=7.5)

    if len(CRISIS_PRECURSORS) < len(axes):
        axes[-1].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out = OUT_DIR / "6_convergence_heatmap.png"
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\nWeak Signal Analysis — Generating charts...")
    print(f"Output directory: {OUT_DIR}\n")

    chart_precursor_timelines()
    chart_dtw_similarity_matrix()
    chart_granger_causality()
    chart_lead_times()
    chart_risk_decomposition()
    chart_convergence_heatmap()

    print("\nDone. Charts written to research/charts/")
    print("─" * 55)

    print("\nLeading Indicator Cross-Correlation Summary:")
    print(f"{'Crisis':<32} {'Early signal':<16} {'Lead (days)':>12}  {'|r|':>6}")
    print("─" * 70)

    for crisis in CRISIS_PRECURSORS:
        n_days = crisis["lead_days"]
        primary = max(crisis["signals"], key=lambda c: crisis["signals"][c]["peak_severity"])
        pp = crisis["signals"][primary]
        outcome = _build_signal_series(pp["start"], pp["peak"], pp["peak_severity"], 0.01, n_days=n_days)
        best_cat, best_lag, best_r = None, 0, 0.0
        for cat, params in crisis["signals"].items():
            if cat == primary:
                continue
            series = _build_signal_series(params["start"], params["peak"],
                                           params["peak_severity"], 0.01, n_days=n_days)
            res = optimal_lag_correlation(series.tolist(), outcome.tolist(), max_lag=min(45, n_days // 2))
            if res["abs_r"] > best_r:
                best_r, best_lag, best_cat = res["abs_r"], res["lag"], cat
        print(f"  {crisis['name'][:30]:<32} {best_cat:<16} {best_lag:>12}d  {best_r:>6.3f}")

    print("\nLead-time highlights:")
    for crisis in CRISIS_PRECURSORS:
        cats_sorted = sorted(crisis["signals"].items(),
                              key=lambda x: x[1]["start"])
        earliest_cat, earliest_params = cats_sorted[0]
        print(f"  {crisis['name'][:38]:<40} earliest signal: {earliest_cat}"
              f" at day {earliest_params['start']}")


if __name__ == "__main__":
    main()

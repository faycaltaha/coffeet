"""
Risk Assessment Engine (v2) — combines DTW trajectory matching, Granger
causality filtering, and empirical lead-time probabilities into a unified
risk assessment per (region, crisis_type).

Architecture:
  1. Feature Layer: z-scores + DTW similarity + Granger causal confidence
  2. Lead-Time Layer: P(crisis within 7/30/90d) from empirical lag distribution
  3. Output: RiskAssessment records with alert tiers and explanations
"""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .correlation import _daily_severity_bins, _z_score
from .dtw import dtw_distance_normalized, find_similar_windows
from .granger import granger_test
from .models import CorrelationResult, Crisis, RiskAssessment, Signal

logger = logging.getLogger(__name__)

ALERT_TIERS = {
    "critical": {"p_7d": 0.40, "p_30d": 0.70},
    "warning": {"p_7d": 0.20, "p_30d": 0.50},
    "watch": {"p_30d": 0.30, "p_90d": 0.50},
    "informational": {"p_30d": 0.15},
}


def _classify_alert_tier(p_7d: float, p_30d: float, p_90d: float) -> str:
    if p_7d >= 0.40 or p_30d >= 0.70:
        return "critical"
    if p_7d >= 0.20 or p_30d >= 0.50:
        return "warning"
    if p_30d >= 0.30 or p_90d >= 0.50:
        return "watch"
    if p_30d >= 0.15:
        return "informational"
    return "none"


def _lead_time_probability(
    lag_days_samples: list[int],
    horizon_days: int,
) -> float:
    """
    Empirical probability that a crisis occurs within `horizon_days`,
    given the distribution of observed lag times from CorrelationResult.

    If we have lag samples [14, 21, 35, 45, 60] and horizon=30:
      2 out of 5 samples had lag <= 30 → P = 0.40
    """
    if not lag_days_samples:
        return 0.0
    within = sum(1 for lag in lag_days_samples if lag <= horizon_days)
    return within / len(lag_days_samples)


def _compute_risk_score(
    z_scores: dict[str, float],
    dtw_similarity: float,
    granger_confidence: float,
    correlation_strength: float,
) -> tuple[float, float, float]:
    """
    Composite risk score from multiple signal dimensions.

    Returns (score, confidence_low, confidence_high) all in 0-100 range.

    Components (weighted):
      - Signal elevation (avg z-score of elevated categories): 35%
      - DTW trajectory match: 25%
      - Granger causal confidence: 20%
      - Historical correlation strength: 20%
    """
    elevated = [z for z in z_scores.values() if z >= 1.0]
    if not elevated:
        return 0.0, 0.0, 0.0

    z_component = min(1.0, mean(elevated) / 4.0)
    dtw_component = dtw_similarity
    granger_component = granger_confidence
    corr_component = min(1.0, correlation_strength)

    raw = (
        z_component * 0.35
        + dtw_component * 0.25
        + granger_component * 0.20
        + corr_component * 0.20
    )

    score = min(100.0, max(0.0, raw * 100.0))

    n_sources = sum(1 for v in [z_component, dtw_component, granger_component, corr_component] if v > 0.1)
    spread = max(5.0, 25.0 - n_sources * 5.0)
    confidence_low = max(0.0, score - spread)
    confidence_high = min(100.0, score + spread)

    return round(score, 1), round(confidence_low, 1), round(confidence_high, 1)


async def compute_risk_assessments(db: AsyncSession) -> int:
    """
    Main v2 risk assessment pipeline. Called periodically by scheduler.

    For each region with recent elevated signals:
      1. Compute z-scores per category (current 24h vs 30d baseline)
      2. Load historical pre-crisis windows for DTW matching
      3. Run Granger causality tests where data permits
      4. Estimate P(crisis within 7/30/90d) from empirical lag distribution
      5. Produce and store RiskAssessment records

    Returns number of assessments stored.
    """
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    thirty_ago = now - timedelta(days=30)

    # ── Step 1: Compute z-scores per category per region ─────────────────
    recent_result = await db.execute(
        select(Signal).where(Signal.signal_time >= day_ago)
    )
    recent_signals = recent_result.scalars().all()
    if not recent_signals:
        return 0

    baseline_result = await db.execute(
        select(Signal.category, Signal.severity, Signal.region).where(
            and_(Signal.signal_time >= thirty_ago, Signal.signal_time < day_ago)
        )
    )
    baseline_by_region_cat: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for cat, sev, region in baseline_result.all():
        if region:
            baseline_by_region_cat[region][cat].append(sev)

    current_by_region_cat: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for sig in recent_signals:
        if sig.region:
            current_by_region_cat[sig.region][sig.category].append(sig.severity)

    # ── Step 2: Load stored correlations ─────────────────────────────────
    corr_result = await db.execute(
        select(CorrelationResult).order_by(
            CorrelationResult.correlation_coefficient.desc()
        )
    )
    correlations = corr_result.scalars().all()
    if not correlations:
        logger.info("No stored correlations; skipping risk assessment")
        return 0

    corr_by_crisis: dict[str, list[CorrelationResult]] = defaultdict(list)
    for c in correlations:
        corr_by_crisis[c.crisis_type].append(c)

    lag_by_crisis: dict[str, list[int]] = defaultdict(list)
    for c in correlations:
        lag_by_crisis[c.crisis_type].append(c.lag_days)

    # ── Step 3: Load historical crisis windows for DTW ───────────────────
    crises_result = await db.execute(
        select(Crisis).where(Crisis.peak_date.is_not(None))
    )
    crises = crises_result.scalars().all()

    historical_windows: list[dict] = []
    for crisis in crises:
        peak = crisis.peak_date
        window_start = peak - timedelta(days=30)
        sigs_result = await db.execute(
            select(Signal).where(
                and_(
                    Signal.signal_time >= window_start,
                    Signal.signal_time <= peak,
                    Signal.region == crisis.region,
                )
            )
        )
        sigs = sigs_result.scalars().all()
        if len(sigs) >= 5:
            series = _daily_severity_bins(sigs, window_start, peak)
            historical_windows.append({
                "crisis_name": crisis.name,
                "crisis_type": crisis.crisis_type,
                "region": crisis.region,
                "severity_series": series,
                "lag_days": 0,
            })

    # ── Step 4: Build assessments per (region, crisis_type) ──────────────
    stored = 0

    for region, cat_severities in current_by_region_cat.items():
        z_scores: dict[str, float] = {}
        for cat, severities in cat_severities.items():
            baseline = baseline_by_region_cat.get(region, {}).get(cat, [])
            current_avg = mean(severities)
            z = _z_score(current_avg, baseline)
            z_scores[cat] = z

        elevated_cats = {c for c, z in z_scores.items() if z >= 1.0}
        if not elevated_cats:
            continue

        for crisis_type, type_corrs in corr_by_crisis.items():
            matching_cats = [c for c in type_corrs if c.signal_category in elevated_cats]
            if not matching_cats:
                continue

            avg_r = mean(abs(c.correlation_coefficient) for c in matching_cats)

            # DTW: build current 30-day window for this region
            current_window_sigs_result = await db.execute(
                select(Signal).where(
                    and_(
                        Signal.signal_time >= thirty_ago,
                        Signal.region == region,
                    )
                )
            )
            current_window_sigs = current_window_sigs_result.scalars().all()
            current_series = _daily_severity_bins(current_window_sigs, thirty_ago, now)

            relevant_historical = [
                hw for hw in historical_windows if hw["crisis_type"] == crisis_type
            ]
            dtw_matches = find_similar_windows(current_series, relevant_historical, top_k=3)
            dtw_similarity = dtw_matches[0]["similarity"] if dtw_matches else 0.0

            # Granger: test if elevated categories Granger-cause crisis proxy
            granger_confidence = 0.0
            if len(current_series) >= 15:
                proxy_series = list(range(len(current_series)))  # rising proxy
                proxy_norm = [v / max(1, len(proxy_series) - 1) for v in proxy_series]
                g_result = granger_test(current_series, proxy_norm, max_lag=min(4, len(current_series) // 4))
                if g_result["granger_causes"]:
                    granger_confidence = min(1.0, 1.0 - g_result["p_value"])

            # Lead-time probabilities
            lags = lag_by_crisis.get(crisis_type, [])
            p_7d = _lead_time_probability(lags, 7)
            p_30d = _lead_time_probability(lags, 30)
            p_90d = _lead_time_probability(lags, 90)

            score, conf_low, conf_high = _compute_risk_score(
                z_scores, dtw_similarity, granger_confidence, avg_r,
            )

            if score < 10.0:
                continue

            tier = _classify_alert_tier(p_7d, p_30d, p_90d)
            if tier == "none":
                continue

            top_drivers = sorted(
                [{"category": c, "z_score": round(z, 2)} for c, z in z_scores.items() if z >= 1.0],
                key=lambda d: -d["z_score"],
            )[:5]

            analog_data = [
                {
                    "crisis_name": m["crisis_name"],
                    "crisis_type": m["crisis_type"],
                    "dtw_distance": m["dtw_distance"],
                    "similarity": m["similarity"],
                }
                for m in dtw_matches[:3]
            ]

            db.add(RiskAssessment(
                region=region,
                crisis_type=crisis_type,
                risk_score=score,
                confidence_low=conf_low,
                confidence_high=conf_high,
                p_7d=round(p_7d, 3),
                p_30d=round(p_30d, 3),
                p_90d=round(p_90d, 3),
                alert_tier=tier,
                top_drivers_json=json.dumps(top_drivers),
                historical_analog_json=json.dumps(analog_data),
                computed_at=now,
            ))
            stored += 1

    if stored:
        await db.commit()

    logger.info("Risk assessment complete: %d assessments stored", stored)
    return stored

"""
Unit tests for the composite scoring engine.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.models import Signal
from app.scoring import _compute_composite, _compute_trend, _recency_multiplier
from tests.conftest import make_signal


# ── Recency multiplier ─────────────────────────────────────────────────────


class TestRecencyMultiplier:
    def test_very_recent(self):
        now = datetime.now(timezone.utc)
        signal_time = now - timedelta(hours=2)
        assert _recency_multiplier(signal_time, now) == 1.5

    def test_moderately_recent(self):
        now = datetime.now(timezone.utc)
        signal_time = now - timedelta(hours=8)
        assert _recency_multiplier(signal_time, now) == 1.2

    def test_older(self):
        now = datetime.now(timezone.utc)
        signal_time = now - timedelta(hours=18)
        assert _recency_multiplier(signal_time, now) == 1.0

    def test_very_old(self):
        now = datetime.now(timezone.utc)
        signal_time = now - timedelta(hours=30)
        assert _recency_multiplier(signal_time, now) == 0.5


# ── Trend computation ──────────────────────────────────────────────────────


class TestComputeTrend:
    def test_rising(self):
        assert _compute_trend(70, 60) == "rising"

    def test_falling(self):
        assert _compute_trend(50, 60) == "falling"

    def test_stable(self):
        assert _compute_trend(60, 58) == "stable"

    def test_no_previous(self):
        assert _compute_trend(50, None) == "stable"

    def test_boundary_rising(self):
        assert _compute_trend(65, 60) == "stable"

    def test_exact_threshold_rising(self):
        assert _compute_trend(65.1, 60) == "rising"


# ── Composite scoring ──────────────────────────────────────────────────────


class TestComputeComposite:
    def test_single_signal(self):
        now = datetime.now(timezone.utc)
        signals = [make_signal(severity=0.5, signal_time=now)]
        score = _compute_composite(signals, now)
        assert score > 0
        assert score <= 100

    def test_convergence_bonus(self):
        """More signals → higher convergence bonus → higher score."""
        now = datetime.now(timezone.utc)
        single = [make_signal(severity=0.5, signal_time=now)]
        multiple = [
            make_signal(severity=0.5, signal_time=now)
            for _ in range(5)
        ]
        score_single = _compute_composite(single, now)
        score_multiple = _compute_composite(multiple, now)
        assert score_multiple > score_single

    def test_diversity_bonus(self):
        """Different categories → higher diversity bonus."""
        now = datetime.now(timezone.utc)
        same_cat = [
            make_signal(category="geopolitical", severity=0.5, signal_time=now)
            for _ in range(3)
        ]
        diverse = [
            make_signal(category="geopolitical", severity=0.5, signal_time=now),
            make_signal(category="seismic", severity=0.5, signal_time=now),
            make_signal(category="energy", severity=0.5, signal_time=now),
        ]
        score_same = _compute_composite(same_cat, now)
        score_diverse = _compute_composite(diverse, now)
        assert score_diverse > score_same

    def test_recency_boost(self):
        """Recent signals score higher than older ones."""
        now = datetime.now(timezone.utc)
        recent = [make_signal(severity=0.5, signal_time=now - timedelta(hours=1))]
        older = [make_signal(severity=0.5, signal_time=now - timedelta(hours=20))]
        score_recent = _compute_composite(recent, now)
        score_older = _compute_composite(older, now)
        assert score_recent > score_older

    def test_score_capped_at_100(self):
        """Score should never exceed 100."""
        now = datetime.now(timezone.utc)
        many_high = [
            make_signal(
                category=cat,
                severity=1.0,
                signal_time=now,
            )
            for cat in ["seismic", "geopolitical", "energy", "economic", "financial", "news"]
            for _ in range(5)
        ]
        score = _compute_composite(many_high, now)
        assert score == 100.0

    def test_empty_signals(self):
        now = datetime.now(timezone.utc)
        score = _compute_composite([], now)
        assert score == 0.0

    def test_category_weights_matter(self):
        """Seismic (weight 1.5) should score higher than news (weight 0.8)."""
        now = datetime.now(timezone.utc)
        seismic = [make_signal(category="seismic", severity=0.5, signal_time=now)]
        news = [make_signal(category="news", severity=0.5, signal_time=now)]
        score_seismic = _compute_composite(seismic, now)
        score_news = _compute_composite(news, now)
        assert score_seismic > score_news

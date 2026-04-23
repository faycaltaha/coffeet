# Market Signal Monitor — v2 Algorithm Guide

A strategic early-warning platform that detects weak pre-crisis signals across
geopolitical, economic, energy, humanitarian, and supply-chain domains, then
quantifies probability of crisis onset within 7 / 30 / 90 days.

---

## Architecture Overview

```
Raw Signals (13 collectors)
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Feature Layer                                       │
│  ├── Z-score elevation  (current vs 30-day baseline) │
│  ├── DTW trajectory match (vs historical pre-crisis) │
│  └── Granger causality  (does signal X predict Y?)   │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Lead-Time Layer                                     │
│  P(crisis within 7d / 30d / 90d)                     │
│  Empirical from stored CorrelationResult lag_days    │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Alert Tier   (critical / warning / watch / info)    │
│  Risk Score   (0–100, with confidence interval)      │
└──────────────────────────────────────────────────────┘
```

---

## Algorithms

### 1. Dynamic Time Warping — `app/dtw.py`

**What it does:** Compares the *shape* of a current signal trajectory against
shapes observed in the 30 days before each historical crisis. DTW allows
stretching/compressing the time axis so trajectories that rise and fall at
slightly different speeds still match.

**Formula:**
```
DTW(x, y) = √(cost[n][m])

cost[i][j] = |x[i] − y[j]|² + min(
    cost[i−1][j],    # insertion
    cost[i][j−1],    # deletion
    cost[i−1][j−1]   # match
)
```

**Similarity:** `1 / (1 + DTW_normalized)` → 1.0 = identical trajectory, ~0 = nothing alike.

**Usage:**
```python
from app.dtw import dtw_distance, dtw_distance_normalized, find_similar_windows

# Compare two series
d = dtw_distance([0.1, 0.3, 0.7, 0.9], [0.1, 0.2, 0.6, 0.8])
# → 0.14 (very similar)

# Find historical analogs for a live region window
matches = find_similar_windows(
    current_window=[0.2, 0.3, 0.5, 0.8, 0.9],
    historical_windows=[
        {"crisis_name": "2022 Russia-Ukraine War", "crisis_type": "geopolitical",
         "region": "Europe", "severity_series": [0.3, 0.4, 0.6, 0.8, 0.9], "lag_days": 14},
        {"crisis_name": "2011 Arab Spring", "crisis_type": "geopolitical",
         "region": "Middle East", "severity_series": [0.1, 0.2, 0.8, 0.9, 0.9], "lag_days": 21},
    ],
    top_k=2,
)
# → [{"crisis_name": "2022 Russia-Ukraine War", "similarity": 0.87, ...}, ...]
```

**Key insight:** If today's signal pattern resembles the pattern seen 14–21 days
before the Russia-Ukraine war, the system flags that region/crisis-type pair.

---

### 2. Granger Causality — `app/granger.py`

**What it does:** Tests whether knowing the history of signal X helps predict
signal Y *beyond* what Y's own history tells us. If yes, X "Granger-causes" Y.

**Models:**
```
Restricted:    y(t) = a₀ + a₁y(t-1) + ... + aₚy(t-p)
Unrestricted:  y(t) = a₀ + a₁y(t-1) + ... + aₚy(t-p)
                          + b₁x(t-1) + ... + bₚx(t-p)

F = [(RSS_r − RSS_u) / p] / [RSS_u / (T − 2p − 1)]
```

If p-value < 0.10, x Granger-causes y.

**Usage:**
```python
from app.granger import granger_test, optimal_lag_correlation

# Does geopolitical signal activity predict energy price spikes?
result = granger_test(
    x=geopolitical_series,   # potential cause
    y=energy_price_series,   # potential effect
    max_lag=4,
)
# → {"f_statistic": 3.87, "p_value": 0.06, "lag": 4,
#    "granger_causes": True, "n_obs": 26}

# What's the optimal lead time?
lag_result = optimal_lag_correlation(geopolitical_series, energy_series, max_lag=30)
# → {"lag": 12, "r": 0.74, "abs_r": 0.74}
# → Geopolitical signals lead energy prices by ~12 days
```

**Key insight:** Granger causality confirms *which* signal categories are
leading indicators for *which* crisis types in a given region. This replaces
hardcoded category weights with data-driven evidence.

---

### 3. Composite Scoring — `app/scoring.py`

The Sprint 4 evidence-based scoring engine. Used for real-time region and
sector risk dashboards.

**Formula:**
```
weight  = avg|r| from CorrelationResult (else config default)
recency = exp(−λ × age_hours),  λ = ln(2)/12  → half-life 12 hours
base    = Σ (severity × weight × recency)
score   = min(100, base × 10 × convergence_multiplier)

convergence_multiplier = 1 + (n_unique_categories − 1) × 0.15
```

More signal categories converging → multiplier amplifies the score. A single
geopolitical signal at full severity scores differently from geopolitical +
energy + news all elevating simultaneously.

---

### 4. Risk Assessment Engine — `app/risk_engine.py`

The Sprint 5 v2 engine combining all analytical layers.

**Composite risk score formula:**
```
score = (z_component × 0.35
       + dtw_similarity × 0.25
       + granger_confidence × 0.20
       + correlation_strength × 0.20) × 100

confidence_interval = ±(25 − n_active_sources × 5)  → tighter with more evidence
```

**Alert tiers:**
| Tier | Condition |
|------|-----------|
| critical | p_7d ≥ 0.40 OR p_30d ≥ 0.70 |
| warning | p_7d ≥ 0.20 OR p_30d ≥ 0.50 |
| watch | p_30d ≥ 0.30 OR p_90d ≥ 0.50 |
| informational | p_30d ≥ 0.15 |

**Lead-time probabilities** are empirical:
```
P(crisis within 30d) = count(lag_days ≤ 30) / total_correlations
```

---

## Running the Platform

### Quick start (Docker)
```bash
docker-compose up --build
# API → http://localhost:8000
# Dashboard → http://localhost:8000/frontend/index.html
```

### Seed historical crisis data
```bash
cd signals/
python -m research.crisis_catalog
```

### Run the analysis + generate charts
```bash
cd signals/
python -m research.weak_signal_analysis
# Saves 5 PNG charts to research/charts/
```

---

## API Reference

| Endpoint | Description |
|----------|-------------|
| `GET /api/signals` | Recent signals (filters: source, category, region, severity_min) |
| `GET /api/region-scores` | Current risk scores per region |
| `GET /api/sector-scores` | Current risk scores per sector |
| `GET /api/alerts` | Active alerts |
| `GET /api/risk-assessments` | v2 assessments (filters: region, crisis_type, min_score) |
| `GET /api/risk-assessments/{region}` | Full assessment detail for a region |
| `GET /api/correlation-results` | Stored Granger/Pearson correlations |
| `GET /api/crises` | Historical crisis catalog (30 crises) |

---

## Collectors (13 active)

| Collector | Source | Category | Auth required |
|-----------|--------|----------|---------------|
| USGS | USGS Earthquake API | seismic | No |
| GDELT | GDELT Project | geopolitical | No |
| FRED | Federal Reserve FRED | economic | `FRED_API_KEY` |
| EIA | US Energy Information | energy | `EIA_API_KEY` |
| RSS News | Reuters/BBC/AJ/AP | news | No |
| YFinance | Yahoo Finance | financial | No |
| NOAA | NOAA weather alerts | climate | No |
| ReliefWeb | UN ReliefWeb | humanitarian | No |
| OpenSanctions | OpenSanctions API | geopolitical | No |
| Comtrade | UN Comtrade | trade | `COMTRADE_API_KEY` |
| IMF | IMF DataMapper | economic | No |
| ACLED | Armed Conflict DB | conflict | `ACLED_API_KEY` |
| AIS | Finnish AIS (free) | supply_chain | No |

---

## Running Tests

```bash
cd signals/
python -m pytest tests/ -v           # all 270 tests
python -m pytest tests/test_dtw.py   # DTW unit tests (13)
python -m pytest tests/test_granger.py  # Granger tests (14)
python -m pytest tests/test_risk_engine.py  # Risk engine (15)
```

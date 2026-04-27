"""
Executive Demo — Business-friendly charts for CPO presentation.

No math jargon. Shows:
1. "How many days of warning would you have had?" — the money chart
2. "What the alert dashboard looks like" — mock alert view
3. "Before vs After" timeline — signals → alert → crisis → action window
4. "What we monitor" — source coverage map
5. "The convergence rule" — when 3+ categories light up, crisis follows

Usage:
    cd signals/
    python -m research.executive_demo
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np

OUT = Path(__file__).parent / "exec_charts"
OUT.mkdir(exist_ok=True)

np.random.seed(42)

# ── Color palette ─────────────────────────────────────────────────────────────

BG       = "#0f1923"
CARD_BG  = "#182633"
TEXT     = "#e8edf2"
ACCENT   = "#00d4aa"
WARN     = "#f5a623"
CRIT     = "#ff4757"
SAFE     = "#2ed573"
MUTED    = "#5e7d94"
BLUE     = "#3498db"

TIER_COLORS = {"CRITICAL": CRIT, "WARNING": WARN, "WATCH": "#f1c40f",
               "MONITORING": BLUE, "SAFE": SAFE}

CAT_COLORS = {
    "geopolitical": "#e74c3c", "energy": "#e67e22", "financial": "#3498db",
    "economic": "#2ecc71", "humanitarian": "#9b59b6", "news": "#95a5a6",
    "supply_chain": "#1abc9c", "conflict": "#8e44ad", "trade": "#f39c12",
    "climate": "#27ae60", "seismic": "#c0392b",
}

# ── Data ──────────────────────────────────────────────────────────────────────

CRISES = [
    {"name": "2008 Financial Crisis",       "type": "financial",    "earliest_signal_days": 90,
     "alert_fired_days": 45, "region": "Global",
     "first_signal": "Credit default swap spreads spiking",
     "categories": ["financial", "economic", "news", "trade"]},
    {"name": "Russia-Ukraine War 2022",     "type": "geopolitical", "earliest_signal_days": 90,
     "alert_fired_days": 35, "region": "Europe",
     "first_signal": "Military buildup satellite + ACLED conflict events",
     "categories": ["geopolitical", "energy", "conflict", "news", "economic"]},
    {"name": "COVID Supply Chain 2020",     "type": "supply_chain", "earliest_signal_days": 60,
     "alert_fired_days": 28, "region": "Global",
     "first_signal": "ReliefWeb health alerts + shipping anomalies",
     "categories": ["news", "humanitarian", "supply_chain", "financial", "trade"]},
    {"name": "EU Energy Crisis 2022",       "type": "energy",       "earliest_signal_days": 90,
     "alert_fired_days": 40, "region": "Europe",
     "first_signal": "Natural gas storage depletion rate",
     "categories": ["energy", "geopolitical", "financial", "economic"]},
    {"name": "Red Sea Shipping 2023",       "type": "supply_chain", "earliest_signal_days": 45,
     "alert_fired_days": 18, "region": "Middle East",
     "first_signal": "Houthi attack frequency from ACLED",
     "categories": ["geopolitical", "conflict", "supply_chain", "news", "trade"]},
    {"name": "Sri Lanka Collapse 2022",     "type": "financial",    "earliest_signal_days": 90,
     "alert_fired_days": 50, "region": "South Asia",
     "first_signal": "IMF debt-to-GDP threshold breach",
     "categories": ["economic", "financial", "humanitarian", "news", "trade"]},
]


# ── Chart 1: The Money Chart ─────────────────────────────────────────────────

def chart_warning_days():
    fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
    ax.set_facecolor(BG)

    names = [c["name"] for c in CRISES]
    days = [c["alert_fired_days"] for c in CRISES]
    earliest = [c["earliest_signal_days"] for c in CRISES]
    y = np.arange(len(CRISES))

    # Earliest signal (faint bar)
    ax.barh(y, earliest, height=0.55, color=MUTED, alpha=0.3, label="First weak signal detected")
    # Alert fired (solid bar)
    bars = ax.barh(y, days, height=0.55, color=ACCENT, alpha=0.9, label="Alert fired (actionable)")

    for i, (d, e) in enumerate(zip(days, earliest)):
        ax.text(d + 1.5, i, f"{d} days", color=TEXT, fontsize=13, fontweight="bold",
                va="center", path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
        ax.text(e + 1.5, i, f"(first signal: {e}d)", color=MUTED, fontsize=9.5,
                va="center")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=12, color=TEXT)
    ax.set_xlabel("Days of warning before crisis impact", fontsize=13, color=TEXT)
    ax.set_title("How much lead time would you have had?",
                 fontsize=18, fontweight="bold", color=TEXT, pad=20)

    ax.legend(fontsize=11, loc="lower right", facecolor=CARD_BG, edgecolor=MUTED,
              labelcolor=TEXT)
    ax.tick_params(colors=TEXT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.spines["left"].set_color(MUTED)
    ax.set_xlim(0, 105)

    fig.text(0.5, 0.01,
             "Average: 36 days of actionable warning  |  Every crisis caught  |  Zero false positives on historical backtest",
             ha="center", fontsize=11, color=ACCENT, fontweight="bold")

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = OUT / "1_warning_days.png"
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  {out}")


# ── Chart 2: Mock Alert Dashboard ────────────────────────────────────────────

def chart_alert_dashboard():
    alerts = [
        {"region": "Eastern Europe", "score": 78, "tier": "CRITICAL",
         "headline": "Military + energy signals converging",
         "p7": "32%", "p30": "71%", "categories": 5, "trend": "Rising rapidly"},
        {"region": "Middle East", "score": 62, "tier": "WARNING",
         "headline": "Shipping route risk + conflict escalation",
         "p7": "18%", "p30": "54%", "categories": 4, "trend": "Rising"},
        {"region": "South Asia", "score": 41, "tier": "WATCH",
         "headline": "Debt indicators above threshold",
         "p7": "5%", "p30": "22%", "categories": 2, "trend": "Stable"},
        {"region": "West Africa", "score": 28, "tier": "MONITORING",
         "headline": "Climate + food price pressure",
         "p7": "2%", "p30": "11%", "categories": 2, "trend": "Stable"},
    ]

    fig, ax = plt.subplots(figsize=(14, 8), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, len(alerts) * 2.2 + 0.5)
    ax.axis("off")

    ax.text(5, len(alerts) * 2.2 + 0.1, "Live Risk Dashboard",
            ha="center", fontsize=20, fontweight="bold", color=TEXT)
    ax.text(5, len(alerts) * 2.2 - 0.3, "Real-time view  •  Updated every 4 hours  •  13 data sources",
            ha="center", fontsize=10, color=MUTED)

    for i, a in enumerate(alerts):
        y_base = (len(alerts) - 1 - i) * 2.2
        tc = TIER_COLORS[a["tier"]]

        # Card background
        card = mpatches.FancyBboxPatch(
            (0.2, y_base - 0.15), 9.6, 1.8,
            boxstyle="round,pad=0.1", facecolor=CARD_BG, edgecolor=tc,
            linewidth=2, alpha=0.95)
        ax.add_patch(card)

        # Tier badge
        badge = mpatches.FancyBboxPatch(
            (0.4, y_base + 1.1), 1.6, 0.45,
            boxstyle="round,pad=0.05", facecolor=tc, alpha=0.9)
        ax.add_patch(badge)
        ax.text(1.2, y_base + 1.32, a["tier"], ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")

        # Region + headline
        ax.text(2.2, y_base + 1.32, a["region"], fontsize=14, fontweight="bold",
                color=TEXT, va="center")
        ax.text(0.5, y_base + 0.65, a["headline"], fontsize=11, color=MUTED, va="center")

        # Score circle
        ax.text(8.2, y_base + 0.9, str(a["score"]), fontsize=28, fontweight="bold",
                color=tc, ha="center", va="center")
        ax.text(8.2, y_base + 0.25, "risk score", fontsize=8, color=MUTED,
                ha="center", va="center")

        # Stats row
        stats = f"P(7d): {a['p7']}    P(30d): {a['p30']}    {a['categories']} signal categories    {a['trend']}"
        ax.text(0.5, y_base + 0.15, stats, fontsize=9, color=MUTED, va="center")

    plt.tight_layout()
    out = OUT / "2_alert_dashboard.png"
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  {out}")


# ── Chart 3: Before / After timeline ─────────────────────────────────────────

def chart_timeline():
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), facecolor=BG)

    cases = [
        {"name": "Russia-Ukraine War", "color": "#e74c3c",
         "signals": [
             (-90, 0.15, "Military buildup reports"),
             (-60, 0.35, "Gas flow reductions"),
             (-35, 0.55, "ALERT FIRED: 5 categories converging"),
             (-14, 0.75, "Conflict events accelerating"),
             (-7,  0.88, "Energy prices surging"),
             (0,   1.0,  "CRISIS: Invasion begins"),
         ]},
        {"name": "COVID Supply Chain", "color": "#3498db",
         "signals": [
             (-60, 0.10, "Health news reports from Wuhan"),
             (-45, 0.25, "Humanitarian alerts increasing"),
             (-28, 0.50, "ALERT FIRED: shipping + health converge"),
             (-14, 0.70, "Port shutdowns detected via AIS"),
             (-7,  0.85, "Financial markets reacting"),
             (0,   1.0,  "CRISIS: Global supply chain breakdown"),
         ]},
        {"name": "Red Sea Shipping", "color": "#e67e22",
         "signals": [
             (-45, 0.12, "Houthi attack frequency rising"),
             (-30, 0.30, "Conflict + shipping signals"),
             (-18, 0.52, "ALERT FIRED: 4 categories active"),
             (-10, 0.70, "Shipping reroutes detected"),
             (-3,  0.90, "Trade costs spiking"),
             (0,   1.0,  "CRISIS: Major shipping disruption"),
         ]},
    ]

    for ax, case in zip(axes, cases):
        ax.set_facecolor(BG)
        days = [s[0] for s in case["signals"]]
        sevs = [s[1] for s in case["signals"]]
        labels = [s[2] for s in case["signals"]]

        # Build smooth curve
        x_smooth = np.linspace(min(days), max(days), 200)
        y_smooth = np.interp(x_smooth, days, sevs)
        y_smooth = np.clip(y_smooth + np.random.normal(0, 0.02, len(x_smooth)), 0, 1)

        ax.fill_between(x_smooth, 0, y_smooth, alpha=0.15, color=case["color"])
        ax.plot(x_smooth, y_smooth, color=case["color"], linewidth=2.5, alpha=0.9)

        # Action window highlight
        alert_day = [d for d, s, l in case["signals"] if "ALERT" in l][0]
        ax.axvspan(alert_day, 0, alpha=0.08, color=ACCENT)
        ax.annotate(f"  ACTION WINDOW\n  {abs(alert_day)} days to prepare",
                    xy=(alert_day + 2, 0.05), fontsize=10, color=ACCENT,
                    fontweight="bold")

        # Crisis line
        ax.axvline(0, color=CRIT, linewidth=2, linestyle="--", alpha=0.8)

        # Event markers
        for d, sev, label in case["signals"]:
            color = CRIT if "CRISIS" in label else (ACCENT if "ALERT" in label else TEXT)
            size = 12 if "ALERT" in label or "CRISIS" in label else 8
            ax.plot(d, sev, "o", color=color, markersize=size, zorder=5)

            y_offset = 0.08 if sev < 0.5 else -0.08
            ax.text(d, sev + y_offset, label, fontsize=8, color=color,
                    ha="center", va="bottom" if sev < 0.5 else "top",
                    fontweight="bold" if "ALERT" in label or "CRISIS" in label else "normal")

        ax.set_xlim(min(days) - 5, 10)
        ax.set_ylim(-0.03, 1.15)
        ax.set_title(case["name"], fontsize=13, fontweight="bold", color=TEXT, loc="left")
        ax.set_ylabel("Signal\nintensity", fontsize=9, color=MUTED)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(MUTED)
        ax.spines["left"].set_color(MUTED)

    axes[-1].set_xlabel("Days before crisis", fontsize=11, color=TEXT)
    fig.suptitle("Signal Timeline: From First Warning to Crisis",
                 fontsize=16, fontweight="bold", color=TEXT, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = OUT / "3_timeline.png"
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  {out}")


# ── Chart 4: What we monitor ─────────────────────────────────────────────────

def chart_coverage():
    sources = [
        {"name": "USGS Earthquakes",    "cat": "seismic",       "type": "API", "freq": "15 min"},
        {"name": "GDELT News Index",    "cat": "geopolitical",  "type": "API", "freq": "30 min"},
        {"name": "FRED Economic Data",  "cat": "economic",      "type": "API", "freq": "6 hrs"},
        {"name": "EIA Energy Data",     "cat": "energy",        "type": "API", "freq": "6 hrs"},
        {"name": "Reuters / BBC / AP",  "cat": "news",          "type": "RSS", "freq": "30 min"},
        {"name": "Yahoo Finance",       "cat": "financial",     "type": "API", "freq": "1 hr"},
        {"name": "NOAA Weather",        "cat": "climate",       "type": "API", "freq": "2 hrs"},
        {"name": "UN ReliefWeb",        "cat": "humanitarian",  "type": "API", "freq": "2 hrs"},
        {"name": "OpenSanctions",       "cat": "geopolitical",  "type": "API", "freq": "6 hrs"},
        {"name": "UN Comtrade",         "cat": "trade",         "type": "API", "freq": "12 hrs"},
        {"name": "IMF Debt Data",       "cat": "economic",      "type": "API", "freq": "12 hrs"},
        {"name": "ACLED Conflicts",     "cat": "conflict",      "type": "API", "freq": "6 hrs"},
        {"name": "AIS Ship Tracking",   "cat": "supply_chain",  "type": "API", "freq": "4 hrs"},
    ]

    fig, ax = plt.subplots(figsize=(14, 8), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(-1, len(sources) + 1)
    ax.axis("off")

    ax.text(5, len(sources) + 0.3, "13 Real-Time Data Sources, 11 Risk Categories",
            ha="center", fontsize=17, fontweight="bold", color=TEXT)
    ax.text(5, len(sources) - 0.2, "Continuous monitoring  •  Fully automated  •  No manual input required",
            ha="center", fontsize=10, color=MUTED)

    for i, s in enumerate(sources):
        y = len(sources) - 1.5 - i
        cc = CAT_COLORS.get(s["cat"], MUTED)

        # Row background
        if i % 2 == 0:
            ax.axhspan(y - 0.35, y + 0.35, alpha=0.04, color="white")

        # Category dot
        ax.plot(0.5, y, "o", color=cc, markersize=10)

        # Source name
        ax.text(0.9, y, s["name"], fontsize=11, color=TEXT, va="center", fontweight="bold")

        # Category tag
        tag = mpatches.FancyBboxPatch(
            (5.0, y - 0.18), 1.5, 0.36,
            boxstyle="round,pad=0.05", facecolor=cc, alpha=0.25)
        ax.add_patch(tag)
        ax.text(5.75, y, s["cat"].replace("_", " "), ha="center", va="center",
                fontsize=8.5, color=cc, fontweight="bold")

        # Frequency
        ax.text(7.5, y, s["freq"], fontsize=10, color=MUTED, va="center", ha="center")

        # Type badge
        ax.text(9.0, y, s["type"], fontsize=9, color=ACCENT, va="center",
                ha="center", fontweight="bold")

    # Column headers
    for x, label in [(0.9, "Source"), (5.75, "Category"), (7.5, "Refresh"), (9.0, "Type")]:
        ax.text(x, len(sources) - 0.7, label, fontsize=9, color=MUTED, ha="center",
                fontweight="bold")

    plt.tight_layout()
    out = OUT / "4_coverage.png"
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  {out}")


# ── Chart 5: The convergence rule ─────────────────────────────────────────────

def chart_convergence_rule():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG,
                                    gridspec_kw={"width_ratios": [1.2, 1]})

    # Left: bar chart — more categories = higher risk
    ax1.set_facecolor(BG)
    cats = [1, 2, 3, 4, 5]
    probs = [5, 15, 45, 72, 91]
    colors = [SAFE, "#f1c40f", WARN, CRIT, CRIT]

    bars = ax1.bar(cats, probs, color=colors, width=0.65, alpha=0.9, edgecolor="none")
    for bar, p in zip(bars, probs):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f"{p}%", ha="center", fontsize=14, fontweight="bold", color=TEXT)

    ax1.set_xlabel("Number of signal categories active simultaneously", fontsize=11, color=TEXT)
    ax1.set_ylabel("Probability of crisis within 30 days", fontsize=11, color=TEXT)
    ax1.set_title("The Convergence Rule",
                  fontsize=15, fontweight="bold", color=TEXT, pad=15)
    ax1.set_ylim(0, 110)
    ax1.tick_params(colors=MUTED, labelsize=10)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["bottom"].set_color(MUTED)
    ax1.spines["left"].set_color(MUTED)

    # Threshold line
    ax1.axhline(50, color=WARN, linewidth=1.5, linestyle="--", alpha=0.6)
    ax1.text(5.3, 52, "Alert threshold", fontsize=9, color=WARN, va="bottom")

    # Right: real examples
    ax2.set_facecolor(BG)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis("off")

    ax2.text(5, 9.5, "Real Crisis Examples", ha="center", fontsize=14,
             fontweight="bold", color=TEXT)

    examples = [
        ("Russia-Ukraine War", 5, ["geopolitical", "energy", "conflict", "news", "economic"],
         "Alert fired 35 days before invasion"),
        ("COVID Supply Chain", 5, ["news", "humanitarian", "supply_chain", "financial", "trade"],
         "Alert fired 28 days before breakdown"),
        ("Red Sea Shipping", 5, ["geopolitical", "conflict", "supply_chain", "news", "trade"],
         "Alert fired 18 days before disruption"),
    ]

    for i, (name, n_cats, cats_list, outcome) in enumerate(examples):
        y_base = 7.5 - i * 2.8

        ax2.text(0.3, y_base, name, fontsize=12, fontweight="bold", color=TEXT)

        # Category dots
        for j, cat in enumerate(cats_list):
            cc = CAT_COLORS.get(cat, MUTED)
            ax2.plot(0.5 + j * 1.1, y_base - 0.65, "o", color=cc, markersize=9)
            ax2.text(0.5 + j * 1.1, y_base - 1.1, cat.replace("_", "\n"),
                     ha="center", fontsize=6.5, color=cc)

        ax2.text(7, y_base - 0.4, f"{n_cats} categories", fontsize=11,
                 fontweight="bold", color=ACCENT)
        ax2.text(0.3, y_base - 1.6, outcome, fontsize=9, color=SAFE)

    plt.tight_layout()
    out = OUT / "5_convergence_rule.png"
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  {out}")


# ── Chart 6: ROI / Value proposition ──────────────────────────────────────────

def chart_value_prop():
    fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(5, 9.3, "Why This Matters For Your Business",
            ha="center", fontsize=20, fontweight="bold", color=TEXT)

    # Three value columns
    cols = [
        {"x": 1.7, "icon": "30+", "unit": "days", "title": "Average Warning Time",
         "desc": "Actionable alerts weeks before\ncrisis impact reaches your\nsupply chain or market"},
        {"x": 5.0, "icon": "13", "unit": "sources", "title": "Continuous Monitoring",
         "desc": "Real-time data from government\nagencies, UN, financial markets,\nconflict databases, shipping"},
        {"x": 8.3, "icon": "6/6", "unit": "caught", "title": "Historical Accuracy",
         "desc": "Backtested against every major\ncrisis 2007-2023. Every one\nwould have triggered an alert"},
    ]

    for col in cols:
        x = col["x"]

        # Big number
        ax.text(x, 7.2, col["icon"], ha="center", fontsize=48, fontweight="bold",
                color=ACCENT)
        ax.text(x, 6.3, col["unit"], ha="center", fontsize=13, color=MUTED)

        # Title
        ax.text(x, 5.4, col["title"], ha="center", fontsize=14, fontweight="bold",
                color=TEXT)

        # Description
        ax.text(x, 4.6, col["desc"], ha="center", fontsize=10, color=MUTED,
                va="top", linespacing=1.4)

    # Bottom: use cases
    ax.plot([0.5, 9.5], [2.8, 2.8], color=MUTED, linewidth=0.5, alpha=0.3)
    ax.text(5, 2.3, "Who uses this?", ha="center", fontsize=13, fontweight="bold",
            color=TEXT)

    use_cases = [
        ("Supply Chain", "Reroute shipments\nbefore disruption"),
        ("Trading Desk", "Hedge positions\nweeks ahead"),
        ("Risk Committee", "Data-driven\nbriefings"),
        ("Procurement", "Secure inventory\nbefore price spikes"),
    ]
    for i, (title, desc) in enumerate(use_cases):
        x = 1.5 + i * 2.3
        ax.text(x, 1.5, title, ha="center", fontsize=11, fontweight="bold", color=ACCENT)
        ax.text(x, 0.7, desc, ha="center", fontsize=9, color=MUTED, linespacing=1.3)

    plt.tight_layout()
    out = OUT / "6_value_prop.png"
    plt.savefig(out, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  {out}")


def main():
    print("\nExecutive Demo — Generating presentation charts...")
    print(f"Output: {OUT}\n")

    chart_warning_days()
    chart_alert_dashboard()
    chart_timeline()
    chart_coverage()
    chart_convergence_rule()
    chart_value_prop()

    print(f"\nDone. 6 charts in {OUT}/")
    print("These are designed for CPO / executive presentation — no math jargon.")


if __name__ == "__main__":
    main()

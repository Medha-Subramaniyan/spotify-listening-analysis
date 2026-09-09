"""
Figures for the README case study.

Deliberately NOT a restatement of the Tableau dashboard, which already answers
"how much / when" (intentionality trend, retention curves, skip heatmap,
session anatomy). These go after questions it never asks, and read the
stream-level parquet rather than the pre-aggregated CSVs — a conditional result
like the shuffle x intent interaction only exists at the row level.

  00  KPI strip - framing numbers for the top of the page
  01  Shuffle is not the villain - the interaction the dashboard averages away
  02  What happens to 3,475 artists - the funnel from discovery to rotation
  03  First impressions - does a skipped first listen kill an artist?
  04  Taste is a power law - concentration of plays

Visual language departs from the dashboard on purpose: warm paper ground rather
than app-dark, clay against green, slope/funnel/area forms instead of
lines-and-bars.

Usage: python make_supplement.py
"""
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch
from pathlib import Path

OUT = Path("charts")
OUT.mkdir(exist_ok=True)
SRC = "spotify_cleaned.parquet"
ARTIST = "master_metadata_album_artist_name"

# --- Supplement palette: paper, not app -----------------------------------
PAPER   = "#F4F1EA"   # warm off-white ground
INK     = "#1A1A1A"   # near-black, never pure
INK_MID = "#6B6B6B"
INK_LOW = "#A8A29B"
GREEN   = "#137A3E"   # deliberate, darkened for light ground
CLAY    = "#B4472F"   # passive/algorithmic - warm counterweight
SAND    = "#C9B99B"   # ambiguous / structural fill

plt.rcParams.update({
    "figure.facecolor":  PAPER,
    "axes.facecolor":    PAPER,
    "savefig.facecolor": PAPER,
    "text.color":        INK,
    "axes.labelcolor":   INK_MID,
    "xtick.color":       INK_MID,
    "ytick.color":       INK_MID,
    "font.family":       "sans-serif",
    "font.sans-serif":   ["Avenir Next", "Avenir", "Helvetica Neue", "DejaVu Sans"],
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.spines.left":  False,
    "axes.spines.bottom":False,
    "axes.grid":         False,
    "figure.dpi":        160,
})
SAVE = dict(dpi=160, bbox_inches="tight", pad_inches=0.4, facecolor=PAPER)

DELIBERATE = {"clickrow", "playbtn", "backbtn"}
PASSIVE    = {"trackdone", "autoplay", "appload"}


def classify(reason):
    if reason in DELIBERATE:
        return "deliberate"
    return "passive" if reason in PASSIVE else "ambiguous"


def titleize(ax, title, subtitle=None):
    ax.set_title(title, loc="left", fontsize=16, fontweight="bold",
                 color=INK, pad=26 if subtitle else 12)
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1.02), xycoords="axes fraction",
                    fontsize=10, color=INK_MID, va="bottom")


def footer(fig, text):
    fig.text(0.5, -0.03, text, ha="center", fontsize=8, color=INK_LOW)


def artist_table(d):
    """One row per artist: discovery method, span, plays, distinct days."""
    d = d.sort_values("date")
    first = d.groupby(ARTIST).first()
    g = d.groupby(ARTIST).agg(first_date=("date", "min"),
                              last_date=("date", "max"),
                              plays=("date", "size"))
    g["span"] = (g.last_date - g.first_date).dt.days
    g["disc"] = first.reason_start.map(classify)
    g["first_skip"] = d.groupby(ARTIST).is_skip.first()
    g["days"] = d.groupby(ARTIST).date.apply(lambda s: s.dt.normalize().nunique())
    return g


# =========================================================================
# 00. KPI strip - framing numbers for the top of the page
# =========================================================================
def chart_kpis(d, g):
    hours = d.ms_played.sum() / 3.6e6
    passive = (~d.is_deliberate_start).mean() * 100
    once = (g.plays == 1).mean() * 100

    cards = [
        (f"{hours:,.0f}", "hours listened", "\u2248 190 days of continuous play", GREEN),
        (f"{len(g):,}",   "distinct artists", "over four years", INK),
        (f"{passive:.0f}%", "streams on autopilot",
         "started without a deliberate action", CLAY),
        (f"{once:.0f}%",  "artists played once", "and never again", CLAY),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(12, 2.6))
    for i, (ax, (big, label, sub, col)) in enumerate(zip(axes, cards)):
        ax.set_xticks([]); ax.set_yticks([])
        for name, sp in ax.spines.items():
            sp.set_visible(name == "left")
            if name == "left":
                sp.set_color("#DAD4C8"); sp.set_linewidth(1.2)
        if i == 0:
            ax.spines["left"].set_visible(False)
        ax.text(.5, .70, big, ha="center", va="center", fontsize=31,
                fontweight="bold", color=col, transform=ax.transAxes)
        ax.text(.5, .38, label, ha="center", va="center", fontsize=10,
                color=INK, transform=ax.transAxes)
        ax.text(.5, .18, sub, ha="center", va="center", fontsize=8.5,
                color=INK_LOW, transform=ax.transAxes)

    fig.subplots_adjust(wspace=.05)
    fig.savefig(OUT / "00_kpi.png", **SAVE)
    plt.close(fig)


# =========================================================================
# 01. The shuffle interaction
# =========================================================================
def chart_shuffle(d):
    t = (d.groupby(["shuffle", "is_deliberate_start"])
           .agg(skip=("is_skip", "mean"), n=("is_skip", "size")))
    t["skip"] *= 100

    fig, ax = plt.subplots(figsize=(10, 5.6))
    xs = [0, 1]
    for delib, color, label in [(True, GREEN, "I chose the track"),
                                (False, CLAY, "The queue chose it")]:
        ys = [t.loc[(False, delib), "skip"], t.loc[(True, delib), "skip"]]
        ax.plot(xs, ys, color=color, lw=2.6, zorder=3, solid_capstyle="round")
        ax.scatter(xs, ys, s=110, color=color, zorder=4,
                   edgecolor=PAPER, linewidth=2.5)
        # The two left-hand values sit ~1pt apart; push them apart vertically.
        ax.annotate(f"{ys[0]:.0f}%", xy=(0, ys[0]),
                    xytext=(-14, 7 if delib is False else -7),
                    textcoords="offset points", ha="right", va="center",
                    fontsize=12, fontweight="bold", color=color)
        ax.annotate(f"{ys[1]:.0f}%", xy=(1, ys[1]), xytext=(14, 0),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=12, fontweight="bold", color=color)
        ax.annotate(label, xy=(1, ys[1]), xytext=(14, -20),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=10, color=color)

    # The whole point: the lines diverge rather than shifting together.
    ax.annotate("", xy=(1.06, t.loc[(True, False), "skip"]),
                xytext=(1.06, t.loc[(True, True), "skip"]),
                arrowprops=dict(arrowstyle="<->", color=INK_MID, lw=1.2))
    ax.annotate("17-point\nspread", xy=(1.09, 42), fontsize=9.5,
                color=INK_MID, va="center", linespacing=1.4)
    # Left pair nearly coincides; brace it from further out so nothing overlaps.
    ax.annotate("", xy=(-0.115, t.loc[(False, False), "skip"]),
                xytext=(-0.115, t.loc[(False, True), "skip"]),
                arrowprops=dict(arrowstyle="<->", color=INK_MID, lw=1.2))
    ax.annotate("2-point spread", xy=(-0.145, 38), fontsize=9.5,
                color=INK_MID, va="center", ha="right")

    ax.set_xticks(xs)
    ax.set_xticklabels(["Shuffle OFF", "Shuffle ON"], fontsize=11, color=INK)
    ax.set_xlim(-0.42, 1.42)
    ax.set_ylim(28, 56)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.tick_params(length=0, labelsize=9)
    ax.set_ylabel("Skip rate", fontsize=9.5, labelpad=10)
    ax.grid(axis="y", color="#E2DED5", lw=.9)
    ax.set_axisbelow(True)

    titleize(ax,
             "Shuffle isn't the problem. Not choosing is.",
             "Turning shuffle on barely moves me when I picked the track — "
             "and wrecks the queue when I didn't")
    footer(fig, "184,805 streams · all four groups n > 28,000 · "
                "pattern holds independently in 2023, 2024 and 2025")
    fig.savefig(OUT / "01_shuffle_interaction.png", **SAVE)
    plt.close(fig)


# =========================================================================
# 02. Artist funnel
# =========================================================================
def chart_funnel(g):
    total = len(g)
    steps = [
        ("Artists I ever played",       total),
        ("Played more than once",       int((g.plays >= 2).sum())),
        ("Came back on another day",    int((g.days >= 2).sum())),
        ("Played on 5+ separate days",  int((g.days >= 5).sum())),
        ("Reached 20+ plays",           int((g.plays >= 20).sum())),
    ]

    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    ys = np.arange(len(steps))[::-1]
    maxv = steps[0][1]

    for y, (label, val) in zip(ys, steps):
        frac = val / maxv
        # Bar centered so the funnel tapers from both sides.
        # Deepen the fill as the funnel narrows: survivors get more weight.
        depth = .18 + .55 * (1 - y / (len(steps) - 1))
        ax.barh(y, frac, left=(1 - frac) / 2, height=.60,
                color=GREEN, alpha=depth, edgecolor=GREEN,
                linewidth=1.1, zorder=3)
        ax.annotate(label, xy=(.5, y + .40), ha="center", va="bottom",
                    fontsize=10.5, color=INK)
        ax.annotate(f"{val:,}   ({frac * 100:.0f}%)", xy=(.5, y - .03),
                    ha="center", va="center", fontsize=13,
                    fontweight="bold", color=PAPER if depth > .5 else INK)

    for i in range(len(steps) - 1):
        drop = steps[i][1] - steps[i + 1][1]
        y0, y1 = ys[i], ys[i + 1]
        ax.annotate(f"−{drop:,}", xy=(.955, (y0 + y1) / 2), ha="right",
                    va="center", fontsize=9.5, color=CLAY)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-.55, len(steps) - .30)
    ax.set_xticks([]); ax.set_yticks([])
    titleize(ax,
             "Most artists never get a second day",
             "Of 3,475 artists I have ever pressed play on, only a quarter "
             "ever reach 20 plays")
    footer(fig, "A 'day' is a distinct calendar date with at least one stream")
    fig.savefig(OUT / "02_artist_funnel.png", **SAVE)
    plt.close(fig)


# =========================================================================
# 03. First impressions
# =========================================================================
def chart_first_impression(g):
    sub = g[g.disc.isin(["deliberate", "passive"])]
    r = (sub.groupby(["disc", "first_skip"])
            .agg(ret=("days", lambda s: (s > 1).mean() * 100),
                 n=("days", "size")))

    fig, ax = plt.subplots(figsize=(10, 5.4))
    groups = [("deliberate", GREEN, "I sought them out"),
              ("passive",    CLAY,  "The algorithm served them")]
    width = .3

    for i, (disc, color, label) in enumerate(groups):
        for j, (skip, alpha, hatch) in enumerate([(False, 1.0, None),
                                                  (True, .30, None)]):
            val = r.loc[(disc, skip), "ret"]
            n = int(r.loc[(disc, skip), "n"])
            x = i + (j - .5) * width * 1.15
            ax.bar(x, val, width=width, color=color, alpha=alpha,
                   edgecolor=color, linewidth=1.4, zorder=3)
            ax.annotate(f"{val:.0f}%", xy=(x, val), xytext=(0, 6),
                        textcoords="offset points", ha="center",
                        fontsize=12, fontweight="bold", color=INK)
            # Below the axis: legible regardless of how dark the bar is.
            ax.annotate(f"n={n:,}", xy=(x, -3.5), ha="center", va="top",
                        fontsize=8, color=INK_MID, annotation_clip=False)
        ax.annotate(label, xy=(i, -11), ha="center", fontsize=11, color=INK,
                    annotation_clip=False)

    ax.annotate("Solid = finished the first track   ·   "
                "Faded = skipped the first track",
                xy=(.5, .95), xycoords="axes fraction", ha="center",
                fontsize=9.5, color=INK_MID)

    ax.set_xticks([]); ax.set_xlim(-.5, 1.5); ax.set_ylim(0, 95)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.tick_params(length=0, labelsize=9)
    ax.set_ylabel("Came back on a later day", fontsize=9.5, labelpad=10)
    ax.grid(axis="y", color="#E2DED5", lw=.9)
    ax.set_axisbelow(True)

    titleize(ax,
             "A bad first impression is survivable — if I chose you",
             "Share of artists played again on a later day, by how their "
             "very first track ended")
    footer(fig, "Artists whose first stream was ambiguous are excluded · "
                "algorithm-served artists whose first track I skipped are the "
                "smallest group (n=144), so that bar is the least certain")
    fig.savefig(OUT / "03_first_impression.png", **SAVE)
    plt.close(fig)


# =========================================================================
# 04. Power law
# =========================================================================
def chart_power_law(g):
    s = g.plays.sort_values(ascending=False).values
    cum = np.cumsum(s) / s.sum() * 100
    rank = np.arange(1, len(s) + 1)

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.fill_between(rank, cum, color=GREEN, alpha=.13, zorder=2)
    ax.plot(rank, cum, color=GREEN, lw=2.4, zorder=3)

    for k, note in [(10, None), (50, "half my listening"), (100, None)]:
        y = cum[k - 1]
        ax.plot([k, k], [0, y], color=INK_LOW, lw=.8, ls=(0, (3, 3)), zorder=1)
        ax.scatter([k], [y], s=44, color=GREEN, zorder=5,
                   edgecolor=PAPER, linewidth=2)
        txt = f"Top {k}\n{y:.0f}%" + (f"\n{note}" if note else "")
        ax.annotate(txt, xy=(k, y), xytext=(9, -16), textcoords="offset points",
                    fontsize=9.5, color=INK, linespacing=1.45,
                    fontweight="bold" if note else "normal")

    tail = (g.plays == 1).sum()
    ax.annotate(f"The other {len(s) - 500:,} artists split the last 10%.\n"
                f"{tail:,} of them I played exactly once.",
                xy=(1500, 62), fontsize=9.5, color=INK_MID, linespacing=1.5)

    ax.set_xscale("log")
    ax.set_xlim(1, len(s))
    ax.set_ylim(0, 103)
    ax.set_xticks([1, 10, 100, 1000, 3475])
    ax.set_xticklabels(["1", "10", "100", "1,000", "3,475"], fontsize=9)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.tick_params(length=0, labelsize=9)
    ax.set_xlabel("Artists, ranked by play count (log scale)",
                  fontsize=9.5, labelpad=8)
    ax.set_ylabel("Cumulative share of all plays", fontsize=9.5, labelpad=10)
    ax.grid(axis="y", color="#E2DED5", lw=.9)
    ax.set_axisbelow(True)

    titleize(ax,
             "Four years of discovery, spent on fifty artists",
             "Cumulative share of 184,805 streams by artist rank")
    footer(fig, "Log x-axis · 3,475 artists total")
    fig.savefig(OUT / "04_power_law.png", **SAVE)
    plt.close(fig)


if __name__ == "__main__":
    d = pd.read_parquet(SRC)
    g = artist_table(d)
    chart_kpis(d, g)
    chart_shuffle(d)
    chart_funnel(g)
    chart_first_impression(g)
    chart_power_law(g)
    for p in sorted(OUT.glob("*.png")):
        print(f"  {p}  ({p.stat().st_size / 1024:.0f} KB)")

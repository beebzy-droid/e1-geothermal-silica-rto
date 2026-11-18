"""
closed_loop_figure.py — E1 / ipis-thesis-geothermal-silica
P8b: the closed-loop safety-harvest figure (both regimes, all arms).

    cd src && python closed_loop_figure.py

Reads results/table2_control.csv (benign) and results/table2b_stress.csv
(stress), written by run_control_experiment.py and
run_stress_experiment.py, and draws for each regime the mean power uplift
against the mean number of constraint-violation days per 45-day episode.

ENCODING
    * The three measured-anchored correction families are drawn as
      FRONTIER CURVES over the back-off gain kappa (0, 0.5, 1, 2); the
      gain is printed beside each point. Hue + marker shape identify the
      family (never hue alone).
    * Reference arms (fixed practice, open-loop robust RTO) and the
      anchoring-ablation arms are single neutral markers with direct
      labels.
    * Bars are seeded percentile-bootstrap 95% intervals of the mean over
      plants (plants are the resampling unit).
    * The y-axis is symmetric-log (linear below 1 day) because the arms
      span 0 to ~20 violation days; the caption says so.

Outputs: figures/fig_closed_loop_frontier.png (300 dpi) and .pdf (vector)
         results/closed_loop_frontier.csv (the plotted numbers)
"""

from pathlib import Path

import numpy as np
import pandas as pd

RESULTS = Path(__file__).parent.parent / "results"
FIGURES = Path(__file__).parent.parent / "figures"

KAPPA_FAMILIES = {            # family -> (label, hue, marker)
    "rto_ma_meas": ("Scalar correction, measured silica", "#2a78d6", "o"),
    "rto_gp":      ("GP residual, measured silica",      "#eb6834", "D"),
    "rto_hybrid":  ("Hybrid sensor, measured silica",    "#1baf7a", "s"),
}
FIXED = {                     # arm -> (label, marker)
    "baseline":       ("Fixed practice", "P"),
    "rto_nominal":    ("Robust optimum, no feedback", "^"),
    "rto_ma_nom":     ("Scalar correction, design case", "X"),
    "rto_malog_nom":  ("Log-space correction, design case", "*"),
    "rto_malog_meas": ("Log-space correction, measured silica", "v"),
}
INK = "#0b0b0b"
MUTED = "#52514e"
NEUTRAL = "#6b6a66"

# Direct labels for the single-marker arms: text position in DATA
# coordinates per regime (tuned by eye on the 20-plant results), joined to
# the marker by a thin leader so crowded corners stay legible.
LABEL_XY = {
    "benign": {"baseline": (-27, 0.22), "rto_nominal": (52, 1.30),
               "rto_ma_nom": (30, 3.0), "rto_malog_nom": (44, 10.5),
               "rto_malog_meas": (-27, 1.10)},
    "stress": {"baseline": (-22, 0.06), "rto_nominal": (2, 24.0),
               "rto_ma_nom": (2, 7.0), "rto_malog_nom": (2, 13.0),
               "rto_malog_meas": (-56, 0.85)},
}
XLIM = {"benign": (-30, 125), "stress": (-60, 48)}
# where the kappa end-labels sit relative to each family's end points
KAPPA_END_OFFSET = {"rto_ma_meas": {"0": (12, -12), "2": (-4, -15)},
                    "rto_gp":      {"0": (-22, 6),  "2": (-6, 10)},
                    "rto_hybrid":  {"0": (12, 4),   "2": (-14, 9)}}


def _boot_ci(x: np.ndarray, n_boot: int = 4000, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    m = x[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def frontier_table() -> pd.DataFrame:
    rows = []
    for regime, fn in (("benign", "table2_control.csv"),
                       ("stress", "table2b_stress.csv")):
        df = pd.read_csv(RESULTS / fn)
        base = df[df.arm == "baseline"].set_index("plant")["gross_mw_mean"]
        df["uplift_pct"] = [100 * (r.gross_mw_mean / base[r.plant] - 1)
                            for r in df.itertuples()]
        for arm, g in df.groupby("arm", sort=False):
            u = g["uplift_pct"].to_numpy(dtype=float)
            v = g["violation_days"].to_numpy(dtype=float)
            w = g["viol_days_postwarmup"].to_numpy(dtype=float)
            ulo, uhi = _boot_ci(u)
            vlo, vhi = _boot_ci(v)
            rows.append((regime, arm, len(g), u.mean(), ulo, uhi,
                         v.mean(), vlo, vhi, w.mean(), int(v.max())))
    return pd.DataFrame(rows, columns=[
        "regime", "arm", "n_plants", "uplift_mean", "uplift_lo",
        "uplift_hi", "viol_mean", "viol_lo", "viol_hi",
        "viol_postwu_mean", "viol_max"])


CONTRASTS = (          # (regime, a, b): reported as mean of (a - b)
    ("benign", "rto_ma_nom", "rto_ma_meas_k0"),
    ("stress", "rto_ma_nom", "rto_ma_meas_k0"),
    ("stress", "rto_malog_nom", "rto_malog_meas"),
    ("benign", "rto_hybrid_k0", "rto_ma_meas_k0"),
    ("stress", "rto_hybrid_k0", "rto_ma_meas_k0"),
    ("stress", "rto_hybrid_k0.5", "rto_ma_meas_k0.5"),
    ("stress", "rto_hybrid_k1", "rto_ma_meas_k1"),
    ("stress", "rto_hybrid_k2", "rto_ma_meas_k2"),
    ("stress", "rto_gp_k0", "rto_ma_meas_k0"),
    ("stress", "rto_gp_k0.5", "rto_ma_meas_k0.5"),
    ("stress", "rto_gp_k1", "rto_ma_meas_k1"),
    ("stress", "rto_gp_k2", "rto_ma_meas_k2"),
    ("stress", "rto_hybrid_k1", "rto_hybrid_k0"),
    ("stress", "rto_ma_meas_k1", "rto_ma_meas_k0"),
    ("stress", "rto_gp_k1", "rto_gp_k0"),
)


def contrasts_table() -> pd.DataFrame:
    """Paired differences (same plants, same brine realizations) with
    seeded percentile-bootstrap 95% intervals; plants are resampled."""
    data = {}
    for regime, fn in (("benign", "table2_control.csv"),
                       ("stress", "table2b_stress.csv")):
        df = pd.read_csv(RESULTS / fn)
        base = df[df.arm == "baseline"].set_index("plant")["gross_mw_mean"]
        df["uplift_pct"] = [100 * (r.gross_mw_mean / base[r.plant] - 1)
                            for r in df.itertuples()]
        data[regime] = df
    rows = []
    for regime, a, b in CONTRASTS:
        df = data[regime]
        for col in ("uplift_pct", "violation_days", "viol_days_postwarmup"):
            pa = df[df.arm == a].set_index("plant")[col]
            pb = df[df.arm == b].set_index("plant")[col]
            d = (pa - pb.reindex(pa.index)).to_numpy(dtype=float)
            lo, hi = _boot_ci(d)
            rows.append((regime, a, b, col, len(d), d.mean(), lo, hi,
                         bool(lo > 0 or hi < 0)))
    out = pd.DataFrame(rows, columns=["regime", "a", "b", "metric",
                                      "n_plants", "mean_a_minus_b",
                                      "ci_lo", "ci_hi", "ci_excludes_0"])
    out.round(3).to_csv(RESULTS / "closed_loop_contrasts.csv", index=False)
    return out


def make_figure() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    FIGURES.mkdir(exist_ok=True)
    tab = frontier_table()
    tab.round(3).to_csv(RESULTS / "closed_loop_frontier.csv", index=False)

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "pdf.fonttype": 42})
    # two stacked panels sized for a single journal column-width page
    # (about 7 in wide), so the direct labels print at a readable size
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 8.6))
    titles = {"benign": "(a) Benign regime: random per-plant mismatch",
              "stress": "(b) Stress regime: true kinetics six times the "
                        "model"}

    for ax, regime in zip(axes, ("benign", "stress")):
        t = tab[tab.regime == regime].set_index("arm")
        ax.set_yscale("symlog", linthresh=1.0, linscale=1.0)
        ax.set_ylim(-0.12, 30)
        ax.set_yticks([0, 0.5, 1, 2, 5, 10, 20])
        ax.set_yticklabels(["0", "0.5", "1", "2", "5", "10", "20"])
        ax.minorticks_off()
        ax.grid(True, color="#e4e3df", lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)

        # reference + anchoring-ablation arms: neutral single markers
        for arm, (label, mk) in FIXED.items():
            r = t.loc[arm]
            ax.errorbar(r.uplift_mean, r.viol_mean,
                        xerr=[[r.uplift_mean - r.uplift_lo],
                              [r.uplift_hi - r.uplift_mean]],
                        yerr=[[r.viol_mean - r.viol_lo],
                              [r.viol_hi - r.viol_mean]],
                        fmt="none", ecolor=NEUTRAL, elinewidth=0.8,
                        zorder=2)
            ax.plot(r.uplift_mean, r.viol_mean, mk, ms=8, color=NEUTRAL,
                    mec="white", mew=1.0, zorder=3)
            ax.annotate(label, (r.uplift_mean, r.viol_mean),
                        xytext=LABEL_XY[regime][arm], textcoords="data",
                        fontsize=7.5, color=INK, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=NEUTRAL,
                                        lw=0.6, shrinkA=1, shrinkB=5))

        # the three measured-anchored families as frontier curves
        for fam, (label, hue, mk) in KAPPA_FAMILIES.items():
            arms = [a for a in t.index if a.startswith(fam + "_k")]
            arms.sort(key=lambda a: float(a.rpartition("_k")[2]))
            x = t.loc[arms, "uplift_mean"].to_numpy()
            y = t.loc[arms, "viol_mean"].to_numpy()
            ax.errorbar(x, y,
                        xerr=[x - t.loc[arms, "uplift_lo"].to_numpy(),
                              t.loc[arms, "uplift_hi"].to_numpy() - x],
                        yerr=[y - t.loc[arms, "viol_lo"].to_numpy(),
                              t.loc[arms, "viol_hi"].to_numpy() - y],
                        fmt="none", ecolor=hue, elinewidth=0.8, alpha=0.7,
                        zorder=2)
            ax.plot(x, y, "-", color=hue, lw=2.0, zorder=3)
            ax.plot(x, y, mk, ms=8, color=hue, mec="white", mew=1.2,
                    zorder=4)
            # label only the two ends of each curve; the interior points
            # are kappa = 0.5 and 1 in order (stated in the caption)
            if regime == "stress":
                for a, xi, yi in ((arms[0], x[0], y[0]),
                                  (arms[-1], x[-1], y[-1])):
                    k = a.rpartition("_k")[2]
                    ax.annotate(rf"$\kappa$={k}", (xi, yi),
                                xytext=KAPPA_END_OFFSET[fam][k],
                                textcoords="offset points", fontsize=7.5,
                                color=INK, ha="center")

        if regime == "benign":
            ax.annotate("all three families, every gain:\n"
                        r"0 to 0.15 violation days ($\kappa$ = 0 at right)",
                        (33, 0.02), xytext=(56, 0.30), textcoords="data",
                        fontsize=7.5, color=INK, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=NEUTRAL,
                                        lw=0.6, shrinkA=1, shrinkB=4))
        ax.set_xlim(*XLIM[regime])
        ax.set_title(titles[regime], fontsize=10, color=INK, loc="left")
        ax.set_xlabel("Gross power gain over fixed practice [%]")
        ax.set_ylabel("Violation days per 45-day run\n"
                      "(mean over plants; linear below 1, log above)")

    handles = [Line2D([], [], color=hue, marker=mk, ms=7, lw=2,
                      mec="white", label=label)
               for (label, hue, mk) in KAPPA_FAMILIES.values()]
    handles += [Line2D([], [], color=NEUTRAL, marker="P", ms=7, lw=0,
                       mec="white",
                       label="Reference and anchoring-ablation arms "
                             "(labelled in the panels)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=8, bbox_to_anchor=(0.5, 0.0),
               title=r"Curves run over the back-off gain $\kappa$ = 0, "
                     "0.5, 1, 2 (ends labelled); bars: 95% bootstrap "
                     "intervals of the mean",
               title_fontsize=8)
    fig.tight_layout(rect=(0, 0.085, 1, 1), h_pad=1.6)
    p = FIGURES / "fig_closed_loop_frontier.png"
    fig.savefig(p, dpi=300)
    fig.savefig(FIGURES / "fig_closed_loop_frontier.pdf", metadata={"CreationDate": None})
    plt.close(fig)
    return str(p)


def refresh():
    """Redraw the figure, rewrite the contrasts and stamp them — only when
    both regimes have full-scale results on disk."""
    if not all((RESULTS / f).exists() for f in ("table2_control.csv",
                                                "table2b_stress.csv")):
        return None
    a = pd.read_csv(RESULTS / "table2_control.csv")
    b = pd.read_csv(RESULTS / "table2b_stress.csv")
    if set(a.arm) != set(b.arm):
        return None                # one regime is from an older arm set
    p = make_figure()
    contrasts_table()
    from provenance import stamp
    stamp("frontier")
    return p


if __name__ == "__main__":
    print("Wrote", refresh() or "(nothing: both regimes must have run)")
    c = contrasts_table()
    print("\nPAIRED CONTRASTS (a - b; 95% bootstrap interval; * = excludes 0)")
    for r in c.itertuples():
        print(f"  {r.regime:6s} {r.a:17s} - {r.b:17s} {r.metric:21s} "
              f"{r.mean_a_minus_b:+7.2f} [{r.ci_lo:+7.2f}, {r.ci_hi:+7.2f}]"
              f"{' *' if r.ci_excludes_0 else ''}")

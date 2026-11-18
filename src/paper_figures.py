"""
paper_figures.py — E1 / ipis-thesis-geothermal-silica
Journal versions of six manuscript figures (Geothermics submission).

    cd src && python paper_figures.py

WHAT THIS DOES
    The gate modules write DIAGNOSTIC figures (titles on the plot, code
    names, evidence-tier tags). This module redraws the same data for the
    paper: no title on the plot (the caption carries it, as the journal's
    artwork rules ask), text legible at the printed width (8 pt at 90 or
    190 mm), and plain-language labels that match the manuscript. It runs
    NO experiment: every number comes from a committed result file or from
    the deterministic model functions, and where it recomputes anything it
    first checks that it reproduces the stored values.

    fig_paper_arrhenius   <- temperature_lever (primary k(T) fits)
    fig_paper_lever       <- temperature_lever (archetype brine)
    fig_paper_kinetics    <- results/kinetics_validation.csv + per-order
                             R^2 recomputed with kinetics_validation's own
                             windowing (needs the Scott 2024 data file)
    fig_paper_scarcity    <- results/scarcity_sweep.csv
    fig_paper_sensor      <- results/sensor_validation_scott.csv + one
                             replayed experiment (needs the Scott data)
    fig_paper_sobol       <- results/sensitivity_sobol.csv

    The closed-loop frontier is already in journal form
    (closed_loop_figure.py) and is not redrawn here.

Outputs: figures/fig_paper_<name>.pdf (vector) and .png (300 dpi).
"""

from pathlib import Path
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = ROOT / "figures"

MM = 1 / 25.4
SINGLE, FULL = 90 * MM, 190 * MM          # journal column widths [in]

INK, MUTED, GRID = "#1a1a1a", "#555555", "#e6e6e6"
BLUE, GREEN, RED = "#2a78d6", "#1baf7a", "#c0392b"
GRAY, VIOLET = "#6b6b6b", "#8e6bbf"


def _style(plt):
    plt.rcParams.update({
        "font.size": 8, "axes.labelsize": 8.5, "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "legend.frameon": False,
        "pdf.fonttype": 42, "savefig.dpi": 300,
    })


def _save(fig, name: str) -> Path:
    FIG.mkdir(exist_ok=True)
    p = FIG / f"fig_paper_{name}.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(p.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.03,
                metadata={"CreationDate": None})
    return p


def _panel(ax, letter: str) -> None:
    ax.text(-0.02, 1.02, f"({letter})", transform=ax.transAxes,
            fontsize=9, fontweight="bold", color=INK, ha="right",
            va="bottom")


# ---------------------------------------------------------------------------
# 1. Non-Arrhenius rate constant
# ---------------------------------------------------------------------------

def fig_arrhenius(plt) -> dict:
    from temperature_lever import _FITS, _T_NODES, _LOGK_NODES
    T_low = [5.0, 30.0, 60.0, 90.0]
    x_low = np.array([1.0 / (t + 273.15) for t in T_low])
    y_low = np.array([math.log(_FITS[t]["k"]) for t in T_low])
    slope, intercept = np.polyfit(x_low, y_low, 1)
    ea = -slope * 8.314 / 1000.0
    invT = 1.0 / (np.asarray(_T_NODES) + 273.15)
    k150_arr = intercept + slope / 423.15
    k150_fit = math.log(_FITS[150.0]["k"])
    over = math.exp(k150_arr - k150_fit)
    assert abs(ea - 9.1) < 0.05 and abs(over - 3.0) < 0.05, \
        "Arrhenius numbers moved; update the manuscript"

    fig, ax = plt.subplots(figsize=(SINGLE, 68 * MM))
    xs = np.linspace(invT.min() * 0.985, invT.max() * 1.015, 100)
    ax.plot(1000 * xs, intercept + slope * xs, "--", color=RED, lw=1.2,
            label=f"Arrhenius fit, 5–90 °C ($E_a$ = {ea:.1f} kJ mol$^{{-1}}$)")
    ax.plot(1000 * invT, _LOGK_NODES, "o", color=INK, ms=4.5,
            label="Fitted constants (Rothbaum and Rohde, 1979)")
    for t, (dx, dy) in {5: (-16, 6), 90: (4, 4), 150: (5, -9),
                        180: (5, 2)}.items():
        i = list(_T_NODES).index(t)
        ax.annotate(f"{t:g} °C", (1000 * invT[i], _LOGK_NODES[i]),
                    textcoords="offset points", xytext=(dx, dy),
                    fontsize=7, color=MUTED)
    x150 = 1000 / 423.15
    ax.annotate("", xy=(x150, k150_fit + 0.04), xytext=(x150, k150_arr),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=0.9))
    ax.text(x150 - 0.025, 0.5 * (k150_fit + k150_arr) - 0.05,
            f"×{over:.1f}\nat 150 °C", color=RED, fontsize=7.5,
            va="center", ha="right")
    ax.set_xlabel("1000/$T$ (K$^{-1}$)")
    ax.set_ylabel("ln $k$  ($k$ in (g t$^{-1}$)$^{-3}$ min$^{-1}$)")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.30 * (hi - lo))     # headroom for the legend
    ax.legend(loc="upper right", handlelength=1.8)
    _save(fig, "arrhenius"); plt.close(fig)
    return {"Ea": ea, "over150": over}


# ---------------------------------------------------------------------------
# 2. Temperature lever
# ---------------------------------------------------------------------------

def fig_lever(plt) -> dict:
    from temperature_lever import archetype_brine_sio2, line_rate
    from silica_saturation import solubility_amorphous_silica_ga00
    c = archetype_brine_sio2()
    Ts = np.linspace(60.0, 180.0, 241)
    rate = np.array([line_rate(c, t) for t in Ts])
    sup = np.array([max(c - solubility_amorphous_silica_ga00(t + 273.15),
                        0.0) for t in Ts])
    r90, r150 = line_rate(c, 90.0), line_rate(c, 150.0)
    assert abs(r90 / r150 - 101) < 1.0, "lever ratio moved"

    fig, ax = plt.subplots(figsize=(SINGLE, 68 * MM))
    ax.semilogy(Ts, np.maximum(rate, 1e-12), color=BLUE, lw=1.6,
                label="Polymerization rate (left axis)")
    ax.set_ylim(1e-5, 50)
    ax.set_xlabel("Reinjection temperature (°C)")
    ax.set_ylabel("Polymerization rate (g t$^{-1}$ min$^{-1}$)")
    for t in (90.0, 120.0, 150.0):
        r = line_rate(c, t)
        ax.plot([t], [r], "o", color=BLUE, ms=4)
        ax.annotate(f"{r:.3g}", (t, r), textcoords="offset points",
                    xytext=(5, 5), fontsize=7, color=BLUE)
    ax2 = ax.twinx()
    ax2.plot(Ts, sup, ":", color=GRAY, lw=1.3,
             label="Supersaturation (right axis)")
    ax2.set_ylabel("Supersaturation $C - C_e$ (mg kg$^{-1}$)", color=MUTED)
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    ax2.set_ylim(0, None)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left")
    _save(fig, "lever"); plt.close(fig)
    return {"c_brine": c, "ratio": r90 / r150}


# ---------------------------------------------------------------------------
# 3. Kinetic test against Scott et al. (2024)
# ---------------------------------------------------------------------------

def _order_r2_table(kv: pd.DataFrame) -> pd.DataFrame:
    """R^2 of the integrated n-th-order linearization, n = 2..6, for each
    experiment of kinetics_validation.csv, with that module's own window."""
    from kinetics_validation import _window, _linfit_r2, ORDER_CANDIDATES
    from scott2024_dataset import load_scott2024
    from silica_saturation import solubility_amorphous_silica_ga00
    data = load_scott2024()
    rows = []
    for r in kv.itertuples():
        g = data.series[data.series.experiment == r.experiment]
        c, t = g.sio2_mgkg.to_numpy(), g.time_min.to_numpy()
        ce = solubility_amorphous_silica_ga00(r.T_C + 273.15)
        u = c - ce
        m = _window(t, u)
        tw, uw = t[m], u[m]
        for n in ORDER_CANDIDATES:
            rows.append((r.experiment, n,
                         _linfit_r2(tw, uw ** (-(n - 1)))[2]))
    out = pd.DataFrame(rows, columns=["experiment", "order", "r2"])
    # integrity: reproduce the stored order-2 and order-4 values
    for n, col in ((2, "r2_order2"), (4, "r2_order4")):
        mine = out[out.order == n].set_index("experiment").r2
        assert np.allclose(mine.loc[kv.experiment].to_numpy(),
                           kv[col].to_numpy(), atol=1e-9), \
            f"recomputed R^2 at order {n} differs from the stored value"
    return out


def fig_kinetics(plt) -> dict:
    kv = pd.read_csv(RES / "kinetics_validation.csv")
    r2 = _order_r2_table(kv)
    med = r2.groupby("order").r2.median()
    assert (np.diff(med.to_numpy()) < 0).all(), \
        "median R^2 no longer falls with the assumed order"

    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL, 70 * MM),
                               gridspec_kw={"width_ratios": [1.15, 1]})
    x = 1000.0 / (kv.T_C + 273.15)
    sl, ic = np.polyfit(x, np.log(kv.k2_scott), 1)
    ea = abs(sl) * 8.314
    sc = a.scatter(x, np.log(kv.k2_scott), c=kv.pH, cmap="viridis", s=26,
                   edgecolor=INK, linewidth=0.4, zorder=3)
    xs = np.linspace(x.min(), x.max(), 50)
    a.plot(xs, ic + sl * xs, "--", color=RED, lw=1.2,
           label=f"Arrhenius trend ($E_a$ ≈ {ea:.0f} kJ mol$^{{-1}}$)")
    cb = fig.colorbar(sc, ax=a, pad=0.02, fraction=0.05)
    cb.set_label("pH", fontsize=8); cb.ax.tick_params(labelsize=7)
    a.set_xlabel("1000/$T$ (K$^{-1}$)")
    a.set_ylabel("ln $k_2$  ($k_2$ in (g t$^{-1}$)$^{-1}$ min$^{-1}$)")
    a.legend(loc="lower left")
    _panel(a, "a")

    for e, g in r2.groupby("experiment"):
        b.plot(g.order, g.r2, "-", color="#b9b9b9", lw=0.8, zorder=2)
    b.plot(med.index, med.to_numpy(), "o-", color=INK, lw=1.6, ms=4.5,
           zorder=3, label=f"Median of {kv.experiment.nunique()} experiments")
    b.plot([], [], "-", color="#b9b9b9", lw=0.8, label="Single experiments")
    b.annotate("fourth order: the peak-rate\nlaw of Rothbaum and Rohde (1979)",
               (4, med.loc[4]), xytext=(4.25, 0.985), textcoords="data",
               fontsize=7, color=MUTED, ha="left", va="center",
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6,
                               shrinkA=2, shrinkB=4))
    b.set_xticks(list(med.index))
    b.set_xlabel("Assumed reaction order $n$")
    b.set_ylabel("$R^2$ of the integrated $n$-th-order fit")
    lo = max(0.0, float(np.floor(r2.r2.min() * 20) / 20))
    b.set_ylim(lo, 1.005)
    b.legend(loc="lower left")
    _panel(b, "b")
    fig.tight_layout(w_pad=2.0)
    _save(fig, "kinetics"); plt.close(fig)
    return {"Ea": ea, "median_r2": med.round(4).to_dict()}


# ---------------------------------------------------------------------------
# 4. Estimation versus label scarcity
# ---------------------------------------------------------------------------

def fig_scarcity(plt) -> dict:
    sc = pd.read_csv(RES / "scarcity_sweep.csv")
    fig, ax = plt.subplots(figsize=(SINGLE, 66 * MM))
    for arm, label, col, mk, off in (
            ("physics", "Kinetic core", GRAY, "s", -0.8),
            ("pure_ml", "Data-driven", VIOLET, "D", 0.0),
            ("hybrid", "Hybrid sensor", GREEN, "o", 0.8)):
        g = sc[sc.arm == arm].sort_values("train_days")
        ax.errorbar(g.train_days + off, g.rmse_log1p_mean,
                    yerr=g.rmse_log1p_sd, fmt=mk + "-", color=col, ms=4,
                    lw=1.3, elinewidth=0.8, capsize=2, label=label)
    ax.set_xlabel("Training history (days = number of daily labels)")
    ax.set_ylabel("Test RMSE in log(1 + rate)")
    ax.set_xticks(sorted(sc.train_days.unique()))
    top = float((sc.rmse_log1p_mean + sc.rmse_log1p_sd).max())
    ax.set_ylim(0, top * 1.28)                 # a row of headroom
    ax.legend(loc="upper center", ncol=3, columnspacing=1.0,
              handlelength=1.6, handletextpad=0.4, fontsize=7)
    _save(fig, "scarcity"); plt.close(fig)
    return {}


# ---------------------------------------------------------------------------
# 5. The correction pattern on laboratory decay curves
# ---------------------------------------------------------------------------

def fig_sensor(plt) -> dict:
    from sensor_validation_scott import build_intervals, predict_arms
    from scott2024_dataset import load_scott2024
    res = pd.read_csv(RES / "sensor_validation_scott.csv")
    exps = build_intervals(load_scott2024())
    K = 3
    resK = res[res.K == K]
    name = (resK.groupby("experiment")["n_test"].first()
            .sort_values(ascending=False).index[0])
    ex = next(e for e in exps if e.experiment == name)
    preds, params = predict_arms(ex, K)
    # integrity: the replay reproduces the stored test RMSE of this curve
    for arm, p in preds.items():
        e = np.log(np.maximum(p, 1e-300)) - np.log(ex.r_obs[K:])
        stored = resK[(resK.experiment == name) & (resK.arm == arm)].rmse_ln
        assert abs(float(np.sqrt(np.mean(e ** 2))) - float(stored.iloc[0])) \
            < 1e-9, f"replay of {name} differs from the stored result"

    ARMS = (("physics", "Kinetic core", GRAY, "s", "--"),
            ("hybrid_scalar", "Offset correction (1 parameter)", BLUE, "^",
             "-"),
            ("hybrid_affine", "Unrestrained affine correction", RED, "x",
             ":"),
            ("hybrid_credible", "Credibility-selected correction", GREEN,
             "o", "-"))
    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL, 78 * MM))
    th = ex.t_mid / 60.0
    handles = {}
    handles["obs"], = a.loglog(th, ex.r_obs, "o", color=INK, ms=3.5,
                               mfc="white", mew=0.9, zorder=4,
                               label="Observed interval rate")
    for arm, label, col, mk, ls in ARMS:
        if arm == "hybrid_credible":
            continue        # identical to the offset at K = 3 (caption)
        handles[arm], = a.loglog(th[K:], preds[arm], mk + ls, color=col,
                                 ms=3, lw=1.1, label=label)
    edge = math.sqrt(th[K - 1] * th[K])
    a.axvspan(th[0] / 1.4, edge, color="#efefef", zorder=0)
    a.text(math.sqrt(th[0] / 1.4 * edge), 0.03, f"{K} labels",
           transform=a.get_xaxis_transform(), ha="center", va="bottom",
           fontsize=7, color=MUTED)
    a.set_xlabel("Time (h)")
    a.set_ylabel("Polymerization rate (g t$^{-1}$ min$^{-1}$)")
    _panel(a, "a")

    med = res.groupby(["K", "arm"]).rmse_ln.median().unstack()
    for arm, label, col, mk, ls in ARMS:
        h, = b.semilogy(med.index, med[arm], mk + ls, color=col, ms=4,
                        lw=1.2, label=label)
        handles.setdefault(arm, h)
    ticks = [2.5, 3, 4, 6, 10, 20]
    b.set_yticks(ticks)
    b.set_yticklabels([f"{t:g}" for t in ticks])
    b.minorticks_off()
    b.set_ylim(2.3, 25)
    b.set_xticks(sorted(res.K.unique()))
    b.set_xlabel("Labels per experiment $K$")
    b.set_ylabel("Median test RMSE in ln(rate)")
    _panel(b, "b")
    order = ["obs", "physics", "hybrid_scalar", "hybrid_affine",
             "hybrid_credible"]
    fig.legend([handles[k] for k in order],
               [handles[k].get_label() for k in order], loc="lower center",
               ncol=3, bbox_to_anchor=(0.5, 0.0), fontsize=7.5,
               columnspacing=1.4, handlelength=2.2)
    fig.tight_layout(w_pad=2.0, rect=(0, 0.13, 1, 1))
    _save(fig, "sensor"); plt.close(fig)
    return {"experiment": name, "T_C": ex.T_C, "pH": ex.pH,
            "b_affine": params.get("b_affine")}


# ---------------------------------------------------------------------------
# 7. Sobol indices
# ---------------------------------------------------------------------------

PARAM_LABEL = {
    "logk_shift": "Kinetic level", "ce_scale": "Solubility",
    "flash": "Flash fraction", "eta_max": "Maximum inhibitor suppression",
    "d_opt_ppm": "Dose of maximum effect", "r_max": "Scaling limit $r_{max}$",
    "eta_binary": "Conversion effectiveness", "price_kwh": "Electricity price"}
QOI_LABEL = {"gross_mw": "Gross power", "T_opt_C": "Optimal reinjection "
             "temperature", "dose_opt_ppm": "Optimal inhibitor dose",
             "net_php_h": "Net objective"}


def fig_sobol(plt) -> dict:
    sb = pd.read_csv(RES / "sensitivity_sobol.csv")
    params = list(PARAM_LABEL)
    fig, axes = plt.subplots(2, 2, figsize=(FULL, 112 * MM), sharex=True)
    y = np.arange(len(params))[::-1]
    for ax, (q, letter) in zip(axes.flat, zip(QOI_LABEL, "abcd")):
        g = sb[sb.qoi == q].set_index("param").loc[params]
        ax.barh(y + 0.19, g.ST.clip(lower=0), height=0.36, color=BLUE,
                label="Total order $S_T$")
        ax.barh(y - 0.19, g.S1.clip(lower=0), height=0.36, color="#9cc3ee",
                label="First order $S_1$")
        ax.set_yticks(y)
        ax.set_yticklabels([PARAM_LABEL[p] for p in params]
                           if letter in "ac" else [])
        ax.set_xlim(0, 1.0)
        ax.grid(axis="y", visible=False)
        ax.set_title(f"({letter}) {QOI_LABEL[q]}", fontsize=8.5, loc="left",
                     color=INK)
    for ax in axes[1]:
        ax.set_xlabel("Sobol index")
    axes[0, 1].legend(loc="lower right")
    fig.tight_layout(h_pad=1.2, w_pad=1.0)
    _save(fig, "sobol"); plt.close(fig)
    return {}


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _style(plt)
    out = {"arrhenius": fig_arrhenius(plt), "lever": fig_lever(plt),
           "kinetics": fig_kinetics(plt), "scarcity": fig_scarcity(plt),
           "sensor": fig_sensor(plt), "sobol": fig_sobol(plt)}
    for k, v in out.items():
        print(f"fig_paper_{k}: {v}")


if __name__ == "__main__":
    main()

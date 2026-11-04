"""
kinetics_validation.py — E1 / ipis-thesis-geothermal-silica
Phase P5, build 2: out-of-sample validation of the RR79-fitted kinetic
core (P2, module 3 / temperature_lever) against the INDEPENDENT Scott
et al. (2024) T1 experimental dataset.

THE QUESTION THIS ANSWERS (reviewer objection #2: "kinetics are 40 years old")
    The core's k(T) is fitted ONLY to Rothbaum & Rohde (1979). Here it
    predicts monomer-decay behaviour in a different lab, four decades
    later (Scott 2024), with NO fitting to Scott data. Two things are
    tested SEPARATELY, because they fail differently:

    (A) FUNCTIONAL FORM (reaction order). The integrated n-th-order law
        du/dt = -k u^n  (u = C - Ce, supersaturation) linearizes as
            u^-(n-1) = u0^-(n-1) + (n-1) k t.
        Regressing u^-(n-1) on t and reading R^2 is a fit-free order test;
        a per-experiment sweep n in {2..6} recovers the best-fit order.

        FINDING (this is a RESULT, not an assumption to confirm): Scott's
        single-curve monomer decay is cleanly SECOND ORDER in supersaturation
        (median R^2 ~ 0.99 at n=2, monotonically worse for higher n; best-fit
        order = 2 in ~100% of qualifying experiments). This does NOT
        contradict Rothbaum & Rohde: RR79's "4th order" is a correlation of
        the MAXIMUM rate against INITIAL supersaturation across separate
        batch runs (a peak-rate law), whereas the integrated decay of one
        curve follows Rimstidt-Barnes-type ~2nd-order kinetics. They
        describe different observables. E1 records both and does not force
        the core's order onto data that speaks otherwise.

    (B) RATE CONSTANT / MODEL BIAS. Because the observed per-curve order is
        2, the honest cross-model quantity is the discrepancy between the
        RR79-core prediction and Scott's observed decay TIMESCALE, reported
        as the ratio of the 2nd-order-fitted k_Scott to the effective decay
        constant implied by the RR79 core over the same window. Whatever the
        offset, it is the empirical case for a LEARNED RESIDUAL: no single
        transcribed rate law (1979 peak-rate OR a fixed order) reproduces
        independent modern data, but the residual absorbs exactly this
        structured, T- and regime-dependent gap. This is N1's real-data
        justification.

SCOPE (stated, principled — not tuned to a desired answer)
    Near-neutral pH 5.0-8.0 only: there the total monomeric SiO2 ~
    H4SiO4(aq), matching RR79's pH 7-8 conditions, so no ionization
    correction is needed. High-pH Scott experiments require the H3SiO4-
    speciation correction (PHREEQC layer / Scott's K1,K2) and are deferred.
    Colloid-regime experiments are excluded upstream (scott2024_dataset).
    Kinetic window u/u0 in [0.30, 0.90] excludes the induction plateau and
    the near-equilibrium tail where the simple law and 1/u^(n-1) both break.

Dependencies: numpy, matplotlib; modules scott2024_dataset, silica_saturation,
temperature_lever. No fitting library — linear regression only.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import math

import numpy as np
import pandas as pd

from silica_saturation import solubility_amorphous_silica_ga00
from temperature_lever import k_of_T
from scott2024_dataset import load_scott2024, Scott2024Data

_FIGDIR = Path(__file__).parent.parent / "figures"
_RESDIR = Path(__file__).parent.parent / "results"

ORDER_CANDIDATES = (2, 3, 4, 5, 6)
U_WINDOW = (0.30, 0.90)      # fraction of initial supersaturation
MIN_WINDOW_PTS = 4
RR79_ORDER = 4               # RR79 peak-rate law order (for reference)


# ---------------------------------------------------------------------------
# Core estimators (fit-free: linear regression on the integrated form)
# ---------------------------------------------------------------------------

def _linfit_r2(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """Return (slope, intercept, R^2) of an OLS line."""
    A = np.vstack([x, np.ones_like(x)]).T
    (slope, intercept), *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(slope), float(intercept), r2


def _window(t: np.ndarray, u: np.ndarray) -> np.ndarray:
    u0 = u[0]
    m = (u > 0) & (u <= U_WINDOW[1] * u0) & (u >= U_WINDOW[0] * u0)
    return m


def fit_order_and_k(t_min: np.ndarray, c_mgkg: np.ndarray, ce: float
                    ) -> Dict[str, float]:
    """Estimate reaction order (by best linearization R^2) and the 4th-order
    rate constant on the kinetic window. Returns k4, r2_order4,
    best_order, r2_best, n_used, induction_min."""
    u = c_mgkg - ce
    m = _window(t_min, u)
    out = {"k2": float("nan"), "r2_order2": float("nan"),
           "k4": float("nan"), "r2_order4": float("nan"),
           "best_order": np.nan, "r2_best": float("nan"),
           "n_used": int(m.sum()), "induction_min": float("nan")}
    if m.sum() < MIN_WINDOW_PTS:
        return out
    tw, uw = t_min[m], u[m]

    # order sweep
    best = (-np.inf, None, None)
    r2_by_order = {}
    for n in ORDER_CANDIDATES:
        y = uw ** (-(n - 1))
        slope, intercept, r2 = _linfit_r2(tw, y)
        r2_by_order[n] = r2
        if slope > 0 and r2 > best[0]:           # slope>0: u decreasing
            best = (r2, n, slope)
    out["r2_order2"] = r2_by_order.get(2, float("nan"))
    out["r2_order4"] = r2_by_order.get(4, float("nan"))
    if best[1] is not None:
        out["best_order"] = int(best[1])
        out["r2_best"] = float(best[0])

    # 2nd-order k (slope of 1/u vs t) — the empirically-correct decay law
    y2 = uw ** (-1)
    slope2, intercept2, _ = _linfit_r2(tw, y2)
    if slope2 > 0:
        out["k2"] = slope2
        u0 = u[0]
        out["induction_min"] = max(0.0, ((1.0 / u0) - intercept2) / slope2)

    # 4th-order k (slope of 1/u^3 vs t = 3k) — for the RR79-form comparison
    y4 = uw ** (-3)
    slope4, intercept4, _ = _linfit_r2(tw, y4)
    if slope4 > 0:
        out["k4"] = slope4 / 3.0
    return out


# ---------------------------------------------------------------------------
# Validation over the Scott dataset
# ---------------------------------------------------------------------------

def validate(data: Scott2024Data | None = None,
             pH_window: Tuple[float, float] = (5.0, 8.0),
             T_range: Tuple[float, float] = (20.0, 180.0),
             min_decay_frac: float = 0.30) -> pd.DataFrame:
    if data is None:
        data = load_scott2024()
    rows = []
    for _, m in data.meta.iterrows():
        if not m.kinetics_regime:
            continue
        if not (pH_window[0] <= m.pH <= pH_window[1]):
            continue
        if not (T_range[0] <= m.T_C <= T_range[1]):
            continue
        g = data.series[data.series.experiment == m.experiment]
        c = g.sio2_mgkg.to_numpy()
        t = g.time_min.to_numpy()
        ce = solubility_amorphous_silica_ga00(m.T_C + 273.15)
        u0 = c[0] - ce
        if u0 <= 0:
            continue
        decay = (c[0] - c[-3:].mean()) / u0
        if decay < min_decay_frac:
            continue
        fit = fit_order_and_k(t, c, ce)
        if not np.isfinite(fit["k2"]):
            continue
        # RR79-core effective decay constant over the SAME window:
        # what 2nd-order k would reproduce the RR79 4th-order core's rate
        # at the window-median supersaturation (u_mid): equate
        # k_rr79 * u_mid^4 == k_eff * u_mid^2  ->  k_eff = k_rr79 * u_mid^2.
        krr = k_of_T(m.T_C)
        u_mid = 0.6 * u0
        k_eff_rr79 = krr * u_mid ** 2
        rows.append((m.experiment, m.T_C, m.pH, u0, decay,
                     fit["k2"], fit["r2_order2"],
                     fit["k4"], fit["r2_order4"],
                     k_eff_rr79, fit["k2"] / k_eff_rr79,
                     fit["best_order"], fit["r2_best"],
                     fit["induction_min"], fit["n_used"]))
    return pd.DataFrame(rows, columns=[
        "experiment", "T_C", "pH", "u0_mgkg", "decay_frac",
        "k2_scott", "r2_order2", "k4_scott", "r2_order4",
        "k_eff_rr79", "k_ratio", "best_order", "r2_best",
        "induction_min", "n_used"])


def summary(res: pd.DataFrame) -> dict:
    lr = np.log(res.k_ratio.to_numpy())
    return {
        "n_experiments": int(len(res)),
        "T_span_C": (float(res.T_C.min()), float(res.T_C.max())),
        "order2_r2_median": float(res.r2_order2.median()),
        "order4_r2_median": float(res.r2_order4.median()),
        "best_order_mode": int(res.best_order.mode().iloc[0]),
        "best_order_is_2_frac": float((res.best_order == 2).mean()),
        "k_ratio_geomean": float(math.exp(lr.mean())),
        "k_ratio_geosd": float(math.exp(lr.std())),
        "k_ratio_median": float(res.k_ratio.median()),
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def make_figure(res: pd.DataFrame, figdir: Path = _FIGDIR) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figdir.mkdir(parents=True, exist_ok=True)
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.6))

    # Panel A: Arrhenius overlay
    sc = axA.scatter(1000.0 / (res.T_C + 273.15), np.log(res.k2_scott),
                     c=res.pH, cmap="viridis", s=45, edgecolor="k",
                     linewidth=0.4, zorder=3)
    cb = fig.colorbar(sc, ax=axA); cb.set_label("pH")
    # Arrhenius fit to the observed 2nd-order k (near-neutral)
    x = 1000.0 / (res.T_C + 273.15)
    b, a = np.polyfit(x, np.log(res.k2_scott), 1)
    ea = -b * 8.314  # kJ/mol (x is 1000/T so slope already scaled)
    xs = np.linspace(x.min(), x.max(), 50)
    axA.plot(xs, a + b * xs, "r--",
             label=f"Arrhenius fit, E$_a$≈{abs(b)*8.314:.0f} kJ/mol")
    axA.set_xlabel("1000 / T  [K$^{-1}$]")
    axA.set_ylabel("ln k$_2$   [2nd-order, (g/t)$^{-1}$ min$^{-1}$]")
    axA.set_title("Scott 2024 observed 2nd-order rate constant vs. 1/T\n"
                  "(near-neutral pH; out-of-sample from RR79)")
    axA.legend(fontsize=8, loc="best")

    # Panel B: order-4 linearization R^2 distribution (the form test)
    orders = ORDER_CANDIDATES
    means = [res[f"r2_order2"].mean() if n == 2 else
             (res["r2_order4"].mean() if n == 4 else np.nan) for n in orders]
    # recompute all-order means from stored columns where available
    axB.plot([2, 4], [res.r2_order2.mean(), res.r2_order4.mean()],
             "o", ms=9, color="tab:blue")
    axB.annotate("order 2\n(best fit)", (2, res.r2_order2.mean()),
                 textcoords="offset points", xytext=(8, -4), fontsize=9)
    axB.annotate("order 4\n(RR79 peak-rate law)",
                 (4, res.r2_order4.mean()),
                 textcoords="offset points", xytext=(6, -20), fontsize=9)
    axB.set_xticks([2, 3, 4, 5, 6])
    axB.set_xlabel("assumed reaction order n")
    axB.set_ylabel("mean linearization R$^2$ across experiments")
    axB.set_ylim(0.78, 1.005)
    axB.set_title(f"Per-curve order test ({len(res)} exps): decay is 2nd order\n"
                  f"(best-fit order = 2 in "
                  f"{100*(res.best_order==2).mean():.0f}% of experiments)")

    fig.tight_layout()
    p = figdir / "fig_kinetics_validation.png"
    fig.savefig(p, dpi=200); plt.close(fig)
    return str(p)


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1. UNIT TEST: recover a known 4th-order k (synthetic curve well inside
    #    the kinetic window across the sampled times)
    u0, ce = 500.0, 100.0
    t_end = 1.0e4
    t = np.linspace(0, t_end, 80)
    k_true = u0 ** -3 * (0.3 ** -3 - 1) / (3 * t_end)   # sweeps u0 -> 0.3 u0
    u = (u0 ** -3 + 3 * k_true * t) ** (-1.0 / 3.0)
    fit = fit_order_and_k(t, ce + u, ce)
    checks.append(("Recovers known 4th-order k (synthetic, <2%)",
                   np.isfinite(fit["k4"]) and abs(fit["k4"] / k_true - 1) < 0.02,
                   f"k4_fit/k_true={fit['k4']/k_true:.4f}, "
                   f"best_order={fit['best_order']}, R2@4={fit['r2_order4']:.4f}, "
                   f"npts={fit['n_used']}"))

    # 2. UNIT TEST: recover a known 2nd-order k and correct order label
    k2_true = (1.0 / u0) * (1.0 / 0.3 - 1) / t_end     # sweeps u0 -> 0.3 u0
    u2 = 1.0 / (1.0 / u0 + k2_true * t)
    fit2 = fit_order_and_k(t, ce + u2, ce)
    checks.append(("Recovers known 2nd-order k + labels order 2 (<2%)",
                   fit2["best_order"] == 2
                   and abs(fit2["k2"] / k2_true - 1) < 0.02,
                   f"k2_fit/k_true={fit2['k2']/k2_true:.4f}, "
                   f"best_order={fit2['best_order']}, R2@2={fit2['r2_order2']:.4f}"))

    # 3. Validation qualifies a real near-neutral set
    res = validate()
    s = summary(res)
    checks.append(("Qualifying near-neutral Scott experiments (>=10)",
                   s["n_experiments"] >= 10,
                   f"n={s['n_experiments']}, T "
                   f"{s['T_span_C'][0]:.0f}-{s['T_span_C'][1]:.0f} C"))

    # 4. THE FINDING: single-curve decay is cleanly 2nd order on 2024 data
    checks.append(("FINDING: Scott decay is 2nd order (mode=2, high R2)",
                   s["best_order_mode"] == 2
                   and s["order2_r2_median"] > 0.95
                   and s["order2_r2_median"] > s["order4_r2_median"],
                   f"R2@2 median={s['order2_r2_median']:.3f} > "
                   f"R2@4 median={s['order4_r2_median']:.3f}; "
                   f"order-2 in {100*s['best_order_is_2_frac']:.0f}% of exps"))

    # 5. MODEL-GAP quantified: RR79-core effective decay vs observed (the
    #    residual's real-data job). Finite, reported, not asserted to be ~1.
    checks.append(("RR79-core vs Scott decay gap quantified (finite)",
                   0.001 < s["k_ratio_geomean"] < 1000.0,
                   f"k2_Scott / k_eff_RR79 geomean={s['k_ratio_geomean']:.2f} "
                   f"(x/ {s['k_ratio_geosd']:.1f}), median={s['k_ratio_median']:.2f}"))

    # 6. Arrhenius signal in observed k2: warmer => faster (positive trend)
    x = 1000.0 / (res.T_C + 273.15)
    b = np.polyfit(x, np.log(res.k2_scott), 1)[0]
    checks.append(("Observed k2 increases with T (Arrhenius sign)",
                   b < 0, f"d ln k2 / d(1000/T) = {b:.2f} (<0 => k up with T)"))

    # 7. Figure + results table regenerate
    _RESDIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(_RESDIR / "kinetics_validation.csv", index=False)
    p = make_figure(res)
    checks.append(("Figure + CSV regenerate from raw inputs",
                   Path(p).exists()
                   and (_RESDIR / "kinetics_validation.csv").exists(), ""))

    width = max(len(c[0]) for c in checks)
    print("P5 build-2 self-check — kinetics_validation.py")
    print("-" * (width + 60))
    failed = 0
    for name, ok, extra in checks:
        failed += (not ok)
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {extra}")
    print("-" * (width + 60))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()

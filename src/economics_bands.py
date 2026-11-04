"""
economics_bands.py — E1 / ipis-thesis-geothermal-silica
Phase P6, build 2: honest ranges on every peso and megawatt.

WHAT THIS DOES
    Re-values the COMMITTED closed-loop results (results/table2_control.csv,
    results/table2b_stress.csv) over the declared economics envelope:

        eta_binary   [0.08, 0.14]     conversion effectiveness (scenario)
        price_kwh    [4.00, 7.00]     PHP/kWh (scenario)
        inhibitor    [150, 600]       PHP/kg (x0.5-x2 scenario band)

    and writes per-arm bands for gross MW, net PHP/h and inhibitor
    PHP/MWh in both regimes -> results/economics_bands.csv (+ figure).

WHY REVALUATION (not re-simulation) IS VALID — VERIFIED, NOT ASSUMED
    The controllers' DECISIONS depend on economics only through the
    objective; inhibitor cost is a few percent of revenue everywhere in
    the envelope, and scaling revenue rescales whole columns of the
    objective grid without reordering the constrained argmax materially.
    Consequence: trajectories (T, dose, violations) are envelope-
    invariant; only their VALUATION changes. The self-check verifies
    this by re-solving the steady robust RTO at all 8 economics corners
    and requiring (T*, dose*) to move by <= 1 grid step. Uplift-% and
    violation-day columns are therefore carried over unchanged; gross MW
    scales linearly with eta_binary; net = MW*1000*price - dose-cost
    with dose-cost scaling in inhibitor price.

    If a future change makes decisions economics-sensitive (e.g., a much
    costlier inhibitor), the corner check FAILS and forces re-simulation
    — the assumption is load-bearing and gated, not silent.
"""

from pathlib import Path
import itertools

import numpy as np
import pandas as pd

from robust_rto import RobustRTO, RTOConfig, Economics

_RESDIR = Path(__file__).parent.parent / "results"
_FIGDIR = Path(__file__).parent.parent / "figures"

ETA_BAND = (0.08, 0.14)
PRICE_BAND = (4.0, 7.0)
PINH_BAND = (150.0, 600.0)

_E0 = Economics()          # the valuation baseline used by the experiments


def _load(name: str) -> pd.DataFrame:
    p = _RESDIR / name
    if not p.exists():
        raise FileNotFoundError(
            f"{p} missing — run run_control_experiment.py / "
            f"run_stress_experiment.py first (results are committed).")
    return pd.read_csv(p)


def revalue(df: pd.DataFrame, eta: float, price: float,
            pinh: float) -> pd.DataFrame:
    """Re-value one committed results table at an economics point."""
    out = df.copy()
    scale_mw = eta / _E0.eta_binary
    mw = df["gross_mw_mean"] * scale_mw
    # recover baseline dose cost [PHP/h] from stored intensity:
    cost0_php_h = df["inhibitor_php_per_mwh"] * df["gross_mw_mean"]
    cost_php_h = cost0_php_h * (pinh / _E0.inhibitor_php_per_kg)
    out["gross_mw_mean"] = mw
    out["net_php_h"] = mw * 1000.0 * price - cost_php_h
    out["inhibitor_php_per_mwh"] = cost_php_h / mw.clip(lower=1e-9)
    return out


def bands(df: pd.DataFrame, regime: str) -> pd.DataFrame:
    """Per-arm min/nominal/max over the envelope corners (monotone in
    each factor, so corners bound the box)."""
    corners = list(itertools.product(ETA_BAND, PRICE_BAND, PINH_BAND))
    rows = []
    for arm, g in df.groupby("arm"):
        vals = {k: [] for k in ("gross_mw_mean", "net_php_h",
                                "inhibitor_php_per_mwh")}
        for eta, price, pinh in corners:
            rv = revalue(g, eta, price, pinh)
            for k in vals:
                vals[k].append(rv[k].mean())
        nom = revalue(g, _E0.eta_binary, _E0.price_php_per_kwh,
                      _E0.inhibitor_php_per_kg)
        rows.append((regime, arm,
                     min(vals["gross_mw_mean"]), nom["gross_mw_mean"].mean(),
                     max(vals["gross_mw_mean"]),
                     min(vals["net_php_h"]), nom["net_php_h"].mean(),
                     max(vals["net_php_h"]),
                     min(vals["inhibitor_php_per_mwh"]),
                     nom["inhibitor_php_per_mwh"].mean(),
                     max(vals["inhibitor_php_per_mwh"]),
                     g["violation_days"].mean()))
    return pd.DataFrame(rows, columns=[
        "regime", "arm", "mw_lo", "mw_nom", "mw_hi",
        "net_lo", "net_nom", "net_hi",
        "inh_lo", "inh_nom", "inh_hi", "viol_days_mean"])


def make_outputs(bd: pd.DataFrame) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _FIGDIR.mkdir(exist_ok=True)
    bd.to_csv(_RESDIR / "economics_bands.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, regime in zip(axes, ("benign", "stress")):
        g = bd[bd.regime == regime]
        xs = np.arange(len(g))
        ax.errorbar(xs, g["net_nom"] / 1000.0,
                    yerr=[(g["net_nom"] - g["net_lo"]) / 1000.0,
                          (g["net_hi"] - g["net_nom"]) / 1000.0],
                    fmt="o", capsize=5, color="tab:blue")
        ax.set_xticks(xs)
        ax.set_xticklabels(g["arm"], rotation=25, ha="right", fontsize=8)
        ax.set_title(f"{regime} regime")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("net objective [kPHP/h]\n(nominal ± economics envelope)")
    fig.suptitle("Economics bands over the declared envelope "
                 "(decisions verified envelope-invariant)")
    fig.tight_layout()
    p = _FIGDIR / "fig_economics_bands.png"
    fig.savefig(p, dpi=200); plt.close(fig)
    return str(p)


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1. DECISION INVARIANCE (the load-bearing assumption, gated):
    #    steady robust RTO re-solved at all 8 economics corners; (T*, d*)
    #    must move <= 1 grid step from nominal.
    ref = RobustRTO().solve()
    dT_grid = (RTOConfig.T_bounds[1] - RTOConfig.T_bounds[0]) \
        / (RTOConfig.grid_T - 1)
    dD_grid = (RTOConfig.dose_bounds[1] - RTOConfig.dose_bounds[0]) \
        / (RTOConfig.grid_dose - 1)
    worst_dT = worst_dD = 0.0
    for eta, price, pinh in itertools.product(ETA_BAND, PRICE_BAND,
                                              PINH_BAND):
        econ = Economics(eta_binary=eta, price_php_per_kwh=price,
                         inhibitor_php_per_kg=pinh)
        r = RobustRTO(econ=econ).solve()
        worst_dT = max(worst_dT, abs(r.T_rej_C - ref.T_rej_C))
        worst_dD = max(worst_dD, abs(r.dose_ppm - ref.dose_ppm))
    checks.append(("Decision invariance at 8 economics corners "
                   "(<= 1 grid step)",
                   worst_dT <= dT_grid + 1e-9 and worst_dD <= dD_grid + 1e-9,
                   f"max dT*={worst_dT:.2f} C (grid {dT_grid:.2f}), "
                   f"max d dose*={worst_dD:.3f} ppm (grid {dD_grid:.3f})"))

    # 2. Nominal revaluation reproduces the stored numbers
    t2 = _load("table2_control.csv")
    rv = revalue(t2, _E0.eta_binary, _E0.price_php_per_kwh,
                 _E0.inhibitor_php_per_kg)
    dev = float((rv["net_php_h"] - t2["net_php_h"]).abs().max())
    checks.append(("Nominal revaluation reproduces stored net_php_h",
                   dev < 1.0, f"max dev={dev:.3f} PHP/h"))

    # 3. Bands computed for both regimes; ordering lo <= nom <= hi
    t2b = _load("table2b_stress.csv")
    bd = pd.concat([bands(t2, "benign"), bands(t2b, "stress")],
                   ignore_index=True)
    ok = bool(((bd["mw_lo"] <= bd["mw_nom"] + 1e-9)
               & (bd["mw_nom"] <= bd["mw_hi"] + 1e-9)
               & (bd["net_lo"] <= bd["net_nom"] + 1e-9)
               & (bd["net_nom"] <= bd["net_hi"] + 1e-9)).all())
    checks.append(("Bands well-ordered (lo <= nominal <= hi), both regimes",
                   ok, f"{len(bd)} arm-regime rows"))

    # 4. Dose cost stays minor across the envelope (the invariance
    #    mechanism): worst-case inhibitor cost share of revenue < 15%
    share = []
    for _, r in bd.iterrows():
        if r.mw_nom > 0:
            share.append(r.inh_hi * 1.0 / (1000.0 * PRICE_BAND[0]))
    worst_share = max(share)
    checks.append(("Inhibitor cost share of revenue < 15% everywhere",
                   worst_share < 0.15, f"worst={100*worst_share:.1f}%"))

    # 5. Outputs regenerate
    p = make_outputs(bd)
    checks.append(("Figure + CSV regenerate",
                   Path(p).exists()
                   and (_RESDIR / "economics_bands.csv").exists(), ""))

    width = max(len(c[0]) for c in checks)
    print("P6 build-2 self-check — economics_bands.py")
    print("-" * (width + 55))
    failed = 0
    for name, ok_, extra in checks:
        failed += (not ok_)
        print(f"{name:<{width}}  {'PASS' if ok_ else 'FAIL'}  {extra}")
    print("-" * (width + 55))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)

    # summary print (nominal-scale numbers come from the committed CSVs)
    print("\nECONOMICS BANDS (net kPHP/h, lo/nom/hi):")
    for _, r in bd.iterrows():
        print(f"  {r.regime:7s} {r.arm:14s} "
              f"{r.net_lo/1000:6.1f} / {r.net_nom/1000:6.1f} / "
              f"{r.net_hi/1000:6.1f}   (MW {r.mw_lo:.1f}-{r.mw_hi:.1f}, "
              f"viol {r.viol_days_mean:.2f} d)")


if __name__ == "__main__":
    _self_check()

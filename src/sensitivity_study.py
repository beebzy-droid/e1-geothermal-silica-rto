"""
sensitivity_study.py — E1 / ipis-thesis-geothermal-silica
Phase P6, build 1: Sobol global sensitivity of the headline quantities
over the DECLARED uncertainty set.

    python sensitivity_study.py           (gate mode: smoke self-check)
    python sensitivity_study.py --full    (full N=512 study, ~1-3 min;
                                           writes results/ + figures/)

WHY THIS EXISTS
    Every P6 claim of the form "the result is robust to X / driven by Y"
    must be a computed Sobol index, not an intuition. The parameter
    RANGES are measurements or declared scenarios — none is a free
    choice made here:

      logk_shift   [-ln6, +ln6]   kinetic model-family band = the P5
                                  MEASURED x6 median cross-model gap
      ce_scale     [0.90, 1.37]   the P5 MEASURED Scott-endpoint/GA00
                                  band (median 1.05)
      flash        [0.20, 0.30]   scenario bounds (P2 close-out)
      eta_max      [0.30, 0.70]   dose-response family about the Gallup
      d_opt_ppm    [0.50, 2.00]   2002 anchors (~50% @ ~1 ppm) [T1-qual]
      r_max        [0.25, 1.00]   constraint calibration band (units
                                  caveat: mm/yr closure pends Weres 1981)
      eta_binary   [0.08, 0.14]   conversion-effectiveness scenario band
      price_kwh    [4.00, 7.00]   PHP/kWh scenario band

SCOPING (stated, not hidden)
    Quantities of interest are the STEADY-STATE RTO layer outputs
    (T*, dose*, gross MW, net PHP/h, feasibility) and the temperature-
    lever ratio rate(90C)/rate(150C). Closed-loop metrics (violation
    days, uplift trajectories) are NOT re-sampled here: each Sobol
    evaluation would cost a 45-day episode x arms, and the two-regime
    Table 2/2b design plus the kappa in {0,1} ablation already covers
    closed-loop robustness. kappa is therefore exercised THERE, not here.

    Note the lever ratio is invariant to logk_shift by construction
    (a uniform multiplicative k shift cancels in the ratio) — so its
    sensitivity decomposes over ce_scale and flash only; finding that
    numerically is itself a correctness check.

Gate mode runs pipeline-validity checks at tiny sample size (indices are
NOT converged there and are not written anywhere); only --full writes
results/sensitivity_sobol.csv and figures/fig_sensitivity_sobol.png.
"""

from pathlib import Path
import sys
import math

import numpy as np
import pandas as pd

from silica_saturation import solubility_amorphous_silica_ga00
from temperature_lever import k_of_T
from robust_rto import RTOConfig, RobustRTO, Economics, VERTEX_SIO2

_RESDIR = Path(__file__).parent.parent / "results"
_FIGDIR = Path(__file__).parent.parent / "figures"

PROBLEM = {
    "num_vars": 8,
    "names": ["logk_shift", "ce_scale", "flash", "eta_max",
              "d_opt_ppm", "r_max", "eta_binary", "price_kwh"],
    "bounds": [[-math.log(6.0), math.log(6.0)],
               [0.90, 1.37],
               [0.20, 0.30],
               [0.30, 0.70],
               [0.50, 2.00],
               [0.25, 1.00],
               [0.08, 0.14],
               [4.00, 7.00]],
}

_CFG = RTOConfig()
_TS = np.linspace(*_CFG.T_bounds, _CFG.grid_T)
_DS = np.linspace(*_CFG.dose_bounds, _CFG.grid_dose)
_K_BASE = np.array([k_of_T(t) for t in _TS])
_CE_BASE = np.array([solubility_amorphous_silica_ga00(t + 273.15)
                     for t in _TS])
_SIO2 = np.array([VERTEX_SIO2[v] for v in ("A", "B", "C", "D")])
_ECON0 = Economics()
_OVERDOSE = 0.10          # fixed family parameter (see synthetic_plant)

QOI_NAMES = ["gross_mw", "T_opt_C", "dose_opt_ppm", "net_php_h",
             "feasible", "lever_ratio_90_150"]


def evaluate(x: np.ndarray) -> np.ndarray:
    """One Sobol sample -> the six QoIs. Vectorized grid RTO solve."""
    (logk, ces, flash, eta, dopt, rmax, etab, price) = x

    kT = _K_BASE * math.exp(logk)
    ce = _CE_BASE * ces
    fD = (1.0 - eta * (_DS / dopt) * np.exp(1.0 - _DS / dopt)
          + _OVERDOSE * np.maximum(0.0, _DS / dopt - 2.0))
    brines = _SIO2 / (1.0 - flash)

    worst = None
    for c in brines:
        s = np.maximum(c - ce, 0.0)
        g = np.outer(kT * s ** 4.0, fD)
        worst = g if worst is None else np.maximum(worst, g)

    rev = (_ECON0.m_flow_kg_s * _ECON0.cp_kj_kg_k
           * np.maximum(_ECON0.T_sep_C - _TS, 0.0) * etab) * price
    cost = _DS * _ECON0.m_flow_kg_s * 3600.0 / 1e6 * _ECON0.inhibitor_php_per_kg
    obj = rev[:, None] - cost[None, :]

    feas = worst <= rmax
    if feas.any():
        objm = np.where(feas, obj, -np.inf)
        i, j = np.unravel_index(np.argmax(objm), objm.shape)
        T_opt, d_opt_sel, feasible = float(_TS[i]), float(_DS[j]), 1.0
    else:
        i, j = len(_TS) - 1, 0
        T_opt, d_opt_sel, feasible = float(_TS[-1]), 0.0, 0.0

    mw = (_ECON0.m_flow_kg_s * _ECON0.cp_kj_kg_k
          * max(_ECON0.T_sep_C - T_opt, 0.0) * etab) / 1000.0
    net = mw * 1000.0 * price - cost[j]

    # temperature lever at vertex-B brine for this (ce_scale, flash);
    # uniform logk shift cancels in the ratio by construction
    cB = VERTEX_SIO2["B"] / (1.0 - flash)
    ce90 = solubility_amorphous_silica_ga00(363.15) * ces
    ce150 = solubility_amorphous_silica_ga00(423.15) * ces
    s90, s150 = max(cB - ce90, 0.0), max(cB - ce150, 0.0)
    if s150 > 0 and s90 > 0:
        lever = (k_of_T(90.0) * s90 ** 4) / (k_of_T(150.0) * s150 ** 4)
    else:
        lever = float("nan")
    return np.array([mw, T_opt, d_opt_sel, net, feasible, lever])


def _sample(n_base: int) -> np.ndarray:
    # seed pinned: the modern sampler scrambles (randomized QMC) by
    # default, which breaks run-to-run reproducibility of committed
    # results — a violation of the repo regeneration rule
    try:                                   # SALib >= 1.4.6
        from SALib.sample import sobol as sobol_sample
        try:
            return sobol_sample.sample(PROBLEM, n_base,
                                       calc_second_order=False, seed=0)
        except TypeError:
            return sobol_sample.sample(PROBLEM, n_base,
                                       calc_second_order=False)
    except (ImportError, AttributeError):  # older SALib (deterministic)
        from SALib.sample import saltelli
        return saltelli.sample(PROBLEM, n_base, calc_second_order=False)


def run_sobol(n_base: int) -> pd.DataFrame:
    from SALib.analyze import sobol as sobol_an
    X = _sample(n_base)
    Y = np.array([evaluate(x) for x in X])
    rows = []
    for q, name in enumerate(QOI_NAMES):
        y = Y[:, q]
        if name == "lever_ratio_90_150":
            # heavy-tailed near the saturation boundary (s150 -> 0+):
            # analyze in ln space (standard for ratio QoIs); NaN = under-
            # saturated at 150 C (no scaling problem) -> median-filled,
            # fraction reported in the summary
            m = np.isfinite(y)
            y = np.where(m, y, np.nanmedian(y))
            y = np.log(np.maximum(y, 1e-12))
        if float(np.std(y)) == 0.0:
            # constant QoI over the set (e.g. feasible == 1 everywhere):
            # sensitivity is zero BY DEFINITION; SALib would divide by 0
            for pname in PROBLEM["names"]:
                rows.append((name, pname, 0.0, 0.0))
            continue
        Si = sobol_an.analyze(PROBLEM, y, calc_second_order=False,
                              print_to_console=False)
        for p, pname in enumerate(PROBLEM["names"]):
            rows.append((name, pname, float(Si["S1"][p]),
                         float(Si["ST"][p])))
    res = pd.DataFrame(rows, columns=["qoi", "param", "S1", "ST"])
    res.attrs["summary"] = {
        "n_base": n_base, "n_evals": len(X),
        "feasible_frac": float(Y[:, QOI_NAMES.index("feasible")].mean()),
        "mw_q05_q50_q95": [float(np.quantile(Y[:, 0], q))
                           for q in (0.05, 0.50, 0.95)],
        "lever_q05_q50_q95": [float(np.nanquantile(Y[:, 5], q))
                              for q in (0.05, 0.50, 0.95)],
        "undersat150_frac": float(np.mean(~np.isfinite(Y[:, 5]))),
    }
    return res, Y


def make_outputs(res: pd.DataFrame, Y: np.ndarray) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _RESDIR.mkdir(exist_ok=True); _FIGDIR.mkdir(exist_ok=True)
    res.to_csv(_RESDIR / "sensitivity_sobol.csv", index=False)

    show = ["gross_mw", "T_opt_C", "net_php_h", "lever_ratio_90_150"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharey=False)
    for ax, q in zip(axes.ravel(), show):
        g = res[res.qoi == q].set_index("param")
        xs = np.arange(len(g))
        ax.bar(xs - 0.2, g["S1"], width=0.4, label="S1 (first order)",
               color="tab:blue")
        ax.bar(xs + 0.2, g["ST"], width=0.4, label="ST (total)",
               color="tab:orange")
        ax.set_xticks(xs)
        ax.set_xticklabels(g.index, rotation=45, ha="right", fontsize=7)
        ax.set_title(q, fontsize=10)
        ax.set_ylim(0, 1.05)
    axes[0, 0].legend(fontsize=8)
    s = res.attrs["summary"]
    fig.suptitle("Sobol sensitivity over the declared uncertainty set "
                 f"(N={s['n_base']}, {s['n_evals']} evals; "
                 f"feasible {100*s['feasible_frac']:.0f}%)")
    fig.tight_layout()
    p = _FIGDIR / "fig_sensitivity_sobol.png"
    fig.savefig(p, dpi=200); plt.close(fig)
    return str(p)


# ---------------------------------------------------------------------------
# Self-check (gate mode: pipeline validity, NOT converged indices)
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1. Nominal-parameter evaluator reproduces the gate-tested solver
    x0 = np.array([0.0, 1.0, 0.30, 0.50, 1.00, 0.50,
                   _ECON0.eta_binary, _ECON0.price_php_per_kwh])
    q0 = evaluate(x0)
    ref = RobustRTO().solve()
    checks.append(("Nominal sample reproduces RobustRTO.solve() (T*, d*)",
                   abs(q0[1] - ref.T_rej_C) < 1e-9
                   and abs(q0[2] - ref.dose_ppm) < 1e-9,
                   f"T*={q0[1]:.2f} vs {ref.T_rej_C:.2f}, "
                   f"d*={q0[2]:.2f} vs {ref.dose_ppm:.2f}"))

    # 2. Directional sanity: harsher kinetics => less power; looser
    #    constraint => more power
    mw_hi_k = evaluate(np.array([math.log(6.0), 1.0, 0.30, 0.5, 1.0,
                                 0.50, 0.10, 5.5]))[0]
    mw_loose = evaluate(np.array([0.0, 1.0, 0.30, 0.5, 1.0,
                                  1.00, 0.10, 5.5]))[0]
    checks.append(("Directional sanity: x6 kinetics cuts MW; "
                   "looser r_max raises MW",
                   mw_hi_k < q0[0] <= mw_loose,
                   f"{mw_hi_k:.1f} < {q0[0]:.1f} <= {mw_loose:.1f} MW"))

    # 3. Fallback branch unit-test: force infeasibility with r_max ~ 0
    #    (outside the declared bounds — a BRANCH test, not a sample; the
    #    declared set itself is ~100% feasible, reported by check 5,
    #    i.e. the uncertainty set never strands the RTO)
    q_inf = evaluate(np.array([0.0, 1.0, 0.30, 0.50, 1.0,
                               1e-9, 0.10, 5.5]))
    checks.append(("Fallback branch (forced r_max~0): hot end, dose 0",
                   q_inf[4] == 0.0 and q_inf[1] == _TS[-1]
                   and q_inf[2] == 0.0,
                   f"T={q_inf[1]:.0f} C, feasible={q_inf[4]:.0f}"))

    # 4. Lever ratio invariant to logk_shift (uniform shift cancels)
    lv_a = evaluate(np.array([0.0, 1.0, 0.25, 0.5, 1.0, 0.5, 0.1, 5.5]))[5]
    lv_b = evaluate(np.array([1.5, 1.0, 0.25, 0.5, 1.0, 0.5, 0.1, 5.5]))[5]
    checks.append(("Lever ratio invariant to uniform k shift",
                   abs(lv_a - lv_b) / lv_a < 1e-12,
                   f"ratio={lv_a:.0f}x at both"))

    # 5. Smoke Sobol pipeline (N=16): finite indices, ST >= S1 - tol
    res, Y = run_sobol(16)
    fin = np.isfinite(res[["S1", "ST"]].to_numpy()).all()
    st_ge = bool((res["ST"] >= res["S1"] - 0.35).all())   # loose at N=16
    checks.append(("Smoke Sobol (N=16) numerically valid "
                   "(finite; ST >= S1 - tol)",
                   bool(fin) and st_ge,
                   f"{len(res)} indices; feasible "
                   f"{100*res.attrs['summary']['feasible_frac']:.0f}%"))

    width = max(len(c[0]) for c in checks)
    print("P6 build-1 self-check — sensitivity_study.py (smoke)")
    print("-" * (width + 55))
    failed = 0
    for name, ok, extra in checks:
        failed += (not ok)
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {extra}")
    print("-" * (width + 55))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


def _full() -> None:
    print("P6 Sobol study — full scale (N=512, 9216 evaluations) ...")
    res, Y = run_sobol(512)
    p = make_outputs(res, Y)
    s = res.attrs["summary"]
    print(f"feasible fraction over the uncertainty set: "
          f"{100*s['feasible_frac']:.1f}%")
    print(f"gross MW at optimum  q05/q50/q95: "
          + "/".join(f"{v:.1f}" for v in s["mw_q05_q50_q95"]))
    print(f"temperature-lever ratio q05/q50/q95: "
          + "/".join(f"{v:.0f}x" for v in s["lever_q05_q50_q95"])
          + f"  (Sobol analyzed in ln space; "
            f"{100*s['undersat150_frac']:.0f}% of scenarios undersaturated "
            f"at 150 C = no scaling problem there)")
    print("\nTop total-order (ST) driver per QoI:")
    for q in QOI_NAMES:
        g = res[res.qoi == q].sort_values("ST", ascending=False)
        if len(g):
            print(f"  {q:20s} <- {g.iloc[0]['param']:11s} "
                  f"ST={g.iloc[0]['ST']:.2f} (S1={g.iloc[0]['S1']:.2f})")
    print(f"\nWrote {p} and results/sensitivity_sobol.csv")
    print("Commit results/ and figures/ after visual QA.")


if __name__ == "__main__":
    if "--full" in sys.argv:
        _full()
    else:
        _self_check()

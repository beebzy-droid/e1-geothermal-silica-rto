"""
run_stress_experiment.py — E1 / ipis-thesis-geothermal-silica
Closed-loop benchmark, adverse-kinetics stress — manuscript Table 2b.

    cd src && python run_stress_experiment.py            (full, ~10-20 min)
    cd src && python run_stress_experiment.py --smoke    (pipeline check)

DESIGN
    Same arms and machinery as Table 2 (run_control_experiment), but every
    plant carries logk_bias_shift = +1.79: true kinetics run ~x6.0 FASTER
    than the model believes.

    STRESS CALIBRATION (a measurement, not a choice): the shift equals the
    P5 cross-model finding — kinetics_validation.py measured a ~x6 MEDIAN
    gap between the RR79-core effective decay constant and independent
    Scott 2024 data. Random per-plant draws are zeroed (single-factor
    design); Table 2 retains the realistic random ensemble. Pilot history
    (x2 and x3 did not discriminate; an early brine-dilution artifact was
    fixed 2026-07-15) is in the git log of this file.

TWO KINDS OF VERDICT, KEPT SEPARATE
    PRE-REGISTERED (July 2026, before the definitive runs): E1, E2, E3',
    E4a, E5. They are evaluated on the corrected arms and reported
    PASS/FAIL as registered.

    POST HOC (2026-11-10, P8b): after the first submission the feedback
    baseline was found to be anchored to the nominal brine composition
    while the hybrid used the measured silica. The anchoring ablation,
    the measured-anchored baseline, its back-off variant and the GP
    comparator were all added AFTER seeing results. They are printed as
    FINDINGS (F1-F3), never as pass/fail, and the manuscript says so.

Outputs: ../results/table2b_stress.csv, table2b_summary.csv,
         ../figures/fig_closed_loop_frontier.(png|pdf) via
         closed_loop_figure.py (needs Table 2 to have run first)
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

from run_control_experiment import (FastRTO, run_arm, summarize,
                                    paired_contrast, ARMS_ALL, KAPPA_SWEEP,
                                    KAPPA_FAMILIES, PREREG_N)
from synthetic_plant import MismatchConfig

# SINGLE-FACTOR stress: all random mismatch zeroed; only the deterministic
# shift remains.
STRESS_MISMATCH = MismatchConfig(sigma_logk_bias=0.0, sigma_order=0.0,
                                 sigma_ce_bias=0.0, sigma_eta=0.0,
                                 sigma_dopt_rel=0.0)

RESULTS = Path(__file__).parent.parent / "results"
FIGURES = Path(__file__).parent.parent / "figures"

SMOKE = "--smoke" in sys.argv
if SMOKE and __name__ == "__main__":
    # smoke output goes to a temp dir: never over the full-scale results
    import tempfile
    _tmp = Path(tempfile.mkdtemp(prefix="e1_smoke_"))
    RESULTS, FIGURES = _tmp / "results", _tmp / "figures"
PLANTS = list(range(100, 102 if SMOKE else 120))   # fresh adverse seeds
DAYS = 12.0 if SMOKE else 45.0
BIAS_SHIFT = 1.79                                   # ~x6.0 true-rate stress
ARMS = ARMS_ALL


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    fast = FastRTO()
    if SMOKE:
        print("SMOKE MODE — pipeline verification only.")
    print(f"Table 2b stress: {len(PLANTS)} plants x {DAYS:.0f} d, "
          f"logk_bias_shift=+{BIAS_SHIFT} (~x{np.exp(BIAS_SHIFT):.1f} true rate)")

    rows = []
    for s in PLANTS:
        for arm in ARMS:
            r = run_arm(s, arm, fast, days=DAYS, logk_bias_shift=BIAS_SHIFT,
                        mismatch=STRESS_MISMATCH)
            rows.append(r)
            print(f"  plant {s} {arm:14s}  MW={r['gross_mw_mean']:.2f} "
                  f"viol_days={r['violation_days']} "
                  f"(postwarmup={r['viol_days_postwarmup']}) "
                  f"inh={r['inhibitor_php_per_mwh']:.0f} PHP/MWh")
    res = pd.DataFrame(rows)
    res.to_csv(RESULTS / "table2b_stress.csv", index=False)
    summ = summarize(res, ARMS)
    summ.to_csv(RESULTS / "table2b_summary.csv")
    print(f"\nTABLE 2b (stress x{np.exp(BIAS_SHIFT):.0f} kinetics, mean over "
          f"plants):")
    print(summ.to_string())

    # ---- pre-registered verdicts: on the six July 2026 plants ----------
    sub = res[res.plant.isin(PLANTS[:PREREG_N])]
    s6 = summarize(sub, ARMS)
    v, w = s6["viol_days_mean"], s6["viol_postwu_mean"]
    verdicts = [
        ("E1 baseline safe", v["baseline"] == 0),
        ("E2 nominal violates under kinetic mismatch", v["rto_nominal"] > 0),
        ("E3' hybrid(kappa=1): post-warmup <= 0.5 days/plant mean",
         w["rto_hybrid_k1"] <= 0.5),
        ("E5 back-off ablation: kappa=1 safer than kappa=0",
         w["rto_hybrid_k1"] < w["rto_hybrid_k0"]),
        ("E4a hybrid safer than open-loop nominal",
         v["rto_hybrid_k1"] < v["rto_nominal"]),
    ]
    print(f"\nPRE-REGISTERED VERDICTS (July 2026; plants "
          f"{PLANTS[0]}-{PLANTS[min(PREREG_N, len(PLANTS)) - 1]}):")
    for name, ok in verdicts:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    # ---- post hoc findings (P8b; reported, never pass/fail) --------------
    v, w, u = (summ["viol_days_mean"], summ["viol_postwu_mean"],
               summ["uplift_pct"])
    print(f"\nPOST HOC FINDINGS (2026-11-10; NOT pre-registered; "
          f"{len(PLANTS)} plants):")
    print(f"  F1 anchoring, additive modifier: nominal {v['rto_ma_nom']:.2f}"
          f" -> measured {v['rto_ma_meas_k0']:.2f} violation days")
    print(f"  F2 anchoring, log-space modifier: nominal "
          f"{v['rto_malog_nom']:.2f} -> measured {v['rto_malog_meas']:.2f} "
          f"violation days; uplift {u['rto_malog_nom']:+.1f}% -> "
          f"{u['rto_malog_meas']:+.1f}%")
    print("  F3 frontier sweep (uplift %, total / post-warmup violation "
          "days):")
    for fam in KAPPA_FAMILIES:
        for k in KAPPA_SWEEP:
            a = f"{fam}_k{k:g}"
            print(f"       {a:18s} {u[a]:+6.1f}%  {v[a]:.2f} / {w[a]:.2f}")

    if SMOKE:
        print(f"\nSmoke outputs (discarded): {RESULTS.parent}")
        return
    from provenance import stamp
    stamp("table2b")
    from closed_loop_figure import refresh
    fig = refresh()
    print("\nDone." + (f" Closed-loop figure and contrasts refreshed: {fig}"
                       if fig else " Run run_control_experiment.py too; the "
                       "closed-loop figure needs both regimes."))
    print("Commit results/ and figures/ after visual QA.")


if __name__ == "__main__":
    main()

"""
feedback_arms_check.py — E1 / ipis-thesis-geothermal-silica
P8b gate module: guards the closed-loop feedback arms.

WHY THIS EXISTS
    The first submission compared a hybrid arm that saw the measured
    silica against a scalar feedback baseline anchored to the NOMINAL
    brine composition. Nothing in the gate could have caught that,
    because the closed-loop experiments were too slow to gate. This
    module is fast (~15 s) and pins three things so the mistake cannot
    return silently:

      * continuity — the nominal-anchored arm and the pre-fix hybrid
        warm-up still reproduce the numbers committed in July 2026
        (commit b6ed76d), so the old tables remain auditable;
      * the anchoring effect itself — on the stress plants the
        measured-anchored modifier must violate far less than the
        nominal-anchored one;
      * the arm registry and the back-off sweep behave as documented.
"""

import warnings

import numpy as np

warnings.filterwarnings("ignore")

from run_control_experiment import (FastRTO, run_arm, parse_arm, ARMS_ALL,
                                    KAPPA_SWEEP, KAPPA_FAMILIES, FIXED_ARMS)
from run_stress_experiment import STRESS_MISMATCH, BIAS_SHIFT


def _self_check() -> None:
    checks = []
    fast = FastRTO()
    stress = dict(days=45.0, logk_bias_shift=BIAS_SHIFT,
                  mismatch=STRESS_MISMATCH)

    # 1. Arm registry
    n_expected = len(FIXED_ARMS) + len(KAPPA_FAMILIES) * len(KAPPA_SWEEP)
    ok = (len(ARMS_ALL) == len(set(ARMS_ALL)) == n_expected
          and parse_arm("rto_hybrid_k0.5") == ("rto_hybrid", 0.5)
          and parse_arm("rto_nominal") == ("rto_nominal", 0.0))
    try:
        parse_arm("rto_ma")          # the retired pre-fix name must fail
        ok = False
    except ValueError:
        pass
    checks.append(("Arm registry: unique names, gain parsing, retired "
                   "name rejected", ok, f"{len(ARMS_ALL)} arms"))

    # 2. Continuity: nominal-anchored additive arm == committed 'rto_ma'
    r_s = run_arm(100, "rto_ma_nom", fast, **stress)
    r_b = run_arm(0, "rto_ma_nom", fast, days=45.0)
    ok = (round(r_s["gross_mw_mean"], 2) == 7.09
          and r_s["violation_days"] == 17
          and r_s["viol_days_postwarmup"] == 15
          and round(r_b["gross_mw_mean"], 2) == 7.94
          and r_b["violation_days"] == 12)
    checks.append(("Continuity: rto_ma_nom reproduces committed rto_ma "
                   "(b6ed76d)", ok,
                   f"stress p100 {r_s['gross_mw_mean']:.2f}/"
                   f"{r_s['violation_days']}/{r_s['viol_days_postwarmup']}"
                   f" (7.09/17/15); benign p0 {r_b['gross_mw_mean']:.2f}/"
                   f"{r_b['violation_days']} (7.94/12)"))

    # 3. Continuity: pre-fix hybrid reproducible with the nominal warm-up
    r_h = run_arm(100, "rto_hybrid_k1", fast, warmup_anchor="nominal",
                  **stress)
    ok = (round(r_h["gross_mw_mean"], 2) == 5.76
          and r_h["violation_days"] == 2
          and r_h["viol_days_postwarmup"] == 0)
    checks.append(("Continuity: hybrid with nominal warm-up reproduces "
                   "committed numbers", ok,
                   f"{r_h['gross_mw_mean']:.2f}/{r_h['violation_days']}/"
                   f"{r_h['viol_days_postwarmup']} (5.76/2/0)"))

    # 4. The anchoring effect (the P8b correction): three stress plants
    v_nom = np.mean([run_arm(s, "rto_ma_nom", fast, **stress)
                     ["violation_days"] for s in (100, 101, 102)])
    v_meas = np.mean([run_arm(s, "rto_ma_meas_k0", fast, **stress)
                      ["violation_days"] for s in (100, 101, 102)])
    checks.append(("Anchoring: measured-anchored modifier violates < 25% "
                   "of nominal-anchored",
                   v_meas < 0.25 * v_nom,
                   f"{v_meas:.2f} vs {v_nom:.2f} violation days"))

    # 5. Back-off only tightens: the largest gain harvests less than none
    mw0 = run_arm(100, "rto_ma_meas_k0", fast, **stress)["gross_mw_mean"]
    mw2 = run_arm(100, "rto_ma_meas_k2", fast, **stress)["gross_mw_mean"]
    checks.append(("Back-off tightens: kappa=2 harvests less than kappa=0",
                   mw2 < mw0, f"{mw2:.2f} < {mw0:.2f} MW"))

    # 6. GP arm: finite and deterministic
    g1 = run_arm(100, "rto_gp_k1", fast, **stress)
    g2 = run_arm(100, "rto_gp_k1", fast, **stress)
    ok = (np.isfinite(g1["gross_mw_mean"])
          and g1["gross_mw_mean"] == g2["gross_mw_mean"]
          and g1["violation_days"] == g2["violation_days"])
    checks.append(("GP arm finite and deterministic (identical rerun)",
                   bool(ok), f"MW={g1['gross_mw_mean']:.2f}, "
                             f"viol={g1['violation_days']}"))

    width = max(len(c[0]) for c in checks)
    print("P8b self-check — feedback_arms_check.py")
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

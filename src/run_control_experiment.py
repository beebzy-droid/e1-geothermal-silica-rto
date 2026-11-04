"""
run_control_experiment.py — E1 / ipis-thesis-geothermal-silica
P4 build 4 (final): closed-loop benchmark — manuscript Table 2.

    cd src && python run_control_experiment.py            (full, ~10-30 min)
    cd src && python run_control_experiment.py --smoke    (pipeline check)

ARMS (per plant, identical brine/mismatch realization across arms)
    baseline    Fixed T=150 C, dose=1.0 ppm continuous — the empirical
                practice pattern (Gallup-informed dosing; cf. the EDC/BWA
                Bacman program, baltazar2014grc [T2]); no feedback.
    rto_nominal Vertex-robust RTO solved once with eps=0; applied constant.
                (No feedback — isolates the value of the model alone.)
    rto_ma      Daily RTO; eps updated each day from the observed daily
                trailing-mean rate label (MA bias, robust_rto mechanism).
    rto_hybrid  Daily RTO whose constraint IS the per-plant hybrid soft
                sensor (trained on the plant's own accumulated labels,
                retrained weekly, LOO-credibility lam): the N2 coupling
                made literal. Warmup: runs as rto_ma until >=7 labels.

METRICS per arm (mean +/- sd over plants): gross MW, uplift % vs baseline,
constraint-violation days (realized trailing-24h mean rate > r_max),
inhibitor cost PHP/MWh, net objective PHP/h.

Outputs: ../results/table2_control.csv, table2_summary.csv,
         ../figures/fig_control_benchmark.png
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

from silica_saturation import solubility_amorphous_silica_ga00
from temperature_lever import k_of_T
from synthetic_plant import (SyntheticPlant, EpisodeConfig, PlantSession,
                             MismatchConfig)
from soft_sensor import (nominal_dose_factor, PHYS_FEATURES, _LGB_SMALL,
                         _loo_shrinkage)
from robust_rto import (Economics, RTOConfig, RobustRTO, scenario_brines,
                        model_rate)
import lightgbm as lgb

RESULTS = Path(__file__).parent.parent / "results"
FIGURES = Path(__file__).parent.parent / "figures"

SMOKE = "--smoke" in sys.argv
PLANTS = list(range(2 if SMOKE else 6))
DAYS = 8.0 if SMOKE else 45.0
DT_MIN = 10.0
WARMUP_LABELS = 7
RETRAIN_EVERY_D = 7

CFG = RTOConfig()
ECON = Economics()
KAPPA = 1.0   # uncertainty back-off: constraint uses r_hat inflated by
              # exp(KAPPA * resid_sd) — the sensor's own LOO error. kappa=0
              # reproduces the no-back-off hybrid (kept as ablation arm
              # rto_hybrid_k0 in the stress experiment).


# ---------------------------------------------------------------------------
# Vectorized robust RTO solve (grid precomputation); consistency-checked
# against the gate-tested RobustRTO.solve()
# ---------------------------------------------------------------------------

class FastRTO:
    def __init__(self, cfg: RTOConfig = CFG, econ: Economics = ECON):
        self.cfg, self.econ = cfg, econ
        self.Ts = np.linspace(*cfg.T_bounds, cfg.grid_T)
        self.Ds = np.linspace(*cfg.dose_bounds, cfg.grid_dose)
        self.kT = np.array([k_of_T(t) for t in self.Ts])
        self.ce = np.array([solubility_amorphous_silica_ga00(t + 273.15)
                            for t in self.Ts])
        self.fD = nominal_dose_factor(self.Ds)
        self.brines = scenario_brines()
        # core rate grids per vertex: (nT, nD)
        self.core = {}
        for v, c in self.brines.items():
            s = np.maximum(c - self.ce, 0.0)
            self.core[v] = np.outer(self.kT * s ** 4.0, self.fD)
        self.rev = self.econ.revenue_php_h(0) * 0  # placeholder
        self.rev = np.array([self.econ.revenue_php_h(t) for t in self.Ts])
        self.cost = np.array([self.econ.inhibitor_cost_php_h(d)
                              for d in self.Ds])
        self.obj = self.rev[:, None] - self.cost[None, :]

    def solve(self, eps: float = 0.0,
              rate_grids: dict | None = None):
        """rate_grids: optional {vertex: (nT,nD)} overriding the core model
        (used by the hybrid-sensor arm). Returns (T*, d*, feasible)."""
        grids = rate_grids if rate_grids is not None else self.core
        worst = np.maximum.reduce([g for g in grids.values()]) + eps
        feas = worst <= self.cfg.r_max_g_t_min
        if not feas.any():
            return float(self.Ts[-1]), 0.0, False
        obj = np.where(feas, self.obj, -np.inf)
        i, j = np.unravel_index(np.argmax(obj), obj.shape)
        return float(self.Ts[i]), float(self.Ds[j]), True


# ---------------------------------------------------------------------------
# Hybrid-sensor constraint grid (steady-state query of the trained sensor)
# ---------------------------------------------------------------------------

def hybrid_rate_grids(fast: FastRTO, model: lgb.LGBMRegressor, lam: float,
                      sio2_held: float, sd: float = 0.0,
                      kappa: float = 0.0) -> dict:
    nT, nD = len(fast.Ts), len(fast.Ds)
    Tg = np.repeat(fast.Ts, nD)
    Dg = np.tile(fast.Ds, nT)
    ceg = np.repeat(fast.ce, nD)
    s_est = np.maximum(sio2_held - ceg, 0.0)
    feats = pd.DataFrame({
        "T_mean_24h": Tg, "T_min_24h": Tg,
        "dose_mean_24h": Dg, "dose_now": Dg,
        "sio2_held_now": sio2_held,
        "staleness_now": 240.0,
        "s_est_mean_24h": s_est,
        "exposure_now_min": 1440.0,
    })
    out = {}
    for v in fast.brines:
        core_flat = fast.core[v].reshape(-1)
        feats["core_24h"] = core_flat
        feats["log1p_core_24h"] = np.log1p(core_flat)
        resid = model.predict(feats[PHYS_FEATURES])
        r = np.maximum(np.expm1(np.log1p(core_flat) + lam * resid
                                + kappa * sd), 0.0)
        out[v] = r.reshape(nT, nD)
    return out


# ---------------------------------------------------------------------------
# Closed-loop episode for one arm
# ---------------------------------------------------------------------------

def run_arm(seed: int, arm: str, fast: FastRTO,
            days: float = DAYS, logk_bias_shift: float = 0.0,
            mismatch: MismatchConfig | None = None) -> dict:
    """logk_bias_shift threads the adverse-mismatch stress knob (Table 2b);
    mismatch overrides the random-draw config (None = Table 2 defaults).
    Defaults reproduce Table 2 exactly."""
    ep = EpisodeConfig(days=days, dt_min=DT_MIN)
    n = int(days * 24 * 60 / DT_MIN)
    steps_day = int(24 * 60 / DT_MIN)
    plant = SyntheticPlant(seed, mismatch=mismatch or MismatchConfig(),
                           logk_bias_shift=logk_bias_shift)
    sess = PlantSession(plant, ep)

    eps = 0.0
    labels = []          # (features_row_dict, label_value) accumulated daily
    lab_feats, lab_y = [], []
    sensor, lam, loo_sd = None, 0.0, 1.0
    is_hybrid = arm.startswith("rto_hybrid")
    kappa = 0.0 if arm.endswith("_k0") else KAPPA
    if arm == "baseline":
        T_cmd, d_cmd = 150.0, 1.0
    else:
        T_cmd, d_cmd, _ = fast.solve(eps=0.0)

    rates, T_hist, d_hist = [], [], []
    sio2_held = None
    day_rows = []
    violations = 0
    violations_postwarmup = 0
    mw_sum = 0.0
    cost_sum = 0.0

    for i in range(n):
        # 8-hourly grab sample (measurement for the sensor feature)
        if i % int(480 / DT_MIN) == 0:
            pass  # sample drawn after step using true value
        rec = sess.step(T_cmd, d_cmd)
        if i % int(480 / DT_MIN) == 0:
            sio2_held = sess.measure_sio2(rec["c_brine_true_mgkg"])
        rates.append(rec["rate_true_g_t_min"])
        mw_sum += ECON.gross_power_mw(T_cmd)
        cost_sum += ECON.inhibitor_cost_php_h(d_cmd) * (DT_MIN / 60.0)

        # end of day: label, learn, re-decide
        if (i + 1) % steps_day == 0:
            day = (i + 1) // steps_day
            target = float(np.mean(rates[-steps_day:]))
            label = sess.measure_rate_label(target)
            if day >= 2 and target > CFG.r_max_g_t_min:
                violations += 1
                if day > 8:
                    violations_postwarmup += 1
            # accumulate training rows for the hybrid arm
            core_now = model_rate(T_cmd, d_cmd, fast.brines["B"] * 0 +
                                  (sio2_held or fast.brines["B"]))
            ce_now = solubility_amorphous_silica_ga00(T_cmd + 273.15)
            lab_feats.append({
                "T_mean_24h": T_cmd, "T_min_24h": T_cmd,
                "dose_mean_24h": d_cmd, "dose_now": d_cmd,
                "sio2_held_now": sio2_held, "staleness_now": 240.0,
                "s_est_mean_24h": max((sio2_held or 0) - ce_now, 0.0),
                "exposure_now_min": 1440.0,
                "core_24h": core_now, "log1p_core_24h": np.log1p(core_now),
            })
            lab_y.append(label)

            if arm == "rto_ma" or is_hybrid:
                r_mod = model_rate(T_cmd, d_cmd, fast.brines["B"])
                eps = (1 - CFG.alpha_bias) * eps \
                    + CFG.alpha_bias * (label - r_mod)
            if is_hybrid and len(lab_y) >= WARMUP_LABELS \
                    and (day % RETRAIN_EVERY_D == 0 or sensor is None):
                labdf = pd.DataFrame(lab_feats)
                labdf["label_24h"] = lab_y
                y_h = np.log1p(labdf["label_24h"]) - labdf["log1p_core_24h"]
                sensor = lgb.LGBMRegressor(**_LGB_SMALL).fit(
                    labdf[PHYS_FEATURES], y_h)
                lam, loo_sd = _loo_shrinkage(labdf)

            if arm == "rto_nominal":
                pass                                  # constant policy
            elif arm == "rto_ma":
                T_cmd, d_cmd, _ = fast.solve(eps=eps)
            elif is_hybrid:
                if sensor is not None:
                    grids = hybrid_rate_grids(fast, sensor, lam,
                                              sio2_held or fast.brines["B"],
                                              sd=loo_sd, kappa=kappa)
                    T_cmd, d_cmd, _ = fast.solve(eps=0.0, rate_grids=grids)
                else:
                    # WARMUP RULE: until the sensor earns credibility,
                    # feedback may only TIGHTEN the constraint (eps >= 0),
                    # never relax it — scalar bias relaxation is exactly
                    # the unsafe extrapolation the rto_ma arm demonstrates.
                    T_cmd, d_cmd, _ = fast.solve(eps=max(eps, 0.0))
            T_hist.append(T_cmd); d_hist.append(d_cmd)

    hours = days * 24.0
    mw_mean = mw_sum / n
    mwh = mw_mean * hours
    return {"plant": seed, "arm": arm, "gross_mw_mean": mw_mean,
            "violation_days": violations,
            "viol_days_postwarmup": violations_postwarmup,
            "inhibitor_php_per_mwh": cost_sum / max(mwh, 1e-9),
            "net_php_h": mw_mean * 1000 * ECON.price_php_per_kwh
            - cost_sum / hours}


def main() -> None:
    RESULTS.mkdir(exist_ok=True); FIGURES.mkdir(exist_ok=True)
    fast = FastRTO()

    # consistency check vs the gate-tested grid solver
    ref = RobustRTO().solve()
    T0, d0, _ = fast.solve(eps=0.0)
    dT, dd = abs(T0 - ref.T_rej_C), abs(d0 - ref.dose_ppm)
    assert dT < 1e-9 and dd < 1e-9, (T0, ref.T_rej_C, d0, ref.dose_ppm)
    print(f"FastRTO consistency vs RobustRTO.solve(): OK "
          f"(T*={T0:.2f} C, d*={d0:.2f} ppm)")
    if SMOKE:
        print("SMOKE MODE — pipeline verification only.")

    rows = []
    arms = ("baseline", "rto_nominal", "rto_ma", "rto_hybrid")
    for s in PLANTS:
        for arm in arms:
            rows.append(run_arm(s, arm, fast))
            print(f"  plant {s} {arm:11s}  MW={rows[-1]['gross_mw_mean']:.2f} "
                  f"viol_days={rows[-1]['violation_days']} "
                  f"inh={rows[-1]['inhibitor_php_per_mwh']:.0f} PHP/MWh")
    res = pd.DataFrame(rows)
    res.to_csv(RESULTS / "table2_control.csv", index=False)

    base = res[res.arm == "baseline"].set_index("plant")["gross_mw_mean"]
    res["uplift_pct"] = res.apply(
        lambda r: 100 * (r.gross_mw_mean / base[r.plant] - 1), axis=1)
    summ = (res.groupby("arm")
            .agg(mw=("gross_mw_mean", "mean"),
                 uplift_pct=("uplift_pct", "mean"),
                 viol_days_mean=("violation_days", "mean"),
                 viol_days_max=("violation_days", "max"),
                 inh_php_mwh=("inhibitor_php_per_mwh", "mean"),
                 net_php_h=("net_php_h", "mean"))
            .reindex(list(arms)).round(2))
    summ.to_csv(RESULTS / "table2_summary.csv")
    print("\nTABLE 2 (mean over plants):")
    print(summ.to_string())

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    order = list(arms)
    a1.bar(order, [summ.loc[a, "mw"] for a in order], color="tab:blue")
    a1.set_ylabel("Mean gross power [MW]"); a1.tick_params(axis="x", rotation=20)
    a2.bar(order, [summ.loc[a, "viol_days_mean"] for a in order],
           color="tab:red")
    a2.set_ylabel("Constraint-violation days (mean)")
    a2.tick_params(axis="x", rotation=20)
    fig.suptitle(f"Closed-loop benchmark — {len(PLANTS)} plants x "
                 f"{DAYS:.0f} d (r_max={CFG.r_max_g_t_min} g/t/min)")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_control_benchmark.png", dpi=200)
    print("\nDone. Commit results/ and figures/ after visual QA.")


if __name__ == "__main__":
    main()

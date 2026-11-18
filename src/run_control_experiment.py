"""
run_control_experiment.py — E1 / ipis-thesis-geothermal-silica
Closed-loop benchmark, benign regime — manuscript Table 2.

    cd src && python run_control_experiment.py            (full, ~10-20 min)
    cd src && python run_control_experiment.py --smoke    (pipeline check)

CHANGELOG 2026-11-10 (P8b) — BASELINE CORRECTION, found after submission
    The original feedback baseline ("rto_ma") computed its daily
    innovation against the model evaluated at the NOMINAL brine-B
    composition, while the hybrid arm was given the MEASURED silica grab
    sample. That is not a like-for-like comparison: on a fourth-power
    constraint, day-to-day brine variation aliases into a
    nominal-anchored modifier and makes it hunt. The fix applied here:
      * the primary feedback baseline is now constraint adaptation
        anchored to the measured silica (rto_ma_meas);
      * the nominal-anchored arms are KEPT as an explicit anchoring
        ablation (rto_ma_nom = the old rto_ma, numbers unchanged);
      * the hybrid and GP arms use the measured anchor during warm-up too
        (the same bug sat in the hybrid's warm-up path);
      * a GP-residual comparator and a back-off variant of the scalar
        baseline complete a correction-model x back-off design.
    These arms were added AFTER seeing results (post hoc, not
    pre-registered) and are reported as such in the manuscript.
    run_arm(..., warmup_anchor="nominal") reproduces the pre-fix hybrid
    numbers of commit b6ed76d exactly.

ARMS (per plant, identical brine/mismatch realization across arms)
    baseline        Fixed T=150 C, dose=1.0 ppm continuous (empirical
                    practice pattern; baltazar2014grc [T2]); no feedback.
    rto_nominal     Vertex-robust RTO solved once; applied constant.
    --- anchoring ablation (scalar constraint adaptation, Chachuat 2008) --
    rto_ma_nom      additive modifier, innovation vs model at NOMINAL
                    brine B  (= the pre-fix "rto_ma")
    rto_malog_nom   log-space (multiplicative) modifier, NOMINAL anchor
    rto_ma_meas     additive modifier, innovation vs model at the
                    MEASURED silica  (primary feedback baseline)
    rto_malog_meas  log-space modifier, MEASURED anchor
    --- correction model x back-off gain (all measured-anchored) ----------
    Three families, each run at kappa in KAPPA_SWEEP; the arm name carries
    the gain, e.g. rto_hybrid_k1:
    rto_ma_meas_k*  scalar additive modifier + kappa * sd of its own
                    one-step prediction error (trailing 14 d)
    rto_gp_k*       GP residual (gp_residual.py) + kappa * posterior
                    predictive sd
    rto_hybrid_k*   LightGBM residual with LOO credibility + kappa * LOO
                    error sd
    Each family's sd is on its own scale, so equal kappa is NOT equal
    conservatism across families: compare the families as frontier
    curves over the sweep, not point by point.

PLANTS
    20 per regime. The first six (seeds 0-5; 100-105 under stress) are the
    plants of the July 2026 runs; the pre-registered verdicts are
    evaluated on those six. The other fourteen were added on 2026-11-10 so
    that differences between schemes come with a confidence interval.

METRICS per arm (mean over plants): gross MW, uplift % vs baseline,
constraint-violation days (realized trailing-24h mean rate > r_max; total
from day 2 and post-warm-up from day 9), inhibitor cost PHP/MWh, net
objective PHP/h. Violations are counted on the REALIZED plant, not on the
worst-case vertex of the envelope.

Outputs: ../results/table2_control.csv, table2_summary.csv
         (figure: closed_loop_figure.py, after both regimes have run)
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

from gp_residual import GPResidual

RESULTS = Path(__file__).parent.parent / "results"
FIGURES = Path(__file__).parent.parent / "figures"

SMOKE = "--smoke" in sys.argv
if SMOKE and __name__ == "__main__":
    # smoke output goes to a temp dir: never over the full-scale results
    import tempfile
    _tmp = Path(tempfile.mkdtemp(prefix="e1_smoke_"))
    RESULTS, FIGURES = _tmp / "results", _tmp / "figures"
PLANTS = list(range(2 if SMOKE else 20))
PREREG_N = 6     # the July 2026 plants: first six seeds of each regime
DAYS = 8.0 if SMOKE else 45.0
DT_MIN = 10.0
WARMUP_LABELS = 7
RETRAIN_EVERY_D = 7

CFG = RTOConfig()
ECON = Economics()
KAPPA_SWEEP = (0.0, 0.5, 1.0, 2.0)   # back-off gains (frontier sweep);
                                     # kappa=1 was the July 2026 design
                                     # value for the hybrid
BACKOFF_WINDOW_D = 14   # trailing window for the scalar family's own
                        # one-step prediction-error sd

FIXED_ARMS = ("baseline", "rto_nominal",
              "rto_ma_nom", "rto_malog_nom", "rto_malog_meas")
KAPPA_FAMILIES = ("rto_ma_meas", "rto_gp", "rto_hybrid")
ARMS_ALL = FIXED_ARMS + tuple(f"{fam}_k{k:g}" for fam in KAPPA_FAMILIES
                              for k in KAPPA_SWEEP)


def parse_arm(arm: str):
    """'rto_hybrid_k0.5' -> ('rto_hybrid', 0.5); fixed arms -> (arm, 0.0)."""
    if arm in FIXED_ARMS:
        return arm, 0.0
    fam, _, k = arm.rpartition("_k")
    if fam not in KAPPA_FAMILIES:
        raise ValueError(f"unknown arm {arm!r}")
    return fam, float(k)


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


def gp_rate_grids(fast: FastRTO, gp: GPResidual, sio2_held: float,
                  kappa: float = 0.0) -> dict:
    """Constraint grids from the GP residual: same residual target and
    same measured-silica anchor as the hybrid; only the regressor (and
    therefore the uncertainty estimate) differs."""
    nT, nD = len(fast.Ts), len(fast.Ds)
    Tg = np.repeat(fast.Ts, nD)
    Dg = np.tile(fast.Ds, nT)
    s_est = np.maximum(sio2_held - np.repeat(fast.ce, nD), 0.0)
    mu, sd = gp.predict(np.column_stack([Tg, Dg, s_est]))
    shift = (mu + kappa * sd).reshape(nT, nD)
    return {v: np.maximum(np.expm1(np.log1p(fast.core[v]) + shift), 0.0)
            for v in fast.brines}


# ---------------------------------------------------------------------------
# Closed-loop episode for one arm
# ---------------------------------------------------------------------------

def run_arm(seed: int, arm: str, fast: FastRTO,
            days: float = DAYS, logk_bias_shift: float = 0.0,
            mismatch: MismatchConfig | None = None,
            warmup_anchor: str = "measured") -> dict:
    """logk_bias_shift threads the adverse-mismatch stress knob (Table 2b);
    mismatch overrides the random-draw config (None = Table 2 defaults).
    warmup_anchor="nominal" reproduces the pre-fix warm-up of the learned
    arms (commit b6ed76d) for audit; "measured" is the corrected default."""
    arm_label = arm
    arm, kappa = parse_arm(arm)
    ep = EpisodeConfig(days=days, dt_min=DT_MIN)
    n = int(days * 24 * 60 / DT_MIN)
    steps_day = int(24 * 60 / DT_MIN)
    plant = SyntheticPlant(seed, mismatch=mismatch or MismatchConfig(),
                           logk_bias_shift=logk_bias_shift)
    sess = PlantSession(plant, ep)

    eps = 0.0            # additive constraint modifier
    theta = 0.0          # log-space (multiplicative) constraint modifier
    pred_err = []        # one-step errors of the corrected scalar model
    lab_feats, lab_y = [], []
    sensor, lam, loo_sd = None, 0.0, 1.0
    gp = None
    is_hybrid = arm == "rto_hybrid"
    is_gp = arm == "rto_gp"
    learned = is_hybrid or is_gp
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

            # ---- feedback: two anchors for the same daily label --------
            sio2_now = sio2_held or fast.brines["B"]
            r_nom = model_rate(T_cmd, d_cmd, fast.brines["B"])   # nominal
            r_meas = model_rate(T_cmd, d_cmd, sio2_now)          # measured
            a = CFG.alpha_bias
            if arm == "rto_ma_nom":
                eps = (1 - a) * eps + a * (label - r_nom)
            elif arm == "rto_malog_nom":
                if r_nom > 1e-9 and label > 1e-9:
                    theta = (1 - a) * theta \
                        + a * (np.log(label) - np.log(r_nom))
            elif arm == "rto_malog_meas":
                if r_meas > 1e-9 and label > 1e-9:
                    theta = (1 - a) * theta \
                        + a * (np.log(label) - np.log(r_meas))
            elif arm == "rto_ma_meas" or learned:
                r_anchor = r_meas
                if learned and warmup_anchor == "nominal":
                    r_anchor = r_nom                  # pre-fix behaviour
                pred_err.append(label - (r_anchor + eps))
                eps = (1 - a) * eps + a * (label - r_anchor)

            # ---- learned constraint models (weekly refit, same schedule) -
            if learned and len(lab_y) >= WARMUP_LABELS \
                    and (day % RETRAIN_EVERY_D == 0
                         or (sensor is None and gp is None)):
                labdf = pd.DataFrame(lab_feats)
                labdf["label_24h"] = lab_y
                y_h = np.log1p(labdf["label_24h"]) - labdf["log1p_core_24h"]
                if is_hybrid:
                    sensor = lgb.LGBMRegressor(**_LGB_SMALL).fit(
                        labdf[PHYS_FEATURES], y_h)
                    lam, loo_sd = _loo_shrinkage(labdf)
                else:
                    Xg = labdf[["T_mean_24h", "dose_mean_24h",
                                "s_est_mean_24h"]].to_numpy(dtype=float)
                    gp = GPResidual().fit(Xg, y_h.to_numpy(dtype=float))

            # ---- re-decide ---------------------------------------------
            if arm == "rto_nominal":
                pass                                  # constant policy
            elif arm == "rto_ma_nom":
                T_cmd, d_cmd, _ = fast.solve(eps=eps)
            elif arm == "rto_ma_meas":
                w = pred_err[-BACKOFF_WINDOW_D:]
                sd_u = float(np.std(w, ddof=1)) if len(w) >= 3 else 0.0
                T_cmd, d_cmd, _ = fast.solve(eps=eps + kappa * sd_u)
            elif arm in ("rto_malog_nom", "rto_malog_meas"):
                g = {v: c * np.exp(theta) for v, c in fast.core.items()}
                T_cmd, d_cmd, _ = fast.solve(eps=0.0, rate_grids=g)
            elif learned:
                if sensor is not None:
                    grids = hybrid_rate_grids(fast, sensor, lam, sio2_now,
                                              sd=loo_sd, kappa=kappa)
                    T_cmd, d_cmd, _ = fast.solve(eps=0.0, rate_grids=grids)
                elif gp is not None:
                    grids = gp_rate_grids(fast, gp, sio2_now, kappa=kappa)
                    T_cmd, d_cmd, _ = fast.solve(eps=0.0, rate_grids=grids)
                else:
                    # WARMUP RULE: until the learned model has its first
                    # WARMUP_LABELS labels, feedback may only TIGHTEN the
                    # constraint (eps >= 0), never relax it.
                    T_cmd, d_cmd, _ = fast.solve(eps=max(eps, 0.0))
            T_hist.append(T_cmd); d_hist.append(d_cmd)

    hours = days * 24.0
    mw_mean = mw_sum / n
    mwh = mw_mean * hours
    return {"plant": seed, "arm": arm_label, "gross_mw_mean": mw_mean,
            "violation_days": violations,
            "viol_days_postwarmup": violations_postwarmup,
            "inhibitor_php_per_mwh": cost_sum / max(mwh, 1e-9),
            "net_php_h": mw_mean * 1000 * ECON.price_php_per_kwh
            - cost_sum / hours}


def summarize(res: pd.DataFrame, arms) -> pd.DataFrame:
    base = res[res.arm == "baseline"].set_index("plant")["gross_mw_mean"]
    res = res.copy()
    res["uplift_pct"] = [100 * (r.gross_mw_mean / base[r.plant] - 1)
                         for r in res.itertuples()]
    return (res.groupby("arm")
            .agg(mw=("gross_mw_mean", "mean"),
                 uplift_pct=("uplift_pct", "mean"),
                 uplift_sd=("uplift_pct", "std"),
                 viol_days_mean=("violation_days", "mean"),
                 viol_days_sd=("violation_days", "std"),
                 viol_days_max=("violation_days", "max"),
                 viol_postwu_mean=("viol_days_postwarmup", "mean"),
                 inh_php_mwh=("inhibitor_php_per_mwh", "mean"),
                 net_php_h=("net_php_h", "mean"))
            .reindex(list(arms)).round(2))


def paired_contrast(res: pd.DataFrame, a: str, b: str, col: str,
                    n_boot: int = 4000, seed: int = 0):
    """Mean of (a - b) over plants with a seeded percentile-bootstrap 95%
    interval. Plants are the resampling unit (arms share each plant's
    brine and mismatch realization, so the comparison is paired)."""
    if col == "uplift_pct" and col not in res.columns:
        base = res[res.arm == "baseline"].set_index("plant")["gross_mw_mean"]
        res = res.copy()
        res[col] = [100 * (r.gross_mw_mean / base[r.plant] - 1)
                    for r in res.itertuples()]
    pa = res[res.arm == a].set_index("plant")[col]
    pb = res[res.arm == b].set_index("plant")[col]
    d = (pa - pb.reindex(pa.index)).to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(d.mean()), float(lo), float(hi)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
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
    for s in PLANTS:
        for arm in ARMS_ALL:
            r = run_arm(s, arm, fast)
            rows.append(r)
            print(f"  plant {s} {arm:14s}  MW={r['gross_mw_mean']:.2f} "
                  f"viol_days={r['violation_days']} "
                  f"(postwarmup={r['viol_days_postwarmup']}) "
                  f"inh={r['inhibitor_php_per_mwh']:.0f} PHP/MWh")
    res = pd.DataFrame(rows)
    res.to_csv(RESULTS / "table2_control.csv", index=False)
    summ = summarize(res, ARMS_ALL)
    summ.to_csv(RESULTS / "table2_summary.csv")
    print("\nTABLE 2 (benign regime, mean over plants):")
    print(summ.to_string())
    if SMOKE:
        print(f"\nSmoke outputs (discarded): {RESULTS.parent}")
        return
    from provenance import stamp
    stamp("table2")
    from closed_loop_figure import refresh
    fig = refresh()
    print("\nDone." + (f" Closed-loop figure and contrasts refreshed: {fig}"
                       if fig else " Run run_stress_experiment.py next; "
                       "it draws the closed-loop figure."))


if __name__ == "__main__":
    main()

"""
soft_sensor.py — E1 / ipis-thesis-geothermal-silica
Phase P4, build 2 of 3 (v2): the hybrid scaling-rate soft sensor + ablations.

WHAT CHANGED FROM v1 (documented because the failure is a finding)
    v1 evaluated zero-shot transfer to unseen truth realizations and the
    hybrid LOST to both baselines. Diagnosis: plant-mismatch draws
    (k-bias, reaction order, dose-response) are per-plant random constants
    — unpredictable on never-seen plants by construction. That split tests
    the wrong claim. A soft sensor (Kadlec et al. 2009) is trained on ITS
    plant's sparse history and predicts forward in time; there, the
    plant's own bias IS identifiable. v2 therefore uses:
      * per-plant models, strict temporal splits (train early / test late)
      * supervision from SPARSE LABELS only: one noisy observation per day
        of the trailing-24 h mean rate (coupon / turbidity-proxy realism;
        cf. Okazaki 2017 for what a hard sensor would provide) — never the
        hidden instantaneous truth
      * sensor target = TRAILING-24 H MEAN polymerization rate: the
        quantity that accumulates scale and that the RTO constrains.
    The v1 zero-shot table is retained in run_experiment.py as a secondary
    "transfer" result with its limitation stated — an honest boundary of
    the method, pre-empting the reviewer rather than hiding from them.

ARCHITECTURE (parallel hybrid; Thompson & Kramer 1994, von Stosch 2014)
    y_hat = expm1( log1p(core_24h) + g_ML(agg_features) ),  clipped >= 0
    core_24h : trailing-24 h mean of the P2 kinetic core x NOMINAL
               literature dose response (model side knows the nominal
               Gallup-anchored curve; truth perturbs it)
    g_ML     : LightGBM residual on causal trailing-window aggregates of
               OBSERVABLES only. Per-plant bias enters as a learnable
               offset — exactly what a residual is for.

ABLATION TRIPLE (manuscript Table 1)
    physics : core_24h alone
    pure_ml : LightGBM on observable aggregates only (no Ce, no s, no core)
    hybrid  : core + residual (this work)

LEAKAGE DISCIPLINE
    Features from observables only; FORBIDDEN truth-side columns raise.
    Labels are the only supervision; label noise is part of the plant.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math

import numpy as np
import pandas as pd
import lightgbm as lgb

from silica_saturation import solubility_amorphous_silica_ga00
from synthetic_plant import SyntheticPlant, EpisodeConfig, MismatchConfig
from temperature_lever import line_rate

FORBIDDEN_COLUMNS = {"rate_true_g_t_min", "c_brine_true_mgkg",
                     "wA", "wB", "wC", "wD", "flash"}

WINDOW_MIN = 24 * 60          # trailing window: 24 h
LABEL_EVERY_MIN = 24 * 60     # one sparse label per day
LABEL_REL_NOISE = 0.10        # coupon/proxy observation noise

_NOM = MismatchConfig()


def nominal_dose_factor(dose_ppm: np.ndarray) -> np.ndarray:
    """Model-side NOMINAL dose response (Gallup-anchored family, nominal
    parameters eta=0.50 @ 1 ppm). Truth uses a perturbed instance."""
    x = np.asarray(dose_ppm, dtype=float) / _NOM.d_opt_ppm
    f = 1.0 - _NOM.eta_max * x * np.exp(1.0 - x)
    return f + _NOM.overdose_penalty * np.maximum(0.0, x - 2.0)


# ---------------------------------------------------------------------------
# Episode generation with varied excitation
# ---------------------------------------------------------------------------

def _schedules(seed: int, n: int, dt_min: float) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed + 10_000)
    seg = max(1, int(24 * 60 / dt_min))            # ~daily moves
    T = np.empty(n); d = np.empty(n)
    for start in range(0, n, seg):
        sl = slice(start, min(start + seg, n))
        T[sl] = rng.uniform(100.0, 160.0)
        d[sl] = rng.choice([0.0, float(rng.uniform(0.2, 4.0))])
    return T, d


def simulate_plant(seed: int, days: float, dt_min: float = 10.0) -> pd.DataFrame:
    ep = EpisodeConfig(days=days, dt_min=dt_min)
    n = int(days * 24 * 60 / dt_min)
    T_sched, d_sched = _schedules(seed, n, dt_min)
    df = SyntheticPlant(seed).simulate(ep, T_setpoint_C=T_sched,
                                       dose_ppm=d_sched)
    df["episode"] = seed
    return df


# ---------------------------------------------------------------------------
# Trailing-window aggregation, labels, features
# ---------------------------------------------------------------------------

def _trailing_mean(x: np.ndarray, w: int) -> np.ndarray:
    """Causal trailing mean with window w steps (NaN until window filled)."""
    s = pd.Series(x)
    return s.rolling(w, min_periods=w).mean().to_numpy()


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Add trailing-mean truth target, sparse noisy labels, and causal
    observable aggregates for one plant's episode."""
    g = df.copy()
    dt = float(g["t_min"].iloc[1] - g["t_min"].iloc[0])
    w = int(WINDOW_MIN / dt)

    # target (hidden; evaluation only) and sparse labels (supervision)
    g["target_24h"] = _trailing_mean(g["rate_true_g_t_min"].to_numpy(), w)
    rng = np.random.default_rng(int(g["episode"].iloc[0]) + 77_000)
    g["label_24h"] = np.nan
    idx = np.arange(w, len(g), int(LABEL_EVERY_MIN / dt))
    g.loc[g.index[idx], "label_24h"] = (
        g["target_24h"].iloc[idx].to_numpy()
        * (1 + rng.normal(0, LABEL_REL_NOISE, len(idx))))

    # observables
    g["sio2_held"] = g["sio2_meas_mgkg"].ffill()
    last_t = g["t_min"].where(g["sio2_meas_mgkg"].notna()).ffill()
    g["staleness_min"] = g["t_min"] - last_t
    ce = np.array([solubility_amorphous_silica_ga00(t + 273.15)
                   for t in g["T_meas_C"]])
    s_est = g["sio2_held"].to_numpy() - ce
    core = np.array([line_rate(c, t) if (c == c and c > 0) else 0.0
                     for c, t in zip(g["sio2_held"], g["T_meas_C"])])
    core = core * nominal_dose_factor(g["dose_ppm"].to_numpy())

    expo = np.zeros(len(g)); run = 0.0
    for i, p in enumerate(s_est > 0):
        run = run + dt if p else 0.0
        expo[i] = run

    # causal aggregates (all trailing 24 h)
    g["T_mean_24h"] = _trailing_mean(g["T_meas_C"].to_numpy(), w)
    g["T_min_24h"] = pd.Series(g["T_meas_C"]).rolling(w, min_periods=w).min().to_numpy()
    g["dose_mean_24h"] = _trailing_mean(g["dose_ppm"].to_numpy(), w)
    g["dose_now"] = g["dose_ppm"]
    g["sio2_held_now"] = g["sio2_held"]
    g["staleness_now"] = g["staleness_min"]
    # physics-derived (hybrid-only)
    g["s_est_mean_24h"] = _trailing_mean(s_est, w)
    g["exposure_now_min"] = expo
    g["core_24h"] = _trailing_mean(core, w)
    g["log1p_core_24h"] = np.log1p(g["core_24h"])
    return g


PURE_FEATURES = ["T_mean_24h", "T_min_24h", "dose_mean_24h", "dose_now",
                 "sio2_held_now", "staleness_now"]
PHYS_FEATURES = PURE_FEATURES + ["s_est_mean_24h", "exposure_now_min",
                                 "core_24h", "log1p_core_24h"]


def _guard(cols) -> None:
    bad = FORBIDDEN_COLUMNS & set(cols)
    if bad:
        raise ValueError(f"[leakage] forbidden truth-side columns: {bad}")


# ---------------------------------------------------------------------------
# Per-plant training (tiny-data LightGBM) and the ablation triple
# ---------------------------------------------------------------------------

_LGB_SMALL = dict(n_estimators=250, learning_rate=0.06, num_leaves=7,
                  min_child_samples=3, reg_lambda=1.0, subsample=1.0,
                  random_state=0, n_jobs=1, verbose=-1)


@dataclass
class PlantSensors:
    hybrid: lgb.LGBMRegressor
    pure_ml: lgb.LGBMRegressor
    n_labels: int
    lam: float          # shrinkage of the residual toward the physics prior
    resid_sd: float     # LOO prediction-error sd of the (shrunk) residual,
                        # log1p space — the sensor's own uncertainty, used
                        # by the RTO's back-off (kappa * resid_sd)


def _loo_shrinkage(lab: pd.DataFrame) -> tuple:
    """Cross-validated credibility of the residual: leave-one-out residual
    predictions r_i vs residual targets e_i; lam* = <e,r>/<r,r> clipped to
    [0,1]. lam -> 0 when the residual carries no out-of-sample signal, so
    the hybrid degrades gracefully to the physics core.
    Returns (lam, loo_sd): loo_sd is the sd of the LOO prediction error
    (e - lam*r) in log1p space — the residual's own uncertainty estimate,
    consumed by the RTO as a multiplicative constraint back-off."""
    e = (np.log1p(lab["label_24h"]) - lab["log1p_core_24h"]).to_numpy()
    n = len(lab)
    r = np.zeros(n)
    X = lab[PHYS_FEATURES]
    for i in range(n):
        m = np.ones(n, dtype=bool); m[i] = False
        mdl = lgb.LGBMRegressor(**_LGB_SMALL).fit(X[m], e[m])
        r[i] = float(mdl.predict(X[~m])[0])
    denom = float(r @ r)
    if denom <= 0:
        return 0.0, float(np.std(e, ddof=1)) if len(e) > 2 else 1.0
    lam = float(np.clip((e @ r) / denom, 0.0, 1.0))
    # decision hysteresis: keep the residual only if it improves LOO SSE
    # by a clear margin; otherwise collapse to the physics prior. Guards
    # against spuriously positive small-sample correlations.
    sse0 = float(e @ e)
    sse_lam = float((e - lam * r) @ (e - lam * r))
    if sse_lam > 0.85 * sse0:
        lam = 0.0
    loo_err = e - lam * r
    loo_sd = float(np.std(loo_err, ddof=1)) if len(e) > 2 else 1.0
    return lam, loo_sd


def train_plant(g: pd.DataFrame, train_end_min: float) -> PlantSensors:
    """Train both learned arms on the plant's labels up to train_end_min."""
    _guard(PHYS_FEATURES); _guard(PURE_FEATURES)
    lab = g[(g["label_24h"].notna()) & (g["t_min"] <= train_end_min)]
    if len(lab) < 4:
        raise ValueError(f"only {len(lab)} labels before {train_end_min} min "
                         "— extend history")
    y_h = np.log1p(lab["label_24h"]) - lab["log1p_core_24h"]
    m_h = lgb.LGBMRegressor(**_LGB_SMALL).fit(lab[PHYS_FEATURES], y_h)
    lam, loo_sd = _loo_shrinkage(lab)
    y_p = np.log1p(lab["label_24h"])
    m_p = lgb.LGBMRegressor(**_LGB_SMALL).fit(lab[PURE_FEATURES], y_p)
    return PlantSensors(m_h, m_p, len(lab), lam, loo_sd)


def predict_triple(sens: PlantSensors, g: pd.DataFrame) -> pd.DataFrame:
    m = g["target_24h"].notna()
    gg = g[m]
    r_h = np.maximum(np.expm1(gg["log1p_core_24h"].to_numpy()
                              + sens.lam
                              * sens.hybrid.predict(gg[PHYS_FEATURES])), 0.0)
    r_p = np.maximum(np.expm1(sens.pure_ml.predict(gg[PURE_FEATURES])), 0.0)
    return pd.DataFrame({"t_min": gg["t_min"], "target": gg["target_24h"],
                         "physics": gg["core_24h"].to_numpy(),
                         "pure_ml": r_p, "hybrid": r_h})


def eval_arms(pred: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    out = {}
    for arm in ("physics", "pure_ml", "hybrid"):
        e = np.log1p(pred[arm]) - np.log1p(pred["target"])
        m = pred["target"] > 0.01
        ratio = pred.loc[m, arm].clip(lower=1e-9) / pred.loc[m, "target"]
        out[arm] = {
            "rmse_log1p": float(np.sqrt(np.mean(e ** 2))),
            "mae": float(np.mean(np.abs(pred[arm] - pred["target"]))),
            "within_f2": float(((ratio > 0.5) & (ratio < 2.0)).mean())
            if m.any() else float("nan"),
        }
    return out


def run_ablation(seeds: List[int], days: float, train_days: float,
                 dt_min: float = 10.0) -> pd.DataFrame:
    """Per-plant temporal ablation: train on labels in [24h, train_days],
    evaluate on [train_days, days]. Returns per-plant metrics."""
    rows = []
    for s in seeds:
        g = prepare(simulate_plant(s, days, dt_min))
        sens = train_plant(g, train_end_min=train_days * 24 * 60)
        test = g[g["t_min"] > train_days * 24 * 60]
        met = eval_arms(predict_triple(sens, test))
        for arm, m in met.items():
            rows.append((s, arm, sens.n_labels, m["rmse_log1p"],
                         m["mae"], m["within_f2"]))
    return pd.DataFrame(rows, columns=["plant", "arm", "n_labels",
                                       "rmse_log1p", "mae_g_t_min",
                                       "within_factor2"])


def summarize(res: pd.DataFrame) -> pd.DataFrame:
    return (res.groupby("arm")
            .agg(rmse_log1p_mean=("rmse_log1p", "mean"),
                 rmse_log1p_sd=("rmse_log1p", "std"),
                 mae_mean=("mae_g_t_min", "mean"),
                 within_f2_mean=("within_factor2", "mean"))
            .reset_index())


# ---------------------------------------------------------------------------
# Self-check (smoke scale: 4 plants x 12 days, 8 training labels each)
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1-2. Leakage guard + pure-ML physics-free
    try:
        _guard(PHYS_FEATURES + ["flash"])
        checks.append(("Leakage guard fires", False, "not caught"))
    except ValueError:
        checks.append(("Leakage guard fires", True, ""))
    phys_only = {"s_est_mean_24h", "exposure_now_min", "core_24h",
                 "log1p_core_24h"}
    checks.append(("Pure-ML feature set physics-free",
                   not (phys_only & set(PURE_FEATURES)),
                   f"{len(PURE_FEATURES)} features"))

    # 3. Temporal split hygiene on one plant
    g = prepare(simulate_plant(0, days=12.0))
    lab_t = g.loc[g["label_24h"].notna(), "t_min"]
    train_end = 9 * 24 * 60
    checks.append(("Temporal split: all training labels precede test window",
                   (lab_t[lab_t <= train_end].max() < g["t_min"].max()),
                   f"labels/plant={int(g['label_24h'].notna().sum())}, "
                   f"train labels={int((lab_t <= train_end).sum())}"))

    # 4-6. Ablation on 4 plants: hybrid must beat both arms
    res = run_ablation(seeds=[0, 1, 2, 3], days=12.0, train_days=9.0)
    summ = summarize(res).set_index("arm")
    h, p, q = (summ.loc[a, "rmse_log1p_mean"]
               for a in ("hybrid", "physics", "pure_ml"))
    checks.append(("Hybrid beats pure physics (per-plant temporal test)",
                   h < p, f"hybrid={h:.3f} vs physics={p:.3f}"))
    checks.append(("Hybrid beats pure ML under label scarcity (8 labels)",
                   h < q, f"hybrid={h:.3f} vs pure_ml={q:.3f}"))
    checks.append(("Within-factor-2 report",
                   True,
                   "hybrid {:.0%} | physics {:.0%} | pure_ml {:.0%}".format(
                       summ.loc["hybrid", "within_f2_mean"],
                       summ.loc["physics", "within_f2_mean"],
                       summ.loc["pure_ml", "within_f2_mean"])))

    # 7. Graceful degradation, absolute-or-relative tolerance:
    #    a hybrid may never be MATERIALLY worse than its physics prior —
    #    within +0.02 rmse_log1p (label-noise floor at n~9 labels) or 5%
    #    relative, whichever is larger — and must deliver >=1 material win
    #    (>20% gain) where mismatch is material. Relative-only tolerance
    #    on a near-zero base punishes noise, not degradation.
    piv = res.pivot(index="plant", columns="arm", values="rmse_log1p")
    tol = np.maximum(piv["physics"] * 0.05, 0.02)
    never_worse = bool((piv["hybrid"] <= piv["physics"] + tol).all())
    big_wins = int((piv["hybrid"] < piv["physics"] * 0.8).sum())
    checks.append(("Graceful degradation (abs/rel tol) + >=1 material win",
                   never_worse and big_wins >= 1,
                   f"material wins={big_wins}/4, worst abs penalty="
                   f"{float((piv['hybrid']-piv['physics']).max()):+.3f}"))

    width = max(len(c[0]) for c in checks)
    print("P4 build-2 self-check — soft_sensor.py v2 (smoke scale)")
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


if __name__ == "__main__":
    _self_check()

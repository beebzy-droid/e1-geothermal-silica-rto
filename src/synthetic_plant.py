"""
synthetic_plant.py — E1 / ipis-thesis-geothermal-silica
Phase P4, build 1 of 3: the synthetic-truth plant.

WHY THIS EXISTS (and how a JPC reviewer will read it)
    The soft sensor and RTO must be evaluated against a "plant" that is
    deliberately NOT the model: structurally perturbed kinetics, induction
    dynamics the model core omits, a non-monotonic inhibitor response, and
    a sparse/noisy measurement layer. Performance claims in P5 are made
    against this truth, never against the model's own outputs, and never
    against T3 vendor numbers (validate_target() rule). This is the
    standard plant-model-mismatch evaluation pattern in the process-control
    literature; the ablation triple (hybrid vs pure-ML vs pure-physics)
    trained/evaluated on this rig becomes Table 1 of the manuscript.

TRUTH-MODEL CONSTRUCTION (every deviation parameterized + documented)
    rate_true = f_dose(u) * B(T) * k(T) * s**n_true, gated by induction
      k(T), Ce(T)  ..... the T1-fitted P2 core (regenerated from raw data)
      B(T) ............. smooth lognormal bias field on the k(T) nodes
                         (structural mismatch, sigma configurable)
      n_true ........... perturbed reaction order ~ N(4, 0.15), clipped
                         [3.6, 4.4] (RR79 calls 4th order "approximate")
      Ce bias .......... +/- few % solubility mismatch
      induction ........ P(s) fitted from RR79 Table II (T1 data) —
                         log10 P = a + b*log10 s + c*T; the truth keeps
                         a supersaturation-exposure clock; the model core
                         has no induction state (known structural gap the
                         ML residual must absorb)
      f_dose(u) ........ non-monotonic inhibitor response anchored
                         QUALITATIVELY to Gallup (2002) [T1]: best organic
                         formulation ~50% suppression near ~1 ppm, benefit
                         lost (and mildly reversed) on overdose. The
                         functional FORM and exact numbers are SYNTHETIC
                         (tagged as such); P4 fits the controller against
                         perturbed instances so nothing depends on the
                         exact shape.

MEASUREMENT MODEL (shift-based plant reality)
    SiO2 grab sample every 8 h, 5% rel. noise (sparse!)
    Line temperature every step, sigma 0.3 degC
    Inhibitor dose: known (manipulated)
    True scaling rate: HIDDEN — evaluation only.

Brine scenarios: convex mixtures of the Tiwi endmembers (T1 envelope per
docs/G7_uncertainty_commitment.md) with a bounded random walk, plus flash-
fraction perturbation. PHREEQC speciation is not called inside the
time-stepping loop (cost); GA00 Ce is used, with the speciation layer
reserved for the P6 chemistry-correction study — a documented choice.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import math

import numpy as np
import pandas as pd

from silica_saturation import solubility_amorphous_silica_ga00
from silica_kinetics import load_tableII
from temperature_lever import k_of_T, line_rate

# Tiwi endmember reservoir SiO2 (mg/kg) — T1: Sugiaman 2004 Table 1,
# mirrored from brine_speciation.TIWI_ENDMEMBERS (import avoided so this
# module runs without phreeqpython installed).
_ENDMEMBER_SIO2 = {"A": 135.0, "B": 638.0, "C": 648.0, "D": 509.0}


# ---------------------------------------------------------------------------
# Induction-period correlation fitted from RR79 Table II (T1 data)
# ---------------------------------------------------------------------------

def _fit_induction() -> Dict[str, float]:
    ds = load_tableII()
    m = (ds.induction_min > 0) & ds.fit_mask
    s, P, T = ds.supersat_g_t[m], ds.induction_min[m], ds.temperature_C[m]
    X = np.column_stack([np.ones(m.sum()), np.log10(s), T])
    y = np.log10(P)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    r2 = 1 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return {"a": float(beta[0]), "b": float(beta[1]),
            "c": float(beta[2]), "r2": r2, "n": int(m.sum())}


_INDUCTION = _fit_induction()


def induction_period_min(s_g_t: float, T_C: float) -> float:
    """Induction period P [min] from the RR79-fitted correlation."""
    if s_g_t <= 0:
        return math.inf
    return 10.0 ** (_INDUCTION["a"]
                    + _INDUCTION["b"] * math.log10(s_g_t)
                    + _INDUCTION["c"] * T_C)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class MismatchConfig:
    sigma_logk_bias: float = 0.35     # lognormal sd of k(T) node bias
    sigma_order: float = 0.15         # sd of true reaction order about 4
    order_clip: tuple = (3.6, 4.4)
    sigma_ce_bias: float = 0.03       # rel. sd of solubility bias
    # SYNTHETIC dose-response (Gallup-2002-anchored qualitatively):
    eta_max: float = 0.50             # max kinetic suppression (~50%, T1-anchored)
    d_opt_ppm: float = 1.0            # dose of max suppression (~1 ppm, T1-anchored)
    sigma_eta: float = 0.10           # per-episode perturbation of eta_max
    sigma_dopt_rel: float = 0.25      # per-episode perturbation of d_opt
    overdose_penalty: float = 0.10    # mild rate increase per (d/d_opt - 2)+


@dataclass
class MeasurementConfig:
    sio2_sample_every_min: int = 480  # shift-based grab sample (8 h)
    sio2_rel_noise: float = 0.05
    temp_noise_C: float = 0.3


@dataclass
class EpisodeConfig:
    days: float = 14.0
    dt_min: float = 10.0
    # Brine-mixture dynamics: mean-reverting (OU) fluctuation AROUND the
    # nominal operating composition. CHANGELOG 2026-07-15: replaced a pure
    # simplex random walk, which systematically DILUTED the brine (drift
    # from vertex B toward the simplex centroid, c_brine 799->579 mg/kg
    # over 10 d) — a modeling artifact, not field physics; it handed every
    # controller a vanishing constraint and inflated harvest-side results.
    mixture_walk_sigma: float = 0.02   # per-step noise on weights
    mixture_reversion: float = 0.01    # OU pull/step toward nominal
                                       # (tau ~ 17 h at dt=10 min)
    mixture_nominal: tuple = (0.0, 1.0, 0.0, 0.0)   # vertex B operating pt
    flash_nominal: float = 0.25        # scenario input (see P2 close-out)
    flash_walk_sigma: float = 0.002
    flash_reversion: float = 0.01
    flash_bounds: tuple = (0.20, 0.30)


class SyntheticPlant:
    """The 'true plant': perturbed kinetics + induction + dose response
    + sparse noisy measurements. One instance = one truth realization."""

    def __init__(self, seed: int,
                 mismatch: MismatchConfig = MismatchConfig(),
                 meas: MeasurementConfig = MeasurementConfig(),
                 zero_mismatch: bool = False,
                 logk_bias_shift: float = 0.0):
        """logk_bias_shift: deterministic shift added to the sampled k(T)
        bias nodes — the ADVERSE-MISMATCH stress knob (+0.69 => plants run
        ~x2.0 faster than the model believes). 0.0 = Table 2 conditions."""
        self.rng = np.random.default_rng(seed)
        self.cfg, self.meas = mismatch, meas
        self.logk_bias_shift = float(logk_bias_shift)
        if zero_mismatch:
            self._logk_bias_nodes = np.zeros(7)
            self.n_true, self.ce_bias = 4.0, 1.0
            self.eta_max, self.d_opt = 0.0, mismatch.d_opt_ppm
        else:
            self._logk_bias_nodes = self.rng.normal(
                0.0, mismatch.sigma_logk_bias, size=7) + self.logk_bias_shift
            self.n_true = float(np.clip(
                self.rng.normal(4.0, mismatch.sigma_order), *mismatch.order_clip))
            self.ce_bias = float(self.rng.normal(1.0, mismatch.sigma_ce_bias))
            self.eta_max = float(np.clip(
                self.rng.normal(mismatch.eta_max, mismatch.sigma_eta), 0.05, 0.9))
            self.d_opt = float(mismatch.d_opt_ppm *
                               self.rng.lognormal(0.0, mismatch.sigma_dopt_rel))
        self._T_nodes = np.array([5.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0])

    # -- truth physics ------------------------------------------------------

    def _k_true(self, T_C: float) -> float:
        bias = float(np.interp(T_C, self._T_nodes, self._logk_bias_nodes))
        return k_of_T(T_C) * math.exp(bias)

    def dose_factor(self, dose_ppm: float) -> float:
        """Non-monotonic TRUE inhibitor response (SYNTHETIC form,
        Gallup-anchored qualitatively). f=1 untreated; min at d_opt;
        mild reversal on gross overdose."""
        if dose_ppm < 0:
            raise ValueError("dose must be >= 0")
        x = dose_ppm / self.d_opt
        f = 1.0 - self.eta_max * x * math.exp(1.0 - x)
        f += self.cfg.overdose_penalty * max(0.0, x - 2.0)
        return f

    def true_rate(self, c_brine_mgkg: float, T_C: float, dose_ppm: float,
                  exposure_min: float) -> float:
        """True polymerization rate [g/t/min], induction-gated."""
        ce = solubility_amorphous_silica_ga00(T_C + 273.15) * self.ce_bias
        s = max(c_brine_mgkg - ce, 0.0)
        if s <= 0.0:
            return 0.0
        if exposure_min < induction_period_min(s, T_C):
            return 0.0
        return self.dose_factor(dose_ppm) * self._k_true(T_C) * s ** self.n_true

    # -- episode simulation --------------------------------------------------

    def simulate(self, ep: EpisodeConfig = EpisodeConfig(),
                 T_setpoint_C: Optional[np.ndarray] = None,
                 dose_ppm: Optional[np.ndarray] = None) -> pd.DataFrame:
        n = int(ep.days * 24 * 60 / ep.dt_min)
        t_min = np.arange(n) * ep.dt_min

        if T_setpoint_C is None:      # default: steps over the lever range
            T_setpoint_C = 150.0 + 0.0 * t_min
            T_setpoint_C[n // 3: 2 * n // 3] = 130.0
            T_setpoint_C[2 * n // 3:] = 115.0
        if dose_ppm is None:
            dose_ppm = np.full(n, 0.0)

        # brine mixture random walk on the Tiwi simplex (start at B)
        w = np.array([0.0, 1.0, 0.0, 0.0])
        sio2_vec = np.array([_ENDMEMBER_SIO2[k] for k in ("A", "B", "C", "D")])
        flash = ep.flash_nominal
        rows = []
        exposure = 0.0
        w_nom = np.array(ep.mixture_nominal, dtype=float)
        for i in range(n):
            w = np.clip(w + ep.mixture_reversion * (w_nom - w)
                        + self.rng.normal(0, ep.mixture_walk_sigma, 4),
                        0, None)
            w = w / w.sum()
            flash = float(np.clip(
                flash + ep.flash_reversion * (ep.flash_nominal - flash)
                + self.rng.normal(0, ep.flash_walk_sigma),
                *ep.flash_bounds))
            c_res = float(w @ sio2_vec)
            c_brine = c_res / (1.0 - flash)
            T = float(T_setpoint_C[i])
            ce = solubility_amorphous_silica_ga00(T + 273.15) * self.ce_bias
            exposure = exposure + ep.dt_min if c_brine > ce else 0.0
            r_true = self.true_rate(c_brine, T, float(dose_ppm[i]), exposure)
            r_model = line_rate(c_brine, T)   # uninhibited P2 core prediction
            rows.append((t_min[i], w[0], w[1], w[2], w[3], flash, c_brine,
                         T, float(dose_ppm[i]), r_true, r_model))

        df = pd.DataFrame(rows, columns=[
            "t_min", "wA", "wB", "wC", "wD", "flash", "c_brine_true_mgkg",
            "T_line_C", "dose_ppm", "rate_true_g_t_min", "rate_core_g_t_min"])

        # measurement layer
        df["T_meas_C"] = df["T_line_C"] + self.rng.normal(
            0, self.meas.temp_noise_C, n)
        df["sio2_meas_mgkg"] = np.nan
        idx = np.arange(0, n, int(self.meas.sio2_sample_every_min / ep.dt_min))
        df.loc[idx, "sio2_meas_mgkg"] = (
            df.loc[idx, "c_brine_true_mgkg"]
            * (1 + self.rng.normal(0, self.meas.sio2_rel_noise, len(idx))))
        return df




# ---------------------------------------------------------------------------
# Incremental API for closed-loop control (decisions made online)
# ---------------------------------------------------------------------------

class PlantSession:
    """Step-by-step interface to the SAME truth physics as simulate():
    the controller sets (T, dose) each step after observing the past.
    Truth-path draws consume the plant rng in the identical per-step order
    as simulate(), so a session driven with a pre-recorded schedule replays
    simulate()'s truth path exactly (verified in the self-check).
    Measurement noise uses a separate stream (seed+50000)."""

    def __init__(self, plant: "SyntheticPlant", ep: EpisodeConfig = EpisodeConfig()):
        self.p, self.ep = plant, ep
        self.meas_rng = np.random.default_rng(
            plant.rng.bit_generator.seed_seq.entropy if False else 0)
        # deterministic separate measurement stream:
        self.meas_rng = np.random.default_rng(50_000)
        self.w = np.array([0.0, 1.0, 0.0, 0.0])
        self.sio2_vec = np.array([_ENDMEMBER_SIO2[k] for k in ("A", "B", "C", "D")])
        self.flash = ep.flash_nominal
        self.exposure = 0.0
        self.i = 0

    def step(self, T_C: float, dose_ppm: float) -> dict:
        ep, p = self.ep, self.p
        w_nom = np.array(ep.mixture_nominal, dtype=float)
        self.w = np.clip(self.w + ep.mixture_reversion * (w_nom - self.w)
                         + p.rng.normal(0, ep.mixture_walk_sigma, 4),
                         0, None)
        self.w = self.w / self.w.sum()
        self.flash = float(np.clip(
            self.flash + ep.flash_reversion * (ep.flash_nominal - self.flash)
            + p.rng.normal(0, ep.flash_walk_sigma),
            *ep.flash_bounds))
        c_res = float(self.w @ self.sio2_vec)
        c_brine = c_res / (1.0 - self.flash)
        ce = solubility_amorphous_silica_ga00(T_C + 273.15) * p.ce_bias
        self.exposure = self.exposure + ep.dt_min if c_brine > ce else 0.0
        r_true = p.true_rate(c_brine, T_C, dose_ppm, self.exposure)
        t_min = self.i * ep.dt_min
        self.i += 1
        return {"t_min": t_min, "c_brine_true_mgkg": c_brine,
                "T_line_C": T_C, "dose_ppm": dose_ppm,
                "rate_true_g_t_min": r_true}

    def measure_sio2(self, c_brine_true: float,
                     rel_noise: float = MeasurementConfig.sio2_rel_noise) -> float:
        return float(c_brine_true * (1 + self.meas_rng.normal(0, rel_noise)))

    def measure_rate_label(self, target_24h: float,
                           rel_noise: float = 0.10) -> float:
        return float(target_24h * (1 + self.meas_rng.normal(0, rel_noise)))


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1. Induction correlation fitted from T1 data, sane
    checks.append(("Induction P(s,T) fitted from RR79 (r2 reported)",
                   _INDUCTION["r2"] > 0.5 and _INDUCTION["b"] < 0,
                   f"n={_INDUCTION['n']}, r2={_INDUCTION['r2']:.2f}, "
                   f"b={_INDUCTION['b']:.2f} (P falls with s)"))

    # 2. Seed reproducibility
    d1 = SyntheticPlant(7).simulate(EpisodeConfig(days=2.0))
    d2 = SyntheticPlant(7).simulate(EpisodeConfig(days=2.0))
    checks.append(("Same seed => identical episode",
                   d1.equals(d2), f"rows={len(d1)}"))

    # 3. Zero-mismatch consistency: truth collapses onto the P2 core
    p0 = SyntheticPlant(1, zero_mismatch=True)
    c, T = 850.0, 130.0
    rt = p0.true_rate(c, T, dose_ppm=0.0, exposure_min=1e9)
    rm = line_rate(c, T)
    checks.append(("Zero-mismatch truth == P2 core (dose=0, post-induction)",
                   abs(rt - rm) / rm < 1e-12, f"dev={abs(rt-rm)/rm:.1e}"))

    # 4. Mismatch is real but bounded across a (T, s) grid
    p = SyntheticPlant(42)
    ratios = []
    for T in (100.0, 120.0, 150.0):
        for c in (700.0, 850.0, 1000.0):
            r_t = p.true_rate(c, T, 0.0, 1e9)
            r_m = line_rate(c, T)
            if r_m > 0:
                ratios.append(r_t / r_m)
    ratios = np.array(ratios)
    checks.append(("Structural mismatch present and bounded (x0.2-5)",
                   ratios.min() > 0.2 and ratios.max() < 5.0
                   and (abs(np.log(ratios)) > 0.05).any(),
                   f"truth/core in [{ratios.min():.2f}, {ratios.max():.2f}]"))

    # 5. Dose response non-monotonic: d_opt suppresses, overdose reverses
    f0 = p.dose_factor(0.0)
    fopt = p.dose_factor(p.d_opt)
    fover = p.dose_factor(4.0 * p.d_opt)
    checks.append(("Dose response: f(d_opt) < f(0)=1 < recovery on overdose",
                   fopt < f0 == 1.0 and fover > fopt,
                   f"f(0)=1.00, f(d_opt)={fopt:.2f}, f(4 d_opt)={fover:.2f}"))

    # 6. Measurement sparsity as configured (8 h grabs over 14 d = 42)
    df = SyntheticPlant(3).simulate()
    n_samples = int(df["sio2_meas_mgkg"].notna().sum())
    checks.append(("SiO2 grabs sparse as configured (42 in 14 d)",
                   n_samples == 42, f"samples={n_samples}, steps={len(df)}"))

    # 7. Envelope respected: brine inside flashed Tiwi bounds
    lo = min(_ENDMEMBER_SIO2.values()) / (1 - 0.20)
    hi = max(_ENDMEMBER_SIO2.values()) / (1 - 0.30)
    inside = df["c_brine_true_mgkg"].between(lo * 0.99, hi * 1.01).all()
    checks.append(("Brine stays inside flashed T1 envelope",
                   bool(inside),
                   f"[{df['c_brine_true_mgkg'].min():.0f}, "
                   f"{df['c_brine_true_mgkg'].max():.0f}] mg/kg"))

    # 8. Induction gating visible: early steps at high T carry zero true rate
    early_zero = (df["rate_true_g_t_min"].iloc[:3] == 0.0).all()
    checks.append(("Induction gate active at episode start", bool(early_zero), ""))

    # 9. PlantSession replays simulate()'s truth path exactly
    ep9 = EpisodeConfig(days=1.0)
    n9 = int(ep9.days * 24 * 60 / ep9.dt_min)
    Tsched = np.full(n9, 140.0); Dsched = np.full(n9, 0.7)
    ref = SyntheticPlant(11).simulate(ep9, T_setpoint_C=Tsched, dose_ppm=Dsched)
    sess = PlantSession(SyntheticPlant(11), ep9)
    got = [sess.step(140.0, 0.7) for _ in range(n9)]
    dev_c = max(abs(g["c_brine_true_mgkg"] - r) for g, r
                in zip(got, ref["c_brine_true_mgkg"]))
    dev_r = max(abs(g["rate_true_g_t_min"] - r) for g, r
                in zip(got, ref["rate_true_g_t_min"]))
    checks.append(("PlantSession replays simulate() truth path exactly",
                   dev_c < 1e-9 and dev_r < 1e-9,
                   f"max devs: c={dev_c:.1e}, r={dev_r:.1e}"))

    # 10b. Brine stationarity: OU fluctuation must NOT drift — mean
    #     c_brine of days 8-10 within 5% of days 1-3 (kills the dilution
    #     artifact permanently)
    epS = EpisodeConfig(days=10.0)
    dfS = SyntheticPlant(31).simulate(epS,
        T_setpoint_C=np.full(int(10*144), 140.0),
        dose_ppm=np.zeros(int(10*144)))
    early = dfS["c_brine_true_mgkg"].iloc[0:3*144].mean()
    late = dfS["c_brine_true_mgkg"].iloc[7*144:10*144].mean()
    checks.append(("Brine stationary (no dilution drift, days 8-10 vs 1-3)",
                   abs(late / early - 1) < 0.05,
                   f"early={early:.0f}, late={late:.0f} mg/kg "
                   f"({100*(late/early-1):+.1f}%)"))

    # 10. Adverse-mismatch knob: +0.69 shift ~doubles the true rate
    p_base = SyntheticPlant(21)
    p_adv = SyntheticPlant(21, logk_bias_shift=0.69)
    rb = p_base.true_rate(900.0, 130.0, 0.0, 1e9)
    ra = p_adv.true_rate(900.0, 130.0, 0.0, 1e9)
    checks.append(("Adverse shift +0.69 doubles true rate (same seed)",
                   rb > 0 and abs(ra / rb - math.exp(0.69)) < 1e-9,
                   f"ratio={ra/rb:.3f} (target {math.exp(0.69):.3f})"))

    width = max(len(c[0]) for c in checks)
    print("P4 build-1 self-check — synthetic_plant.py")
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
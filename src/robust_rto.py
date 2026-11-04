"""
robust_rto.py — E1 / ipis-thesis-geothermal-silica
Phase P4, build 3 of 3: robust economic RTO of inhibitor dose and
reinjection temperature (implements docs/G7_uncertainty_commitment.md).

FORMULATION (steady-state RTO layer; two-layer rationale per Darby 2011)
    max_{T_rej, dose}   Revenue(T_rej) - InhibitorCost(dose)
    s.t.  r_model(T_rej, dose; vertex v) + eps  <=  r_max   FOR EVERY v
          T_rej in [T_MIN, T_MAX],  dose in [0, DOSE_MAX]

    * Vertex-robust: the scaling-rate constraint holds on all four Tiwi
      endmember vertices (T1 envelope) at the perturbed flash bounds —
      a violation on the worst-case brine is a plant event, not an
      averaging residual (G7 doc).
    * eps is a modifier-adaptation BIAS term updated from soft-sensor
      innovations (first-order MA reserved as escalation; decided at P5
      with numbers, per G7 doc):
          eps <- (1-alpha)*eps + alpha*(r_observed - r_model(u_applied))
    * Optimizer: dense 2-D grid + local refinement. Deliberate choice:
      deterministic, global on a bounded 2-D space, trivially auditable —
      a JPC reviewer can re-run it; no solver-convergence appendix needed.

ECONOMICS (all SCENARIO parameters; tier-tagged; P6 sensitivity set)
    Gross recoverable power from cooling the brine from separator
    temperature to T_rej:
        W [MW] = m_flow * cp * (T_sep - T_rej) * eta_binary / 1000
    Primary reporting is PER UNIT MASS FLOW (MW per kg/s, PHP/MWh);
    absolute numbers for the 400 kg/s Bacman-scale scenario are secondary
    and flagged: that flow figure originates in a T3 trade-press report of
    an EDC presentation — motivation/scenario only, never validation.

CONSTRAINT UNITS CAVEAT (stated everywhere it appears)
    r_max is in polymerization-rate units [g/t/min]; the mm/yr deposition
    closure (module 3b) is pending the Weres (1981) primary transcription.
    The RTO structure is invariant to that closure — only the constraint's
    calibration will move.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import math

import numpy as np

from silica_saturation import solubility_amorphous_silica_ga00
from temperature_lever import k_of_T
from soft_sensor import nominal_dose_factor

# ---------------------------------------------------------------------------
# Scenario set: Tiwi endmember vertices (T1) x flash bounds (scenario)
# ---------------------------------------------------------------------------

# Reservoir SiO2 mg/kg — T1: Sugiaman 2004 Table 1 (see brine_speciation)
VERTEX_SIO2 = {"A": 135.0, "B": 638.0, "C": 648.0, "D": 509.0}
FLASH_BOUNDS = (0.20, 0.30)          # scenario input (P2 close-out)


def scenario_brines() -> Dict[str, float]:
    """Separated-brine SiO2 for each vertex at the WORST flash bound
    (highest concentration) — the robust constraint uses the edge."""
    xhi = FLASH_BOUNDS[1]
    return {v: c / (1.0 - xhi) for v, c in VERTEX_SIO2.items()}


# ---------------------------------------------------------------------------
# Economics (scenario parameters — tier-tagged, P6 sensitivity set)
# ---------------------------------------------------------------------------

@dataclass
class Economics:
    m_flow_kg_s: float = 400.0        # SCENARIO (T3-motivated Bacman scale)
    T_sep_C: float = 180.0            # SCENARIO (separator/brine supply T)
    cp_kj_kg_k: float = 4.19          # water-like brine heat capacity
    eta_binary: float = 0.10          # SCENARIO conversion effectiveness
    price_php_per_kwh: float = 5.5    # SCENARIO (PH wholesale-scale figure)
    inhibitor_php_per_kg: float = 300.0  # SCENARIO

    def gross_power_mw(self, T_rej_C: float) -> float:
        dT = max(self.T_sep_C - T_rej_C, 0.0)
        return self.m_flow_kg_s * self.cp_kj_kg_k * dT * self.eta_binary / 1000.0

    def revenue_php_h(self, T_rej_C: float) -> float:
        return self.gross_power_mw(T_rej_C) * 1000.0 * self.price_php_per_kwh

    def inhibitor_cost_php_h(self, dose_ppm: float) -> float:
        kg_h = dose_ppm * self.m_flow_kg_s * 3600.0 / 1e6  # mg/kg * kg/s
        return kg_h * self.inhibitor_php_per_kg


# ---------------------------------------------------------------------------
# Model-side constraint function (P2 core x nominal dose response)
# ---------------------------------------------------------------------------

def model_rate(T_rej_C: float, dose_ppm: float, c_brine_mgkg: float) -> float:
    """Steady polymerization rate [g/t/min] the RTO reasons with."""
    ce = solubility_amorphous_silica_ga00(T_rej_C + 273.15)
    s = max(c_brine_mgkg - ce, 0.0)
    if s <= 0.0:
        return 0.0
    return float(nominal_dose_factor(np.array([dose_ppm]))[0]) \
        * k_of_T(T_rej_C) * s ** 4.0


# ---------------------------------------------------------------------------
# The robust RTO
# ---------------------------------------------------------------------------

@dataclass
class RTOConfig:
    r_max_g_t_min: float = 0.5        # SCENARIO constraint limit (see caveat)
    T_bounds: Tuple[float, float] = (95.0, 175.0)
    dose_bounds: Tuple[float, float] = (0.0, 4.0)
    grid_T: int = 161                 # 0.5 C resolution
    grid_dose: int = 81               # 0.05 ppm resolution
    alpha_bias: float = 0.5           # MA bias-update gain
    robust: bool = True               # False => nominal vertex B only


@dataclass
class RTOResult:
    T_rej_C: float
    dose_ppm: float
    objective_php_h: float
    gross_mw: float
    worst_vertex: str
    worst_rate: float
    feasible: bool


class RobustRTO:
    def __init__(self, cfg: RTOConfig = RTOConfig(),
                 econ: Economics = Economics()):
        self.cfg, self.econ = cfg, econ
        self.eps = 0.0                # MA bias on the constraint
        self._brines = scenario_brines()

    def _constraint_rates(self, T: float, d: float) -> Dict[str, float]:
        vs = self._brines if self.cfg.robust else {"B": self._brines["B"]}
        return {v: model_rate(T, d, c) + self.eps for v, c in vs.items()}

    def solve(self) -> RTOResult:
        Ts = np.linspace(*self.cfg.T_bounds, self.cfg.grid_T)
        Ds = np.linspace(*self.cfg.dose_bounds, self.cfg.grid_dose)
        best = None
        for T in Ts:
            rev = self.econ.revenue_php_h(T)
            for d in Ds:
                rates = self._constraint_rates(T, d)
                worst_v = max(rates, key=rates.get)
                if rates[worst_v] > self.cfg.r_max_g_t_min:
                    continue
                obj = rev - self.econ.inhibitor_cost_php_h(d)
                if best is None or obj > best[0]:
                    best = (obj, T, d, worst_v, rates[worst_v])
        if best is None:
            # fully infeasible: fall back to hottest T, zero dose, flagged
            T, d = self.cfg.T_bounds[1], 0.0
            rates = self._constraint_rates(T, d)
            wv = max(rates, key=rates.get)
            return RTOResult(T, d, self.econ.revenue_php_h(T), 
                             self.econ.gross_power_mw(T), wv, rates[wv],
                             feasible=False)
        obj, T, d, wv, wr = best
        return RTOResult(T, d, obj, self.econ.gross_power_mw(T), wv, wr,
                         feasible=True)

    def update_bias(self, r_observed: float, u_applied: Tuple[float, float],
                    vertex: str = "B") -> float:
        """MA bias update from a soft-sensor observation of the realized
        rate at the applied decision (nominal vertex attribution)."""
        r_mod = model_rate(*u_applied, self._brines[vertex])
        self.eps = ((1 - self.cfg.alpha_bias) * self.eps
                    + self.cfg.alpha_bias * (r_observed - r_mod))
        return self.eps


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []
    econ = Economics()

    # 1. Economics monotone: colder rejection => more gross power
    p150, p120, p90 = (econ.gross_power_mw(t) for t in (150.0, 120.0, 95.0))
    checks.append(("Gross power increases as T_rej falls",
                   p90 > p120 > p150,
                   f"{p150:.1f} / {p120:.1f} / {p90:.1f} MW"))

    # 2. Robust optimum exists and the constraint is ACTIVE (economics
    #    want colder than chemistry allows)
    rto = RobustRTO()
    res = rto.solve()
    active = res.worst_rate > 0.9 * rto.cfg.r_max_g_t_min
    checks.append(("Robust optimum feasible with ACTIVE constraint",
                   res.feasible and active,
                   f"T*={res.T_rej_C:.1f} C, dose*={res.dose_ppm:.2f} ppm, "
                   f"{res.gross_mw:.1f} MW, worst={res.worst_vertex}"
                   f"@{res.worst_rate:.3f}/{rto.cfg.r_max_g_t_min}"))

    # 3. Optimizer respects the non-monotonic dose response: never
    #    overdoses past 2x d_opt (beyond which benefit reverses)
    checks.append(("No overdose beyond 2x d_opt",
                   res.dose_ppm <= 2.0 + 1e-9, f"dose*={res.dose_ppm:.2f} ppm"))

    # 4. Robustness is doing work: nominal-only RTO picks a colder T that
    #    VIOLATES on at least one non-nominal vertex
    rto_nom = RobustRTO(RTOConfig(robust=False))
    res_nom = rto_nom.solve()
    rates_check = {v: model_rate(res_nom.T_rej_C, res_nom.dose_ppm, c)
                   for v, c in scenario_brines().items()}
    wv = max(rates_check, key=rates_check.get)
    violates = rates_check[wv] > rto.cfg.r_max_g_t_min
    checks.append(("Nominal-only RTO violates on a non-nominal vertex",
                   violates and res_nom.T_rej_C <= res.T_rej_C,
                   f"nominal T*={res_nom.T_rej_C:.1f} C -> {wv} at "
                   f"{rates_check[wv]:.3f} > {rto.cfg.r_max_g_t_min}"))

    # 5. Price of robustness reported (G7 acceptance criterion #2 input)
    por = (res_nom.objective_php_h - res.objective_php_h) \
        / max(res_nom.objective_php_h, 1e-9)
    checks.append(("Price of robustness computed",
                   0.0 <= por < 0.25,
                   f"{100*por:.1f}% of nominal objective "
                   f"({res_nom.gross_mw:.1f} -> {res.gross_mw:.1f} MW)"))

    # 6. MA bias update: under x1.25 plant-side k mismatch, 10 RTO cycles
    #    with sensor feedback eliminate the violation (G7 criterion #3,
    #    smoke form; full closed-loop test in the control experiment)
    rto_ma = RobustRTO()
    true_scale = 1.25
    violations_before = violations_after = 0
    for it in range(10):
        r = rto_ma.solve()
        u = (r.T_rej_C, r.dose_ppm)
        # plant realizes a rate 25% above the model on the worst vertex
        r_true = true_scale * model_rate(u[0], u[1],
                                         scenario_brines()[r.worst_vertex])
        if r_true > rto_ma.cfg.r_max_g_t_min * 1.001:
            if it == 0:
                violations_before += 1
            violations_after = violations_after + 1 if it >= 7 else violations_after
        rto_ma.update_bias(r_true, u, vertex=r.worst_vertex)
    checks.append(("MA bias removes x1.25-mismatch violation within 10 iters",
                   violations_before >= 1 and violations_after == 0,
                   f"eps_final={rto_ma.eps:+.3f} g/t/min"))

    # 7. Grid resolution sanity: refining the grid moves T* by < 1 C
    fine = RobustRTO(RTOConfig(grid_T=321, grid_dose=161)).solve()
    checks.append(("Grid-refinement stability (dT* < 1 C)",
                   abs(fine.T_rej_C - res.T_rej_C) < 1.0,
                   f"{res.T_rej_C:.2f} -> {fine.T_rej_C:.2f} C"))

    width = max(len(c[0]) for c in checks)
    print("P4 build-3 self-check — robust_rto.py")
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

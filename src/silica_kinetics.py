"""
silica_kinetics.py — E1 / ipis-thesis-geothermal-silica
Phase P2 (base process model), module 3 of 3.

Amorphous-silica polymerization kinetics for the brine line: the
first-principles core that the ML residual (P4) will correct.

RATE-LAW STRUCTURE — transcribed from the primary source in hand
(Rothbaum & Rohde 1979, JCIS 71(3), doi:10.1016/0021-9797(79)90328-X,
PDF in literature/; structural statements verified against abstract,
Figs. 14-15 discussion, and Table II layout on 2026-07-14):

  1. After an induction period P, the maximum polymerization rate obeys
     approximately FOURTH-ORDER kinetics in supersaturation:
         R_max(T) = k(T) * (C0 - Ce(T))**4          [g SiO2 / (L*hr)]
  2. Induction period P shortens with supersaturation; at fixed T,
     R * P**1.5 is approximately constant (their correlating function).
  3. Temperature dependence is WEAK and NON-MONOTONIC: formal
     Ea ~ 3 kcal/mol for 5-90 degC; above ~90 degC the maximum rate
     DECREASES with temperature (larger, fewer polymers; falling
     supersaturation as Ce rises). Consequence for E1: at the 150 degC
     reinjection line, naive Arrhenius extrapolation of low-T data
     OVERPREDICTS the polymerization rate. This is the quantitative
     mitigation of "Limitation A" and must appear in the manuscript.

PARAMETER PROVENANCE
  k(T) is NOT hard-coded. It is fitted from src/data/rothbaum1979_tableII.csv,
  a human-transcribed copy of the paper's Table II (protocol in the CSV
  header). Vision-based auto-transcription was rejected: a misread digit
  becomes a silently wrong fitted parameter, violating the evidence rules.
  Until the CSV is filled and marked VERIFIED, this module runs in
  DEV mode on structure-only self-checks and refuses strict mode.

SCOPE NOTES
  - This module predicts POLYMERIZATION rate (monomer depletion). The
    wall-DEPOSITION closure (mm/yr) additionally needs molecular-deposition
    kinetics (Weres 1981 — primary PDF still to be acquired) and a
    transport factor; that is module 3b, stubbed at the bottom.
  - Inhibitor/pH effects enter HERE (kinetic suppression), not in the
    equilibrium layer — established by module-2 self-check #3.

Dependencies: numpy; silica_saturation (module 1) for Ce(T).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import csv
import math

import numpy as np

from silica_saturation import solubility_amorphous_silica_ga00

_DATA = Path(__file__).parent / "data" / "rothbaum1979_tableII.csv"

RATE_ORDER = 4.0  # Rothbaum & Rohde (1979): approximate 4th-order kinetics

CHECKSUM_TOL = 0.02  # rows must satisfy |R*P^1.5 - printed|/printed < 2%


@dataclass(frozen=True)
class KineticDataset:
    temperature_C: np.ndarray
    supersat_g_t: np.ndarray      # (C0-Ce), g/t = mg/L, as printed
    rate_g_t_min: np.ndarray      # R, g t^-1 min^-1, as printed
    induction_min: np.ndarray     # P, minutes (0 = none observed)
    fit_mask: np.ndarray          # rows eligible for 4th-order fitting
    verified: bool
    n: int
    n_checksum_pass: int
    n_excluded: int


def load_tableII(path: Path = _DATA) -> KineticDataset:
    """Load the transcription CSV; validate every row against the paper's
    own printed R*P^(3/2) checksum; build the fitting mask."""
    verified = False
    rows, chks, notes = [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                key = line.lstrip("#").strip()
                if key.lower().startswith("transcription_status:"):
                    verified = key.split(":", 1)[1].strip().upper() == "VERIFIED"
                continue
            f_rest = [line] + list(f)
            reader = csv.DictReader(f_rest)
            for r in reader:
                if not r.get("temperature_C"):
                    continue
                rows.append((float(r["temperature_C"]),
                             float(r["supersaturation_g_per_t"]),
                             float(r["max_rate_g_per_t_min"]),
                             float(r["induction_period_min"])))
                chks.append(r["checksum_printed"].strip())
                notes.append((r.get("notes") or "").strip())
            break
    arr = np.array(rows) if rows else np.empty((0, 4))
    n = len(rows)
    n_pass, fit_mask = 0, np.zeros(n, dtype=bool)
    for i in range(n):
        T, s, R, P = arr[i]
        excluded = "excluded" in notes[i].lower()
        if chks[i] not in ("--", ""):
            printed = float(chks[i])
            ok = abs(R * P ** 1.5 - printed) / printed < CHECKSUM_TOL
            n_pass += ok
            if not ok and not excluded:
                raise ValueError(
                    f"[evidence] Table II row {i} (T={T:g}, s={s:g}) fails the "
                    f"printed R*P^1.5 checksum and is not marked excluded — "
                    f"fix the transcription."
                )
        fit_mask[i] = (not excluded) and ("goldbag" not in notes[i].lower())
    return KineticDataset(
        temperature_C=arr[:, 0] if n else np.array([]),
        supersat_g_t=arr[:, 1] if n else np.array([]),
        rate_g_t_min=arr[:, 2] if n else np.array([]),
        induction_min=arr[:, 3] if n else np.array([]),
        fit_mask=fit_mask, verified=verified, n=n,
        n_checksum_pass=n_pass, n_excluded=int(n - fit_mask.sum()),
    )


# ---------------------------------------------------------------------------
# Fitting — k(T) per isotherm from R = k * s**4
# ---------------------------------------------------------------------------

def fit_rate_constants(ds: KineticDataset, strict: bool = False) -> Dict[float, Dict[str, float]]:
    """
    Fit k(T) per experimental isotherm by least squares on
    log(R) = log(k) + 4*log(s). Returns {T_C: {"k": ..., "r2": ..., "n": ...}}.

    strict=True refuses to fit from an UNVERIFIED transcription — the
    code-level analogue of validate_target() for hand-entered data.
    """
    if strict and not ds.verified:
        raise ValueError(
            "[evidence] rothbaum1979_tableII.csv is UNVERIFIED. Complete the "
            "transcription protocol in the CSV header before strict-mode fitting."
        )
    if ds.n == 0:
        raise ValueError("Dataset empty — transcribe Table II first (see CSV header).")

    out: Dict[float, Dict[str, float]] = {}
    for T in sorted(set(ds.temperature_C.tolist())):
        m = (ds.temperature_C == T) & ds.fit_mask
        s, r = ds.supersat_g_t[m], ds.rate_g_t_min[m]
        if len(s) < 2:
            continue
        y = np.log(r) - RATE_ORDER * np.log(s)   # log k per point
        logk = float(np.mean(y))
        pred = logk + RATE_ORDER * np.log(s)
        ss_res = float(np.sum((np.log(r) - pred) ** 2))
        ss_tot = float(np.sum((np.log(r) - np.mean(np.log(r))) ** 2))
        out[T] = {
            "k": math.exp(logk),
            "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "n": int(m.sum()),
        }
    return out


def polymerization_rate(
    c_sio2_mgkg: float,
    T_K: float,
    k_at_T: float,
    inhibition_factor: float = 1.0,
) -> float:
    """
    R = f_inh * k * max(C - Ce, 0)**4, in g SiO2 t^-1 min^-1 (the paper's
    printed units); C in mg/kg (~= g/t for dilute brine), Ce from the GA00
    primary correlation. Multiply by 0.060 to convert to g L^-1 hr^-1.

    inhibition_factor in (0, 1]: the kinetic-suppression multiplier through
    which the dose/pH lever acts (parameterized in P4 from Gallup dose-
    response data; non-monotonic in dose per gallup2002investigations).
    """
    if not (0.0 < inhibition_factor <= 1.0):
        raise ValueError("inhibition_factor must be in (0, 1].")
    ce_g_t = solubility_amorphous_silica_ga00(T_K)   # mg/kg ~= g/t
    s = max(c_sio2_mgkg - ce_g_t, 0.0)
    return inhibition_factor * k_at_T * s ** RATE_ORDER


# ---------------------------------------------------------------------------
# Module 3b stub — wall deposition closure (blocked on Weres 1981 primary)
# ---------------------------------------------------------------------------

def deposition_rate_mm_per_yr(*args, **kwargs):
    """
    BLOCKED: requires molecular-deposition kinetics from Weres, Yee & Tsao
    (1981) — acquire the primary PDF (doi:10.1016/0021-9797(81)90230-7).
    Implementing the mm/yr closure without it would be fabrication.
    """
    raise NotImplementedError(
        "Deposition closure pending Weres (1981) primary-source transcription. "
        "Polymerization rate (this module) is the soft-sensor core quantity "
        "until module 3b lands."
    )


# ---------------------------------------------------------------------------
# Self-check — structural tests that need NO transcribed data,
# plus data tests that activate automatically once the CSV is filled.
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # Structure 1: 4th-order scaling — doubling supersaturation => 16x rate
    T = 373.15
    ce = solubility_amorphous_silica_ga00(T)
    c1, c2 = ce + 200.0, ce + 400.0
    r1 = polymerization_rate(c1, T, k_at_T=1.0)
    r2 = polymerization_rate(c2, T, k_at_T=1.0)
    checks.append(("4th-order structure: 2x supersat -> 16x rate",
                   abs(r2 / r1 - 16.0) < 1e-9, f"ratio={r2/r1:.3f}"))

    # Structure 2: undersaturated brine => zero rate
    r0 = polymerization_rate(ce * 0.5, T, k_at_T=1.0)
    checks.append(("Undersaturated => zero polymerization rate", r0 == 0.0, ""))

    # Structure 3: inhibition factor scales rate; domain guard fires
    r_inh = polymerization_rate(c1, T, k_at_T=1.0, inhibition_factor=0.3)
    checks.append(("Inhibition factor scales rate", abs(r_inh / r1 - 0.3) < 1e-12, ""))
    try:
        polymerization_rate(c1, T, k_at_T=1.0, inhibition_factor=0.0)
        checks.append(("Inhibition domain guard fires", False, "no exception"))
    except ValueError:
        checks.append(("Inhibition domain guard fires", True, ""))

    # Structure 4: deposition stub is blocked, loudly
    try:
        deposition_rate_mm_per_yr()
        checks.append(("Deposition closure correctly blocked", False, "no exception"))
    except NotImplementedError:
        checks.append(("Deposition closure correctly blocked", True, ""))

    # Data 1: dataset loads, checksums pass, exclusions counted
    ds = load_tableII()
    checks.append(("Table II loads: 37 rows, VERIFIED",
                   ds.n == 37 and ds.verified, f"rows={ds.n}, verified={ds.verified}"))
    checks.append(("Printed R*P^1.5 checksums pass (33 checkable rows)",
                   ds.n_checksum_pass == 33,
                   f"pass={ds.n_checksum_pass}, excluded_from_fit={ds.n_excluded}"))

    # Data 2: strict-mode fit now permitted
    fits = fit_rate_constants(ds, strict=True)
    rep = ", ".join(f"{t:.0f}C r2={v['r2']:.2f}" for t, v in fits.items())
    checks.append(("Strict-mode fit unlocked, all isotherms fitted",
                   len(fits) == 7, rep))

    # Data 3 (PHYSICS, the Limitation-A result): k(T) rises to ~90C then falls
    ks = {t: v["k"] for t, v in fits.items()}
    rises = ks[90.0] > ks[5.0]
    falls = ks[150.0] < ks[90.0] and ks[180.0] < ks[90.0]
    checks.append(("k(T) non-monotonic: rises 5->90C, falls 90->180C",
                   rises and falls,
                   "k90/k5={:.1f}, k150/k90={:.2f}, k180/k90={:.2f}".format(
                       ks[90.0]/ks[5.0], ks[150.0]/ks[90.0], ks[180.0]/ks[90.0])))

    # Data 4: Arrhenius-overprediction quantified at 150C
    #   Fit Ea on 5-90C isotherm k values, extrapolate to 150C, compare.
    import numpy as _np
    lowT = [(t + 273.15, ks[t]) for t in (5.0, 30.0, 60.0, 90.0)]
    x = _np.array([1.0 / tk for tk, _ in lowT])
    y = _np.array([math.log(k) for _, k in lowT])
    slope, intercept = _np.polyfit(x, y, 1)
    k150_arrh = math.exp(intercept + slope / 423.15)
    over = k150_arrh / ks[150.0]
    ea_kj = -slope * 8.314 / 1000.0
    checks.append(("Naive Arrhenius (5-90C) OVERPREDICTS k(150C)",
                   over > 1.0, f"Ea={ea_kj:.1f} kJ/mol, overprediction x{over:.1f}"))

    width = max(len(c[0]) for c in checks)
    print("P2 module 3 self-check — silica_kinetics.py")
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

"""
silica_saturation.py — E1 / ipis-thesis-geothermal-silica
Phase P2 (base process model), module 1 of 3.

Silica saturation-index (SSI) core for the surface brine / reinjection line
of a Bacman/Leyte-type liquid-dominated field archetype.

DESIGN RULES (from SESSION_BRIEF_E1.md — do not relax):
  1. Every numerical constant carries a provenance tag: (tier, source, status).
  2. STATUS 'PROVISIONAL' constants are usable for development but the module
     REFUSES to run in strict mode until they are transcribed from the primary
     source. This is the code-level analogue of validate_target().
  3. No T3/T4 datum may ever enter this module as a parameter. T3 numbers
     (e.g., the 400 kg/s @ 150 °C Bacman figure) are SCENARIO INPUTS handled
     in /notebooks, never constants here.

Verification targets for this module (P2 gate):
  - Amorphous-silica solubility at 25 °C  ≈ 100–130 mg/kg   (literature range)
  - Amorphous-silica solubility at 100 °C ≈ 340–390 mg/kg
  - Monotonic increase of solubility with T over 0–250 °C
  Run `python silica_saturation.py` to execute the self-check.

Dependencies: numpy only (CoolProp/PHREEQC enter in module 2, speciation).
"""

from dataclasses import dataclass
from typing import Callable
import math

# ---------------------------------------------------------------------------
# Provenance machinery (mirrors src/evidence.py conventions)
# ---------------------------------------------------------------------------

T1, T2, T3, T4 = "T1", "T2", "T3", "T4"
VERIFIED, PROVISIONAL = "VERIFIED", "PROVISIONAL"


@dataclass(frozen=True)
class Datum:
    """A literature-sourced constant or correlation with provenance."""
    name: str
    tier: str
    status: str
    source: str

    def assert_usable(self, strict: bool = False) -> None:
        if self.tier in (T3, T4):
            raise ValueError(
                f"[evidence] {self.name}: tier {self.tier} may not be used as "
                f"a model parameter (source: {self.source})."
            )
        if strict and self.status != VERIFIED:
            raise ValueError(
                f"[evidence] {self.name}: status {self.status}. Transcribe and "
                f"verify against the primary source before strict-mode use "
                f"(source: {self.source})."
            )


# ---------------------------------------------------------------------------
# Amorphous-silica solubility correlations
# ---------------------------------------------------------------------------

FOURNIER_ROWE_1977 = Datum(
    name="Amorphous SiO2 solubility, log10 C [mg/kg] = -731/T[K] + 4.52",
    tier=T1,
    status=PROVISIONAL,  # coefficients from secondary reproductions —
                         # transcribe from Fournier & Rowe (1977),
                         # Am. Mineral. 62:1052-1056, before P2 gate.
    source="fournier1977solubility (references.bib)",
)

GUNNARSSON_ARNORSSON_2000 = Datum(
    name="Amorphous SiO2 solubility: log K = k1 + k2/T + k3*T^2 + k4*log10(T), "
         "k1=-8.476, k2=-485.24, k3=-2.268e-6, k4=3.068; K = m(H4SiO4) mol/kgw; "
         "valid 0-350 degC (1 bar <100 degC, Psat above)",
    tier=T1,
    status=VERIFIED,  # transcribed from the primary PDF (literature/
                      # gunnarsson2000.pdf) Eqn. 4 + Table 2 on 2026-07-14;
                      # paper's own anchor reproduced: logK(25C) = -2.713
                      # (116 ppm) — see self-check.
    source="gunnarsson2000amorphous (references.bib), "
           "GCA 64(13):2295-2307, doi:10.1016/S0016-7037(99)00426-3",
)

_MW_SIO2_G_PER_MOL = 60.084  # standard atomic weights; SiO2 molar mass


def solubility_amorphous_silica_fr77(T_K: float, strict: bool = False) -> float:
    """
    Amorphous-silica solubility in pure water [mg SiO2 / kg H2O].

    Correlation: log10(C) = -731 / T + 4.52  (Fournier & Rowe, 1977 form).
    Valid range asserted: 273-523 K (0-250 degC); extrapolation refused.

    Parameters
    ----------
    T_K : float
        Temperature in kelvin.
    strict : bool
        If True, refuse to run until the correlation constants are
        primary-source verified (P2 gate mode).
    """
    FOURNIER_ROWE_1977.assert_usable(strict=strict)
    if not (273.15 <= T_K <= 523.15):
        raise ValueError(
            f"T = {T_K:.2f} K outside asserted validity window 273-523 K. "
            "Do not extrapolate the solubility correlation."
        )
    return 10.0 ** (-731.0 / T_K + 4.52)


def solubility_amorphous_silica_ga00(T_K: float, strict: bool = False) -> float:
    """
    Amorphous-silica solubility in pure water [mg SiO2 / kg H2O],
    Gunnarsson & Arnorsson (2000), Eqn. 4 + Table 2:

        log10 K = -8.476 - 485.24/T - 2.268e-6 * T**2 + 3.068 * log10(T)

    with K = molality of H4SiO4(aq) [mol/kg H2O], T in kelvin.
    Validity: 0-350 degC (1 bar below 100 degC, Psat above).
    Conversion: mg/kg = 10**logK * MW_SiO2 * 1000.

    This is the PRIMARY solubility correlation of E1 (transcribed and
    anchor-verified from the source PDF); FR77 is retained as an
    independent cross-check.
    """
    GUNNARSSON_ARNORSSON_2000.assert_usable(strict=strict)
    if not (273.15 <= T_K <= 623.15):
        raise ValueError(
            f"T = {T_K:.2f} K outside GA00 validity window 273-623 K (0-350 degC)."
        )
    log_k = (-8.476
             - 485.24 / T_K
             - 2.268e-6 * T_K ** 2
             + 3.068 * math.log10(T_K))
    return (10.0 ** log_k) * _MW_SIO2_G_PER_MOL * 1000.0


# ---------------------------------------------------------------------------
# Flash concentration and saturation index
# ---------------------------------------------------------------------------

def silica_after_flash(c_reservoir_mgkg: float, steam_fraction: float) -> float:
    """
    Dissolved-silica concentration in separated brine after steam flash.

    Pure mass balance (silica is non-volatile): C_brine = C_res / (1 - x).
    No literature constant involved — no provenance tag required.

    Parameters
    ----------
    c_reservoir_mgkg : float
        Reservoir-fluid SiO2 concentration [mg/kg].
    steam_fraction : float
        Mass fraction flashed to steam, 0 <= x < 1.
    """
    if not (0.0 <= steam_fraction < 1.0):
        raise ValueError("steam_fraction must satisfy 0 <= x < 1.")
    if c_reservoir_mgkg < 0:
        raise ValueError("Concentration must be non-negative.")
    return c_reservoir_mgkg / (1.0 - steam_fraction)


def saturation_index(
    c_sio2_mgkg: float,
    T_K: float,
    solubility_fn: Callable[..., float] = solubility_amorphous_silica_ga00,
    strict: bool = False,
) -> float:
    """
    Silica saturation index SSI = C / C_eq(T)  [-].

    SSI > 1 -> supersaturated: polymerization/deposition thermodynamically
    possible; the RATE comes from the kinetics module (module 3), never
    from SSI alone.

    NOTE (scope): pure-water solubility basis. Salinity and pH speciation
    corrections enter in module 2 (PHREEQC layer); until then, SSI here is
    an UPPER-BOUND-style screening quantity for PH dilute-to-moderate brines,
    and this caveat must appear in every figure caption that uses it.
    """
    c_eq = solubility_fn(T_K, strict=strict)
    if c_eq <= 0:
        raise ValueError("Equilibrium solubility must be positive.")
    return c_sio2_mgkg / c_eq


# ---------------------------------------------------------------------------
# Self-check (run: python silica_saturation.py)
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1. Solubility magnitude checks against literature ranges
    c25 = solubility_amorphous_silica_fr77(298.15)
    checks.append(("C_eq(25 degC) in 100-130 mg/kg", 100 <= c25 <= 130, f"{c25:.1f}"))

    c100 = solubility_amorphous_silica_fr77(373.15)
    checks.append(("C_eq(100 degC) in 340-390 mg/kg", 340 <= c100 <= 390, f"{c100:.1f}"))

    c150 = solubility_amorphous_silica_fr77(423.15)
    checks.append(("C_eq(150 degC) reported for reference", True, f"{c150:.1f}"))

    # 2. Monotonicity over 0-250 degC
    temps = [273.15 + 5 * i for i in range(51)]
    vals = [solubility_amorphous_silica_fr77(t) for t in temps]
    mono = all(b > a for a, b in zip(vals, vals[1:]))
    checks.append(("C_eq monotonic increasing, 0-250 degC", mono, ""))

    # 3. Flash mass balance: 25% flash raises concentration by 1/0.75
    c_flash = silica_after_flash(750.0, 0.25)
    checks.append(("Flash mass balance 750/(1-0.25) = 1000", abs(c_flash - 1000.0) < 1e-9, f"{c_flash:.1f}"))

    # 4. SSI worked example: 1000 mg/kg brine at 150 degC
    ssi = saturation_index(1000.0, 423.15)
    checks.append(("SSI(1000 mg/kg, 150 degC) > 1 (supersaturated)", ssi > 1.0, f"{ssi:.2f}"))

    # 5. Guardrails fire
    try:
        solubility_amorphous_silica_fr77(600.0)
        checks.append(("Extrapolation guard fires", False, "no exception"))
    except ValueError:
        checks.append(("Extrapolation guard fires", True, ""))

    try:
        solubility_amorphous_silica_fr77(298.15, strict=True)
        checks.append(("Strict mode blocks PROVISIONAL constants", False, "no exception"))
    except ValueError:
        checks.append(("Strict mode blocks PROVISIONAL constants", True, ""))

    # 6. GA00 primary-source anchor: paper states logK(25C) = -2.713 (116 ppm)
    logk25 = math.log10(solubility_amorphous_silica_ga00(298.15)
                        / (_MW_SIO2_G_PER_MOL * 1000.0))
    checks.append(("GA00 reproduces paper anchor logK(25C)=-2.713",
                   abs(logk25 - (-2.713)) < 0.001, f"logK={logk25:.4f}"))
    c25_ga = solubility_amorphous_silica_ga00(298.15)
    checks.append(("GA00 C_eq(25C) ~ 116 mg/kg (paper's own value)",
                   abs(c25_ga - 116.0) < 1.0, f"{c25_ga:.1f}"))

    # 7. GA00 strict mode now UNLOCKED (VERIFIED transcription)
    try:
        c_strict = solubility_amorphous_silica_ga00(423.15, strict=True)
        checks.append(("GA00 strict mode unlocked", True, f"C_eq(150C)={c_strict:.1f}"))
    except ValueError:
        checks.append(("GA00 strict mode unlocked", False, "still blocked"))

    # 8. Independent-correlation agreement: GA00 vs FR77 within 5%
    #    at 25/100/150 degC (both pure-water basis)
    devs = []
    for tk in (298.15, 373.15, 423.15):
        ga = solubility_amorphous_silica_ga00(tk)
        fr = solubility_amorphous_silica_fr77(tk)
        devs.append(abs(ga - fr) / fr)
    checks.append(("GA00 vs FR77 agree within 5% (25/100/150 degC)",
                   max(devs) < 0.05,
                   "devs=" + "/".join(f"{d*100:.1f}%" for d in devs)))

    width = max(len(c[0]) for c in checks)
    print("P2 module 1 self-check — silica_saturation.py")
    print("-" * (width + 18))
    failed = 0
    for name, ok, extra in checks:
        status = "PASS" if ok else "FAIL"
        failed += (not ok)
        print(f"{name:<{width}}  {status}  {extra}")
    print("-" * (width + 18))
    print(f"{len(checks) - failed}/{len(checks)} passed. "
          f"{'GATE BLOCKED — fix before merge.' if failed else 'Primary correlation (GA00) VERIFIED from source; FR77 retained as PROVISIONAL cross-check only.'}")


if __name__ == "__main__":
    _self_check()

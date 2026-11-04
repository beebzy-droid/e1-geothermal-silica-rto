"""
brine_speciation.py — E1 / ipis-thesis-geothermal-silica
Phase P2 (base process model), module 2 of 3.

PHREEQC-based brine speciation and salinity/pH-corrected silica saturation
for the surface brine / reinjection line of a Bacman/Leyte-type
liquid-dominated field archetype.

This module RESOLVES the pure-water caveat of module 1
(silica_saturation.py): PHREEQC accounts for ionic strength, pH-dependent
silica speciation (H4SiO4 / H3SiO4-), and temperature simultaneously.

ARCHETYPE DATA PROVENANCE
    Endmember compositions transcribed verbatim from the primary source:
    Sugiaman, Sunio, Molling & Stimac (2004), "Geochemical response to
    production of the Tiwi geothermal field, Philippines", Geothermics
    33:57-86, Table 1 (PDF in literature/, transcription verified
    2026-07-14). TIER: T1, STATUS: VERIFIED.
    Interpretation caution carried from the table footnote: values are
    reservoir-fluid concentrations; pH was measured on separated brine.
    HCO3 values represent total carbonate at reservoir conditions.

    Endmembers B (Bariis upflow) and C (South Kapipihan upflow) bound the
    neutral-chloride production fluid; A (meteoric recharge) and D (acid
    fluid) bound the mixing envelope. This four-vertex envelope IS the
    brine-chemistry uncertainty set used by the robust RTO
    (docs/G7_uncertainty_commitment.md).

Property-method rationale (per session-brief P2 requirement):
    PHREEQC default database (phreeqc.dat, ion-association Debye-Huckel).
    Justification: Tiwi/Bacman-type brines are dilute-to-moderate
    (I ~ 0.1-0.3 mol/kg; Cl <= ~5000 mg/kg) — well inside the
    ion-association model's validity. Pitzer (pitzer.dat) is only needed
    for hypersaline systems (Salton Sea class); switching databases is a
    one-line change and belongs in the P6 sensitivity set.

Dependencies: phreeqpython (pip install phreeqpython), module 1 in the
same package for the cross-check.
"""

from dataclasses import dataclass, field
from typing import Dict
import math

try:
    import phreeqpython
except ImportError as e:
    raise ImportError(
        "phreeqpython is required for module 2: pip install phreeqpython"
    ) from e

# ---------------------------------------------------------------------------
# Tiwi endmember compositions — Sugiaman et al. (2004), Table 1
# Units: mg/kg (reservoir-fluid basis); pH from separated brine.
# TIER: T1 | STATUS: VERIFIED (transcribed from primary PDF, 2026-07-14)
# ---------------------------------------------------------------------------

TIWI_ENDMEMBERS: Dict[str, Dict[str, float]] = {
    # A = Naglagbong meteoric recharge
    "A_meteoric_recharge": {
        "pH": 7.16, "Cl": 25, "SO4": 38, "Mg": 12, "HCO3": 333,
        "Na": 89, "K": 32, "Ca": 38, "SiO2": 135,
    },
    # B = Bariis upflow  <- PRIMARY ARCHETYPE for the neutral-chloride brine
    "B_bariis_upflow": {
        "pH": 5.60, "Cl": 4850, "SO4": 61, "Mg": 0.06, "HCO3": 5016,
        "Na": 2647, "K": 783, "Ca": 54, "SiO2": 638,
    },
    # C = South Kapipihan upflow
    "C_skapipihan_upflow": {
        "pH": 5.75, "Cl": 4300, "SO4": 59, "Mg": 0.06, "HCO3": 7076,
        "Na": 2441, "K": 582, "Ca": 40, "SiO2": 648,
    },
    # D = acid fluid (envelope vertex; NOT a nominal operating case)
    "D_acid_fluid": {
        "pH": 3.20, "Cl": 3100, "SO4": 550, "Mg": 8.12, "HCO3": 4650,
        "Na": 1672, "K": 310, "Ca": 22, "SiO2": 509,
    },
}

_PHASE_AMORPHOUS_SILICA = "SiO2(a)"  # phreeqc.dat amorphous-silica phase


@dataclass
class SpeciationResult:
    """Output of one PHREEQC speciation call."""
    T_C: float
    pH_input: float
    si_amorphous: float          # log10(IAP/K) for SiO2(a)
    saturation_ratio: float      # 10**SI = C/C_eq analogue
    ionic_strength_molal: float
    composition_mgkg: Dict[str, float] = field(default_factory=dict)


class BrineSpeciation:
    """Thin, provenance-aware wrapper around phreeqpython for E1."""

    def __init__(self) -> None:
        self._pp = phreeqpython.PhreeqPython()

    def speciate(
        self,
        composition_mgkg: Dict[str, float],
        T_C: float,
        pH_override: float | None = None,
        sio2_override_mgkg: float | None = None,
    ) -> SpeciationResult:
        """
        Speciate a brine and return the amorphous-silica saturation state.

        Parameters
        ----------
        composition_mgkg : dict
            Keys: pH, Cl, SO4, Mg, HCO3, Na, K, Ca, SiO2 (mg/kg).
        T_C : float
            Temperature in degC (module scope: 25-250 degC line conditions).
        pH_override : float, optional
            Overrides the composition pH — this is the pH-mod / acid-dosing
            manipulated variable entering from the RTO layer.
        sio2_override_mgkg : float, optional
            Overrides SiO2 — e.g., flash-concentrated value from
            silica_saturation.silica_after_flash().
        """
        if not (25.0 <= T_C <= 250.0):
            raise ValueError(f"T = {T_C} degC outside module scope 25-250 degC.")

        comp = dict(composition_mgkg)
        ph = pH_override if pH_override is not None else comp["pH"]
        sio2 = sio2_override_mgkg if sio2_override_mgkg is not None else comp["SiO2"]

        sol = self._pp.add_solution({
            "units": "mg/kgw",
            "temp": T_C,
            "pH": ph,
            "Na": comp["Na"],
            "K": comp["K"],
            "Ca": comp["Ca"],
            "Mg": comp["Mg"],
            "Cl": comp["Cl"],
            "S(6)": f"{comp['SO4']} as SO4",
            "C(4)": f"{comp['HCO3']} as HCO3",
            "Si": f"{sio2} as SiO2",
        })
        try:
            si = sol.si(_PHASE_AMORPHOUS_SILICA)
            mu = sol.mu()
        finally:
            sol.forget()  # keep the PHREEQC instance clean across many calls

        return SpeciationResult(
            T_C=T_C,
            pH_input=ph,
            si_amorphous=si,
            saturation_ratio=10.0 ** si,
            ionic_strength_molal=mu,
            composition_mgkg={**comp, "pH": ph, "SiO2": sio2},
        )

    def envelope_saturation(self, T_C: float) -> Dict[str, SpeciationResult]:
        """Saturation state of all four Tiwi endmembers at line temperature."""
        return {name: self.speciate(c, T_C) for name, c in TIWI_ENDMEMBERS.items()}


# ---------------------------------------------------------------------------
# Self-check (run: python brine_speciation.py, with module 1 alongside)
# ---------------------------------------------------------------------------

def _self_check() -> None:
    bs = BrineSpeciation()
    checks = []

    # 1. Archetype B at reservoir-ish 250 degC: should be UNDERsaturated
    r250 = bs.speciate(TIWI_ENDMEMBERS["B_bariis_upflow"], 250.0)
    checks.append(("Archetype B undersaturated at 250 degC (SI<0)",
                   r250.si_amorphous < 0, f"SI={r250.si_amorphous:.3f}"))

    # 2. Flash to 150 degC line: concentrate SiO2 by 25% steam flash,
    #    should be SUPERsaturated — the scaling driving force
    sio2_flash = TIWI_ENDMEMBERS["B_bariis_upflow"]["SiO2"] / (1 - 0.25)
    r150 = bs.speciate(TIWI_ENDMEMBERS["B_bariis_upflow"], 150.0,
                       sio2_override_mgkg=sio2_flash)
    checks.append(("Flashed archetype B supersaturated at 150 degC (SI>0)",
                   r150.si_amorphous > 0, f"SI={r150.si_amorphous:.3f}, ratio={r150.saturation_ratio:.2f}"))

    # 3. pH-mod lever moves saturation the right way at fixed T:
    #    acidification must NOT increase the saturation ratio
    r_ph5 = bs.speciate(TIWI_ENDMEMBERS["B_bariis_upflow"], 150.0,
                        pH_override=5.0, sio2_override_mgkg=sio2_flash)
    checks.append(("Acidification does not raise saturation ratio",
                   r_ph5.saturation_ratio <= r150.saturation_ratio * 1.001,
                   f"pH5.0 ratio={r_ph5.saturation_ratio:.2f} vs pH5.6 {r150.saturation_ratio:.2f}"))

    # 4. Cross-validation vs module 1 (pure-water FR77 basis):
    #    at low ionic strength (endmember A) the two engines should agree
    #    within 15% on saturation ratio at 100 degC.
    try:
        from silica_saturation import saturation_index
        ra = bs.speciate(TIWI_ENDMEMBERS["A_meteoric_recharge"], 100.0,
                         sio2_override_mgkg=400.0)
        ssi_fr77 = saturation_index(400.0, 373.15)
        rel = abs(ra.saturation_ratio - ssi_fr77) / ssi_fr77
        checks.append(("PHREEQC vs FR77 cross-check (dilute, 100 degC) <15%",
                       rel < 0.15,
                       f"PHREEQC={ra.saturation_ratio:.2f}, FR77={ssi_fr77:.2f}, dev={rel*100:.1f}%"))
    except ImportError:
        checks.append(("PHREEQC vs FR77 cross-check", False,
                       "module 1 not importable — run from src/"))

    # 5. Envelope spans the uncertainty set: acid vertex differs from nominal
    env = bs.envelope_saturation(150.0)
    spread = max(r.saturation_ratio for r in env.values()) - \
             min(r.saturation_ratio for r in env.values())
    checks.append(("Endmember envelope has non-trivial spread at 150 degC",
                   spread > 0.05, f"spread={spread:.2f}"))

    # 6. Scope guard fires
    try:
        bs.speciate(TIWI_ENDMEMBERS["B_bariis_upflow"], 300.0)
        checks.append(("Temperature scope guard fires", False, "no exception"))
    except ValueError:
        checks.append(("Temperature scope guard fires", True, ""))

    width = max(len(c[0]) for c in checks)
    print("P2 module 2 self-check — brine_speciation.py")
    print("-" * (width + 40))
    failed = 0
    for name, ok, extra in checks:
        failed += (not ok)
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {extra}")
    print("-" * (width + 40))
    print(f"{len(checks) - failed}/{len(checks)} passed.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()

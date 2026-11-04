"""
temperature_lever.py — E1 / ipis-thesis-geothermal-silica
Phase P2 close-out: the reinjection-temperature lever, quantified.

Combines the three P2 modules into the line-rate model the soft sensor
and RTO operate on:

    rate(T_set, C_brine, u_inh) = f_inh(u_inh) * k(T_set) * s(T_set)**4
    s(T_set) = C_brine - Ce_GA00(T_set)

with k(T) regenerated ON EVERY IMPORT from the raw transcription
(src/data/rothbaum1979_tableII.csv) via the strict-mode fit — no cached
parameters, satisfying the repo rule that /src regenerates everything
from raw inputs.

PROVENANCE
    k(T) nodes ..... T1 (Rothbaum & Rohde 1979, checksum-validated fit)
    Ce(T) .......... T1 (Gunnarsson & Arnorsson 2000, primary-transcribed)
    Archetype brine  T1 (Sugiaman et al. 2004, Table 1, endmember B)
    Steam fraction . SCENARIO INPUT (default 0.25) — an operating
                     assumption, not a literature datum; varied in P6.

Figures (written to ../figures/, regenerate with `python temperature_lever.py`):
    fig_arrhenius_overprediction.png — Limitation A as a result
    fig_temperature_lever.png        — rate vs reinjection-T setpoint
Captions with evidence tiers: ../figures/captions.md
"""

from pathlib import Path
import math

import numpy as np

from silica_saturation import solubility_amorphous_silica_ga00
from silica_kinetics import (load_tableII, fit_rate_constants,
                             polymerization_rate, RATE_ORDER)

_FIGDIR = Path(__file__).parent.parent / "figures"

# ---------------------------------------------------------------------------
# k(T): regenerated from raw data at import, log-linear interpolation
# ---------------------------------------------------------------------------

_DS = load_tableII()
_FITS = fit_rate_constants(_DS, strict=True)
_T_NODES = np.array(sorted(_FITS.keys()))                      # 5..180 degC
_LOGK_NODES = np.array([math.log(_FITS[t]["k"]) for t in _T_NODES])


def k_of_T(T_C: float) -> float:
    """
    Fitted 4th-order rate constant k(T) [ (g/t)^-3 min^-1 ], log-linearly
    interpolated between the seven RR79 isotherm fits. Refuses to
    extrapolate outside the experimental range 5-180 degC.
    """
    if not (_T_NODES[0] <= T_C <= _T_NODES[-1]):
        raise ValueError(
            f"T = {T_C:g} degC outside the RR79 kinetic data range "
            f"{_T_NODES[0]:g}-{_T_NODES[-1]:g} degC — no extrapolation."
        )
    return math.exp(float(np.interp(T_C, _T_NODES, _LOGK_NODES)))


def line_rate(c_brine_mgkg: float, T_C: float,
              inhibition_factor: float = 1.0) -> float:
    """Polymerization rate [g SiO2 t^-1 min^-1] at line temperature T_C
    for separated-brine silica C_brine (mg/kg), uninhibited by default."""
    return polymerization_rate(c_brine_mgkg, T_C + 273.15,
                               k_at_T=k_of_T(T_C),
                               inhibition_factor=inhibition_factor)


# Archetype operating point (Tiwi endmember B, scenario flash) -------------

ARCHETYPE_SIO2_RESERVOIR_MGKG = 638.0   # T1: Sugiaman 2004, Table 1, endmember B
DEFAULT_STEAM_FRACTION = 0.25           # SCENARIO INPUT — varied in P6


def archetype_brine_sio2(steam_fraction: float = DEFAULT_STEAM_FRACTION) -> float:
    """Separated-brine SiO2 after flash (mass balance, module 1 logic)."""
    if not (0.0 <= steam_fraction < 1.0):
        raise ValueError("steam_fraction must satisfy 0 <= x < 1.")
    return ARCHETYPE_SIO2_RESERVOIR_MGKG / (1.0 - steam_fraction)


# ---------------------------------------------------------------------------
# Figures — regenerated from raw inputs
# ---------------------------------------------------------------------------

def make_figures(figdir: Path = _FIGDIR) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figdir.mkdir(parents=True, exist_ok=True)
    out = {}

    # ---- Fig 1: Arrhenius overprediction (Limitation A as a result) ----
    T_low = [5.0, 30.0, 60.0, 90.0]
    x_low = np.array([1.0 / (t + 273.15) for t in T_low])
    y_low = np.array([math.log(_FITS[t]["k"]) for t in T_low])
    slope, intercept = np.polyfit(x_low, y_low, 1)
    ea_kj = -slope * 8.314 / 1000.0

    invT = np.array([1.0 / (t + 273.15) for t in _T_NODES])
    logk = _LOGK_NODES
    xs = np.linspace(invT.min() * 0.98, invT.max() * 1.02, 100)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(1000 * xs, intercept + slope * xs, "--", color="tab:red",
            label=f"Arrhenius fit 5–90 °C (Ea = {ea_kj:.1f} kJ/mol)")
    ax.plot(1000 * invT, logk, "o", color="k", ms=7,
            label="Fitted k(T), RR79 Table II (T1)")
    k150_arr = intercept + slope / 423.15
    k150_fit = math.log(_FITS[150.0]["k"])
    over150 = math.exp(k150_arr - k150_fit)
    ax.annotate(f"×{over150:.1f} overprediction\nat 150 °C",
                xy=(1000 / 423.15, k150_fit),
                xytext=(1000 / 423.15 - 0.25, k150_fit + 1.4),
                arrowprops=dict(arrowstyle="->"))
    for t in (5, 90, 150, 180):
        i = list(_T_NODES).index(t)
        ax.annotate(f"{t:g} °C", (1000 * invT[i], logk[i]),
                    textcoords="offset points", xytext=(6, -12), fontsize=8)
    ax.set_xlabel("1000 / T  [K$^{-1}$]")
    ax.set_ylabel("ln k  [k in (g/t)$^{-3}$ min$^{-1}$]")
    ax.set_title("Silica polymerization rate constant vs. temperature:\n"
                 "low-T Arrhenius extrapolation fails above 90 °C")
    ax.legend(fontsize=9)
    fig.tight_layout()
    p1 = figdir / "fig_arrhenius_overprediction.png"
    fig.savefig(p1, dpi=200); plt.close(fig)
    out["arrhenius"] = {"path": str(p1), "Ea_kJ_mol": ea_kj,
                        "overprediction_150C": over150}

    # ---- Fig 2: the reinjection-temperature lever ----
    c_brine = archetype_brine_sio2()
    Ts = np.linspace(60.0, 180.0, 121)
    rates, supersats = [], []
    for t in Ts:
        ce = solubility_amorphous_silica_ga00(t + 273.15)
        supersats.append(max(c_brine - ce, 0.0))
        rates.append(line_rate(c_brine, t))
    rates = np.array(rates); supersats = np.array(supersats)

    fig, ax1 = plt.subplots(figsize=(7, 5))
    ax1.semilogy(Ts, np.maximum(rates, 1e-12), color="tab:blue", lw=2)
    ax1.set_xlabel("Reinjection-line temperature setpoint [°C]")
    ax1.set_ylabel("Polymerization rate R [g t$^{-1}$ min$^{-1}$]",
                   color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax2 = ax1.twinx()
    ax2.plot(Ts, supersats, color="tab:gray", lw=1.5, ls=":")
    ax2.set_ylabel("Supersaturation C − Ce [g/t]", color="tab:gray")
    ax2.tick_params(axis="y", labelcolor="tab:gray")
    marks = {}
    for t in (90.0, 120.0, 150.0):
        r = line_rate(c_brine, t)
        marks[t] = r
        ax1.plot([t], [r], "o", color="tab:blue")
        ax1.annotate(f"{t:g} °C: {r:.3g}", (t, r),
                     textcoords="offset points", xytext=(8, 6), fontsize=8)
    ax1.set_title("Reinjection-temperature lever — Tiwi endmember B,\n"
                  f"flash x = {DEFAULT_STEAM_FRACTION:.2f} "
                  f"(C$_{{brine}}$ = {c_brine:.0f} g/t)")
    fig.tight_layout()
    p2 = figdir / "fig_temperature_lever.png"
    fig.savefig(p2, dpi=200); plt.close(fig)
    out["lever"] = {"path": str(p2), "c_brine_g_t": c_brine,
                    "rate_90C": marks[90.0], "rate_120C": marks[120.0],
                    "rate_150C": marks[150.0],
                    "ratio_90_over_150": marks[90.0] / marks[150.0]}

    # ---- Captions with evidence tiers ----
    cap = figdir / "captions.md"
    cap.write_text(f"""# Figure captions (with evidence tiers)

**fig_arrhenius_overprediction.png.** Fitted 4th-order rate constants k(T)
for amorphous-silica polymerization, 5–180 °C, regenerated from the
checksum-validated transcription of Rothbaum & Rohde (1979) Table II [T1].
Dashed line: Arrhenius fit to the 5–90 °C nodes
(Ea = {ea_kj:.1f} kJ/mol), which overpredicts k at 150 °C by
×{over150:.1f}. Quantifies why low-temperature kinetics must not be
Arrhenius-extrapolated to reinjection-line conditions.

**fig_temperature_lever.png.** Uninhibited polymerization rate along the
brine line vs. temperature setpoint for the archetype brine
(Tiwi endmember B, SiO2 = {ARCHETYPE_SIO2_RESERVOIR_MGKG:.0f} mg/kg
reservoir [T1: Sugiaman et al. 2004]; flash fraction
x = {DEFAULT_STEAM_FRACTION:.2f} [scenario input]; solubility from
Gunnarsson & Arnórsson 2000 [T1]; kinetics as above [T1]). Cooling the
line from 150 °C to 90 °C raises the rate ×{marks[90.0]/marks[150.0]:.0f}
— the quantitative core of the output-vs-scaling trade-off the RTO
optimizes.
""")
    out["captions"] = str(cap)
    return out


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []

    # 1. Interpolator reproduces the fitted nodes exactly
    dev = max(abs(k_of_T(float(t)) - _FITS[float(t)]["k"]) / _FITS[float(t)]["k"]
              for t in _T_NODES)
    checks.append(("k_of_T reproduces all 7 fitted nodes", dev < 1e-12, f"maxdev={dev:.1e}"))

    # 2. Extrapolation guards fire
    ok = 0
    for bad in (2.0, 200.0):
        try:
            k_of_T(bad)
        except ValueError:
            ok += 1
    checks.append(("k(T) extrapolation guards fire (both sides)", ok == 2, ""))

    # 3. The lever, quantified: cooling 150 -> 90 degC raises rate >10x
    c = archetype_brine_sio2()
    r90, r120, r150 = (line_rate(c, t) for t in (90.0, 120.0, 150.0))
    checks.append(("Rate(90C) > Rate(120C) > Rate(150C)",
                   r90 > r120 > r150,
                   f"R90={r90:.3g}, R120={r120:.3g}, R150={r150:.3g} g/t/min"))
    checks.append(("Cooling 150->90C raises rate >10x",
                   r90 / r150 > 10.0, f"ratio={r90/r150:.0f}x"))

    # 4. Inhibition lever composes with the temperature lever
    checks.append(("70% kinetic inhibition scales rate by 0.30",
                   abs(line_rate(c, 120.0, 0.30) / r120 - 0.30) < 1e-12, ""))

    # 5. Figures regenerate from raw inputs
    res = make_figures()
    p1 = Path(res["arrhenius"]["path"]); p2 = Path(res["lever"]["path"])
    checks.append(("Both figures regenerate from raw data",
                   p1.exists() and p2.exists(),
                   f"Ea={res['arrhenius']['Ea_kJ_mol']:.1f} kJ/mol, "
                   f"over150=x{res['arrhenius']['overprediction_150C']:.1f}"))

    width = max(len(c[0]) for c in checks)
    print("P2 close-out self-check — temperature_lever.py")
    print("-" * (width + 55))
    failed = 0
    for name, okk, extra in checks:
        failed += (not okk)
        print(f"{name:<{width}}  {'PASS' if okk else 'FAIL'}  {extra}")
    print("-" * (width + 55))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()

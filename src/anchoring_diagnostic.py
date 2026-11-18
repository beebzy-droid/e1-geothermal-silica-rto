"""
anchoring_diagnostic.py — E1 / ipis-thesis-geothermal-silica
P8b: WHY a nominal-anchored modifier hunts — measured, not asserted.

    cd src && python anchoring_diagnostic.py        (~10 s)

EXPERIMENT
    Hold the operating point FIXED at the open-loop robust optimum and
    run the stress plants (true kinetics exactly six times the model, all
    random mismatch zeroed). The model error a feedback scheme ought to
    see is then a constant factor of six. Each day, form the ratio

        label / model(T*, u*, c)

    with the model evaluated at (a) the DESIGN-CASE composition the
    robust optimizer is solved against (envelope vertex B at the adverse
    flash bound; "nominal anchor" in the arm names) and (b) the MEASURED
    silica grab sample.

WHAT IT SHOWS (the numbers are printed and written to CSV)
    The design-case composition is more concentrated than the brine the
    plant actually sees, so through the fourth-power rate law the
    design-case model over-predicts the realized-brine model by a large
    "envelope margin" factor. That margin is the robust optimizer's
    safety cushion. A modifier anchored at the design case cannot tell
    the cushion from model error:
      * under the x6 stress the two nearly cancel — ratio (a) sits near
        ONE, the modifier sees no error and does nothing while the plant
        rides the constraint;
      * with no kinetic error (benign regime) ratio (a) sits far BELOW
        one, the modifier reads the cushion as conservatism and removes
        it.
    Ratio (b) carries the kinetic error alone (median near six), though
    with a heavy right tail on days when the measured supersaturation is
    small — which is why the additive form, insensitive to that tail,
    outperforms the log-space form at the measured anchor.

Outputs: results/anchoring_diagnostic.csv (one row per plant-day)
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from run_control_experiment import FastRTO, model_rate, DT_MIN
from run_stress_experiment import STRESS_MISMATCH, BIAS_SHIFT
from synthetic_plant import SyntheticPlant, EpisodeConfig, PlantSession

RESULTS = Path(__file__).parent.parent / "results"
PLANTS = list(range(100, 120))
DAYS = 45.0


def run() -> pd.DataFrame:
    fast = FastRTO()
    T_star, u_star, _ = fast.solve(eps=0.0)
    steps_day = int(24 * 60 / DT_MIN)
    grab_every = int(480 / DT_MIN)
    rows = []
    for seed in PLANTS:
        plant = SyntheticPlant(seed, mismatch=STRESS_MISMATCH,
                               logk_bias_shift=BIAS_SHIFT)
        sess = PlantSession(plant, EpisodeConfig(days=DAYS, dt_min=DT_MIN))
        rates, sio2_held = [], None
        for i in range(int(DAYS * steps_day)):
            rec = sess.step(T_star, u_star)
            if i % grab_every == 0:
                sio2_held = sess.measure_sio2(rec["c_brine_true_mgkg"])
            rates.append(rec["rate_true_g_t_min"])
            if (i + 1) % steps_day == 0:
                day = (i + 1) // steps_day
                label = sess.measure_rate_label(
                    float(np.mean(rates[-steps_day:])))
                r_nom = model_rate(T_star, u_star, fast.brines["B"])
                r_meas = model_rate(T_star, u_star, sio2_held)
                rows.append((seed, day, label, r_nom, r_meas,
                             label / r_nom if r_nom > 0 else np.nan,
                             label / r_meas if r_meas > 0 else np.nan))
    return pd.DataFrame(rows, columns=["plant", "day", "label", "r_nominal",
                                       "r_measured", "ratio_nominal",
                                       "ratio_measured"])


def summarize(df: pd.DataFrame) -> dict:
    d = df[df.day >= 2].copy()               # day 1 carries the induction
    d["margin"] = d.r_nominal / d.r_measured
    out = {}
    for k in ("ratio_nominal", "ratio_measured", "margin"):
        x = d[k].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        out[k] = {"q05": float(np.quantile(x, 0.05)),
                  "q50": float(np.quantile(x, 0.50)),
                  "q95": float(np.quantile(x, 0.95))}
    out["share_above_rmax"] = float((d.label > 0.5).mean())
    out["label_median"] = float(d.label.median())
    return out


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    df = run()
    df.round(6).to_csv(RESULTS / "anchoring_diagnostic.csv", index=False)
    s = summarize(df)
    print("Apparent model error at a FIXED operating point; true kinetic "
          "error = x6.0 on every day")
    for k, name in (("ratio_nominal", "label / model at design-case "
                                      "composition"),
                    ("ratio_measured", "label / model at measured silica  "
                                       "  "),
                    ("margin", "envelope margin (design / measured)  ")):
        r = s[k]
        print(f"  {name}: q05/q50/q95 = {r['q05']:.2f} / {r['q50']:.2f} / "
              f"{r['q95']:.2f}")
    print(f"  days with realized rate above r_max at the fixed point: "
          f"{100*s['share_above_rmax']:.0f}%")
    from provenance import stamp
    stamp("anchoring")
    print("Wrote results/anchoring_diagnostic.csv")


if __name__ == "__main__":
    main()

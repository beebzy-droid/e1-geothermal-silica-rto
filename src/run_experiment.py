"""
run_experiment.py — E1 / ipis-thesis-geothermal-silica
P4 full-scale soft-sensor experiment (run on the workstation, ~5-20 min):

    cd src && python run_experiment.py

Produces (all regenerable from raw inputs, per repo rule):
    ../results/table1_ablation.csv      — per-plant ablation, 8 plants x 90 d
    ../results/table1_summary.csv       — manuscript Table 1
    ../results/scarcity_sweep.csv       — rmse vs training-history length
    ../results/transfer_boundary.csv    — zero-shot transfer (secondary,
                                          limitation stated in ledger/§Lim.)
    ../figures/fig_scarcity_sweep.png   — the data-scarcity claim (N1)

Design constants below are the experiment definition — change only with a
ledger changelog entry.
"""

from pathlib import Path
import numpy as np
import pandas as pd

from soft_sensor import (simulate_plant, prepare, train_plant,
                         predict_triple, eval_arms, run_ablation, summarize)

RESULTS = Path(__file__).parent.parent / "results"
FIGURES = Path(__file__).parent.parent / "figures"

import sys

SMOKE = "--smoke" in sys.argv    # reduced scale: verifies the pipeline only

PLANTS = list(range(3 if SMOKE else 8))
DAYS = 20.0 if SMOKE else 90.0
TRAIN_DAYS = 12.0 if SMOKE else 60.0
SCARCITY_GRID = [6.0, 12.0] if SMOKE else [10.0, 20.0, 40.0, 60.0]
TRANSFER_PLANTS = list(range(300, 302 if SMOKE else 306))
TRANSFER_DAYS = 10.0 if SMOKE else 30.0


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    rng_report = {}

    # ---- Table 1: primary per-plant temporal ablation ----
    if SMOKE:
        print("SMOKE MODE — pipeline verification only; numbers are NOT "
              "the manuscript numbers.")
    print(f"[1/3] Table 1 ablation: {len(PLANTS)} plants x {DAYS:.0f} d "
          f"(train {TRAIN_DAYS:.0f} d) ...")
    res = run_ablation(PLANTS, days=DAYS, train_days=TRAIN_DAYS)
    res.to_csv(RESULTS / "table1_ablation.csv", index=False)
    summ = summarize(res)
    summ.to_csv(RESULTS / "table1_summary.csv", index=False)
    print(summ.round(3).to_string(index=False))

    # ---- Scarcity sweep: the N1 claim ----
    print("[2/3] scarcity sweep over training history ...")
    rows = []
    for td in SCARCITY_GRID:
        r = run_ablation(PLANTS, days=DAYS, train_days=td)
        s = summarize(r)
        for _, x in s.iterrows():
            rows.append((td, x["arm"], x["rmse_log1p_mean"],
                         x["rmse_log1p_sd"]))
        print(f"    train_days={td:>4.0f}  " + "  ".join(
            f"{x['arm']}={x['rmse_log1p_mean']:.3f}" for _, x in s.iterrows()))
    sweep = pd.DataFrame(rows, columns=["train_days", "arm",
                                        "rmse_log1p_mean", "rmse_log1p_sd"])
    sweep.to_csv(RESULTS / "scarcity_sweep.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5))
    for arm, c in (("physics", "tab:gray"), ("pure_ml", "tab:orange"),
                   ("hybrid", "tab:blue")):
        g = sweep[sweep.arm == arm]
        ax.errorbar(g.train_days, g.rmse_log1p_mean, yerr=g.rmse_log1p_sd,
                    marker="o", capsize=3, color=c, label=arm)
    ax.set_xlabel("Training history [days] (= number of daily labels)")
    ax.set_ylabel("Test RMSE, log1p rate space")
    ax.set_title("Soft-sensor ablation vs. label scarcity\n"
                 f"({len(PLANTS)} plants, {DAYS:.0f}-day episodes, "
                 "per-plant temporal split; mean ± sd)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_scarcity_sweep.png", dpi=200)
    plt.close(fig)

    # ---- Transfer boundary (secondary, honest limitation) ----
    print("[3/3] zero-shot transfer boundary (secondary result) ...")
    # A per-plant residual applied to UNSEEN plants with the DONOR's lam:
    # mismatch draws are unpredictable ex ante, so this configuration is
    # expected to HARM relative to the physics prior. It is reported to
    # demonstrate why the deployment rule (lam earned from the target
    # plant's own labels; zero labels => lam=0 => pure physics) is the
    # safety interlock of the architecture.
    rows = []
    donor = prepare(simulate_plant(PLANTS[0], days=DAYS))
    donor_sens = train_plant(donor, train_end_min=TRAIN_DAYS * 24 * 60)
    for s in TRANSFER_PLANTS:
        g = prepare(simulate_plant(s, days=TRANSFER_DAYS))
        met = eval_arms(predict_triple(donor_sens, g[g["t_min"] > 24 * 60]))
        for arm, m in met.items():
            rows.append((s, arm, m["rmse_log1p"]))
    tr = pd.DataFrame(rows, columns=["plant", "arm", "rmse_log1p"])
    tr.to_csv(RESULTS / "transfer_boundary.csv", index=False)
    piv = tr.pivot(index="plant", columns="arm", values="rmse_log1p")
    print("    transfer (donor-plant residual on unseen plants), "
          "mean rmse_log1p:")
    print("    " + "  ".join(f"{a}={piv[a].mean():.3f}"
                             for a in ("physics", "pure_ml", "hybrid")))
    print("    READING: a TRANSFERRED residual (donor lam kept) actively "
          "harms —")
    print("    which is precisely why the deployment rule matters: lam is "
          "earned")
    print("    from the target plant's own labels; at zero labels lam=0 and "
          "the")
    print("    hybrid IS the physics prior (the 'physics' column above). "
          "The")
    print("    credibility mechanism is the safety interlock, not "
          "decoration.")

    print("\nDone. Commit results/ and figures/ after visual QA.")


if __name__ == "__main__":
    main()

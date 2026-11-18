"""
run_all_checks.py — E1 repo gate.

Runs every module self-check in dependency order; exits nonzero on any
failure. Run before every commit that touches /src or /src/data:

    cd src && python run_all_checks.py
"""

import subprocess
import sys
from pathlib import Path

# Environment guard: the gate must run in the pinned e1 env. A wrong env
# (e.g. conda base) crashes modules with no output — fail loudly instead.
try:
    import phreeqpython  # noqa: F401
    import lightgbm      # noqa: F401
except ImportError as _e:
    sys.exit("[env] Missing dependency (%s). You are probably not in the "
             "'e1' conda environment. Run:  conda activate e1" % _e.name)

MODULES = [
    "silica_saturation.py",   # module 1: solubility / SSI (GA00 primary)
    "brine_speciation.py",    # module 2: PHREEQC speciation, Tiwi envelope
    "silica_kinetics.py",     # module 3: RR79 kinetics, checksum-gated
    "temperature_lever.py",   # P2 close-out: k(T) lever + figures
    "synthetic_plant.py",     # P4 build 1: synthetic-truth rig
    "soft_sensor.py",         # P4 build 2: hybrid sensor + ablations
    "robust_rto.py",          # P4 build 3: vertex-robust economic RTO + MA
    "scott2024_dataset.py",   # P5 build 1: T1 validation dataset parser
    "kinetics_validation.py", # P5 build 2: RR79 core vs Scott 2024 (order-2 finding)
    "sensor_validation_scott.py", # P5 build 3: sensor architecture on real T1 curves
    "sensitivity_study.py",   # P6 build 1: Sobol over the declared uncertainty set
    "economics_bands.py",     # P6 build 2: envelope revaluation of Tables 2/2b
    "weres_deposition.py",    # Weres 1981 T1 transcription: r_max mm/yr closure
    "gp_residual.py",         # P8b: GP comparator for the learned correction
    "feedback_arms_check.py", # P8b: anchoring fix + continuity with July numbers
    "provenance.py",          # P8b: committed results match the current code
]


def main() -> int:
    import re
    here = Path(__file__).parent
    results = []
    for m in MODULES:
        r = subprocess.run([sys.executable, str(here / m)],
                           capture_output=True, text=True)
        counts = re.findall(r"(\d+)/(\d+) passed", r.stdout)
        npass, ntot = (int(counts[-1][0]), int(counts[-1][1])) \
            if counts else (0, 0)
        if r.returncode == 0:
            lines = [ln for ln in r.stdout.strip().splitlines()
                     if re.search(r"\d+/\d+ passed", ln)]
            tail = lines[-1] if lines else "<no check summary>"
        else:
            err = r.stderr.strip().splitlines()
            out = r.stdout.strip().splitlines()
            tail = (err[-1] if err else (out[-1] if out else "<no output>"))
        results.append((m, r.returncode, tail, npass, ntot))

    width = max(len(m) for m, *_ in results)
    print("=" * (width + 60))
    print("E1 GATE — all module self-checks")
    print("=" * (width + 60))
    failed = 0
    for m, rc, tail, _, _ in results:
        status = "PASS" if rc == 0 else "FAIL"
        failed += (rc != 0)
        print(f"{m:<{width}}  {status}  {tail}")
    print("=" * (width + 60))
    n_checks = sum(t for *_, t in results)
    if failed:
        print(f"GATE BLOCKED — {failed} module(s) failing. Do not commit.")
        return 1
    # the manuscript quotes these two counts; write them, do not type them
    status = here.parent / "results" / "gate_status.csv"
    status.write_text("module,passed,total\n" + "".join(
        f"{m},{p_},{t}\n" for m, _, _, p_, t in results))
    print(f"GATE OPEN — {len(results)} modules, {n_checks} checks, all "
          f"green. Figures regenerated in /figures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

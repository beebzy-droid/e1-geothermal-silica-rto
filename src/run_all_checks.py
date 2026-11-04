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
]


def main() -> int:
    here = Path(__file__).parent
    results = []
    for m in MODULES:
        r = subprocess.run([sys.executable, str(here / m)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            tail = (r.stdout.strip().splitlines() or ["<no output>"])[-1]
        else:
            err = r.stderr.strip().splitlines()
            out = r.stdout.strip().splitlines()
            tail = (err[-1] if err else (out[-1] if out else "<no output>"))
        results.append((m, r.returncode, tail))

    width = max(len(m) for m, _, _ in results)
    print("=" * (width + 60))
    print("E1 GATE — all module self-checks")
    print("=" * (width + 60))
    failed = 0
    for m, rc, tail in results:
        status = "PASS" if rc == 0 else "FAIL"
        failed += (rc != 0)
        print(f"{m:<{width}}  {status}  {tail}")
    print("=" * (width + 60))
    if failed:
        print(f"GATE BLOCKED — {failed} module(s) failing. Do not commit.")
        return 1
    print("GATE OPEN — all modules green. Figures regenerated in /figures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

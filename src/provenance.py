"""
provenance.py — E1 / ipis-thesis-geothermal-silica
P8b gate module: are the committed results the ones the CURRENT code
produces?

WHY THIS EXISTS
    Two errors reached a submitted manuscript because nothing tied a
    results file to the code that made it:
      * Table 1 was generated in July 2026 BEFORE the brine-dynamics fix
        (mean-reverting mixture walk) and was never rerun afterwards, so
        its numbers described a plant the repository no longer contained;
      * a --smoke run overwrote full-scale CSVs and a figure in a working
        copy with reduced-scale output of the same file names.
    Both are now impossible to commit against a green gate:
      * every long experiment calls stamp() after writing its outputs,
        recording a digest of the source files it depends on, of the
        result files it reads, and of the files it wrote;
      * this module's self-check recomputes all three and FAILS, naming
        the script to rerun, if any of them no longer matches;
      * smoke runs write to a temporary directory and never stamp.

    Digests are taken over text with line endings normalized, so a
    Windows checkout (CRLF) and a Linux one (LF) agree. No timestamp is
    stored: rerunning an experiment on unchanged code leaves
    results/provenance.json byte-identical, so `git diff results/` is
    empty exactly when a rerun reproduced the committed numbers.
"""

from pathlib import Path
import hashlib
import json

_SRC = Path(__file__).parent
_RES = _SRC.parent / "results"
_MANIFEST = _RES / "provenance.json"

_PLANT = ["synthetic_plant.py", "silica_kinetics.py", "silica_saturation.py",
          "temperature_lever.py", "data/rothbaum1979_tableII.csv"]
_SENSOR = ["soft_sensor.py"]
_RTO = ["robust_rto.py", "gp_residual.py", "run_control_experiment.py"]

RECIPES = {
    "table1": {
        "script": "run_experiment.py",
        "sources": _PLANT + _SENSOR + ["run_experiment.py"],
        "inputs": [],
        "outputs": ["table1_ablation.csv", "table1_summary.csv",
                    "scarcity_sweep.csv", "transfer_boundary.csv"]},
    "table2": {
        "script": "run_control_experiment.py",
        "sources": _PLANT + _SENSOR + _RTO,
        "inputs": [],
        "outputs": ["table2_control.csv", "table2_summary.csv"]},
    "table2b": {
        "script": "run_stress_experiment.py",
        "sources": _PLANT + _SENSOR + _RTO + ["run_stress_experiment.py"],
        "inputs": [],
        "outputs": ["table2b_stress.csv", "table2b_summary.csv"]},
    "frontier": {
        "script": "closed_loop_figure.py",
        "sources": ["closed_loop_figure.py"],
        "inputs": ["table2_control.csv", "table2b_stress.csv"],
        "outputs": ["closed_loop_frontier.csv",
                    "closed_loop_contrasts.csv"]},
    "anchoring": {
        "script": "anchoring_diagnostic.py",
        "sources": _PLANT + ["robust_rto.py", "run_control_experiment.py",
                             "run_stress_experiment.py",
                             "anchoring_diagnostic.py"],
        "inputs": [],
        "outputs": ["anchoring_diagnostic.csv"]},
    "sobol": {
        "script": "sensitivity_study.py --full",
        "sources": ["sensitivity_study.py", "robust_rto.py",
                    "temperature_lever.py", "silica_saturation.py",
                    "silica_kinetics.py", "data/rothbaum1979_tableII.csv"],
        "inputs": [],
        "outputs": ["sensitivity_sobol.csv", "sensitivity_summary.csv"]},
}


def _digest(paths) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda q: q.name):
        if not p.exists():
            h.update(b"<missing:" + p.name.encode() + b">")
            continue
        # line-ending- and EOF-insensitive: CRLF vs LF checkouts and a
        # missing final newline must not change the digest
        text = p.read_bytes().replace(b"\r", b"").rstrip() + b"\n"
        h.update(p.name.encode() + b"\0" + text + b"\0")
    return h.hexdigest()[:16]


def _current(name: str) -> dict:
    r = RECIPES[name]
    return {"recipe": _digest([_SRC / s for s in r["sources"]]
                              + [_RES / i for i in r["inputs"]]),
            "product": _digest([_RES / o for o in r["outputs"]])}


def stamp(name: str) -> None:
    """Call at the END of a full-scale run, after all outputs are written."""
    man = json.loads(_MANIFEST.read_text()) if _MANIFEST.exists() else {}
    man[name] = _current(name)
    _MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")


def check() -> list:
    """Return [(name, ok, message)] for every recipe."""
    man = json.loads(_MANIFEST.read_text()) if _MANIFEST.exists() else {}
    out = []
    for name, r in RECIPES.items():
        cur = _current(name)
        rec = man.get(name)
        missing = [o for o in r["outputs"] if not (_RES / o).exists()]
        if missing:
            out.append((name, False, f"missing {missing[0]} — run "
                                     f"python {r['script']}"))
        elif rec is None:
            out.append((name, False, f"never stamped — run "
                                     f"python {r['script']}"))
        elif rec["recipe"] != cur["recipe"]:
            out.append((name, False, f"code or inputs changed since these "
                                     f"results were made — rerun "
                                     f"python {r['script']}"))
        elif rec["product"] != cur["product"]:
            out.append((name, False, f"result files were modified after "
                                     f"the run — rerun "
                                     f"python {r['script']}"))
        else:
            out.append((name, True, "current"))
    return out


def _self_check() -> None:
    rows = check()
    width = max(len(f"results fresh: {n}") for n, _, _ in rows)
    print("P8b self-check — provenance.py (results vs current code)")
    print("-" * (width + 70))
    failed = 0
    for name, ok, msg in rows:
        failed += (not ok)
        print(f"{'results fresh: ' + name:<{width}}  "
              f"{'PASS' if ok else 'FAIL'}  {msg}")
    print("-" * (width + 70))
    print(f"{len(rows) - failed}/{len(rows)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()

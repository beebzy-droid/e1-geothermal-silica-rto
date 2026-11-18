"""
build_submission.py — E1 manuscript: numbers, checks, LaTeX proof copy and
journal artwork for Geothermics.

    python manuscript/build_submission.py        (needs a TeX install with
                                                  elsarticle + bibtex, and
                                                  poppler's pdftoppm)

What it does, in order:
  1. regenerates manuscript/latex/numbers.tex and the table bodies from
     results/*.csv (make_numbers.py; it stops if results are stale or if
     the prose claims no longer hold);
  2. inlines every \\input into one .tex and builds a LaTeX PROOF copy
     (BibTeX with the Elsevier Harvard style on a cleaned copy of
     literature/references.bib: internal TIER notes stripped, journal
     names abbreviated per the ISSN List of Title Word Abbreviations);
     it fails on any LaTeX error, undefined reference or undefined
     citation. The proof is for reading, not for upload: Geothermics
     receives the Word manuscript built by build_docx.py;
  3. redraws the journal figures (src/paper_figures.py) and exports each
     figure, in order of first appearance, as Figure_N.png rendered from
     its vector PDF at >= 1000 dpi and at least the journal's pixel width
     for its column class (3543 px single column, 7480 px full page);
  4. writes abstract.txt and highlights.txt (plain text, numbers
     expanded) for the submission form, and checks the 250-word and
     85-character limits.

Output folder: submission/geot/ (proof copy in submission/geot/proof/)
"""

from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
LX = ROOT / "manuscript" / "latex"
FIGS = ROOT / "figures"
OUT = ROOT / "submission" / "geot"
PROOF = OUT / "proof"
NAME = "manuscript_GEOT"
FULL_PAGE_PX = 7480          # 190 mm at 1000 dpi
SINGLE_COL_PX = 3543         # 90 mm at 1000 dpi

LTWA = {
    "Journal of Process Control": "J. Process Control",
    "AIChE Journal": "AIChE J.",
    r"Computers \& Chemical Engineering": "Comput. Chem. Eng.",
    "Nature Reviews Physics": "Nat. Rev. Phys.",
    "Geothermics": "Geothermics",
    "Journal of Colloid and Interface Science": "J. Colloid Interface Sci.",
    "Geochimica et Cosmochimica Acta": "Geochim. Cosmochim. Acta",
    "Journal of Open Source Software": "J. Open Source Softw.",
    r"Industrial \& Engineering Chemistry Research": "Ind. Eng. Chem. Res.",
    "Processes": "Processes",
    "Geothermal Energy": "Geotherm. Energy",
    "Scientific Reports": "Sci. Rep.",
    "Energies": "Energies",
    "Geothermal Resources Council Transactions":
        "Geotherm. Resour. Counc. Trans.",
}


def inline_inputs(text: str, base: Path) -> str:
    def repl(m):
        p = base / (m.group(1) + ("" if m.group(1).endswith(".tex")
                                  else ".tex"))
        return inline_inputs(p.read_text(), base)
    return re.sub(r"\\input\{([^}]*)\}", repl, text)


def strip_field(entry: str, field: str) -> str:
    """Remove a brace-delimited BibTeX field (balanced braces)."""
    m = re.search(r"\n\s*" + field + r"\s*=\s*\{", entry)
    if not m:
        return entry
    i, depth = m.end(), 1
    while depth:
        depth += {"{": 1, "}": -1}.get(entry[i], 0)
        i += 1
    if entry[i:i + 1] == ",":
        i += 1
    return entry[:m.start()] + entry[i:]


def clean_bib(src: str, cited: set) -> str:
    out, unknown = [], set()
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+),", src):
        key = m.group(2)
        if key not in cited:
            continue
        i, depth = src.index("{", m.start()) + 1, 1
        while depth:
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        raw = src[m.start():i]
        if re.search(r"to confirm\]|\[first author", raw):
            sys.exit(f"'{key}' is cited but is still a placeholder entry "
                     f"in references.bib: verify it against the source or "
                     f"remove the citation")
        e = strip_field(raw, "note")
        jm = re.search(r"journal\s*=\s*\{(.*?)\},?\s*\n", e)
        if jm:
            j = jm.group(1)
            if j in LTWA:
                e = e.replace("{" + j + "}", "{" + LTWA[j] + "}", 1)
            else:
                unknown.add(j)
        out.append(e)
    if unknown:
        sys.exit("No LTWA abbreviation on file for: " + "; ".join(unknown))
    return "\n\n".join(out) + "\n"


def export_png(pdf: Path, png: Path) -> None:
    """Rasterize a one-page vector figure for upload as line art: at least
    1000 dpi at its own width, and at least the journal's minimum pixel
    width for its column class (single column 3543 px, full page 7480 px).
    White background; the effective dpi is recorded in the file."""
    import math
    from PIL import Image
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True,
                          text=True).stdout
    w_pt = float(re.search(r"Page size:\s+([\d.]+) x", info).group(1))
    w_in = w_pt / 72.0
    min_px = SINGLE_COL_PX if w_in * 25.4 <= 100 else FULL_PAGE_PX
    px = max(min_px, math.ceil(w_in * 1000))
    tmp = png.with_suffix("")
    r = subprocess.run(["pdftoppm", "-png", "-singlefile", "-scale-to-x",
                        str(px), "-scale-to-y", "-1", str(pdf), str(tmp)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"pdftoppm failed on {pdf}: {r.stderr}")
    im = Image.open(tmp.with_suffix(".png")).convert("RGB")
    dpi = round(im.size[0] / w_in)
    im.save(png, dpi=(dpi, dpi), optimize=True)
    if im.size[0] != px or dpi < 1000:
        sys.exit(f"{png.name}: {im.size[0]} px at {dpi} dpi")


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          errors="replace")


def expand_plain(tex: str, numbers: str) -> str:
    defs = dict(re.findall(r"\\@namedef\{([^}]*)\}\{(.*)\}", numbers))
    tex = re.sub(r"\\NUM\{([^}]*)\}", lambda m: defs["num@" + m.group(1)],
                 tex)
    for kind, mac in (("cl", "CL"), ("ct", "CT")):
        tex = re.sub(r"\\" + mac + r"\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}",
                     lambda m: defs[f"{kind}@{m.group(1)}@{m.group(2)}"
                                    f"@{m.group(3)}"], tex)
    tex = re.sub(r"~?\$\^\{\\circ\}\$C", " \u00b0C", tex)
    tex = (tex.replace("$-$", "\u2212").replace(r"\%", "%")
           .replace("--", "\u2013").replace("~", " "))
    return re.sub(r"\s+", " ", tex).strip()


def main() -> None:
    sys.path.insert(0, str(ROOT / "manuscript"))
    import make_numbers
    make_numbers.main()
    # journal figures are redrawn from the same result files every build
    # (needs the Scott 2024 data file for two of them; see paper_figures)
    sys.path.insert(0, str(ROOT / "src"))
    import paper_figures
    paper_figures.main()

    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    for old in list(OUT.glob("Figure_*")) + list(PROOF.glob("Figure_*")):
        old.unlink()

    flat = inline_inputs((LX / "main.tex").read_text(), LX)
    flat = flat.replace(r"\graphicspath{{../../figures/}}",
                        r"\graphicspath{{./}}")
    flat = re.sub(r"\A(%[^\n]*\n)+",
                  "% E1 manuscript — single-file LaTeX proof source "
                  "(Geothermics).\n% GENERATED by manuscript/"
                  "build_submission.py: edit manuscript/latex/, not this "
                  "file.\n", flat)

    # figures in order of first appearance: vector PDF for the proof,
    # Figure_N.png at full-page line-art resolution for the upload
    order = []
    for name in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", flat):
        if name not in order:
            order.append(name)
    for n, name in enumerate(order, 1):
        src = FIGS / (Path(name).stem + ".pdf")
        if not src.exists():
            sys.exit(f"missing vector figure {src} — run the gate and the "
                     f"experiment scripts first")
        shutil.copy(src, PROOF / f"Figure_{n}.pdf")
        export_png(src, OUT / f"Figure_{n}.png")
        flat = flat.replace("{" + name + "}", "{" + f"Figure_{n}" + "}")

    # bibliography via BibTeX, then inlined
    cited = set()
    for grp in re.findall(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]*)\}", flat):
        cited |= {k.strip() for k in grp.replace("%", "").split(",")
                  if k.strip()}
    bib = clean_bib((ROOT / "literature" / "references.bib").read_text(),
                    cited)
    (PROOF / "references.bib").write_text(bib)
    (PROOF / f"{NAME}.tex").write_text(flat)
    for cmd in (["pdflatex", "-interaction=nonstopmode", NAME],
                ["bibtex", NAME]):
        r = run(cmd, PROOF)
        if cmd[0] == "bibtex" and ("error" in r.stdout.lower()
                                   or "I couldn't" in r.stdout):
            sys.exit("BibTeX failed:\n" + r.stdout[-1500:])
    bbl = (PROOF / f"{NAME}.bbl").read_text()
    missing = cited - set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]*)\}", bbl))
    if missing:
        sys.exit(f"cited but not in the reference list: {sorted(missing)}")
    flat = re.sub(r"\\bibliographystyle\{[^}]*\}\s*\\bibliography\{[^}]*\}",
                  lambda m: bbl.strip(), flat)
    (PROOF / f"{NAME}.tex").write_text(flat)

    for _ in range(3):
        r = run(["pdflatex", "-interaction=nonstopmode", NAME], PROOF)
    log = (PROOF / f"{NAME}.log").read_text(errors="replace")
    errors = re.findall(r"^! .*$", log, flags=re.M)
    undefined = re.findall(r"(?:Reference|Citation) `[^']*' .*undefined",
                           log)
    overfull = len(re.findall(r"Overfull \\hbox", log))
    for ext in ("aux", "log", "out", "bbl", "blg", "spl"):
        (PROOF / f"{NAME}.{ext}").unlink(missing_ok=True)
    (PROOF / "references.bib").unlink()
    if errors or undefined:
        sys.exit("LaTeX problems:\n  " + "\n  ".join(errors + undefined))

    abstract = expand_plain((LX / "sections" / "00_abstract.tex").read_text(),
                            (LX / "numbers.tex").read_text())
    nwords = len(abstract.split())
    (OUT / "abstract.txt").write_text(abstract + "\n")
    if nwords > 250:
        sys.exit(f"abstract is {nwords} words; the journal limit is 250")

    # highlights: 3-5 bullets, each at most 85 characters incl. spaces
    numbers = (LX / "numbers.tex").read_text()
    hl = [expand_plain(ln, numbers)
          for ln in (LX / "highlights.tex").read_text().splitlines()
          if ln.strip()]
    too_long = [f"{len(h)}: {h}" for h in hl if len(h) > 85]
    if not 3 <= len(hl) <= 5 or too_long:
        sys.exit("highlights break the journal rule (3-5 bullets, <= 85 "
                 "characters):\n  " + "\n  ".join(too_long))
    (OUT / "highlights.txt").write_text("\n".join(hl) + "\n")

    pages = run(["pdfinfo", f"{NAME}.pdf"], PROOF).stdout
    pages = re.search(r"Pages:\s+(\d+)", pages)
    print(f"built proof {PROOF / (NAME + '.pdf')}: "
          f"{pages.group(1) if pages else '?'} pages, {len(order)} figures, "
          f"{len(cited)} references, abstract {nwords} words, "
          f"{overfull} overfull lines, 0 errors, 0 undefined")


if __name__ == "__main__":
    main()

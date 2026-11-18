"""
build_docx.py — E1 submission files for Geothermics, in Word.

    python manuscript/build_docx.py      (needs pandoc >= 3 and python-docx;
                                          run AFTER build_submission.py)

The Word manuscript is generated from the SAME LaTeX sources and the SAME
numbers.tex as the LaTeX proof, so the two cannot drift apart:
  * number macros are expanded from numbers.tex;
  * section (1, 1.1, 1.1.1), equation, figure and table numbers are
    resolved here (Word has no \\ref), and equations carry their numbers;
  * citations and the reference list are produced by pandoc's citeproc
    with the Elsevier Harvard style from the cleaned bibliography;
  * equations stay editable (Word math), tables stay real tables, figures
    are embedded as 300-dpi PNGs (the upload copies, Figure_N.png, come
    from build_submission.py);
  * a python-docx pass sets A4 / Times New Roman 12 pt / 1.5 line
    spacing, continuous line numbers and page numbers, puts each display
    equation in a borderless three-cell row with its number at the right
    margin, and sizes the tables to the text width.

It also writes, into the same folder:
  supplementary_material.docx   Table S1 (learned corrections)
  highlights.docx               3-5 bullets, each <= 85 characters
  cover_letter.docx             from manuscript/cover_letter.txt
  declaration_of_competing_interest.docx

Output folder: submission/geot/
"""

from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_submission import (ROOT, LX, FIGS, OUT, NAME,  # noqa
                              inline_inputs, clean_bib)

CSL = HERE / "elsevier-harvard.csl"


def expand_macros(tex: str, numbers: str) -> str:
    defs = dict(re.findall(r"\\@namedef\{([^}]*)\}\{(.*)\}", numbers))
    tex = re.sub(r"\\NUM\{([^}]*)\}", lambda m: defs["num@" + m.group(1)],
                 tex)
    for kind, mac in (("cl", "CL"), ("ct", "CT")):
        tex = re.sub(r"\\" + mac + r"\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}",
                     lambda m: defs[f"{kind}@{m.group(1)}@{m.group(2)}"
                                    f"@{m.group(3)}"], tex)
    return tex


def number_everything(body: str, tab_prefix: str = "",
                      labels_out: dict = None):
    labels = {}
    sec = sub = subsub = eq = fig = tab = 0
    in_app, app = False, 0
    out, pos = [], 0
    pat = re.compile(
        r"\\appendix\b|\\(section|subsection|subsubsection)"
        r"\{((?:[^{}]|\{[^{}]*\})*)\}"
        r"(\s*\\label\{([^}]*)\})?|\\begin\{(equation|figure|table)\}")
    for m in pat.finditer(body):
        out.append(body[pos:m.start()])
        pos = m.end()
        if m.group(0).startswith("\\appendix"):
            in_app = True
            continue
        if m.group(1) == "section":
            if in_app:
                app += 1
                num = "Appendix " + chr(64 + app)
                ref = num
            else:
                sec += 1; sub = 0
                num = ref = str(sec)
            if m.group(4):
                labels[m.group(4)] = ref
            out.append(f"\\section{{{num}. {m.group(2)}}}")
        elif m.group(1) == "subsection":
            sub += 1; subsub = 0
            num = f"{sec}.{sub}"
            if m.group(4):
                labels[m.group(4)] = num
            out.append(f"\\subsection{{{num}. {m.group(2)}}}")
        elif m.group(1) == "subsubsection":
            subsub += 1
            num = f"{sec}.{sub}.{subsub}"
            if m.group(4):
                labels[m.group(4)] = num
            out.append(f"\\subsubsection{{{num}. {m.group(2)}}}")
        else:
            env = m.group(5)
            end = body.index(f"\\end{{{env}}}", pos)
            block = body[pos:end]
            lab = re.search(r"\\label\{([^}]*)\}", block)
            if env == "equation":
                eq += 1
                if lab:
                    labels[lab.group(1)] = str(eq)
                block = re.sub(r"\\label\{[^}]*\}", "", block)
                # the number is attached in the python-docx pass (finish)
                out.append("\\begin{equation}" + block.rstrip() + "\n")
            else:
                if env == "figure":
                    fig += 1; n, word = fig, "Fig."
                else:
                    tab += 1; n, word = f"{tab_prefix}{tab}", "Table"
                if lab:
                    labels[lab.group(1)] = str(n)
                block = re.sub(r"\\label\{[^}]*\}", "", block)
                block = block.replace("\\caption{",
                                      f"\\caption{{{word} {n}. ", 1)
                out.append(f"\\begin{{{env}}}" + block)
            pos = end
    out.append(body[pos:])
    body = "".join(out)

    if labels_out is not None:
        labels_out.update(labels)

    def ref(m):
        key = m.group(2)
        if key not in labels:
            sys.exit(f"unresolved cross-reference: {key}")
        v = labels[key]
        return f"({v})" if m.group(1) == "eqref" else v
    return re.sub(r"\\(eqref|ref)\{([^}]*)\}", ref, body), eq


def keep_with_next(p) -> None:
    """Set <w:keepNext/> on a paragraph, in schema order (after pStyle)."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = parse_xml(f"<w:pPr {nsdecls('w')}/>")
        p.insert(0, ppr)
    if ppr.find(qn("w:keepNext")) is not None:
        return
    kn = parse_xml(f"<w:keepNext {nsdecls('w')}/>")
    pst = ppr.find(qn("w:pStyle"))
    if pst is not None:
        pst.addnext(kn)
    else:
        ppr.insert(0, kn)


# A4 with 25.4 mm margins, in twentieths of a point
PAGE_W, PAGE_H, MARGIN = 11906, 16838, 1440
TEXT_W = PAGE_W - 2 * MARGIN
FONT = "Times New Roman"


def finish(path: Path, n_eq: int, line_numbers: bool = True,
           centre: int = 4) -> None:
    """Layout pass on the pandoc output (python-docx)."""
    from copy import deepcopy
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn
    from docx.shared import Pt, RGBColor, Twips

    doc = Document(str(path))
    body = doc.element.body

    # page; continuous line numbers for reviewers; page number in footer
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Twips(PAGE_W), Twips(PAGE_H)
    for side in ("left_margin", "right_margin", "top_margin",
                 "bottom_margin"):
        setattr(sec, side, Twips(MARGIN))
    sp = sec._sectPr
    for old in sp.findall(qn("w:lnNumType")):
        sp.remove(old)
    if line_numbers:
        ln = parse_xml(f"<w:lnNumType {nsdecls('w')} w:countBy='1' "
                       f"w:distance='360' w:restart='continuous'/>")
        # schema order: lnNumType sits before pgNumType/cols/docGrid
        anchor = None
        for tag in ("w:pgNumType", "w:cols", "w:formProt", "w:vAlign",
                    "w:noEndnote", "w:titlePg", "w:textDirection",
                    "w:bidi", "w:rtlGutter", "w:docGrid"):
            anchor = sp.find(qn(tag))
            if anchor is not None:
                break
        if anchor is not None:
            anchor.addprevious(ln)
        else:
            sp.append(ln)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # schema order inside pPr: pStyle ... suppressLineNumbers ... jc
    ppr = fp._p.get_or_add_pPr()
    sln = parse_xml(f"<w:suppressLineNumbers {nsdecls('w')}/>")
    pst = ppr.find(qn("w:pStyle"))
    if pst is not None:
        pst.addnext(sln)
    else:
        ppr.insert(0, sln)
    fp._p.append(parse_xml(f"<w:fldSimple {nsdecls('w')} w:instr='PAGE'>"
                           f"<w:r><w:t>1</w:t></w:r></w:fldSimple>"))

    # type: one serif face, black headings, 1.5 line spacing in running text
    for st in doc.styles:
        if st.type != 1:                       # paragraph styles only
            continue
        st.font.name = FONT
        rpr = st.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(a), FONT)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme",
                  "w:eastAsiaTheme"):
            rfonts.attrib.pop(qn(a), None)
        st.font.color.rgb = RGBColor(0, 0, 0)
        name = st.name
        if name in ("Normal", "Body Text", "First Paragraph", "Abstract",
                    "Bibliography"):
            st.font.size = Pt(12)
            st.paragraph_format.line_spacing = 1.5
        elif name == "Title":
            st.font.size, st.font.bold = Pt(16), True
        elif name == "Heading 1":
            st.font.size, st.font.bold = Pt(13), True
        elif name in ("Heading 2", "Heading 3", "Heading 4"):
            st.font.size, st.font.bold = Pt(12), name == "Heading 2"
            st.font.italic = name != "Heading 2"
        elif name in ("Caption", "Table Caption", "Image Caption"):
            st.font.size = Pt(10)
        elif name == "Compact":             # table cells
            st.font.size = Pt(9.5)

    # data tables: full text width, first column wider
    for tbl in list(body.iter(qn("w:tbl"))):
        cols = tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol"))
        n = len(cols)
        if n == 6:      # closed-loop tables: room for the row labels
            frac = (0.30, 0.16, 0.13, 0.16, 0.125, 0.125)
        else:
            frac = (0.34,) + ((1 - 0.34) / (n - 1),) * (n - 1)
        widths = [int(TEXT_W * f) for f in frac]
        for c, w in zip(cols, widths):
            c.set(qn("w:w"), str(w))
        tw = tbl.find(qn("w:tblPr")).find(qn("w:tblW"))
        tw.set(qn("w:type"), "pct"); tw.set(qn("w:w"), "5000")
        # keep a table (and its caption, which precedes it) on one page:
        # rows may not split, and every row but the last keeps with next
        rows = tbl.findall(qn("w:tr"))
        for k, tr in enumerate(rows):
            trpr = tr.find(qn("w:trPr"))
            if trpr is None:
                trpr = parse_xml(f"<w:trPr {nsdecls('w')}/>")
                tr.insert(0, trpr)
            if trpr.find(qn("w:cantSplit")) is None:
                trpr.insert(0, parse_xml(f"<w:cantSplit {nsdecls('w')}/>"))
            if k < len(rows) - 1:
                for para in tr.iter(qn("w:p")):
                    keep_with_next(para)
        prev = tbl.getprevious()
        if prev is not None and prev.tag == qn("w:p"):
            keep_with_next(prev)
        # booktabs-like rules: top and bottom of the table, and under the
        # row that carries the column names
        tpr = tbl.find(qn("w:tblPr"))
        for old in tpr.findall(qn("w:tblBorders")):
            tpr.remove(old)
        borders = parse_xml(
            f"<w:tblBorders {nsdecls('w')}>"
            "<w:top w:val='single' w:sz='8' w:space='0' w:color='000000'/>"
            "<w:bottom w:val='single' w:sz='8' w:space='0' w:color='000000'/>"
            "</w:tblBorders>")
        after = None
        for tag in ("w:tblW", "w:jc", "w:tblCellSpacing", "w:tblInd"):
            el = tpr.find(qn(tag))
            if el is not None:
                after = el
        if after is not None:
            after.addnext(borders)
        else:
            tpr.insert(0, borders)
        for tr in rows:
            first = "".join(t.text or "" for t in
                            tr.find(qn("w:tc")).iter(qn("w:t"))).strip()
            if first in ("Policy", "Estimator"):
                for tc in tr.findall(qn("w:tc")):
                    tcpr = tc.get_or_add_tcPr()
                    for old in tcpr.findall(qn("w:tcBorders")):
                        tcpr.remove(old)
                    tb = parse_xml(
                        f"<w:tcBorders {nsdecls('w')}><w:bottom w:val='single' "
                        "w:sz='4' w:space='0' w:color='000000'/></w:tcBorders>")
                    # tcBorders follows tcW/gridSpan/vMerge in tcPr
                    anchor = None
                    for tag in ("w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge"):
                        el = tcpr.find(qn(tag))
                        if el is not None:
                            anchor = el
                    if anchor is not None:
                        anchor.addnext(tb)
                    else:
                        tcpr.insert(0, tb)
        for tr in tbl.findall(qn("w:tr")):
            i = 0
            for tc in tr.findall(qn("w:tc")):
                pr = tc.get_or_add_tcPr()
                span = pr.find(qn("w:gridSpan"))
                k = int(span.get(qn("w:val"))) if span is not None else 1
                tcw = pr.find(qn("w:tcW"))
                if tcw is None:
                    tcw = parse_xml(f"<w:tcW {nsdecls('w')}/>")
                    pr.insert(0, tcw)
                tcw.set(qn("w:type"), "dxa")
                tcw.set(qn("w:w"), str(sum(widths[i:i + k])))
                i += k

    # every table's properties in schema order (pandoc writes tblLook
    # before jc; Word is strict about CT_TblPr order)
    TBLPR = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual",
             "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
             "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout",
             "tblCellMar", "tblLook", "tblCaption", "tblDescription"]
    for tpr in body.iter(qn("w:tblPr")):
        kids = list(tpr)
        kids.sort(key=lambda el: TBLPR.index(el.tag.split("}")[1])
                  if el.tag.split("}")[1] in TBLPR else len(TBLPR))
        for el in kids:
            tpr.remove(el)
            tpr.append(el)

    # display equations: [ blank | equation | (n) ] in a borderless row,
    # which keeps display-style math and a right-aligned number in Word,
    # LibreOffice and Google Docs alike
    eqs = [p for p in body.iter(qn("w:p"))
           if p.find(qn("m:oMathPara")) is not None]
    if len(eqs) != n_eq:
        sys.exit(f"equation numbering: {n_eq} equation environments but "
                 f"{len(eqs)} display equations in the Word file")
    side = 760
    grid = (side, TEXT_W - 2 * side, side)
    for k, p in enumerate(eqs, 1):
        cells = []
        for j, w in enumerate(grid):
            jc = ("left", "center", "right")[j]
            cells.append(
                f"<w:tc><w:tcPr><w:tcW w:w='{w}' w:type='dxa'/>"
                f"<w:vAlign w:val='center'/></w:tcPr>"
                f"<w:p><w:pPr><w:spacing w:before='60' w:after='60'/>"
                f"<w:jc w:val='{jc}'/></w:pPr>"
                + (f"<w:r><w:t>({k})</w:t></w:r>" if j == 2 else "")
                + "</w:p></w:tc>")
        tbl = parse_xml(
            f"<w:tbl {nsdecls('w')}><w:tblPr><w:tblW w:w='5000' "
            f"w:type='pct'/><w:tblLayout w:type='fixed'/></w:tblPr>"
            f"<w:tblGrid>"
            + "".join(f"<w:gridCol w:w='{w}'/>" for w in grid)
            + f"</w:tblGrid><w:tr>{''.join(cells)}</w:tr></w:tbl>")
        mid = tbl.findall(".//" + qn("w:tc"))[1].find(qn("w:p"))
        mid.append(deepcopy(p.find(qn("m:oMathPara"))))
        p.addprevious(tbl)
        p.getparent().remove(p)

    if any(len(e) == 0 for e in body.iter(qn("m:e"))):
        sys.exit("Word math with an empty base (a bare $_{..}$ or $^{..}$ in "
                 "the LaTeX source); rewrite it in build_docx.py")

    # centre the title block; line numbers off there and in the references
    for para in doc.paragraphs[:centre]:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.core_properties.author = "Bien Don Busico"
    doc.save(str(path))


TITLE_BLOCK = (
    "\\author{Bien Don Busico\\textsuperscript{a,}*}\n\\date{}\n"
    "\\begin{document}\n\\maketitle\n\n"
    "\\textsuperscript{a}University of the Philippines Diliman, Quezon City "
    "1101, Philippines\n\n"
    "*Corresponding author. E-mail address: bienbusico@gmail.com\n\n")


def word_ready(body: str) -> str:
    """LaTeX that pandoc reads well and Word renders cleanly."""
    body = re.sub(r"\\(cmidrule\([a-z]*\)\{[^}]*\}|addlinespace)", "", body)
    body = re.sub(r"\\setlength\{\\tabcolsep\}\{[^}]*\}"
                  r"|\\renewcommand\{\\arraystretch\}\{[^}]*\}"
                  r"|\\footnotesize|\\small\b", "", body)
    body = re.sub(r"\\begin\{(figure|table)\}\[[^\]]*\]", r"\\begin{\1}",
                  body)
    body = body.replace("AI-assisted\\\\ technologies",
                        "AI-assisted technologies")
    body = body.replace("are available at\\\\\n", "are available at\n")
    body = re.sub(r"\\includegraphics\[([^\]]*)\]\{([^}]*)\}",
                  lambda m: f"\\includegraphics[{m.group(1)}]"
                            f"{{{(FIGS / (m.group(2) + '.png')).as_posix()}}}",
                  body)
    # signed numbers set in math mode come out of Word math with a gap
    # after the sign ("+ 41.7"); write them as text instead
    body = re.sub(r"\$([+-])(\d+\.\d) \\pm (\d+\.\d)\$",
                  lambda m: ("+" if m.group(1) == "+" else "\u2212")
                  + f"{m.group(2)}\u00a0\u00b1\u00a0{m.group(3)}", body)
    body = re.sub(r"\$([+-])(\d+)\\%\$",
                  lambda m: ("+" if m.group(1) == "+" else "\u2212")
                  + f"{m.group(2)}\\%", body)
    # degree signs as text, not as a superscript ring in Word math
    body = re.sub(r"\\,\^\{\\circ\}\$C", "$~\u00b0C", body)
    body = re.sub(r"~?\$\^\{\\circ\}\$C", "~\u00b0C", body)
    # table entries as text, so table cells keep one size and font
    body = re.sub(r"\$(\d+\.\d+) \\pm (\d+\.\d+)\$",
                  "\\1\u00a0\u00b1\u00a0\\2", body)
    body = body.replace("RMSE$_{\\log 1p}$", "RMSE\\textsubscript{log1p}")
    # a bare sub/superscript ("RMSE$_{x}$", "min$^{-1}$") becomes Word math
    # with an empty base, which Word draws as a dotted box
    body = re.sub(r"([A-Za-z]+)\$_\{([^$]*)\}\$",
                  r"$\\mathrm{\1}_{\2}$", body)
    body = re.sub(r"([A-Za-z]+)\$\^\{-(\d)\}\$",
                  "\\1\\\\textsuperscript{\u2212\\2}", body)
    # small symbols as text, so table cells and captions keep one size
    body = re.sub(r"\$\\kappa\s*(?:=|\{=\})\s*([0-9.]+)\$",
                  "\\\\textit{\u03ba}\u00a0=\u00a0\\1", body)
    body = re.sub(r"\$\\kappa\$", "\\\\textit{\u03ba}", body)
    body = re.sub(r"\$\\times\s*(\d+)\$", "\u00d7\\1", body)
    # parentheses inside \text{} are mangled by LibreOffice's math import
    body = re.sub(r"\\text\{\((\w+)\)\}", r"(\\text{\1})", body)
    return body


def run_pandoc(tex: str, dst: Path, cited: set) -> list:
    bib = OUT / "_refs_docx.bib"
    bibtxt = clean_bib((ROOT / "literature" / "references.bib").read_text(),
                       cited) if cited else ""
    bibtxt = bibtxt.replace("{H$_4$SiO$_4^\\circ$}",
                            "{H\\textsubscript{4}SiO\\textsubscript{4}"
                            "\\textsuperscript{\u00b0}}")
    bibtxt = bibtxt.replace("{\\textdegree}", "\u00b0")
    bib.write_text(bibtxt)
    src = OUT / "_docx_source.tex"
    src.write_text(tex)
    cmd = ["pandoc", str(src), "-f", "latex", "-t", "docx"]
    if cited:
        cmd += ["--citeproc", f"--bibliography={bib}", f"--csl={CSL}",
                "-M", "link-citations=true"]
    cmd += ["-o", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    src.unlink(); bib.unlink()
    if r.returncode != 0:
        sys.exit("pandoc failed:\n" + r.stderr[-2000:])
    return [ln for ln in r.stderr.splitlines() if ln.strip()]


def cited_keys(body: str) -> set:
    cited = set()
    for grp in re.findall(r"\\cite[tp]?\{([^}]*)\}", body):
        cited |= {k.strip() for k in grp.split(",") if k.strip()}
    return cited


def build_manuscript(numbers: str) -> dict:
    flat = inline_inputs((LX / "main.tex").read_text(), LX)
    flat = expand_macros(flat, numbers)
    # '%' line joins (e.g. inside \cite); an escaped '\%' is a percent sign
    # and must survive at the end of a line
    flat = re.sub(r"(?<!\\)%\n\s*", "", flat)

    title = re.search(r"\\title\{(.*?)\}\s*\n\s*\n", flat, re.S).group(1)
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                         flat, re.S).group(1).strip()
    keywords = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}",
                         flat, re.S).group(1)
    keywords = "; ".join(k.strip() for k in keywords.split("\\sep"))
    body = flat[flat.index("\\end{frontmatter}") + len("\\end{frontmatter}"):
                flat.index("\\bibliographystyle")]
    labels = {}
    body, n_eq = number_everything(body, labels_out=labels)
    body = word_ready(body)
    abstract = word_ready(abstract)
    cited = cited_keys(body)

    tex = ("\\documentclass{article}\n\\usepackage{amsmath,graphicx,"
           "booktabs}\n"
           f"\\title{{{title}}}\n" + TITLE_BLOCK
           + "\\section*{Abstract}\n" + abstract + "\n\n"
           "\\textbf{Keywords:} " + keywords + "\n\n"
           + body + "\n\\section*{References}\n\\end{document}\n")
    dst = OUT / f"{NAME}.docx"
    warn = run_pandoc(tex, dst, cited)
    finish(dst, n_eq)
    print(f"built {dst} ({len(cited)} references cited, {n_eq} numbered "
          f"equations)"
          + (f"; pandoc warnings:\n  " + "\n  ".join(warn[:12])
             if warn else "; no pandoc warnings"))
    return {"title": title, "labels": labels, "abstract": abstract}


def build_supplementary(numbers: str, meta: dict) -> None:
    # the supplementary caption names article items by number: hold them
    want = {"tab:closedloop": "2", "fig:frontier": "6"}
    got = {k: meta["labels"].get(k) for k in want}
    if got != want:
        sys.exit(f"supplementary.tex cites article numbers {want}, but the "
                 f"article now numbers them {got}: update the caption")
    sup = expand_macros(inline_inputs((LX / "supplementary.tex").read_text(),
                                      LX), numbers)
    sup = sup[sup.index("\\section*"):]
    sup, _ = number_everything(sup, tab_prefix="S")
    sup = word_ready(sup)
    tex = ("\\documentclass{article}\n\\usepackage{amsmath,booktabs}\n"
           f"\\title{{Supplementary material for: {meta['title']}}}\n"
           + TITLE_BLOCK
           + sup.replace("\\section*{Supplementary material}", "")
           + "\n\\end{document}\n")
    dst = OUT / "supplementary_material.docx"
    run_pandoc(tex, dst, set())
    finish(dst, 0, line_numbers=False)
    print(f"built {dst}")


def plain_paragraphs(path: Path, numbers: str) -> list:
    from build_submission import expand_plain
    text = path.read_text()
    paras = [expand_plain(p, numbers) for p in re.split(r"\n\s*\n", text)
             if p.strip() and not p.lstrip().startswith("%")]
    return paras


def simple_docx(dst: Path, heading: str, paras: list,
                bullets_marker: str = "- ") -> None:
    """One-column Times New Roman document from plain paragraphs; a
    paragraph starting with '- ' becomes a bullet."""
    from docx import Document
    from docx.shared import Pt, Twips
    from docx.oxml.ns import qn
    d = Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Twips(PAGE_W), Twips(PAGE_H)
    for side in ("left_margin", "right_margin", "top_margin",
                 "bottom_margin"):
        setattr(sec, side, Twips(MARGIN))
    for name in ("Normal", "List Bullet"):
        st = d.styles[name]
        st.font.name, st.font.size = FONT, Pt(11)
        st.element.get_or_add_rPr().find(qn("w:rFonts")).set(
            qn("w:eastAsia"), FONT)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.08
    if heading:
        r = d.add_paragraph().add_run(heading)
        r.bold, r.font.size = True, Pt(14)
    for para in paras:
        if para.startswith(bullets_marker.strip()):
            d.add_paragraph(para.lstrip("- ").strip(), style="List Bullet")
        else:
            d.add_paragraph(para)
    d.core_properties.author = "Bien Don Busico"
    d.core_properties.title = heading or dst.stem
    d.save(str(dst))


def build_forms(numbers: str, meta: dict) -> None:
    # highlights: same text and checks as build_submission.py
    hl = (OUT / "highlights.txt").read_text().splitlines()
    hl = [h for h in hl if h.strip()]
    if not 3 <= len(hl) <= 5 or max(len(h) for h in hl) > 85:
        sys.exit("highlights.txt breaks the 3-5 bullets / 85-character rule")
    simple_docx(OUT / "highlights.docx", "Highlights",
                ["- " + h for h in hl])

    letter = plain_paragraphs(HERE / "cover_letter.txt", numbers)
    letter = [p.replace("{TITLE}", re.sub(r"\s+", " ", meta["title"]))
              for p in letter]
    simple_docx(OUT / "cover_letter.docx", "", letter)

    simple_docx(OUT / "declaration_of_competing_interest.docx",
                "Declaration of competing interest", [
        "Manuscript title: " + re.sub(r"\s+", " ", meta["title"]),
        "Journal: Geothermics",
        "Author: Bien Don Busico, University of the Philippines Diliman, "
        "Quezon City 1101, Philippines",
        "\u2612  The author declares that he has no known competing "
        "financial interests or personal relationships that could have "
        "appeared to influence the work reported in this paper.",
        "\u2610  The author declares the following financial interests/"
        "personal relationships which may be considered as potential "
        "competing interests: none.",
        "Funding: this research did not receive any specific grant from "
        "funding agencies in the public, commercial, or not-for-profit "
        "sectors.",
        "Bien Don Busico, sole and corresponding author"])
    print(f"built highlights.docx, cover_letter.docx, "
          f"declaration_of_competing_interest.docx in {OUT}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    numbers = (LX / "numbers.tex").read_text()
    meta = build_manuscript(numbers)
    build_supplementary(numbers, meta)
    build_forms(numbers, meta)


if __name__ == "__main__":
    main()

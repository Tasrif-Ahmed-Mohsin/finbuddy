"""Build the submission PDFs from the repository's Markdown (cover, at a glance, contents, figures, page numbers).

Usage: python docs/build/build_pdfs.py . submission [name filter]   (from the repository root; needs Google Chrome)
Rendering: marked (Markdown) inside headless Chrome, printed to PDF with a throwaway profile.
"""
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
REPO = "https://github.com/Tasrif-Ahmed-Mohsin/finbuddy"
ICON = base64.b64encode((ROOT / "mobile/assets/images/icon.png").read_bytes()).decode()

DOCS = [
    {
        "file": "Bluefin_Technical_Documentation.pdf", "short": "Technical Documentation", "toc3": True,
        "title": "Technical Documentation", "subtitle": "System architecture · core algorithms · security design",
        "parts": [("docs/TECHNICAL_DOCUMENTATION.md", None),
                  ("docs/FINTECH_STANDARDS_ISO20022.md", "Appendix B · Banking standards: ISO 20022 and SWIFT gpi")],
    },
    {
        "file": "Bluefin_Security_Self_Assessment.pdf", "short": "Security Self-Assessment", "toc3": False, "flow": True,
        "title": "Security Self-Assessment", "subtitle": "Permission-tier implementation · known-risk list · red-team results",
        "parts": [("docs/SECURITY_SELF_ASSESSMENT.md", None)],
    },
    {
        "file": "Bluefin_Execution_Evidence.pdf", "short": "Execution Evidence", "toc3": False, "flow": True,
        "title": "Execution Evidence", "subtitle": "Sandbox operation logs · scripted tasks · safety fuzzing · on-chain anchor",
        "parts": [("docs/EXECUTION_EVIDENCE.md", None),
                  ("docs/evidence/scenario_summary.md", "Appendix A · The four-month sandbox run, every step"),
                  ("docs/evidence/judge_tasks.md", "Appendix B · Judge mode: the 20 scripted tasks in full"),
                  ("docs/evidence/safety_fuzzing_evidence.md", "Appendix C · Safety-invariant fuzzing in full")],
    },
]

META_PREFIXES = ("**FinTechathon 2026", "Team inki_ponki", "Repository:", "Companions:", "Companion:")


def clean(md: str, appendix: str | None) -> str:
    out, dropped_h1 = [], False
    for i, line in enumerate(md.splitlines()):
        if not dropped_h1 and line.startswith("# "):
            dropped_h1 = True
            if appendix:
                out.append(f"# {appendix}")
            continue
        if i < 10 and line.startswith(META_PREFIXES):
            continue
        out.append(line)
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 16mm 15mm 17mm 15mm;
  @bottom-left { content: "Bluefin · %(short)s · FinTechathon 2026, Topic C"; font: 7.5pt 'Segoe UI', sans-serif; color: #8A93A6; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt 'Segoe UI', sans-serif; color: #8A93A6; } }
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font: 10.1pt/1.56 'Segoe UI', 'Nirmala UI', 'Microsoft YaHei', 'Segoe UI Emoji', sans-serif; color: #1D1D1F; }
a { color: #1565C0; text-decoration: none; }
b, strong { color: #0E1324; }

/* ---------- cover ---------- */
.cover { height: 297mm; position: relative; break-after: page; overflow: hidden;
  background: #0A1022; color: #fff; padding: 28mm 20mm 18mm; display: flex; flex-direction: column; }
.cover:before { content: ""; position: absolute; inset: 0; opacity: .9;
  background-image: linear-gradient(rgba(77,163,255,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(77,163,255,.07) 1px, transparent 1px);
  background-size: 9mm 9mm; }
.cover:after { content: ""; position: absolute; right: -60mm; top: -50mm; width: 190mm; height: 190mm; border-radius: 50%%;
  background: radial-gradient(circle, rgba(31,123,234,.55), rgba(31,123,234,0) 68%%); }
.cover > * { position: relative; z-index: 1; }
.cover img.icon { width: 26mm; height: 26mm; border-radius: 6.5mm; box-shadow: 0 0 40px rgba(77,163,255,.45); }
.cover .brand { font-size: 12pt; letter-spacing: 4px; text-transform: uppercase; color: #9CC8FF; margin-top: 12mm; font-weight: 600; }
.cover h1 { font-size: 34pt; line-height: 1.1; margin: 3mm 0 4mm; font-weight: 800; color: #fff; border: 0; padding: 0; letter-spacing: -0.5px; }
.cover .sub { font-size: 13pt; color: #C9D6F5; }
.cover .loop { display: flex; gap: 3mm; margin-top: 12mm; }
.cover .loop span { padding: 2mm 4mm; border-radius: 99px; font-size: 9.5pt; font-weight: 700; letter-spacing: 1px; border: 1px solid; }
.cover .meta { margin-top: auto; display: grid; grid-template-columns: 32mm 1fr; row-gap: 2.8mm; font-size: 9.8pt; color: #E8EEFF;
  background: rgba(14,19,36,.75); border: 1px solid rgba(77,163,255,.28); border-radius: 4mm; padding: 6mm 7mm; }
.cover .meta b { color: #8E9AC0; font-weight: 600; text-transform: uppercase; font-size: 7.6pt; letter-spacing: 1.2px; padding-top: 1.2mm; }
.cover .meta a { color: #9CC8FF; }
.cover .tag { margin-top: 5mm; font-size: 8.5pt; color: #8E9AC0; }

/* ---------- contents ---------- */
.toc { break-before: page; break-after: page; }
.toc h2 { margin-top: 0; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li { padding: 1.7mm 0; border-bottom: 1px dotted #CBD2DE; font-size: 10.2pt; }
.toc li.l3 { padding-left: 7mm; font-size: 9pt; color: #3A4256; border-bottom: 0; padding-top: .5mm; padding-bottom: .5mm; }
.toc li.app { margin-top: 3mm; font-weight: 600; }

/* ---------- headings ---------- */
h1 { font-size: 19pt; margin: 0 0 5mm; padding-bottom: 2.5mm; border-bottom: 2px solid #1F7BEA; break-before: page; color: #0E1324; }
h2 { font-size: 17pt; margin: 0 0 4mm; color: #0E1324; break-before: page; break-after: avoid; letter-spacing: -0.2px; }
h2:before { content: ""; display: block; width: 24mm; height: 1.3mm; border-radius: 1mm; margin-bottom: 3.5mm;
  background: linear-gradient(90deg, #1F7BEA, #4DA3FF); }
h2.first { break-before: avoid; }
body.flow h2 { break-before: auto; margin-top: 10mm; }
body.flow h2.first, body.flow h2.after-toc { margin-top: 0; }
h3 { font-size: 12.6pt; margin: 6.5mm 0 2.5mm; color: #16244A; break-after: avoid; padding-left: 2.8mm; border-left: 3px solid #1F7BEA; }
h4 { font-size: 10.6pt; margin: 4mm 0 1.5mm; color: #16244A; break-after: avoid; }
p { margin: 1.8mm 0; orphans: 3; widows: 3; }
ul, ol { margin: 1.6mm 0 1.6mm 5mm; padding-left: 3mm; }
li { margin: .8mm 0; }
hr { border: 0; border-top: 1px solid #E3E7EF; margin: 5mm 0; }

/* ---------- blocks ---------- */
.glance { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm; margin: 4mm 0 5mm; break-inside: avoid; }
.glance .stat { border: 1px solid #D6E2F5; border-radius: 3mm; padding: 3.5mm 3.8mm; background: linear-gradient(160deg, #F7FAFF, #EEF4FF); }
.glance .stat b { display: block; font-size: 19pt; line-height: 1.1; color: #1F7BEA; font-weight: 800; margin-bottom: 1.5mm; letter-spacing: -0.3px; }
.glance .stat span { display: block; font-size: 8.6pt; line-height: 1.38; color: #3A4256; }
.key { background: #F2F7FF; border-left: 4px solid #1F7BEA; border-radius: 0 3mm 3mm 0; padding: 2.6mm 4.5mm; margin: 3.5mm 0; break-inside: avoid; }
.key p { margin: 1mm 0; }
.key ul, .key ol { margin-top: .8mm; margin-bottom: .8mm; }
.algo { border: 1px solid #E3E7EF; border-radius: 3mm; padding: 1mm 4.5mm 2.5mm; margin: 2mm 0 3mm; }
.algo > p:first-child { margin-top: 2.5mm; }
blockquote { margin: 3.5mm 0; padding: 2.4mm 4.5mm; background: #FFF8E6; border-left: 4px solid #E0A100; border-radius: 0 3mm 3mm 0; color: #3A2E10; break-inside: avoid; }
blockquote p { margin: 1mm 0; }
figure.fig { margin: 4mm 0 1mm; text-align: center; break-inside: avoid; }
figure.fig img { width: 100%%; height: auto; border: 1px solid #E8ECF3; border-radius: 3mm; }
p.cap { font-size: 8.6pt; color: #5A6378; font-style: italic; text-align: center; margin: 1.2mm 6mm 4mm; break-before: avoid; }
code { font-family: 'Cascadia Mono', Consolas, monospace; font-size: 8.3pt; background: #F1F3F7; padding: 0 1.1mm; border-radius: 3px; overflow-wrap: break-word; }
td code { overflow-wrap: normal; word-break: normal; }
pre { background: #0E1324; color: #E8EEFF; padding: 3mm 4mm; border-radius: 2.5mm; white-space: pre-wrap; word-break: break-word; break-inside: avoid; margin: 2.5mm 0; }
pre code { background: none; color: inherit; padding: 0; font-size: 7.9pt; }
pre.long { background: #F4F6FA; color: #1D1D1F; border: 1px solid #E3E7EF; }

/* ---------- tables ---------- */
table { width: 100%%; border-collapse: separate; border-spacing: 0; margin: 2.5mm 0 4mm; font-size: 8.6pt; line-height: 1.4;
  border: 1px solid #DCE2EC; border-radius: 2.5mm; overflow: hidden; }
table.wide { font-size: 7.7pt; }
thead { display: table-header-group; }
th { background: #16244A; color: #FFFFFF; text-align: left; font-weight: 600; padding: 1.8mm 2.2mm; }
th strong, th b { color: #FFFFFF; }
th code { background: rgba(255,255,255,.16); color: #FFFFFF; }
td { padding: 1.5mm 2.2mm; border-top: 1px solid #E6E9F0; vertical-align: top; }
tr { break-inside: avoid; }
tbody tr:nth-child(even) td { background: #F8FAFD; }
img { max-width: 100%%; }
"""

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Bluefin: %(title)s</title>
<style>%(css)s</style>
<script src="lib/marked.min.js"></script>
</head><body class="%(bodyclass)s">
<section class="cover">
  <img class="icon" src="data:image/png;base64,%(icon)s" alt="">
  <div class="brand">Bluefin</div>
  <h1>%(title)s</h1>
  <div class="sub">%(subtitle)s</div>
  <div class="loop">
    <span style="color:#4DA3FF;border-color:#4DA3FF88">1 · SENSE</span><span style="color:#FFC24D;border-color:#FFC24D88">2 · PLAN</span>
    <span style="color:#3DDC97;border-color:#3DDC9788">3 · ACT</span><span style="color:#C792EA;border-color:#C792EA88">4 · PROVE</span>
  </div>
  <div class="meta">
    <b>Competition</b><span>2026 Shenzhen International FinTech Competition (FinTechathon) · International Track (AI)</span>
    <b>Topic</b><span>C · Cross-border &amp; Student Finance Assistant</span>
    <b>Project</b><span>Bluefin keeps an international student funded all year through the legal bank channel (Bangladesh → China)</span>
    <b>Team</b><span>inki_ponki</span>
    <b>Live demo</b><span><a href="https://20-193-145-135.sslip.io">https://20-193-145-135.sslip.io</a> · Android app at /download/bluefin.apk</span>
    <b>Repository</b><span><a href="%(repo)s">%(repo)s</a></span>
    <b>Version</b><span>19 October 2026</span>
  </div>
  <div class="tag">Sandbox: no real money moves. Exchange rates, the banks' published rate sheets and fees, and the laws cited are real; every number carries its source.</div>
</section>
<main id="doc"></main>
<script>
const PARTS = %(parts)s;
const REPO = %(repo_json)s;
const ROOT = %(root_json)s;
function norm(base, href) {
  const parts = (base + '/' + href).split('/'); const out = [];
  for (const p of parts) { if (p === '..') out.pop(); else if (p && p !== '.') out.push(p); }
  return out.join('/');
}
function resolveLink(base, href) {
  if (/^(https?:|mailto:|#)/.test(href)) return href;
  const [path, hash] = norm(base, href).split('#');
  return REPO + '/blob/main/' + path + (hash ? '#' + hash : '');
}
(async () => {
  const doc = document.getElementById('doc');
  const toc = document.createElement('section'); toc.className = 'toc';
  toc.innerHTML = '<h2 class="first">Contents</h2><ol id="toc"></ol>';
  const tocList = toc.querySelector('ol');
  let n = 0;
  for (const part of PARTS) {
    const sec = document.createElement('section');
    sec.innerHTML = marked.parse(part.md, { gfm: true });
    sec.querySelectorAll('img').forEach((im) => {
      const src = im.getAttribute('src');
      if (!/^(https?:|data:|file:)/.test(src)) im.src = ROOT + '/' + norm(part.base, src);
      const p = im.parentElement;
      if (p && p.tagName === 'P' && p.children.length === 1) { const f = document.createElement('figure'); f.className = 'fig'; f.appendChild(im); p.replaceWith(f); }
    });
    sec.querySelectorAll('a[href]').forEach((a) => a.setAttribute('href', resolveLink(part.base, a.getAttribute('href'))));
    if (part.appendix) {  // an appendix keeps one page break: its title; its own sections become sub-headings
      [...sec.querySelectorAll('h4')].forEach((h) => { const x = document.createElement('h5'); x.innerHTML = h.innerHTML; h.replaceWith(x); });
      [...sec.querySelectorAll('h3')].forEach((h) => { const x = document.createElement('h4'); x.innerHTML = h.innerHTML; h.replaceWith(x); });
      [...sec.querySelectorAll('h2')].forEach((h) => { const x = document.createElement('h3'); x.innerHTML = h.innerHTML; h.replaceWith(x); });
    }
    sec.querySelectorAll('table').forEach((t) => {
      const cols = t.querySelectorAll('thead th').length; if (cols >= 6) t.classList.add('wide');
      for (let c = 0; c < cols; c++) {
        const cells = [...t.querySelectorAll(`tr > :nth-child(${c + 1})`)];
        const longest = Math.max(...cells.map((x) => x.textContent.trim().length));
        if (longest <= (cols <= 3 ? 30 : 22)) cells.forEach((x) => { x.style.whiteSpace = 'nowrap'; });
      }
      t.querySelectorAll('code').forEach((c) => { c.textContent = c.textContent.replace(/([/_,])/g, '$1\\u200b'); });
    });
    sec.querySelectorAll('pre').forEach((pr) => { const n = pr.textContent.split('\\n').length; if (n > 40) pr.style.breakInside = 'auto'; if (n > 25) pr.classList.add('long'); });
    sec.querySelectorAll('table, figure, pre').forEach((t) => { const pv = t.previousElementSibling; if (pv && pv.tagName === 'P') pv.style.breakAfter = 'avoid'; });
    doc.appendChild(sec);
    // contents
    const heads = part.appendix ? sec.querySelectorAll('h1') : sec.querySelectorAll(part.toc3 ? 'h2, h3' : 'h2');
    heads.forEach((h) => {
      if (!part.appendix && /^At a glance/.test(h.textContent)) { h.classList.add('first'); return; }
      h.id = 'h' + (++n);
      const li = document.createElement('li');
      li.className = part.appendix ? 'app' : (h.tagName === 'H3' ? 'l3' : 'l2');
      const a = document.createElement('a'); a.href = '#' + h.id; a.textContent = h.textContent; li.appendChild(a); tocList.appendChild(li);
    });
  }
  // cover → at a glance → contents → the rest
  const glance = [...doc.querySelectorAll('h2')].find((h) => /^At a glance/.test(h.textContent));
  const second = glance ? [...doc.querySelectorAll('h2')].find((h) => h !== glance && h.compareDocumentPosition(glance) & Node.DOCUMENT_POSITION_PRECEDING) : null;
  if (second) second.parentNode.insertBefore(toc, second); else doc.prepend(toc);
  if (second) second.classList.add('after-toc');
  await Promise.all([...document.images].map((im) => im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; })));
})();
</script></body></html>"""


def build(spec: dict) -> Path:
    parts = []
    for i, (rel, appendix) in enumerate(spec["parts"]):
        md = (ROOT / rel).read_bytes().decode("utf-8")
        parts.append({"md": clean(md, appendix), "base": str(Path(rel).parent).replace("\\", "/"), "appendix": bool(appendix),
                      "toc3": spec.get("toc3", False) and i == 0})
    html = PAGE % {"css": CSS % {"short": spec["short"]}, "icon": ICON, "title": spec["title"], "subtitle": spec["subtitle"],
                   "repo": REPO, "repo_json": json.dumps(REPO), "bodyclass": "flow" if spec.get("flow") else "", "root_json": json.dumps(ROOT.as_uri()),
                   "parts": json.dumps(parts, ensure_ascii=False)}
    page = HERE / (spec["file"].replace(".pdf", ".html"))
    page.write_bytes(html.encode("utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / spec["file"]
    with tempfile.TemporaryDirectory(dir=HERE, ignore_cleanup_errors=True) as profile:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                        f"--user-data-dir={profile}", "--allow-file-access-from-files", "--no-pdf-header-footer",
                        "--virtual-time-budget=30000", "--run-all-compositor-stages-before-draw",
                        f"--print-to-pdf={pdf}", page.as_uri()], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pdf


if __name__ == "__main__":
    for spec in DOCS:
        if len(sys.argv) > 3 and sys.argv[3] not in spec["file"]:
            continue
        p = build(spec)
        print(f"{p.name}: {p.stat().st_size // 1024} KB")

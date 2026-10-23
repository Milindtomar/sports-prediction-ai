"""Build research/paper.md (+ paper.docx) from research/paper_src.md so every number comes from the measured outputs.

    python scripts/make_figures.py && python scripts/build_paper.py

Markers in paper_src.md:
    <!--TABLE:name-->          -> contents of research/tables/name.md (written by make_figures.py from metrics.json)
    {{dotted.path|dp}}         -> value from backend/artifacts/metrics.json, rounded to dp decimals
    {{pct:dotted.path|dp}}     -> same, shown as a percentage
The build fails if any marker cannot be resolved, so the paper can never silently contain a stale or invented number.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "research"
M = json.loads((ROOT / "backend" / "artifacts" / "metrics.json").read_text())


def lookup(path: str):
    cur = M
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def value(m: re.Match) -> str:
    kind, path, dp = m.group(1), m.group(2), int(m.group(3) or 3)
    v = lookup(path)
    if isinstance(v, (int,)) and m.group(3) is None:
        return f"{v:,}"
    return f"{v * 100:.{dp}f}%" if kind else f"{v:.{dp}f}"


def main() -> int:
    src = (R / "paper_src.md").read_text()
    src = re.sub(r"<!--TABLE:([a-z_]+)-->", lambda m: (R / "tables" / f"{m.group(1)}.md").read_text(), src)
    try:
        out = re.sub(r"\{\{(pct:)?([A-Za-z0-9_.]+)(?:\|(\d))?\}\}", value, src)
    except (KeyError, IndexError, FileNotFoundError) as e:
        print("UNRESOLVED marker:", e)
        return 1
    left = re.findall(r"\{\{|<!--TABLE", out)
    if left:
        print("unresolved markers remain")
        return 1
    (R / "paper.md").write_text(out)
    print("wrote research/paper.md")
    if shutil.which("pandoc"):
        r = subprocess.run(["pandoc", "paper.md", "-o", "paper.docx", "--resource-path=.", "--toc", "--toc-depth=2"], cwd=R, capture_output=True, text=True)
        print("wrote research/paper.docx" if r.returncode == 0 else f"pandoc failed: {r.stderr[:300]}")
    else:
        print("pandoc not found: paper.docx not produced")
    return 0


if __name__ == "__main__":
    sys.exit(main())

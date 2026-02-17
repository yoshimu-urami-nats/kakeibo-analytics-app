# 旧メモジェネレーター　現在使用無し
# 旧全投入メモ自動生成ツール
# コマンド：python tools/memo_gen.py

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DELIM = "ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー"

# 強制的に除外したいパス（相対パス運用）
FORCE_EXCLUDE = {
    "tools/memo_gen.py",  # このスクリプト自身
}

@dataclass
class Section:
    filename: str
    body: str  # includes "↓\n...."

def run_git(repo: Path, args: List[str]) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout

def parse_memo(text: str) -> Dict[str, Section]:
    out: Dict[str, Section] = {}
    blocks = [b.strip("\n") for b in text.split(DELIM)]
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        lines = b.splitlines()
        filename = lines[0].strip()
        body = "\n".join(lines[1:]).lstrip("\n")
        if filename:
            out[filename] = Section(filename=filename, body=body)
    return out

def format_sections(sections_in_order: List[Section]) -> str:
    chunks: List[str] = []
    for s in sections_in_order:
        chunks.append(f"{s.filename}\n{s.body}".rstrip() + "\n")
        chunks.append(DELIM + "\n")
    return "\n".join(chunks).rstrip() + "\n"

def git_changed_files(repo: Path) -> List[str]:
    """
    Changed files in working tree (modified, staged, untracked).
    Similar to VSCode 'changes'.
    """
    out = run_git(repo, ["status", "--porcelain"])
    files: List[str] = []
    for line in out.splitlines():
        if not line:
            continue
        # format: XY <path>
        path = line[3:]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        files.append(path)

    # unique preserve order
    seen = set()
    uniq: List[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq

def read_file(repo: Path, relpath: str) -> str:
    p = repo / relpath
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(relpath)
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp932", errors="replace")

def find_latest_memo(memo_dir: Path) -> Optional[Path]:
    """
    Find latest memo file in memo_dir.
    Priority:
      1) memo-YYMMDD-HHMM.txt (generated format)
      2) memo*.txt (fallback for memo6.txt etc.)
    Uses mtime as source of truth.
    """
    if not memo_dir.exists():
        return None

    candidates = list(memo_dir.glob("memo-*.txt"))
    if not candidates:
        candidates = list(memo_dir.glob("memo*.txt"))
    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]

def build_prev_order(prev_text: str) -> List[str]:
    order: List[str] = []
    for blk in [b.strip() for b in prev_text.split(DELIM) if b.strip()]:
        fn = blk.splitlines()[0].strip()
        if fn:
            order.append(fn)
    return order

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="repo root (default: .)")
    ap.add_argument("--memo-dir", default="docs/memo", help="memo directory (default: docs/memo)")
    ap.add_argument("--prev", default=None, help="previous memo file path (optional: auto-detect if omitted)")
    ap.add_argument("--out", default=None, help="output file path (optional: auto name in memo-dir)")
    ap.add_argument("--exclude", nargs="*", default=[], help="exclude these changed files (optional)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    memo_dir = (repo / args.memo_dir).resolve()

    # prev auto detect
    if args.prev:
        prev_path = Path(args.prev).resolve()
    else:
        prev_path = find_latest_memo(memo_dir)
        if prev_path is None:
            raise FileNotFoundError(
                f"No previous memo found in: {memo_dir}\n"
                f"Put an initial memo file there (e.g. memo6.txt) and re-run."
            )

    prev_text = prev_path.read_text(encoding="utf-8", errors="replace")
    prev_map = parse_memo(prev_text)
    prev_order = build_prev_order(prev_text)

    changed = git_changed_files(repo)

    # --- 強制除外（スクリプト自身など） ---
    changed = [c for c in changed if c not in FORCE_EXCLUDE]

    # --- 任意除外（引数指定） ---
    if args.exclude:
        ex = set(args.exclude)
        changed = [c for c in changed if c not in ex]

    new_sections: Dict[str, Section] = dict(prev_map)
    newly_added: List[str] = []

    for rel in changed:
        key = rel  # relative path is the memo header

        try:
            content = read_file(repo, rel)
        except FileNotFoundError:
            # deleted: keep previous if exists; otherwise skip
            continue

        body = "↓\n" + content.rstrip() + "\n"
        new_sections[key] = Section(filename=key, body=body)

        if key not in prev_map:
            newly_added.append(key)

    final_order = prev_order[:] + newly_added
    ordered_sections = [new_sections[k] for k in final_order if k in new_sections]

    memo_dir.mkdir(parents=True, exist_ok=True)

    if args.out:
        out_path = Path(args.out).resolve()
    else:
        stamp = datetime.now().strftime("%y%m%d-%H%M")
        out_path = memo_dir / f"memo-{stamp}.txt"

    out_path.write_text(format_sections(ordered_sections), encoding="utf-8")

    print(f"OK: prev={prev_path}")
    print(f"OK: wrote {out_path}")
    print(f"Changed files ({len(changed)}):")
    for c in changed:
        print(" -", c)

if __name__ == "__main__":
    main()

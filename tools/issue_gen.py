# Issueジェネレーター
# コマンド：python tools/issue_gen.py --title "タイトル"
# 生成先：docs/issues/ISSUE_250218-0012_タイトル.md

from __future__ import annotations
import subprocess
import re
from datetime import datetime
from pathlib import Path
import argparse


def run_git(repo: Path, args: list[str]) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return r.stdout.strip()


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]+", "", s)
    return s[:60] if s else "issue"


def generate_issue(repo: Path, title: str):
    template_path = repo / "docs/ISSUE_TEMPLATE.md"
    issues_dir = repo / "docs/issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    if not template_path.exists():
        raise FileNotFoundError("docs/ISSUE_TEMPLATE.md が見つかりません")

    template = template_path.read_text(encoding="utf-8", errors="replace")

    now = datetime.now()
    yyyymmdd = now.strftime("%Y%m%d")
    stamp = now.strftime("%y%m%d-%H%M")

    # --- タイトル置換 ---
    content = template.replace("ISSUE_YYYYMMDD", f"ISSUE_{yyyymmdd}")
    content = content.replace("<短いタイトル>", title)

    # --- diff取得 ---
    diff_stat = run_git(repo, ["diff", "--stat"])
    diff_body = run_git(repo, ["diff"])

    if not diff_stat:
        diff_stat = "(no unstaged diff)"
    if not diff_body:
        diff_body = "(no unstaged diff)"

    content = content.replace(
        "# AUTO: git diff --stat",
        f"# AUTO: git diff --stat\n{diff_stat}"
    )

    content = content.replace(
        "# AUTO: git diff",
        f"# AUTO: git diff\n{diff_body}"
    )

    # --- 変更ファイル候補（最大6） ---
    changed_files = run_git(repo, ["diff", "--name-only"]).splitlines()
    if changed_files:
        insert_block = "\n※自動候補（変更ファイルより）\n"
        for f in changed_files[:6]:
            insert_block += f"- {f}\n"

        marker = "## 7. 関連ファイル（最大3〜6）"
        if marker in content:
            idx = content.find(marker)
            endline = content.find("\n", idx)
            content = content[:endline+1] + insert_block + content[endline+1:]

    # --- 出力 ---
    slug = slugify(title)
    out_path = issues_dir / f"ISSUE_{stamp}_{slug}.md"
    out_path.write_text(content, encoding="utf-8")

    print(f"OK: {out_path} を生成しました")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True, help="ISSUEの短いタイトル")
    parser.add_argument("--repo", default=".", help="リポジトリルート")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    generate_issue(repo, args.title)


if __name__ == "__main__":
    main()

# 使用時はプロジェクト直下へ
# プロジェクトのツリー構造の自動生成

from pathlib import Path

IGNORE = {"venv", "__pycache__", ".git"}

def print_tree(path: Path, prefix=""):
    for p in sorted(path.iterdir()):
        if p.name in IGNORE:
            continue
        print(prefix + "├── " + p.name)
        if p.is_dir():
            print_tree(p, prefix + "│   ")

print_tree(Path("."))

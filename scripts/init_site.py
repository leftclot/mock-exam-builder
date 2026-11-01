"""Create a new mock-exam site from site-template/.

Usage: python init_site.py "<dest dir>" --title "My Study Mock Exams" \
         --tagline "made by me, for personal enrichment only" --owner "Me"
Refuses to overwrite an existing catalog.json.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "site-template"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--title", required=True)
    ap.add_argument("--tagline", required=True)
    ap.add_argument("--owner", required=True, help="name used in \"<owner>'s Personal Notes\"")
    args = ap.parse_args()

    dest = Path(args.dest)
    if (dest / "catalog.json").exists():
        print(f"{dest} already has a catalog.json - not overwriting.")
        return 1
    shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True)
    catalog = {"site": {"title": args.title, "tagline": args.tagline, "owner": args.owner}, "subjects": []}
    (dest / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    env = dest / ".env"
    if not env.exists():
        shutil.copy(dest / ".env.example", env)
    (dest / "exams").mkdir(exist_ok=True)
    (dest / "sources").mkdir(exist_ok=True)
    print(f"site created at {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

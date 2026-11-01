"""Publish validated exam drafts into a site and update its catalog.json.

Local source paths are stripped (only the source label is published).

Usage: python register_exam.py --site "<site dir>" draft-a.json draft-b.json draft-c.json
       [--subject-description "..."]
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate_exam import validate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--subject-description", default=None)
    ap.add_argument("drafts", nargs="+")
    args = ap.parse_args()

    site = Path(args.site)
    catalog_path = site / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    for d in args.drafts:
        errors, _ = validate(Path(d))
        if errors:
            print(f"{d}: failed validation ({len(errors)} errors) - run validate_exam.py first. Nothing published.")
            return 1

    for d in args.drafts:
        exam = json.loads(Path(d).read_text(encoding="utf-8"))
        s, l, v = exam["subject"], exam["lesson"], exam["variant"].lower()
        exam["variant"] = v
        exam["sources"] = [{k: x[k] for k in ("id", "type", "label") if k in x} for x in exam["sources"]]
        exam.setdefault("created", date.today().isoformat())

        out = site / "exams" / s["slug"] / l["slug"] / f"set-{v}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(exam, ensure_ascii=False, indent=2), encoding="utf-8")

        subj = next((x for x in catalog["subjects"] if x["slug"] == s["slug"]), None)
        if subj is None:
            subj = {"slug": s["slug"], "title": s["title"], "description": s.get("description", ""), "lessons": []}
            catalog["subjects"].append(subj)
        if args.subject_description:
            subj["description"] = args.subject_description
        les = next((x for x in subj["lessons"] if x["slug"] == l["slug"]), None)
        if les is None:
            les = {"slug": l["slug"], "title": l["title"], "date": l.get("date", ""), "variants": []}
            subj["lessons"].append(les)
        les["title"] = l["title"]
        les["focus"] = exam.get("focus") or les.get("focus", "")
        les["updated"] = date.today().isoformat()
        les["variants"] = sorted(set(les["variants"]) | {v})
        print(f"published {out.relative_to(site)}")

    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print("catalog.json updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

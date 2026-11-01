"""Validate mock-exam draft JSON files.

Checks the schema (see references/exam-schema.md) and that every citation quote
appears verbatim (whitespace/quote-style/markdown-insensitive) in its source file.

Usage: python validate_exam.py draft-a.json [draft-b.json ...]
Exit code 0 = all good, 1 = errors found.
"""
import json
import re
import sys
from pathlib import Path

SOURCE_TYPES = {"official", "personal", "lecturer"}
SECTION_TYPES = {"mcq", "short", "open"}
_text_cache = {}


def normalize(s: str) -> str:
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    s = re.sub(r"(?m)^\s*>+\s?", "", s)          # markdown blockquote markers
    s = re.sub(r"[*_`]", "", s)                  # emphasis / code markers
    s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)  # [[wikilinks]]
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def read_source(path: str) -> str:
    if path in _text_cache:
        return _text_cache[path]
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError(f"{path}: install pypdf to validate quotes against PDFs (pip install pypdf)")
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
    _text_cache[path] = normalize(text)
    return _text_cache[path]


def quote_found(quote: str, haystack: str) -> bool:
    """Every ellipsis-separated fragment must occur, in order."""
    parts = [normalize(x) for x in re.split(r"\.\.\.|…", quote)]
    parts = [x.strip(" .,;:") for x in parts if x.strip(" .,;:")]
    pos = 0
    for part in parts:
        i = haystack.find(part, pos)
        if i < 0:
            return False
        pos = i + len(part)
    return bool(parts)


def validate(path: Path):
    errors, warnings = [], []
    try:
        exam = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"cannot parse JSON: {e}"], warnings

    for key in ("subject", "lesson"):
        obj = exam.get(key) or {}
        if not obj.get("slug") or not obj.get("title"):
            errors.append(f"{key}.slug and {key}.title are required")
        elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", obj["slug"]):
            errors.append(f"{key}.slug must be kebab-case: {obj['slug']!r}")
    if str(exam.get("variant", "")).lower() not in {"a", "b", "c"}:
        errors.append("variant must be one of a/b/c")

    sources = {}
    for s in exam.get("sources") or []:
        sid = s.get("id")
        if not sid or sid in sources:
            errors.append(f"source id missing or duplicated: {sid!r}")
            continue
        if s.get("type") not in SOURCE_TYPES:
            errors.append(f"source {sid}: type must be one of {sorted(SOURCE_TYPES)}")
        if not s.get("label"):
            errors.append(f"source {sid}: label is required")
        if not s.get("path") or not Path(s["path"]).is_file():
            errors.append(f"source {sid}: path missing or not a file: {s.get('path')!r}")
        sources[sid] = s
    if not sources:
        errors.append("at least one source is required")

    sections = exam.get("sections") or []
    if not sections:
        errors.append("at least one section is required")
    for si, sec in enumerate(sections, 1):
        where = f"section {si}"
        if sec.get("type") not in SECTION_TYPES:
            errors.append(f"{where}: type must be one of {sorted(SECTION_TYPES)}")
        if not sec.get("title"):
            errors.append(f"{where}: title is required")
        qs = sec.get("questions") or []
        if not qs:
            errors.append(f"{where}: no questions")
        for qi, q in enumerate(qs, 1):
            w = f"{where} Q{qi}"
            if not q.get("prompt"):
                errors.append(f"{w}: prompt is required")
            if not q.get("explanation"):
                errors.append(f"{w}: explanation is required")
            if sec.get("type") == "mcq":
                opts = q.get("options") or []
                if len(opts) < 2:
                    errors.append(f"{w}: MCQ needs at least 2 options")
                if not isinstance(q.get("answer"), int) or not 0 <= q["answer"] < len(opts):
                    errors.append(f"{w}: answer must be the 0-based index of the correct option")
                if len(set(opts)) != len(opts):
                    errors.append(f"{w}: duplicate options")
            elif sec.get("type") in ("short", "open"):
                if not q.get("model_answer"):
                    errors.append(f"{w}: model_answer is required")
                if not q.get("key_points"):
                    warnings.append(f"{w}: no key_points")
            c = q.get("citation") or {}
            if not c.get("quote") or c.get("source") not in sources:
                errors.append(f"{w}: citation needs a quote and a valid source id")
                continue
            src = sources[c["source"]]
            if src.get("path") and Path(src["path"]).is_file():
                try:
                    if not quote_found(c["quote"], read_source(src["path"])):
                        errors.append(f"{w}: quote NOT found verbatim in {src['label']}: {c['quote'][:90]!r}")
                except RuntimeError as e:
                    errors.append(f"{w}: {e}")
    return errors, warnings


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    bad = False
    prompts = {}
    for arg in argv:
        path = Path(arg)
        errors, warnings = validate(path)
        print(f"== {path.name}: {'OK' if not errors else f'{len(errors)} error(s)'}")
        for e in errors:
            print(f"  ERROR  {e}")
        for w in warnings:
            print(f"  warn   {w}")
        bad |= bool(errors)
        try:
            for sec in json.loads(path.read_text(encoding="utf-8")).get("sections", []):
                for q in sec.get("questions", []):
                    prompts.setdefault(normalize(q.get("prompt", "")), []).append(path.name)
        except Exception:
            pass
    dupes = {p: f for p, f in prompts.items() if len(set(f)) > 1}
    for p, files in dupes.items():
        print(f"  warn   same question in {sorted(set(files))}: {p[:80]!r}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

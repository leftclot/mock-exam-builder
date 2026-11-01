# Exam draft schema

One JSON file per variant (`set-a`, `set-b`, `set-c`). Drafts live in the site's gitignored
`sources/<subject>/<lesson>/drafts/` folder. `register_exam.py` publishes them to
`exams/<subject>/<lesson>/set-<v>.json` with the local `path` of each source removed.

```jsonc
{
  "subject": { "slug": "contemporary-theology-i", "title": "Contemporary Theology I",
               "description": "FEBC · optional one-liner shown on the home page" },
  "lesson":  { "slug": "lectures-1-4", "title": "Lectures 1–4: Liberalism to Neo-orthodoxy",
               "date": "2026-11-01" },
  "variant": "a",
  "focus": "Barth vs Schleiermacher on revelation",   // "" if none
  "sources": [
    { "id": "off1", "type": "official", "label": "Course Notes ch.2",
      "path": "H:\\...\\Reference\\course-notes\\02-....md" },
    { "id": "per1", "type": "personal", "label": "Personal notes 2026-10-30",
      "path": "H:\\...\\sources\\...\\personal-notes.md" },
    { "id": "lec1", "type": "lecturer", "label": "Lecture 3 transcript",
      "path": "H:\\...\\Outgest\\...\\2026-10-28_lecture-3.md" }
  ],
  "sections": [
    { "title": "Section 1 · Multiple Choice", "type": "mcq",
      "questions": [
        { "id": "a-1-1", "prompt": "…?", "options": ["…", "…", "…", "…"], "answer": 2,
          "explanation": "Why C is right / why the tempting distractor is wrong.",
          "citation": { "source": "off1", "quote": "exact words from the source", "locator": "§2.1" } }
      ] },
    { "title": "Section 2 · Short Answer", "type": "short",
      "questions": [
        { "id": "a-2-1", "prompt": "…?", "model_answer": "1–3 sentences.",
          "key_points": ["point a", "point b"], "explanation": "Common mistake: …",
          "citation": { "source": "lec1", "quote": "…", "locator": "00:14:32" } }
      ] },
    { "title": "Section 3 · Open Ended", "type": "open",
      "questions": [ { "id": "a-3-1", "prompt": "Discuss …", "model_answer": "Paragraph-length outline.",
          "key_points": ["…"], "explanation": "…", "citation": { "source": "per1", "quote": "…" } } ] }
  ]
}
```

## Rules
- `type` of a source: `official` → shown as **Official Notes**; `personal` → **<owner>'s Personal Notes**
  (owner comes from `catalog.json` → `site.owner`); `lecturer` → **Lecturer's Words**.
- `citation.quote` must be **copied verbatim** from the source file: one sentence or a short span,
  ≤ ~40 words. Use `...` to elide a middle part. Whitespace, curly quotes, markdown `*_\``, `>`
  and `[[wikilinks]]` are ignored when matching. Never paraphrase inside `quote`.
- `locator` is optional: section heading, page, or `hh:mm:ss` timestamp for transcripts.
- MCQ `answer` is a 0-based index. Give 4 options, one clearly correct, with plausible distractors
  taken from the same material. Vary the position of the correct answer.
- Every question needs an `explanation`. It's shown to the student when they get the question wrong.
- `short`/`open` need `model_answer`; `key_points` are what the student self-marks against.
- Slugs are kebab-case. Variant ids are `a`, `b`, `c`.

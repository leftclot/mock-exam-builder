---
name: mock-exam-builder
description: >
  Build a self-graded mock exam website page from study material — official notes, personal
  notes, and lecture videos/transcripts — for any subject. Produces 3 exam variants (Set A/B/C)
  mixing MCQ, Short Answer and Open Ended sections; every answer carries a verbatim quote and
  source (Official Notes / <owner>'s Personal Notes / Lecturer's Words) shown when the student
  gets it wrong. Publishes into a static site (one page per subject, growing over time) served
  from this PC via Tailscale Funnel. Trigger on "make a mock exam", "quiz me on <class>",
  "build an exam from my notes", "add <lesson> to the exam site", or /mock-exam-builder.
---

# Mock Exam Builder

Turns notes into 3 mock-exam variants and publishes them to a static site. Two halves:
- **This skill** (generic, public): workflow + scripts + `site-template/` engine.
- **The site** (personal, private repo): `catalog.json` + `exams/` + the engine files.

## Config
Read `.env` in this skill's folder (copy `.env.example` if it's missing and ask the user to fill it):
- `SITE_DIR` — the site folder. If no site exists yet, create one with
  `python scripts/init_site.py "<dir>" --title ... --tagline ... --owner ...`
- `NOTES_ROOTS` — where notes usually live (e.g. Lesson Note Taker `Outgest\`, Bible Knowledge).
- `PUBLIC_URL` — the Funnel URL, for reporting links.

Never ask for, store or echo passwords/tokens. GitHub and Tailscale logins are done by the user
in their own terminal (`! gh auth login`, Tailscale tray app).

## Workflow

### 1. Subject + lesson
Ask which subject / lecture series and which lesson(s) the exam covers. Look in
`<SITE_DIR>\catalog.json` for an existing subject slug and reuse it, so new exams land on
the same subject page. Otherwise make a new kebab-case slug (e.g. `contemporary-theology-i`).
A "lesson" can be one lecture or a range (`lectures-1-4`, `midterm-review`).

### 2. Gather + label sources
Collect every source and give it one of these types:

| type | What | Where to look |
|---|---|---|
| `official` | Official course notes, syllabus, handouts, textbook PDFs | `NOTES_ROOTS` → e.g. `Outgest\<Class>\Reference\`, `Attachments\` |
| `personal` | The user's own notes | **Ask the user**: paste or file path. Save pasted text verbatim to `<SITE_DIR>\sources\<subject>\<lesson>\personal-notes.md` |
| `lecturer` | The lecturer's own words | Lesson notes from `lesson-note-taker` (`type: lesson`, Parts 1–3 are near-verbatim; **don't cite Part 4 "Additional AI Notes" as Lecturer's Words**), raw transcripts, or videos |

Videos: `python scripts/transcribe.py "<file-or-url>" --out "<SITE_DIR>\sources\<subject>\<lesson>"`
(faster-whisper; `--model medium` for better accuracy, `--lang en`). Cite the transcript as
`lecturer` with `hh:mm:ss` locators.

Read every source in full. If a type has no material, say so. Don't invent it.

### 3. Ask the user (always, in one AskUserQuestion round)
- **Formats**: which of MCQ / Short Answer / Open Ended (multi-select).
- **Sections + counts**: how many sections and questions per section. Suggested default: 3 sections,
  10 MCQ, 5 Short Answer and 2 Open Ended.
- **Focus**: anything the questions should concentrate on (a topic, lecture, theme, the lecturer's
  exam hints), or broad coverage. Mention any exam hints found in the lesson notes'
  "About Assessments" section as candidate focuses.

### 4. Write 3 variants
Follow `references/exam-schema.md` exactly. Draft to
`<SITE_DIR>\sources\<subject>\<lesson>\drafts\set-a.json`, `set-b.json` and `set-c.json`.
- Same structure in each set, **different questions**, with little overlap. Together the
  three should cover the material (weighted toward the focus).
- Test understanding, not trivia: who taught what, why it matters, how ideas compare, and how to apply them.
- MCQ distractors must be plausible and come from the same material. Vary where the correct answer sits.
- Each question must be answerable from the sources alone, with one `citation` whose `quote`
  is **copied character-for-character** from its source file (short span, `...` to elide).
- `explanation` says why the right answer is right and names the likely mistake. It's shown on wrong answers.
- Prefer citing `lecturer` and `official` sources. Use `personal` where the user's notes add something.

### 5. Validate
`python scripts/validate_exam.py <drafts>\set-a.json <drafts>\set-b.json <drafts>\set-c.json`
Fix every ERROR by re-copying the quote from the source or choosing a different one. Never
loosen the quote check. Clear duplicate-question warnings across sets. Repeat until all pass.

### 6. Publish
`python scripts/register_exam.py --site "<SITE_DIR>" <the 3 drafts> [--subject-description "..."]`
This writes `exams/<subject>/<lesson>/set-{a,b,c}.json` (with local paths stripped) and updates
`catalog.json`, so the home page and subject page pick it up automatically.
Then in `SITE_DIR`: `git add -A`, check `git status` that nothing under `sources/` or `.env` is
staged, then commit and `git push`.

### 7. Report
Give the subject page and Set A/B/C links (`PUBLIC_URL` if set, else `http://127.0.0.1:<PORT>`).
If the server isn't running: `powershell -ExecutionPolicy Bypass -File "<SITE_DIR>\serve.ps1"`.

## Site behaviour (for reference)
- `index.html` lists subjects. `subject.html?s=` lists lessons and their sets. `exam.html?s=&l=&v=` runs an exam.
- MCQ is auto-marked. For Short Answer and Open Ended, the student sees the model answer and key
  points and marks themselves Correct/Partial/Wrong (1/0.5/0).
- The results page shows a letter grade (A ≥80, B ≥70, C ≥60, D ≥50, else F), a score per
  section, and for each miss: the student's answer, the correct answer, why, and
  *From the notes: "quote" — Source (label, locator)*.
- Attempt history is stored only in the browser's localStorage.

## Hosting (one-time)
1. Install Tailscale and log in (the user does this). In the admin console, enable HTTPS and Funnel.
2. `serve.ps1` starts `serve.py` (an **allowlist** server: only the pages, `catalog.json`, `assets/` and `exams/`; never `.env`, `sources/` or `.git`) on 127.0.0.1:`PORT`, then runs `tailscale funnel --bg PORT`. Never serve the site with plain `python -m http.server`, which would publish personal notes.
3. Create a Scheduled Task to run `serve.ps1` at logon, and turn off PC sleep so the site stays up.

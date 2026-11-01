# mock-exam-builder

A Claude Code skill that turns study material into self-graded mock exams. It reads official notes,
your personal notes and lecture videos, and publishes the exams to a small static website that
grows one subject page at a time.

- 3 variants per lesson (Set A/B/C), with MCQ, Short Answer and Open Ended sections
- MCQ is auto-marked; written answers are self-marked against a model answer and key points
- every wrong answer shows why, plus a verbatim quote and its source
  (Official Notes / Personal Notes / Lecturer's Words)
- `validate_exam.py` rejects any quote that isn't word for word in its source file
- static site: no server code and no database. Serve it with anything; Tailscale Funnel works well

## Setup
```
pip install faster-whisper pypdf          # transcription + PDF quote checks; needs ffmpeg (+ yt-dlp for URLs)
python scripts/init_site.py "C:\path\to\my-site" --title "My Mock Exams" \
       --tagline "made by me, for personal enrichment only" --owner "Me"
copy .env.example .env                     # set SITE_DIR to the folder above
```
Put this folder in `~/.claude/skills/`, then ask Claude to "make a mock exam from my <class> notes".

## Layout
- `SKILL.md`: the workflow Claude follows
- `references/exam-schema.md`: exam JSON format and citation rules
- `scripts/`: `transcribe.py`, `validate_exam.py`, `register_exam.py`, `init_site.py`
- `site-template/`: the site engine (`index.html`, `subject.html`, `exam.html`, `assets/`, plus `serve.py`, an allowlist server, and `serve.ps1`)

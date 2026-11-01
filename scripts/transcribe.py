"""Transcribe a lecture video/audio (local file or URL) to timestamped markdown.

Usage: python transcribe.py <file-or-url> --out "<dir>" [--model small] [--lang en] [--device auto]
Writes <out>/<name>.transcript.md. Needs: faster-whisper, ffmpeg, and yt-dlp for URLs.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="small", help="tiny/base/small/medium/large-v3")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--device", default="auto", help="auto/cpu/cuda")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    media = Path(args.source)
    if args.source.startswith(("http://", "https://")):
        tmpl = str(out / "%(title).80B.%(ext)s")
        subprocess.run(["yt-dlp", "-x", "--audio-format", "m4a", "-o", tmpl, args.source], check=True)
        media = max(out.glob("*.m4a"), key=lambda p: p.stat().st_mtime)
    if not media.is_file():
        print(f"not found: {media}")
        return 1

    from faster_whisper import WhisperModel
    compute = "int8" if args.device == "cpu" else "default"
    model = WhisperModel(args.model, device=args.device, compute_type=compute)
    segments, info = model.transcribe(str(media), language=args.lang, vad_filter=True)

    lines = ["---", f'title: "Transcript: {media.stem}"', f'source: "{args.source}"',
             f'language: "{info.language}"', f'model: "faster-whisper {args.model}"', "---", ""]
    for seg in segments:
        lines.append(f"[{ts(seg.start)}] {seg.text.strip()}")
        print(f"[{ts(seg.start)}] {seg.text.strip()}", flush=True)
    dest = out / f"{media.stem}.transcript.md"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

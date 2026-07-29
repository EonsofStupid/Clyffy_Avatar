#!/usr/bin/env python3
"""Local voice.tts adapter for Clyffy (OuteTTS via llama-tts).

Slot name: voice.tts  — do not hardcode a different product stack.

    python3 tools/voice_tts.py --text "We are doing this today." \\
        --out work/voice/samples/line_00.wav

    python3 tools/voice_tts.py --from-pack

Env overrides:
  CLYFFY_TTS_BIN   path to llama-tts
  CLYFFY_TTS_LLM   OuteTTS gguf
  CLYFFY_TTS_VOC   WavTokenizer gguf
  CLYFFY_TTS_SPEAKER  speaker json (optional)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIN = Path(
    os.environ.get(
        "CLYFFY_TTS_BIN",
        "/home/hades/llama-cpp-roce/build/bin/llama-tts",
    )
)
DEFAULT_LLM = Path(
    os.environ.get(
        "CLYFFY_TTS_LLM",
        ROOT / "work/voice/models/OuteTTS-0.2-500M-Q5_K_M.gguf",
    )
)
DEFAULT_VOC = Path(
    os.environ.get(
        "CLYFFY_TTS_VOC",
        ROOT / "work/voice/models/WavTokenizer-Large-75-F16.gguf",
    )
)
DEFAULT_SPEAKER = Path(
    os.environ.get(
        "CLYFFY_TTS_SPEAKER",
        ROOT / "work/voice/speakers/en_male_1.json",
    )
)

# fallback if pack parse fails
DEFAULT_LINES = [
    "We are doing this today.",
    "Alright — here is the plan.",
    "That is the root cause. We fix it at the source.",
    "Hold on. I am thinking.",
    "Done. Check the gate.",
]


def slugify(text: str, idx: int) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    s = (s[:40] or "line").rstrip("_")
    return f"{idx:02d}_{s}"


def parse_pack_sample_lines(pack: Path) -> list[str]:
    if not pack.is_file():
        return list(DEFAULT_LINES)
    text = pack.read_text()
    # simple extract of sample_lines = [ ... ]
    m = re.search(r"sample_lines\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        return list(DEFAULT_LINES)
    body = m.group(1)
    lines = re.findall(r'"([^"]+)"', body)
    return lines or list(DEFAULT_LINES)


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


def synthesize(
    text: str,
    out: Path,
    *,
    bin_path: Path,
    llm: Path,
    voc: Path,
    speaker: Path | None,
    n_threads: int = 8,
) -> dict:
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not bin_path.is_file():
        raise SystemExit(f"llama-tts not found: {bin_path}")
    if not llm.is_file():
        raise SystemExit(f"OuteTTS model missing: {llm}")
    if not voc.is_file():
        raise SystemExit(f"WavTokenizer model missing: {voc}")

    # llama-tts writes to -o; cwd-independent
    cmd = [
        str(bin_path),
        "-m", str(llm),
        "-mv", str(voc),
        "-p", text,
        "-o", str(out),
        "-t", str(n_threads),
        "-n", "512",
    ]
    if speaker and speaker.is_file():
        cmd.extend(["--tts-speaker-file", str(speaker)])

    t0 = time.time()
    # run from out parent so any relative default doesn't litter root
    proc = subprocess.run(
        cmd,
        cwd=str(out.parent),
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    if proc.returncode != 0 or not out.is_file():
        # some builds always write output.wav next to cwd
        fallback = out.parent / "output.wav"
        if fallback.is_file() and not out.is_file():
            fallback.rename(out)
        elif proc.returncode != 0:
            sys.stderr.write(proc.stdout[-2000:] + "\n" + proc.stderr[-2000:] + "\n")
            raise SystemExit(f"llama-tts failed (code {proc.returncode})")

    if not out.is_file():
        raise SystemExit(f"no wav written to {out}")

    return {
        "text": text,
        "wav": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
        "duration_s": round(wav_duration(out), 3),
        "elapsed_s": round(elapsed, 3),
        "bytes": out.stat().st_size,
        "speaker": str(speaker) if speaker and speaker.is_file() else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Clyffy local voice.tts (OuteTTS)")
    ap.add_argument("--text", help="single line to speak")
    ap.add_argument("--out", help="output wav path")
    ap.add_argument("--from-pack", action="store_true", help="all pack sample_lines")
    ap.add_argument("--samples-dir", default=str(ROOT / "work/voice/samples"))
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--no-speaker", action="store_true")
    args = ap.parse_args()

    bin_path = DEFAULT_BIN
    llm = DEFAULT_LLM
    voc = DEFAULT_VOC
    speaker = None if args.no_speaker else DEFAULT_SPEAKER

    results: list[dict] = []
    if args.from_pack:
        lines = parse_pack_sample_lines(ROOT / "clyffy.pack.toml")
        samples_dir = Path(args.samples_dir)
        samples_dir.mkdir(parents=True, exist_ok=True)
        for i, line in enumerate(lines):
            slug = slugify(line, i)
            out = samples_dir / f"{slug}.wav"
            print(f"[{i+1}/{len(lines)}] {line!r}")
            r = synthesize(
                line, out,
                bin_path=bin_path, llm=llm, voc=voc,
                speaker=speaker, n_threads=args.threads,
            )
            results.append(r)
            print(f"  → {r['wav']}  {r['duration_s']}s  gen {r['elapsed_s']}s")
    else:
        if not args.text or not args.out:
            ap.error("need --text and --out, or --from-pack")
        r = synthesize(
            args.text, Path(args.out),
            bin_path=bin_path, llm=llm, voc=voc,
            speaker=speaker, n_threads=args.threads,
        )
        results.append(r)
        print(json.dumps(r, indent=2))

    report = {
        "slot": "voice.tts",
        "backend": "llama-tts/outetts-0.2",
        "character": "clyffy",
        "brief": "warm confident baritone (scaffold via en_male_1 speaker)",
        "bin": str(bin_path),
        "llm": str(llm),
        "vocoder": str(voc),
        "speaker": str(speaker) if speaker and speaker.is_file() else None,
        "samples": results,
    }
    report_path = ROOT / "work/voice/tts_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # merge if from-pack or always overwrite with latest batch
    if args.from_pack or not report_path.is_file():
        report_path.write_text(json.dumps(report, indent=2))
    else:
        report_path.write_text(json.dumps(report, indent=2))
    print(f"wrote {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    # Path.is_relative_to is 3.9+; guard
    if not hasattr(Path, "is_relative_to"):
        def _is_rel(self, other):  # type: ignore
            try:
                self.relative_to(other)
                return True
            except ValueError:
                return False
        Path.is_relative_to = _is_rel  # type: ignore
    sys.exit(main())

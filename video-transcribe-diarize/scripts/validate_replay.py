#!/usr/bin/env python3
"""Validate expected replay folder outputs."""
from __future__ import annotations

import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_replay.py /path/to/replay-folder", file=sys.stderr)
        return 2
    replay_dir = pathlib.Path(sys.argv[1]).expanduser().resolve()
    required = [
        replay_dir / "video",
        replay_dir / "audio_chunks",
        replay_dir / "transcripts/transcript.txt",
        replay_dir / "transcripts/diarization.json",
        replay_dir / "transcripts/diarized_transcript.srt",
        replay_dir / "transcripts/diarized_transcript.txt",
        replay_dir / "transcripts/diarized_transcript.json",
    ]
    missing = [p for p in required if not p.exists()]
    symlinks = [p for p in replay_dir.rglob("*") if p.is_symlink()]
    videos = sorted((replay_dir / "video").glob("*.mp4")) + sorted((replay_dir / "video").glob("*.mov")) + sorted((replay_dir / "video").glob("*.mkv"))
    chunks = sorted((replay_dir / "audio_chunks").glob("part_*.m4a"))

    print(f"Replay folder: {replay_dir}")
    print(f"Videos: {len(videos)}")
    print(f"Audio chunks: {len(chunks)}")
    print(f"Symlinks: {len(symlinks)}")
    if missing:
        print("Missing expected paths:")
        for p in missing:
            print(f"  - {p}")
        return 1
    if symlinks:
        print("Symlinks found:")
        for p in symlinks[:50]:
            print(f"  - {p}")
        return 1
    print("Validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

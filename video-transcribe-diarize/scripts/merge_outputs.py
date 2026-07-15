#!/usr/bin/env python3
"""Merge LocalAI chunk transcription + diarization into final transcript files."""
from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys
from collections import defaultdict


def duration(path: pathlib.Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip())


def srt_time(sec: float) -> str:
    sec = max(0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
        if s == 60:
            m += 1
            s = 0
        if m == 60:
            h += 1
            m = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def txt_time(sec: float) -> str:
    return srt_time(sec).replace(",", ".")


def best_speaker(t0: float, t1: float, diar_segments: list[dict]) -> str:
    best = None
    best_overlap = 0.0
    mid = (t0 + t1) / 2
    for d in diar_segments:
        ds = float(d.get("chunk_start", d.get("start", 0)))
        de = float(d.get("chunk_end", d.get("end", 0)))
        ov = max(0.0, min(t1, de) - max(t0, ds))
        if ov > best_overlap:
            best_overlap = ov
            best = d
    if best and best_overlap > 0:
        return best.get("speaker", "SPEAKER_UNKNOWN")
    for d in diar_segments:
        ds = float(d.get("chunk_start", d.get("start", 0)))
        de = float(d.get("chunk_end", d.get("end", 0)))
        if ds <= mid <= de:
            return d.get("speaker", "SPEAKER_UNKNOWN")
    return "SPEAKER_UNKNOWN"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: merge_outputs.py /path/to/replay-folder", file=sys.stderr)
        return 2

    replay_dir = pathlib.Path(sys.argv[1]).expanduser().resolve()
    audio_dir = replay_dir / "audio_chunks"
    raw_tr = replay_dir / "tmp/localai_raw/transcription"
    raw_diar = replay_dir / "tmp/localai_raw/diarization"
    out = replay_dir / "transcripts"
    out.mkdir(parents=True, exist_ok=True)

    chunks = []
    offset = 0.0
    for idx, audio in enumerate(sorted(audio_dir.glob("part_*.m4a"))):
        dur = duration(audio)
        chunks.append({"chunk": idx, "file": str(audio), "offset": offset, "duration": dur})
        offset += dur

    all_diar = []
    diar_by_chunk: dict[int, list[dict]] = defaultdict(list)
    for c in chunks:
        idx = c["chunk"]
        off = c["offset"]
        p = raw_diar / f"part_{idx:03d}.diarization.json"
        d = json.loads(p.read_text())
        for seg in d.get("segments", []):
            item = dict(seg)
            item["id"] = len(all_diar)
            item["chunk"] = idx
            item["chunk_start"] = float(seg.get("start", 0))
            item["chunk_end"] = float(seg.get("end", 0))
            item["start"] = off + item["chunk_start"]
            item["end"] = off + item["chunk_end"]
            all_diar.append(item)
            diar_by_chunk[idx].append(item)

    all_trans = []
    diarized = []
    for c in chunks:
        idx = c["chunk"]
        off = c["offset"]
        p = raw_tr / f"part_{idx:03d}.transcription.json"
        t = json.loads(p.read_text())
        for seg in t.get("segments", []):
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            cs = float(seg.get("start", 0))
            ce = float(seg.get("end", cs))
            item = {
                "id": len(all_trans) + 1,
                "chunk": idx,
                "start": off + cs,
                "end": off + ce,
                "chunk_start": cs,
                "chunk_end": ce,
                "text": text,
            }
            all_trans.append(item)
            ditem = dict(item)
            ditem["speaker"] = best_speaker(cs, ce, diar_by_chunk[idx])
            diarized.append(ditem)

    (out / "transcript.json").write_text(json.dumps({"chunks": chunks, "segments": all_trans}, ensure_ascii=False, indent=2))
    (out / "diarization.json").write_text(json.dumps({"chunks": chunks, "segments": all_diar}, ensure_ascii=False, indent=2))
    (out / "diarized_transcript.json").write_text(json.dumps({"chunks": chunks, "segments": diarized}, ensure_ascii=False, indent=2))
    (out / "transcript.txt").write_text("\n".join(s["text"] for s in all_trans), encoding="utf-8")

    with open(out / "diarization.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "chunk", "speaker", "label", "start", "end", "chunk_start", "chunk_end"])
        w.writeheader()
        for s in all_diar:
            w.writerow({k: s.get(k) for k in w.fieldnames})

    with open(out / "diarization_timeline.txt", "w") as f:
        for s in all_diar:
            f.write(f"{s['id']:04d}\tchunk {s['chunk']:03d}\t{s.get('speaker')}\t{txt_time(s['start'])} --> {txt_time(s['end'])}\n")

    with open(out / "diarized_transcript.srt", "w") as f:
        for i, s in enumerate(diarized, 1):
            f.write(f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['speaker']}: {s['text']}\n\n")

    blocks = []
    for s in diarized:
        if blocks and blocks[-1]["speaker"] == s["speaker"] and blocks[-1]["chunk"] == s["chunk"]:
            blocks[-1]["end"] = s["end"]
            blocks[-1]["texts"].append(s["text"])
            blocks[-1]["segment_count"] += 1
        else:
            blocks.append({
                "speaker": s["speaker"], "chunk": s["chunk"], "start": s["start"],
                "end": s["end"], "texts": [s["text"]], "segment_count": 1,
            })
    with open(out / "diarized_transcript.txt", "w") as f:
        f.write(f"Diarized transcript for {replay_dir.name}\n")
        f.write("Grouped consecutive transcript segments by speaker. Speaker labels are local to each audio chunk.\n\n")
        for b in blocks:
            f.write(f"[{txt_time(b['start'])} --> {txt_time(b['end'])}] chunk {b['chunk']:03d} {b['speaker']} ({b['segment_count']} segments)\n")
            f.write(" ".join(b["texts"]) + "\n\n")

    print(f"Wrote final transcript files to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

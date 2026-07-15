---
name: video-transcribe-diarize
description: Transcribe and speaker-diarize a local video file using the private LocalAI server, then organize outputs into a clean per-video folder with video, audio chunks, raw LocalAI outputs, transcript, diarization, and diarized TXT/SRT files.
allowed-tools: Bash(ffmpeg:*) Bash(ffprobe:*) Bash(curl:*) Bash(python3:*) Bash(find:*) Bash(mkdir:*) Bash(mv:*) Bash(cp:*) Bash(test:*) Bash(ls:*) Bash(chmod:*)
---

# Video transcription + diarization

Use this skill when the user provides a local video file and asks to transcribe it, diarize it, generate speaker-labelled transcripts, or organize replay/video outputs.

## Files in this skill

```text
video-transcribe-diarize/
├── SKILL.md
├── .env              # local constants, git-ignored
├── .env.example      # safe template
├── .gitignore        # ignores .env
└── scripts/
    ├── process_video.sh     # full pipeline: organize, chunk, transcribe, diarize, merge, validate
    ├── merge_outputs.py     # merge raw chunk outputs into final transcript files
    └── validate_replay.py   # sanity-check final folder
```

Configuration constants live in `.env`, not inline in the scripts.

Current defaults:

```dotenv
LOCALAI_BASE=http://192.168.0.7:11435
TRANSCRIBE_MODEL=whisper-large-turbo-q5_0
DIARIZE_MODEL=pyannote-diarization
LANGUAGE=fr
CHUNK_SECONDS=1080
AUDIO_BITRATE=64k
NUM_SPEAKERS=2
```

`.env` is git-ignored. Commit `.env.example`, not `.env`.

## Folder organization for one input video

For input:

```text
/path/to/AIBUS4-example.mp4
```

The pipeline creates:

```text
/path/to/AIBUS4-example/
├── README.md
├── video/
│   └── AIBUS4-example.mp4
├── audio_chunks/
│   ├── part_000.m4a
│   ├── part_001.m4a
│   └── ...
├── transcripts/
│   ├── transcript.txt
│   ├── transcript.json
│   ├── diarization.json
│   ├── diarization.csv
│   ├── diarization_timeline.txt
│   ├── diarized_transcript.json
│   ├── diarized_transcript.txt
│   └── diarized_transcript.srt
└── tmp/
    ├── localai_raw/
    │   ├── transcription/
    │   │   ├── part_000.transcription.json
    │   │   └── ...
    │   └── diarization/
    │       ├── part_000.diarization.json
    │       └── ...
    ├── logs/
    └── scratch/
```

Rules:

- Do **not** create aliases/symlinks unless the user explicitly asks.
- Default script mode is `--copy`; original video remains in place.
- Use `--move` only after explicit user consent.
- All temporary/raw files go under the replay folder’s `tmp/` subtree.
- Final human-facing outputs go under `transcripts/`.

## Full pipeline

From this skill folder:

```bash
scripts/process_video.sh --copy /absolute/path/to/video.mp4
```

Move the original video into the organized folder only with explicit user permission:

```bash
scripts/process_video.sh --move /absolute/path/to/video.mp4
```

Re-run and overwrite generated files:

```bash
scripts/process_video.sh --copy --force /absolute/path/to/video.mp4
```

The script performs:

1. create replay folder structure
2. copy/move video to `video/<real-name>.mp4`
3. split audio into 18-minute chunks using `ffmpeg`
4. transcribe each chunk via LocalAI `/v1/audio/transcriptions`
5. diarize each chunk via LocalAI `/v1/audio/diarization`
6. merge transcript + diarization with `merge_outputs.py`
7. validate output folder with `validate_replay.py`

## Merge-only workflow

If raw LocalAI outputs already exist:

```bash
scripts/merge_outputs.py /absolute/path/to/replay-folder
scripts/validate_replay.py /absolute/path/to/replay-folder
```

## Output formats

### `diarized_transcript.srt`

Subtitle-style, one caption per Whisper transcript segment:

```srt
1
00:00:06,393 --> 00:00:11,033
SPEAKER_00: Bonjour à toutes et à tous.
```

### `diarized_transcript.txt`

Readable text grouped by consecutive same-speaker turns inside each audio chunk:

```text
[00:01:23.200 --> 00:03:42.900] chunk 000 SPEAKER_00 (34 segments)
Bonjour à toutes et à tous. Aujourd’hui nous allons parler de ...
```

## Important caveats

- LocalAI upload limits can reject full-length videos/audio (`413`); always chunk audio.
- Diarization returns only speaker/time segments, not transcription text.
- Speaker labels from chunked diarization are local to each chunk. `SPEAKER_00` in chunk 000 is not guaranteed to be the same person as `SPEAKER_00` in chunk 001.
- If auto diarization over-splits speakers, set `NUM_SPEAKERS` in `.env` to the expected number, commonly `2` for AI4BUS replays.
- Prefer Whisper transcription + `pyannote-diarization` endpoint + merge. Do not rely on WhisperX diarization if timestamps are corrupted.
- Never expose API keys or Hugging Face tokens in chat or logs.

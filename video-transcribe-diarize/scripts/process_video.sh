#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SKILL_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

LOCALAI_BASE="${LOCALAI_BASE:-http://192.168.0.7:11435}"
TRANSCRIBE_MODEL="${TRANSCRIBE_MODEL:-whisper-large-turbo-q5_0}"
DIARIZE_MODEL="${DIARIZE_MODEL:-pyannote-diarization}"
LANGUAGE="${LANGUAGE:-fr}"
CHUNK_SECONDS="${CHUNK_SECONDS:-1080}"
AUDIO_BITRATE="${AUDIO_BITRATE:-64k}"
NUM_SPEAKERS="${NUM_SPEAKERS:-2}"
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-15}"
CURL_MAX_TIME="${CURL_MAX_TIME:-1800}"
CURL_RETRIES="${CURL_RETRIES:-3}"
CURL_RETRY_DELAY="${CURL_RETRY_DELAY:-10}"

MODE="copy"   # copy | move | in-place
FORCE=0
VIDEO=""

usage() {
  cat <<USAGE
Usage: $0 [--copy|--move|--in-place] [--force] /absolute/path/to/video

Creates a per-video folder next to the input video:
  <parent>/<video-stem>/
    video/<video-stem>.<ext>
    audio_chunks/part_000.m4a ...
    transcripts/...
    tmp/localai_raw/...

Defaults are read from: $ENV_FILE
USAGE
}

valid_json_response() {
  local json_file="$1"
  python3 - "$json_file" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
if not p.exists() or p.stat().st_size == 0:
    raise SystemExit(1)
try:
    data = json.loads(p.read_text())
except Exception:
    raise SystemExit(1)
if isinstance(data, dict) and data.get("error"):
    raise SystemExit(1)
PY
}

post_localai_form() {
  local out_json="$1" status_file="$2" url="$3"
  shift 3
  local tmp_json="${out_json}.tmp.$$" tmp_status="${status_file}.tmp.$$"
  local attempt rc http_code

  rm -f "$tmp_json" "$tmp_status"
  for attempt in $(seq 1 "$CURL_RETRIES"); do
    set +e
    http_code="$(curl -sS --fail-with-body --http1.1 \
      -H 'Expect:' \
      --connect-timeout "$CURL_CONNECT_TIMEOUT" \
      -m "$CURL_MAX_TIME" \
      -o "$tmp_json" -w '%{response_code}' \
      "$url" "$@")"
    rc=$?
    set -e
    printf '%s' "$http_code" > "$tmp_status"

    if [[ "$rc" == "0" && "$http_code" == "200" ]] && valid_json_response "$tmp_json"; then
      mv -f "$tmp_json" "$out_json"
      mv -f "$tmp_status" "$status_file"
      return 0
    fi

    echo "Attempt $attempt/$CURL_RETRIES failed for $(basename "$out_json"): curl_exit=$rc HTTP=${http_code:-none}" >&2
    rm -f "$tmp_json"
    if [[ "$attempt" != "$CURL_RETRIES" ]]; then
      sleep "$CURL_RETRY_DELAY"
    fi
  done

  mv -f "$tmp_status" "$status_file"
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --copy) MODE="copy"; shift ;;
    --move) MODE="move"; shift ;;
    --in-place) MODE="in-place"; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) VIDEO="$1"; shift ;;
  esac
done

if [[ -z "$VIDEO" ]]; then usage; exit 2; fi
if [[ ! -f "$VIDEO" ]]; then echo "Video not found: $VIDEO" >&2; exit 2; fi

VIDEO="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())' "$VIDEO")"
PARENT="$(dirname "$VIDEO")"
FILE="$(basename "$VIDEO")"
EXT="${FILE##*.}"
STEM="${FILE%.*}"
if [[ "$(basename "$PARENT")" == "video" && -d "$(dirname "$PARENT")/audio_chunks" ]]; then
  REPLAY_DIR="$(dirname "$PARENT")"
else
  REPLAY_DIR="$PARENT/$STEM"
fi
VIDEO_DEST="$REPLAY_DIR/video/$STEM.$EXT"

mkdir -p \
  "$REPLAY_DIR/video" \
  "$REPLAY_DIR/audio_chunks" \
  "$REPLAY_DIR/transcripts" \
  "$REPLAY_DIR/tmp/localai_raw/transcription" \
  "$REPLAY_DIR/tmp/localai_raw/diarization" \
  "$REPLAY_DIR/tmp/logs" \
  "$REPLAY_DIR/tmp/scratch"

cat > "$REPLAY_DIR/README.md" <<README
# $STEM

- Video: video/$STEM.$EXT
- Audio chunks: audio_chunks/part_000.m4a, ...
- Final transcripts: transcripts/
- Raw/temporary LocalAI files: tmp/localai_raw/
README

if [[ "$MODE" == "copy" ]]; then
  if [[ "$VIDEO" != "$VIDEO_DEST" && ( ! -f "$VIDEO_DEST" || "$FORCE" == "1" ) ]]; then
    cp -f "$VIDEO" "$VIDEO_DEST"
  fi
elif [[ "$MODE" == "move" ]]; then
  if [[ "$VIDEO" != "$VIDEO_DEST" ]]; then
    if [[ -f "$VIDEO_DEST" && "$FORCE" != "1" ]]; then
      echo "Destination exists, use --force to overwrite: $VIDEO_DEST" >&2; exit 3
    fi
    mv -f "$VIDEO" "$VIDEO_DEST"
  fi
else
  VIDEO_DEST="$VIDEO"
fi

VIDEO_FOR_FFMPEG="$VIDEO_DEST"

if ! find "$REPLAY_DIR/audio_chunks" -maxdepth 1 -name 'part_*.m4a' | grep -q . || [[ "$FORCE" == "1" ]]; then
  ffmpeg -hide_banner -y \
    -i "$VIDEO_FOR_FFMPEG" \
    -vn -ac 1 -ar 16000 -c:a aac -b:a "$AUDIO_BITRATE" \
    -f segment -segment_time "$CHUNK_SECONDS" -reset_timestamps 1 \
    "$REPLAY_DIR/audio_chunks/part_%03d.m4a" \
    2>&1 | tee "$REPLAY_DIR/tmp/logs/audio_split.log"
fi

for audio in "$REPLAY_DIR"/audio_chunks/part_*.m4a; do
  [[ -f "$audio" ]] || continue
  part="$(basename "$audio" .m4a)"
  tr_json="$REPLAY_DIR/tmp/localai_raw/transcription/$part.transcription.json"
  tr_status="$REPLAY_DIR/tmp/localai_raw/transcription/$part.transcription.status.txt"
  diar_json="$REPLAY_DIR/tmp/localai_raw/diarization/$part.diarization.json"
  diar_status="$REPLAY_DIR/tmp/localai_raw/diarization/$part.diarization.status.txt"

  legacy_tr_json="$REPLAY_DIR/tmp/localai_raw/transcription/${STEM}_${part}.json"
  if [[ "$FORCE" != "1" && ! -f "$tr_json" && -f "$legacy_tr_json" ]] && valid_json_response "$legacy_tr_json"; then
    cp -f "$legacy_tr_json" "$tr_json"
    printf '200' > "$tr_status"
  fi

  if [[ "$FORCE" == "1" || ! -f "$tr_json" ]] || ! valid_json_response "$tr_json"; then
    echo "Transcribing $part"
    post_localai_form "$tr_json" "$tr_status" \
      "$LOCALAI_BASE/v1/audio/transcriptions" \
      -F file=@"$audio" \
      -F model="$TRANSCRIBE_MODEL" \
      -F language="$LANGUAGE" \
      -F response_format=verbose_json \
      || { echo "Transcription failed for $part after $CURL_RETRIES attempts: HTTP $(cat "$tr_status" 2>/dev/null || true)" >&2; exit 4; }
  fi

  legacy_diar_json="$REPLAY_DIR/tmp/localai_raw/diarization/${STEM}_${part}.json"
  if [[ "$FORCE" != "1" && ! -f "$diar_json" && -f "$legacy_diar_json" ]] && valid_json_response "$legacy_diar_json"; then
    cp -f "$legacy_diar_json" "$diar_json"
    printf '200' > "$diar_status"
  fi

  if [[ "$FORCE" == "1" || ! -f "$diar_json" ]] || ! valid_json_response "$diar_json"; then
    echo "Diarizing $part"
    post_localai_form "$diar_json" "$diar_status" \
      "$LOCALAI_BASE/v1/audio/diarization" \
      -F file=@"$audio" \
      -F model="$DIARIZE_MODEL" \
      -F response_format=verbose_json \
      -F num_speakers="$NUM_SPEAKERS" \
      || { echo "Diarization failed for $part after $CURL_RETRIES attempts: HTTP $(cat "$diar_status" 2>/dev/null || true)" >&2; exit 5; }
  fi
done

python3 "$SCRIPT_DIR/merge_outputs.py" "$REPLAY_DIR"
python3 "$SCRIPT_DIR/validate_replay.py" "$REPLAY_DIR"

echo "Done: $REPLAY_DIR"

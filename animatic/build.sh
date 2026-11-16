#!/usr/bin/env bash
# Rebuild the animatic from scratch: picture, scratch soundtrack, subtitles, mux, checks.
#
#   VOICE=/path/to/en_GB-alan-medium.onnx ./build.sh
#
# Needs: python3 with numpy and pillow, ffmpeg, piper-tts (pip install piper-tts) and the
# Piper voice "en_GB-alan-medium" (.onnx and .onnx.json side by side), from
# https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/alan/medium
# Fonts: Liberation Serif and Liberation Sans in /usr/share/fonts/truetype/liberation.
# Set SKIP_RENDER=1 to reuse picture segments already in $WORK.
set -euo pipefail
cd "$(dirname "$0")"
: "${VOICE:?set VOICE to the Piper voice .onnx file}"
WORK="${WORK:-../build}"
OUT="../deliverables"
NAME="the-faithful-friend_animatic_v1"
JOBS="${JOBS:-4}"
mkdir -p "$WORK" "$OUT"

# 1. Picture: 3000 frames at 3840x2160, rendered in parallel slices that start on shot boundaries
if [ -z "${SKIP_RENDER:-}" ]; then
  for i in $(seq 0 $((JOBS - 1))); do
    python3 render.py segment "$i" "$JOBS" "$WORK/seg$i.mp4" &
  done
  wait
fi
: > "$WORK/list.txt"
for i in $(seq 0 $((JOBS - 1))); do echo "file seg$i.mp4" >> "$WORK/list.txt"; done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$WORK/picture.mp4"

# 2. Sound: synthetic narration, scratch music and ambience; subtitles from the real cue timings
python3 audio.py "$VOICE" "$WORK/audio" "$WORK/mix_raw.wav" "$OUT/$NAME.en.srt"

# 3. Loudness: one linear gain to reach -23 LUFS integrated (EBU R 128)
I=$(ffmpeg -hide_banner -nostats -i "$WORK/mix_raw.wav" -af ebur128 -f null - 2>&1 | awk '/I:/{v=$2} END{print v}')
GAIN=$(python3 -c "print(round(-23.0 - ($I), 2))")
ffmpeg -loglevel error -y -i "$WORK/mix_raw.wav" -af "volume=${GAIN}dB" -ar 48000 "$WORK/mix.wav"

# 4. Mux the 4K master and make a 1080p viewing copy
ffmpeg -loglevel error -y -i "$WORK/picture.mp4" -i "$WORK/mix.wav" -c:v copy -c:a aac -b:a 256k \
  -movflags +faststart -metadata title="The Faithful Friend (animatic v1)" "$OUT/${NAME}_2160p25.mp4"
ffmpeg -loglevel error -y -i "$OUT/${NAME}_2160p25.mp4" -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset slow \
  -crf 21 -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT/${NAME}_1080p25.mp4"

# 5. Contact sheet for the documentation
python3 render.py sheet "$OUT/${NAME}_contact-sheet.jpg"

# 6. Checks
echo "--- frames / size / rate"
ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames,width,height,r_frame_rate \
  -of default=nw=1 "$OUT/${NAME}_2160p25.mp4"
echo "--- duration"
ffprobe -v error -show_entries format=duration -of default=nw=1 "$OUT/${NAME}_2160p25.mp4"
echo "--- loudness of the delivered audio"
ffmpeg -hide_banner -nostats -i "$OUT/${NAME}_2160p25.mp4" -af ebur128=peak=true -f null - 2>&1 | tail -12

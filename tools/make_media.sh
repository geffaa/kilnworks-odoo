#!/usr/bin/env bash
# Turn media/clips/*.webm (from tools/capture.py) into catalog GIFs and the walkthrough video.
#   media/gif/<scene>.gif        one per Upwork catalog, 960 px wide
#   media/kilnworks-walkthrough.mp4   intro, the six modules, outro (1440x900, H.264)
set -euo pipefail
cd "$(dirname "$0")/.."
clips=media/clips
mkdir -p media/gif "$clips/mp4"
scenes=(approval shopify payment api dashboard firing)

start_of() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['start'])" "$clips/$1.json"; }

for s in intro "${scenes[@]}" outro; do
  ffmpeg -v error -y -ss "$(start_of "$s")" -i "$clips/$s.webm" \
    -vf "fps=30,format=yuv420p" -c:v libx264 -crf 20 -preset slow -an "$clips/mp4/$s.mp4"
done

for s in "${scenes[@]}"; do
  ffmpeg -v error -y -i "$clips/mp4/$s.mp4" -vf \
    "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
    "media/gif/$s.gif"
done

list=$(mktemp "$PWD/$clips/concat.XXXX")
for s in intro "${scenes[@]}" outro; do echo "file 'mp4/$s.mp4'" >> "$list"; done
ffmpeg -v error -y -f concat -safe 0 -i "$list" -c copy -movflags +faststart media/kilnworks-walkthrough.mp4
rm -f "$list"

for f in media/gif/*.gif media/kilnworks-walkthrough.mp4; do
  printf '%-36s %6s  %5.1fs\n' "$f" "$(du -h "$f" | cut -f1)" \
    "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"
done

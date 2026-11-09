#!/usr/bin/env bash
# 逐章製作：Edge TTS 備用版 → ebook2audiobook(XTTS) 完整版；E2A 失敗就用備用版
set -uo pipefail
mkdir -p output/edge work/out
E2A_OK=0
if [ "${USE_E2A:-1}" = "1" ] && docker pull -q athomasson2/ebook2audiobook:cpu; then E2A_OK=1; fi
python make_voices.py

e2a() {  # $1=SML 檔 $2=輸出名稱
  rm -rf work/out && mkdir -p work/out
  docker run --rm -v "$PWD/work:/work" athomasson2/ebook2audiobook:cpu \
    --headless --ebook "/work/$1" --language zho --tts_engine xtts \
    --voice /work/voices/旁白.wav --output_format mp3 --output_dir /work/out --device CPU \
    2>&1 | tail -n 40
  local mp3; mp3=$(find work/out -type f -name '*.mp3' | head -n 1)
  [ -n "$mp3" ] && cp "$mp3" "$2"
}

make() {  # $1=章節號或「試聽」
  local ch="$1" src name
  if [ "$ch" = "試聽" ]; then src="scripts/試聽.txt"; name="output/試聽"; else src="scripts/第${ch}章.txt"; name="output/第${ch}章_完整版"; fi
  echo "===== $ch ====="
  python run_edge.py "$ch" || { echo "Edge 版失敗：$ch"; return 1; }
  local edge_mp3; if [ "$ch" = "試聽" ]; then edge_mp3="output/edge/試聽.mp3"; else edge_mp3="output/edge/第${ch}章_完整版.mp3"; fi
  local engine="EdgeTTS"
  if [ $E2A_OK = 1 ]; then
    python to_sml.py "$src" "work/sml_${ch}.txt"
    if e2a "sml_${ch}.txt" "${name}.mp3"; then engine="XTTS"; else echo "ebook2audiobook 失敗，改用 Edge 版"; fi
  fi
  [ "$engine" = "EdgeTTS" ] && cp "$edge_mp3" "${name}.mp3"
  [ "$ch" != "試聽" ] && python note_engine.py "$ch" "$engine"
  echo "$ch 完成，引擎：$engine"
}

[ -f output/試聽.mp3 ] || make 試聽
for f in scripts/第*章.txt; do
  [ -e "$f" ] || continue
  n=$(basename "$f" | sed -E 's/第([0-9]+)章\.txt/\1/')
  [ -f "output/第${n}章_完整版.mp3" ] && continue
  make "$n"
done
rm -rf output/edge/_work output/edge/片段快取

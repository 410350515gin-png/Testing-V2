#!/usr/bin/env python3
"""Create Mandarin audiobook MP3s on GitHub Actions; only process authorized texts."""
import argparse
import asyncio
import csv
import hashlib
import pathlib
import re
import shutil
import subprocess

import edge_tts

VOICES = {
    "旁白": "zh-TW-HsiaoChenNeural",
    "宋辭": "zh-TW-YunJheNeural",
    "許明珠": "zh-TW-HsiaoYuNeural",
    "其他男聲": "zh-TW-YunJheNeural",
    "其他女聲": "zh-TW-HsiaoChenNeural",
}
# Original demonstration; no third-party novel text is committed to this public repository.
DEMO = [
    ("旁白", "夜色漸深，街道兩旁的燈火一盞接著一盞亮起。"),
    ("許明珠", "你看，那盞花燈是不是很好看？"),
    ("宋辭", "嗯，很好看。我陪你慢慢走。"),
]
def parse_rows(path):
    if not path:
        return DEMO
    source=pathlib.Path(path)
    if not source.is_file():
        raise FileNotFoundError(path)
    if source.suffix.lower()==".csv":
        with source.open(encoding="utf-8-sig",newline="") as f:
            data=list(csv.DictReader(f))
        rows=[(str(r["speaker"]).strip(), str(r["text"]).strip()) for r in data]
    elif source.suffix.lower()==".txt":
        # Explicit speaker label per line; avoids guessing who speaks.
        rows=[]
        for lineno, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(),1):
            if not line.strip():continue
            m=re.match(r"^(旁白|宋辭|許明珠|其他男聲|其他女聲)[：:]\s*(.+)$",line.strip())
            if not m: raise ValueError(f"第 {lineno} 行缺少角色標記")
            rows.append(m.groups())
    else:
        raise ValueError("Only CSV and speaker-tagged TXT are accepted")
    if not rows: raise ValueError("輸入是空的")
    for speaker, _ in rows:
        if speaker not in VOICES:raise ValueError(f"未知角色：{speaker}")
    return rows

async def one(i, speaker, text, output):
    if not text.strip(): return None
    filename=output/"segments"/f"{i:05d}_{hashlib.sha256((speaker+text).encode()).hexdigest()[:10]}.mp3"
    if not filename.exists():
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, voice=VOICES[speaker],rate="-5%").save(str(filename))
                break
            except Exception:
                if attempt == 3:raise
                await asyncio.sleep(3*(attempt+1))
    return filename

async def produce(rows, output):
    (output/"segments").mkdir(parents=True,exist_ok=True)
    paths=[]
    for i,(speaker,text) in enumerate(rows):
        for k in range(0,len(text),220):
            part=await one(len(paths),speaker,text[k:k+220],output)
            if part:paths.append(part)
    if not paths: raise ValueError("無有效文字可生成")
    listfile=output/"concat.txt"
    # concat demuxer concatenates audio without repeated re-encoding.
    listfile.write_text("\n".join("file '"+str(p.resolve()).replace("'","'\\''")+"'" for p in paths),encoding="utf-8")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
                    "-i",str(listfile),"-c:a","libmp3lame","-b:a","128k",str(output/"audiobook.mp3")],check=True)
    assert (output/"audiobook.mp3").stat().st_size > 1024
    print("完成",output/"audiobook.mp3","片段數",len(paths))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",help="CSV or tagged TXT; omit to generate original demo only")
    parser.add_argument("--output",default="output-audiobook")
    args=parser.parse_args()
    asyncio.run(produce(parse_rows(args.input),pathlib.Path(args.output)))

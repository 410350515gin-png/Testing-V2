"""把【角色|情緒】劇本轉成 ebook2audiobook 的 SML 文字（[voice:路徑]…[/voice]）。"""
import sys
from pathlib import Path
import audiobook_core as C

VOICE_DIR = "/work/voices"   # 容器內路徑


def convert(src, dst):
    segs = C.parse_script(Path(src).read_text(encoding="utf-8"))
    out, prev = [], None
    for s in segs:
        if s["para_break"] and out:
            out.append("\n\n")
        elif prev is not None and s["speaker"] != prev:
            out.append("\n")
        if s["speaker"] == C.DEFAULT_SPEAKER:
            out.append(s["text"])
        else:
            out.append(f"[voice:{VOICE_DIR}/{s['speaker']}.wav]{s['text']}[/voice]")
        prev = s["speaker"]
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text("".join(out) + "\n", encoding="utf-8")
    print(f"SML：{dst}（{len(segs)} 段）")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])

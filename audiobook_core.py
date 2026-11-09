# ===== 有聲小說多角色配音核心程式（Edge TTS 版）=====
import re, json, hashlib, asyncio, subprocess, time, csv
from pathlib import Path

# ---------- 1. 角色聲線（同一角色跨章節固定不變） ----------
# rate: 語速百分比；pitch: 音高 Hz；volume: 音量百分比
VOICES = {
    "旁白":   {"voice": "zh-TW-HsiaoChenNeural", "rate": -5, "pitch": -2, "volume": 0},   # 成熟溫柔女聲
    "許明珠": {"voice": "zh-TW-HsiaoYuNeural",   "rate": 0,  "pitch": 0,  "volume": 0},   # 清亮有活力
    "宋辭":   {"voice": "zh-TW-YunJheNeural",    "rate": -8, "pitch": -4, "volume": 0},   # 低沉溫柔
    # 配角：同一套臺灣聲線，用音高/語速區分；新角色請在這裡新增，之後不要改
    "王婆婆": {"voice": "zh-TW-HsiaoChenNeural", "rate": -12, "pitch": -12, "volume": 0},
    "其他男": {"voice": "zh-TW-YunJheNeural",    "rate": 4,   "pitch": 6,   "volume": 0},
    "其他女": {"voice": "zh-TW-HsiaoYuNeural",   "rate": 2,   "pitch": -6,  "volume": 0},
}
DEFAULT_SPEAKER = "旁白"   # 無法確認說話者 → 旁白

# ---------- 2. 情緒 → 語速/音高/音量微調（Edge TTS 無真正情緒參數） ----------
EMOTIONS = {
    "平常": (0, 0, 0),
    "開心": (6, 3, 5),
    "害羞": (-10, 1, -10),
    "深情": (-12, -2, -12),
    "溫柔": (-8, -1, -8),
    "緊張": (8, 2, 0),
    "生氣": (5, -1, 10),
    "悲傷": (-12, -3, -8),
    "調侃": (4, 2, 0),
    "認真": (-3, 0, 3),
}

TAG_RE = re.compile(r"^\s*[\[【]\s*([^\]】|｜]+?)\s*(?:[|｜]\s*([^\]】]+?))?\s*[\]】]\s*(.*)$")


def parse_script(text):
    """
    劇本格式（每行一段）：
      【旁白】文字
      【許明珠|害羞】「文字」
      空行 = 段落停頓；# 開頭 = 註解，不朗讀
      沒有標籤的行 → 旁白
    """
    segs, para_break = [], False
    for ln_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            para_break = True
            continue
        if line.startswith("#"):
            continue
        m = TAG_RE.match(line)
        if m:
            spk, emo, body = m.group(1).strip(), (m.group(2) or "平常").strip(), m.group(3).strip()
        else:
            spk, emo, body = DEFAULT_SPEAKER, "平常", line
        if not body:
            continue
        warn = []
        if spk not in VOICES:
            warn.append(f"未知角色「{spk}」→ 改用旁白")
            spk = DEFAULT_SPEAKER
        if emo not in EMOTIONS:
            warn.append(f"未知情緒「{emo}」→ 平常")
            emo = "平常"
        for piece in split_long(body):
            segs.append({"speaker": spk, "emotion": emo, "text": piece,
                         "line": ln_no, "para_break": para_break, "warn": "；".join(warn)})
            para_break = False
    return segs


def split_long(body, limit=800):
    """過長段落依句號切開，避免單次請求失敗；不改動文字。"""
    if len(body) <= limit:
        return [body]
    parts, buf = [], ""
    for sent in re.findall(r".+?(?:[。！？…」]+|$)", body):
        if buf and len(buf) + len(sent) > limit:
            parts.append(buf); buf = ""
        buf += sent
    if buf:
        parts.append(buf)
    return parts


def voice_params(seg):
    v = VOICES[seg["speaker"]]
    dr, dp, dv = EMOTIONS[seg["emotion"]]
    r = max(-50, min(100, v["rate"] + dr))
    p = max(-50, min(50, v["pitch"] + dp))
    vol = max(-50, min(100, v["volume"] + dv))
    return {"voice": v["voice"], "rate": f"{r:+d}%", "pitch": f"{p:+d}Hz", "volume": f"{vol:+d}%"}


def seg_key(seg):
    vp = voice_params(seg)
    h = hashlib.sha1(json.dumps([vp, seg["text"]], ensure_ascii=False).encode()).hexdigest()[:14]
    return h


async def edge_synth(text, vp, out_path):
    import edge_tts
    c = edge_tts.Communicate(text, vp["voice"], rate=vp["rate"], pitch=vp["pitch"], volume=vp["volume"])
    await c.save(str(out_path))


async def synth_all(segs, seg_dir, synth=edge_synth, retries=3):
    """逐段生成；已生成過（同文字同參數）的片段直接沿用，不重複消耗。"""
    seg_dir = Path(seg_dir); seg_dir.mkdir(parents=True, exist_ok=True)
    new, reused = 0, 0
    for i, s in enumerate(segs):
        s["file"] = str(seg_dir / f"{seg_key(s)}.mp3")
        f = Path(s["file"])
        if f.exists() and f.stat().st_size > 0:
            reused += 1
            continue
        for attempt in range(1, retries + 1):
            try:
                await synth(s["text"], voice_params(s), f)
                if f.exists() and f.stat().st_size > 0:
                    break
            except Exception as e:
                print(f"  第 {i+1} 段失敗（第 {attempt} 次）：{e}")
                time.sleep(2 * attempt)
        else:
            raise RuntimeError(f"第 {i+1} 段（原稿第 {s['line']} 行）生成失敗，已停止。重跑會從這裡接續。")
        new += 1
        if (i + 1) % 10 == 0 or i + 1 == len(segs):
            print(f"  進度 {i+1}/{len(segs)}")
    return new, reused


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


PAUSE_SAME = 0.25     # 同角色連續
PAUSE_SWITCH = 0.45   # 換人說話
PAUSE_PARA = 0.80     # 段落


def merge(segs, out_mp3, work_dir, bitrate="96k"):
    """依原稿順序合併為單一 MP3，並插入自然停頓。"""
    work = Path(work_dir); work.mkdir(parents=True, exist_ok=True)
    sil = {}
    for name, sec in [("same", PAUSE_SAME), ("switch", PAUSE_SWITCH), ("para", PAUSE_PARA)]:
        p = work / f"sil_{name}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"anullsrc=r=24000:cl=mono", "-t", str(sec), "-c:a", "pcm_s16le", str(p)], check=True)
        sil[name] = p
    lst = []
    prev = None
    for i, s in enumerate(segs):
        wav = work / f"{i:05d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", s["file"], "-ar", "24000", "-ac", "1",
                        "-c:a", "pcm_s16le", str(wav)], check=True)
        if prev is not None:
            kind = "para" if s["para_break"] else ("same" if s["speaker"] == prev else "switch")
            lst.append(sil[kind])
        lst.append(wav)
        prev = s["speaker"]
    lf = work / "concat.txt"
    lf.write_text("".join(f"file '{p.resolve()}'\n" for p in lst), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lf),
                    "-c:a", "libmp3lame", "-b:a", bitrate, str(out_mp3)], check=True)
    for p in work.glob("*.wav"):
        p.unlink()
    return duration(out_mp3)


def write_report(segs, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["順序", "原稿行", "角色", "情緒", "聲線", "語速", "音高", "音量", "字數", "秒數", "警告", "內容開頭"])
        for i, s in enumerate(segs, 1):
            vp = voice_params(s)
            w.writerow([i, s["line"], s["speaker"], s["emotion"], vp["voice"], vp["rate"], vp["pitch"],
                        vp["volume"], len(s["text"]), round(duration(s["file"]), 2), s["warn"], s["text"][:20]])


def update_progress(progress_path, chapter, segs, mp3_path, total_sec, new, reused):
    p = Path(progress_path)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"chapters": {}}
    data["voices"] = {k: v["voice"] for k, v in VOICES.items()}
    data["chapters"][str(chapter)] = {
        "狀態": "完成",
        "片段數": len(segs),
        "本次新生成": new,
        "沿用快取": reused,
        "使用角色": sorted({s["speaker"] for s in segs}),
        "音檔": Path(mp3_path).name,
        "長度": f"{int(total_sec // 60)} 分 {int(total_sec % 60)} 秒",
        "警告": [f"第{s['line']}行：{s['warn']}" for s in segs if s["warn"]],
        "需要重新生成": False,
        "完成時間": time.strftime("%Y-%m-%d %H:%M"),
    }
    done = sorted(int(c) for c in data["chapters"])
    data["下一章"] = done[-1] + 1
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


async def produce_chapter(chapter, script_path, base_dir, synth=edge_synth, record=True):
    base = Path(base_dir); base.mkdir(parents=True, exist_ok=True)
    text = Path(script_path).read_text(encoding="utf-8")
    segs = parse_script(text)
    if not segs:
        raise ValueError("劇本是空的")
    label = f"第{chapter}章" if record else str(chapter)
    print(f"{label}：共 {len(segs)} 段，{sum(len(s['text']) for s in segs)} 字")
    for s in segs:
        if s["warn"]:
            print(f"  ⚠ 原稿第 {s['line']} 行：{s['warn']}")
    new, reused = await synth_all(segs, base / "片段快取", synth)
    name = f"第{chapter}章_完整版.mp3" if record else f"{chapter}.mp3"
    out = base / name
    total = merge(segs, out, base / "_work")
    write_report(segs, base / name.replace(".mp3", "_分段報告.csv"))
    if record:
        update_progress(base / "製作進度.json", chapter, segs, out, total, new, reused)
    print(f"✅ 完成：{out.name}（{int(total // 60)} 分 {int(total % 60)} 秒），新生成 {new} 段、沿用 {reused} 段")
    return out

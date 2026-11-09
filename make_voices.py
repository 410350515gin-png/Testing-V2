"""用 Edge TTS（臺灣國語）為每個角色產生 15 秒左右的參考聲音，給 ebook2audiobook 複製聲線。"""
import asyncio, subprocess
from pathlib import Path
import audiobook_core as C

REF = ("今天的天氣很好，市場裡人來人往，熱鬧得很。我們慢慢走，一邊聊天，一邊看看有什麼新鮮的東西。"
       "如果累了，就找個地方坐下來，喝杯茶，休息一下再出發。")
OUT = Path("work/voices")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    await C.resolve_voices()
    for name in C.VOICES:
        mp3 = OUT / f"{name}.mp3"
        vp = C.voice_params({"speaker": name, "emotion": "平常"})
        await C.edge_synth(REF, vp, mp3)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "24000", "-ac", "1",
                        str(OUT / f"{name}.wav")], check=True)
        mp3.unlink()
        print("參考聲音：", name, vp["voice"])


asyncio.run(main())

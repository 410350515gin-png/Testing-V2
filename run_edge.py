"""Edge TTS 備用版：python run_edge.py 151  或  python run_edge.py 試聽"""
import asyncio, sys
from pathlib import Path
import audiobook_core as C

ch = sys.argv[1]
script = Path("scripts") / ("試聽.txt" if ch == "試聽" else f"第{ch}章.txt")
record = ch != "試聽"
asyncio.run(C.produce_chapter(int(ch) if record else ch, script, Path("output/edge"), record=record))

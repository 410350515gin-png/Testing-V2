"""在製作進度裡記錄最終使用的引擎。python note_engine.py 151 XTTS"""
import json, sys
from pathlib import Path

ch, engine = sys.argv[1], sys.argv[2]
src = Path("output/edge/製作進度.json")
data = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {"chapters": {}}
if ch in data["chapters"]:
    data["chapters"][ch]["完整版引擎"] = engine
    data["chapters"][ch]["音檔"] = f"第{ch}章_完整版.mp3"
    data["chapters"][ch]["備用版"] = f"edge/第{ch}章_完整版.mp3"
Path("output/製作進度.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

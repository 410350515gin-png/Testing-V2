# 有聲小說多角色配音

把標好說話者的劇本放進 `scripts/第N章.txt`，push 後 GitHub Actions 會：

1. 用 Edge TTS（臺灣國語）為每個角色產生參考聲音
2. 用 ebook2audiobook（XTTS，CPU）複製聲線，逐段切換角色，輸出 `output/第N章_完整版.mp3`
3. 同時產生 Edge TTS 備用版 `output/edge/第N章_完整版.mp3`；若 ebook2audiobook 失敗，完整版改用備用版
4. 更新 `output/製作進度.json`

劇本格式：`【角色|情緒】文字`，空行為段落停頓，`#` 開頭為註解。

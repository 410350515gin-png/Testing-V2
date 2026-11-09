# 免費三聲線小說有聲書（Colab）

這個資料夾提供 iPhone 可用的 Google Colab 筆記本，將你**有權轉換**的 TXT、EPUB、PDF、DOCX 轉成中文 MP3。使用線上 Edge TTS，預設：
- 旁白：zh-TW-HsiaoChenNeural
- 宋辭：zh-TW-YunJheNeural
- 許明珠：zh-TW-HsiaoYuNeural

## 使用

1. 在 GitHub 打開 `novel_audiobook_colab.ipynb`，點選 **Open in Colab**（或在 Colab 選「GitHub」匯入筆記本）。
2. 執行第 1、2 格。上傳自己有權轉製、無 DRM 的小說。
3. 下載「角色校對表.csv」，把 `待確認對話` 修正為 `宋辭`、`許明珠`、`旁白`、`其他男聲` 或 `其他女聲`。
4. 執行第 3 格，重新上傳校對 CSV；程式會分段合成並下載 MP3。

**限制：** 中文角色辨識僅初判，沒有保證自動辨識所有對話。聲音分配不等於真正真人情緒演出。Edge TTS 需要連線，可能限流。Colab 運算資源不保證永遠免費。掃描型 PDF 無法直接擷取，需可選取文字。大型小說可能生成很久；建議先從一章試聽。

**版權：** 不在公開 GitHub 儲存小說全文；請只處理具備適當權利的內容。本程式不自動抓取第三方網站受版權保護的小說。

本工具為獨立製作的快速三聲線工作流；與 [ebook2audiobook](https://github.com/DrewThomasson/ebook2audiobook) 不同，不宣稱為其官方多角色系統。

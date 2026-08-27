# AI 股市投資決策委員會（資料驅動雲端版）

把「數據研究員 → 基本面分析師 → 風控與決策官」三代理人委員會流程，從手動複製貼上搬到 GitHub Actions 自動跑：RS 動能與部位風控數字由程式碼精算，Claude 負責論述與決策，結果推播到 LINE。

完整技術規劃背景（含跟 `ai-stock-weekly-report-bot` 的關係）見 content-hub：
https://github.com/AlbertChou20250706/content-hub/tree/main/topics/2026-08-27_ai-stock-weekly-report-line-bot

> ⚠️ 免責聲明（每次生成內容都固定附上，見 `prompts/system_prompt.md`）：
> 投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議

## 跟手動版的差異（`manual-tool/`）

`manual-tool/committee_prompt_generator.html` 是原本的手動版：離線 HTML，使用者輸入參數、產生提示詞、自己複製貼到 claude.ai、自己看結果。**保留在這個 repo 裡作為 ad hoc 查詢工具**——想臨時分析一支不在 `config/must_watch.json` 裡的標的，直接開這個 HTML 用最快。

自動化版本的關鍵差異：**RS 報酬率、止損價、每股風險、可買股數這些數字，改由 `src/lib.py` 實際抓歷史股價計算，不再讓 Claude 憑空估算**，Claude 只負責消息面彙整、基本面論述、風控結論的文字寫作，並且逐字引用程式碼算好的數字。

## 架構

```
src/lib.py            RS 區間報酬率、止損/部位規模計算（yfinance 真實股價，非 AI 估算）
src/run_committee.py  讀 config/must_watch.json（或 workflow_dispatch 的 main/compare 輸入）
                       → 呼叫 lib 算數字 → 呼叫 Claude API 生成論述
                       → 存到 reports/<symbol>_<date>.md，並寫一份到 output/<symbol>.txt
src/send_line.py      把 output/ 底下每個報告 push 給 LINE_PUSH_TARGET_IDS 裡的每個目標
src/notify_failure.py 任一步驟失敗時，發一則簡短告警訊息
```

`.github/workflows/committee-report.yml`：
- **排程**：每週一台灣時間 08:00，自動跑 `config/must_watch.json` 裡的全部標的（目前是 3706 神達、00935 野村臺灣新科技50、009816 凱基台灣TOP50）
- **手動觸發**：GitHub 網頁上 **Run workflow**，可以填 `main`／`compare` 臨時分析任意一組標的，不用等排程

## 必看代號清單（可擴充）

`config/must_watch.json`：每筆是 `{ main, compare, label }`，之後要加新的必看代號，直接在這個 JSON 加一筆即可，不用改程式碼。`config/symbol_names.json` 是代號→中文名稱對照表，同樣可自行擴充。

## 目前狀態：個人測試模式

`LINE_PUSH_TARGET_IDS` 目前應該填**你自己的 LINE User ID**（U 開頭），先驗證整條流程穩定，之後才切換成正式群組的 Group ID。

## 設定 GitHub Secrets

Settings → Secrets and variables → Actions，新增：

| Secret | 說明 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key（可跟 `ai-stock-weekly-report-bot` 共用同一組） |
| `LINE_CHANNEL_ACCESS_TOKEN` | 沿用既有 ChouAP.Cloud channel 的 long-lived token |
| `LINE_PUSH_TARGET_IDS` | 個人測試階段填自己的 User ID；正式階段換成群組 Group ID（逗號分隔多個） |

## 本機測試

```bash
cp .env.example .env   # 填入真實值，.env 已加入 .gitignore 不會被 commit
pip install -r requirements.txt
export $(cat .env | xargs)
python src/run_committee.py   # MAIN 留空 = 跑 must_watch.json 全部標的
python src/send_line.py
```

## 風控公式（與原手動版一致，見 `manual-tool/README.md` 第 3 節）

- 可容許最大虧損金額 = 總資金 × 單筆最大風險%
- 每股承受風險 = 進場價 − 止損價（止損價 = 進場價 ×（1 − 止損%））
- 可購入股數 = ⌊可容許虧損金額 ÷ 每股承受風險⌋

止損% 目前預設 8%（可調參數，非原版既有規範，是這次資料驅動化時新加的明確規則，取代原本交給 AI 自行判斷技術止損點的做法）。

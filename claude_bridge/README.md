# claude_bridge — 讓 Openclaw 用自然語言呼叫 Claude Code 整理 NAS 檔案

你已經有一個 AI Agent(Openclaw,掛 Telegram、用 MiniMax)。
這支橋接腳本讓 Openclaw 能「多一個工具」:把你的話交給 **Claude Code**,
由它在 NAS 上實際讀取/整理檔案,再把結果回傳。

```
你 (Telegram) → Openclaw 收到訊息 → 執行 claude_bridge.sh → Claude Code 動工 → 結果回傳
```

## 為什麼是這支腳本

Openclaw 要呼叫 Claude Code,最乾淨的接點就是「執行一行 shell 指令」。
這支腳本把 Claude Code 的 headless(無互動)模式包好,並加上安全限制,
所以 Openclaw 只要會跑這支腳本就行,不用懂 Claude Code 的細節。

## 前置作業

1. **在 NAS 上裝好 Claude Code**(建議用 Container Manager / Docker),
   確認 `claude` 指令可用:`claude --version`
2. **準備 Anthropic API key**(headless 模式吃 `ANTHROPIC_API_KEY` 環境變數;
   訂閱登入在 bare/headless 模式不適用)。這跟 MiniMax 是分開的帳號與費用。
3. 設定環境變數:
   ```sh
   export ANTHROPIC_API_KEY=你的key
   export CLAUDE_ROOT=/volume1/photo   # 只允許動這個資料夾
   ```

## 自己先測試

```sh
chmod +x claude_bridge.sh

# 唯讀盤點(安全,先試這個)
./claude_bridge.sh scan "這個資料夾有哪些重複或相似的檔案?"

# 實際整理(會動檔案,動手前請先開 NAS 快照)
./claude_bridge.sh apply "把副檔名是 .tmp 的暫存檔集中到一個 _待刪除 子資料夾"
```

## 接到 Openclaw

你說要直接問 Openclaw 會不會加工具。可以這樣描述給它:

> 幫我加一個工具/指令。當我要你整理 NAS 檔案時,
> 執行 `/volume1/scripts/claude_bridge/claude_bridge.sh`,
> 第一個參數用 `scan`(我只是想看)或 `apply`(我要你真的動手),
> 第二個參數是我的原話,然後把腳本輸出回傳給我。

把路徑換成你實際放的位置即可。

## 安全設計

| 機制 | 說明 |
|------|------|
| 資料夾沙盒 | 只透過 `--add-dir $CLAUDE_ROOT` 授權單一資料夾,提示也限定範圍 |
| 模式分離 | `scan` 唯讀(只給 Read/Glob/Grep);`apply` 才允許 Bash/Edit |
| 回合上限 | `CLAUDE_MAX_TURNS`(預設 8)避免無限跑、控制花費 |
| 紀錄 | 每次呼叫寫入 `claude_bridge.log` |

⚠️ **強烈建議**:第一次 `apply` 之前,先在 DSM 開啟該共享資料夾的**快照**,
萬一整理結果不滿意可以還原。先大量用 `scan` 確認 Claude 的判斷再放行 `apply`。

## 環境變數一覽

| 變數 | 必填 | 說明 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `CLAUDE_ROOT` | ✅ | 允許操作的資料夾 |
| `CLAUDE_MAX_TURNS` | | 最多代理回合,預設 8 |
| `CLAUDE_LOG` | | log 路徑,預設 `./claude_bridge.log` |

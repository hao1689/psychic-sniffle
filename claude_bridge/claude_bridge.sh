#!/bin/sh
# claude_bridge.sh — 讓你的 AI Agent(Openclaw)用一行指令呼叫 Claude Code,
# 在 NAS 上用自然語言整理檔案。
#
# 用法:
#   ./claude_bridge.sh scan  "看看 photo 資料夾有哪些重複的照片"
#   ./claude_bridge.sh apply "把 2022 年的照片搬到 photo/2022/"
#
# 第一個參數是模式:
#   scan  (預設) 唯讀:只允許讀取/搜尋,不會更動任何檔案 —— 安全,先用這個
#   apply       可寫:允許搬移/改名/刪除,會真的動檔案 —— 動手前請先開 NAS 快照
#
# 其餘參數合併成你給 Claude 的自然語言指令。
#
# 需要的環境變數:
#   ANTHROPIC_API_KEY   Claude 的 API key(headless 模式必填)
#   CLAUDE_ROOT         允許操作的資料夾,例如 /volume1/photo(必填)
# 選用:
#   CLAUDE_MAX_TURNS    最多代理回合數,預設 8(防止無限跑、控制花費)
#   CLAUDE_LOG          紀錄檔路徑,預設 ./claude_bridge.log

set -eu

# ---- 解析參數 ----
MODE="${1:-scan}"
shift 2>/dev/null || true
INSTRUCTION="$*"

if [ -z "$INSTRUCTION" ]; then
  echo "用法:$0 [scan|apply] \"你的指令\"" >&2
  exit 2
fi

# ---- 檢查環境 ----
: "${ANTHROPIC_API_KEY:?請先設定環境變數 ANTHROPIC_API_KEY}"
: "${CLAUDE_ROOT:?請先設定環境變數 CLAUDE_ROOT(允許操作的資料夾)}"
MAX_TURNS="${CLAUDE_MAX_TURNS:-8}"
LOG="${CLAUDE_LOG:-./claude_bridge.log}"

if [ ! -d "$CLAUDE_ROOT" ]; then
  echo "❌ CLAUDE_ROOT 不是資料夾:$CLAUDE_ROOT" >&2
  exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "❌ 找不到 claude 指令,請先在這個環境安裝 Claude Code" >&2
  exit 127
fi

# ---- 依模式設定權限 ----
# scan: 只給讀取類工具,且加一段守則禁止任何修改
# apply: 額外允許 Bash 與 Edit,並自動接受編輯(headless 無法互動確認)
case "$MODE" in
  scan)
    ALLOWED="Read,Glob,Grep"
    PERM="default"
    GUARD="你只能『讀取與分析』,絕對不可以建立、搬移、改名或刪除任何檔案。請只回報你的發現與建議。"
    ;;
  apply)
    ALLOWED="Read,Glob,Grep,Edit,Bash"
    PERM="acceptEdits"
    GUARD="你可以搬移/改名/整理檔案,但所有動作都必須嚴格限制在 $CLAUDE_ROOT 之內,絕不可碰此資料夾以外的東西。刪除前請優先改用搬移到子資料夾的方式。動作做完後請條列你實際做了哪些變更。"
    ;;
  *)
    echo "❌ 未知模式:$MODE(只能是 scan 或 apply)" >&2
    exit 2
    ;;
esac

# ---- 組出給 Claude 的完整提示 ----
PROMPT="你正在協助整理 Synology NAS 上的檔案。工作目錄是:$CLAUDE_ROOT。
$GUARD

使用者的指令是:
$INSTRUCTION"

# ---- 記錄並執行 ----
printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$MODE" "$INSTRUCTION" >> "$LOG"

# --bare:跳過本機設定/外掛探索,確保腳本呼叫結果一致
# --add-dir:授權存取 CLAUDE_ROOT
# --output-format text:直接拿純文字結果回傳給 Telegram
claude --bare -p "$PROMPT" \
  --add-dir "$CLAUDE_ROOT" \
  --allowedTools "$ALLOWED" \
  --permission-mode "$PERM" \
  --max-turns "$MAX_TURNS" \
  --output-format text

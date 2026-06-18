#!/usr/bin/env python3
"""
Telegram NAS Bot — 第一階段(唯讀、安全)

只用 Python 標準函式庫,不需 pip 安裝任何套件,方便在 Synology NAS 上直接跑。

功能:
  /start        說明
  /whoami       回報你的 Telegram user id(用來填 ALLOWED_USER_ID)
  /ls  <資料夾>  列出資料夾內容(唯讀)
  /scan <資料夾> 盤點報告:檔案數量、類型分布、總大小、最大檔(唯讀)

安全設計:
  - 只回應 ALLOWED_USER_ID 指定的帳號,其他人一律忽略
  - 所有路徑都被限制在 ALLOWED_ROOT 之內,無法用 .. 跳出去
  - 這個階段「完全不會」刪除或搬移任何檔案

設定(環境變數):
  TELEGRAM_BOT_TOKEN   跟 @BotFather 申請的 token(必填)
  ALLOWED_USER_ID      你的 Telegram user id(第一次可留空,用 /whoami 取得)
  ALLOWED_ROOT         允許操作的根目錄,例如 /volume1/data(預設為當前目錄)
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

API = "https://api.telegram.org/bot{token}/{method}"

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID", "").strip()
ALLOWED_ROOT = os.path.realpath(os.environ.get("ALLOWED_ROOT", os.getcwd()))


def api_call(method, params=None, timeout=60):
    """呼叫 Telegram Bot API,失敗時回傳 None 而不丟例外。"""
    url = API.format(token=TOKEN, method=method)
    data = urllib.parse.urlencode(params or {}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:  # 網路波動不該讓 bot 整個掛掉
        sys.stderr.write("api_call error (%s): %s\n" % (method, e))
        return None


def send(chat_id, text):
    # Telegram 單則訊息上限約 4096 字,過長就截斷
    if len(text) > 4000:
        text = text[:3990] + "\n…(已截斷)"
    api_call("sendMessage", {"chat_id": chat_id, "text": text})


def safe_path(arg):
    """把使用者輸入解析成絕對路徑,並確保仍在 ALLOWED_ROOT 內。"""
    arg = (arg or "").strip() or "."
    target = os.path.realpath(os.path.join(ALLOWED_ROOT, arg))
    if target == ALLOWED_ROOT or target.startswith(ALLOWED_ROOT + os.sep):
        return target
    return None


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.1f%s" % (n, unit)
        n /= 1024
    return "%.1fPB" % n


def cmd_ls(path):
    target = safe_path(path)
    if target is None:
        return "❌ 路徑超出允許範圍(只能在 %s 之內)" % ALLOWED_ROOT
    if not os.path.isdir(target):
        return "❌ 不是資料夾或不存在:%s" % target
    lines = ["📁 %s\n" % target]
    try:
        entries = sorted(os.listdir(target))
    except PermissionError:
        return "❌ 沒有權限讀取:%s" % target
    if not entries:
        return lines[0] + "(空的)"
    for name in entries[:100]:
        full = os.path.join(target, name)
        if os.path.isdir(full):
            lines.append("📂 %s/" % name)
        else:
            try:
                lines.append("📄 %s  (%s)" % (name, human_size(os.path.getsize(full))))
            except OSError:
                lines.append("📄 %s" % name)
    if len(entries) > 100:
        lines.append("…還有 %d 項未顯示" % (len(entries) - 100))
    return "\n".join(lines)


def cmd_scan(path):
    target = safe_path(path)
    if target is None:
        return "❌ 路徑超出允許範圍(只能在 %s 之內)" % ALLOWED_ROOT
    if not os.path.isdir(target):
        return "❌ 不是資料夾或不存在:%s" % target

    total_files = 0
    total_size = 0
    ext_counter = Counter()
    biggest = []  # (size, path)

    for root, _dirs, files in os.walk(target):
        for fn in files:
            full = os.path.join(root, fn)
            try:
                sz = os.path.getsize(full)
            except OSError:
                continue
            total_files += 1
            total_size += sz
            ext = (os.path.splitext(fn)[1].lower() or "(無副檔名)")
            ext_counter[ext] += 1
            biggest.append((sz, full))

    biggest.sort(reverse=True)
    top_ext = ext_counter.most_common(10)

    out = ["🔎 盤點報告:%s\n" % target]
    out.append("總檔案數:%d" % total_files)
    out.append("總大小:%s\n" % human_size(total_size))
    out.append("檔案類型 Top 10:")
    for ext, cnt in top_ext:
        out.append("  %s × %d" % (ext, cnt))
    out.append("\n最大的 5 個檔案:")
    for sz, full in biggest[:5]:
        out.append("  %s  %s" % (human_size(sz), os.path.relpath(full, target)))
    out.append("\n(此為唯讀盤點,未更動任何檔案)")
    return "\n".join(out)


HELP = (
    "🤖 NAS 助手(第一階段:唯讀)\n\n"
    "/whoami — 顯示你的 Telegram id\n"
    "/ls <資料夾> — 列出資料夾內容\n"
    "/scan <資料夾> — 盤點報告(數量/大小/類型/最大檔)\n\n"
    "目前所有指令都是唯讀的,不會更動檔案。\n"
    "可操作範圍:%s" % ALLOWED_ROOT
)


def handle(update):
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    user_id = str(msg.get("from", {}).get("id", ""))
    text = (msg.get("text") or "").strip()

    # /whoami 永遠允許,讓你能取得自己的 id 去填 ALLOWED_USER_ID
    if text.startswith("/whoami"):
        send(chat_id, "你的 Telegram user id 是:%s" % user_id)
        return

    # 安全閘門:沒設定白名單就拒絕所有人;設了就只認本人
    if not ALLOWED_USER_ID:
        send(chat_id, "⚠️ 尚未設定 ALLOWED_USER_ID。請先用 /whoami 取得 id,"
                      "填進設定後重新啟動 bot。")
        return
    if user_id != ALLOWED_USER_ID:
        # 安靜忽略陌生人,不回應以免暴露 bot 行為
        return

    if text.startswith("/start") or text.startswith("/help"):
        send(chat_id, HELP)
    elif text.startswith("/ls"):
        send(chat_id, cmd_ls(text[3:]))
    elif text.startswith("/scan"):
        send(chat_id, cmd_scan(text[5:]))
    else:
        send(chat_id, "不認得這個指令。輸入 /help 看可用指令。")


def main():
    if not TOKEN:
        sys.exit("錯誤:請先設定環境變數 TELEGRAM_BOT_TOKEN")
    print("Bot 啟動。可操作範圍:%s" % ALLOWED_ROOT)
    print("白名單 user id:%s" % (ALLOWED_USER_ID or "(未設定,僅開放 /whoami)"))

    offset = None
    while True:
        params = {"timeout": 50}
        if offset is not None:
            params["offset"] = offset
        resp = api_call("getUpdates", params, timeout=60)
        if not resp or not resp.get("ok"):
            time.sleep(3)  # 出錯就稍等再試,避免狂打 API
            continue
        for update in resp["result"]:
            offset = update["update_id"] + 1
            try:
                handle(update)
            except Exception as e:
                sys.stderr.write("handle error: %s\n" % e)


if __name__ == "__main__":
    main()

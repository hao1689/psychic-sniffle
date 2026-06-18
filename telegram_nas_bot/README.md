# Telegram NAS Bot(第一階段:唯讀)

用 Telegram 在手機上盤點 Synology NAS 上的散亂資料。
這個階段**只看不動**:不會刪除、不會搬移任何檔案,先確認整套流程能通。

## 它能做什麼

| 指令 | 說明 |
|------|------|
| `/whoami` | 顯示你的 Telegram user id(用來設定白名單) |
| `/ls <資料夾>` | 列出資料夾內容 |
| `/scan <資料夾>` | 盤點報告:檔案數量、總大小、類型分布、最大檔 |

## 安全設計

- **只回應你本人**:靠 `ALLOWED_USER_ID` 白名單,陌生人發訊息一律忽略。
- **路徑沙盒**:所有操作都被鎖在 `ALLOWED_ROOT` 之內,無法用 `..` 跳出去。
- **唯讀**:這個版本沒有任何刪除/搬移功能。

---

## 安裝步驟

### 1. 建立 Telegram Bot,取得 token
1. 在 Telegram 找 **@BotFather**
2. 送 `/newbot`,照指示命名
3. 它會給你一組 **token**(長得像 `123456:ABC-DEF...`),記下來

### 2. 把這個資料夾放到 NAS
例如放到 `/volume1/scripts/telegram_nas_bot/`。

### 3. 設定環境變數
複製範例檔並填入你的值:
```bash
cp config.example.env config.env
# 編輯 config.env,至少填 TELEGRAM_BOT_TOKEN
```

### 4. 第一次啟動,取得你的 user id
```bash
set -a; . ./config.env; set +a
python3 bot.py
```
在 Telegram 對你的 bot 送 `/whoami`,它會回覆你的 user id。
把這個 id 填進 `config.env` 的 `ALLOWED_USER_ID`,然後**重新啟動** bot。

### 5. 正式使用
重新啟動後,送:
```
/scan downloads
```
就會回報 `ALLOWED_ROOT/downloads` 的盤點結果。

---

## 在 NAS 上怎麼跑

**方法 A:Docker(推薦)**
用 Container Manager 開一個 `python:3` 容器,把這個資料夾掛進去,
再把你要整理的資料夾(例如 `/volume1/data`)以**唯讀**掛載進容器,
設好環境變數後執行 `python3 bot.py`。

**方法 B:直接跑**
若 NAS 已有 Python 3(`python3 -v` 確認),SSH 進去後直接跑即可。
要長期背景執行,可搭配 DSM「排程任務」於開機時啟動,或用 `nohup`。

---

## 下一階段(還沒做)

確認唯讀版沒問題後,可以再加:
- `/plan` — 提出分類搬移計畫(只列計畫,先不動手)
- `/move`、`/dedup` — 實際搬移、找重複檔(會加上「需回覆確認」的保護)
- 串接 Claude Code,讓它用自然語言幫你決定怎麼歸類

⚠️ 寫入功能務必在動手前先開 **DSM 快照/備份**。

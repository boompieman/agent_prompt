# agent_prompt

兩個東西住在這個 repo 裡。

## 一、AI 一人公司

在這個資料夾開 Claude Code（或 Codex），跟它說一句「**開始**」就好——
它會照 [`SETUP.md`](SETUP.md) §0 帶你走完，你只要回答問題。約 30 分鐘，
中間隨時可以喊停；下次說一聲「**Setup**」就從停的地方接下去。

第一次 clone 回來請先跑一次健檢（它會順手把技能別名建好）：

```bash
node ./offline/doctor.mjs
```

印出「已修: .claude/skills …」就關掉 Claude Code 重開一次，skills 才載得進來。
Windows 上這份 repo 裡所有 `python3 …` 一律改用 `py -3 …`，指令用 Bash 跑不要用 PowerShell。

| 檔案 | 是什麼 |
|---|---|
| `SETUP.md` | 安裝說明書兼開場劇本。§1 之後是給 AI 看的 |
| `HUB.md` | 你手上同時在跑哪幾件事。每場對話開場會先唸這張 |
| `北極星.md` | 你最想達成的目標 |
| `資料地圖.md` | 東西**在哪**：筆記庫、連結器、排程 |
| `路由.md` | 東西**該去哪**：新進來的東西放哪 |
| `機制.md` | 平常怎麼自己運作（決策三閘、重複偵測） |
| `.claude/agents/` | 員工。跑 `node ./offline/build.mjs` 開 `offline/index.html` 看有誰 |
| `skills/` | 技能本體。`.claude/skills/` 底下是指過來的別名，由 doctor 維護 |
| `.claude/hooks/` | 對話存檔、開場提醒、兩支全域設定安裝器 |
| `Sessionlog/` | 對話原文。**只留在本機，`.gitignore` 擋著不上傳** |

### 資料去哪裡

對話原文只寫進本機的 `Sessionlog/`，不上傳任何地方——`.gitignore` 已經擋掉，不要繞過它。
`.claude/hooks/install_claude_hook.py` 和 `install_codex_hook.py` 會改你的**全域**設定，
所以兩支都是 `check` 先把要寫的內容印給你看、你同意才 `install`；改之前自動備份，
`uninstall` 可以完全還原。

## 二、社群撰文 agent

[`threads_content.md`](threads_content.md) — 深度敘事型社群長文的完整撰寫規範。
`copywriter` 這位員工的 `narrative-post` 能力就是照它寫的。

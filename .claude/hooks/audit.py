#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""開場提醒：唸一次 HUB.md，哪件擱太久了就標紅。

每場對話開場由 SessionStart hook 跑，也可以手動跑來驗證 §2。
一律 exit 0——這支壞掉不該害使用者開不了對話。

  audit.py          人看的格式（手動跑、驗證 §2 用）
  audit.py --hook   SessionStart hook 用：吐 JSON，使用者看得到 systemMessage
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HUB = ROOT / "HUB.md"
FIELDS = {"現在做到哪": "now", "東西放在哪": "where", "下一步": "next", "下次碰它": "due"}


def parse(text: str):
    entries = []
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "now": "", "where": "", "next": "", "due": ""}
            entries.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^\s*-\s*\*\*(.+?)\*\*\s*[：:]\s*(.*)$", line)
        if m and m.group(1) in FIELDS:
            cur[FIELDS[m.group(1)]] = m.group(2).strip()
    return entries


def due_date(s: str):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def report(entries, today):
    """回傳 (給人看的多行字串, 逾期清單)。"""
    lines, overdue = ["【你手上在跑的事】"], []
    for e in entries:
        d = due_date(e["due"])
        late = d is not None and d < today
        if late:
            overdue.append((e, (today - d).days))
        tag = f"  ⚠ 逾期 {(today - d).days} 天" if late else (f"  （下次碰它 {d}）" if d else "")
        lines.append(f"\n· {e['title']}{tag}")
        if e["now"]:
            lines.append(f"    現在：{e['now']}")
        if e["next"]:
            lines.append(f"    下一步：{e['next']}")
    return "\n".join(lines), overdue


def main() -> int:
    as_hook = "--hook" in sys.argv

    if not HUB.exists():
        if not as_hook:
            print("（找不到 HUB.md，開場提醒跳過）")
        return 0
    entries = parse(HUB.read_text(encoding="utf-8", errors="replace"))
    if not entries:
        msg = "（HUB.md 還沒有任何主線。跟我說一句「Setup」就能建。）"
        print(json.dumps({"systemMessage": msg}, ensure_ascii=False) if as_hook else msg)
        return 0

    today = date.today()

    if as_hook:
        text, overdue = report(entries, today)
        late_lines = "\n".join(f"逾期：{e['title']}（{d} 天）" for e, d in overdue)
        print(json.dumps({
            "systemMessage": text + ("\n\n" + late_lines if late_lines else ""),
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "使用者手上在跑的事（來自 HUB.md）：\n" + text
                + ("\n\n" + late_lines if late_lines else ""),
            },
        }, ensure_ascii=False))
        return 0

    overdue = []
    print("【你手上在跑的事】")
    for e in entries:
        d = due_date(e["due"])
        late = d is not None and d < today
        if late:
            overdue.append((e, (today - d).days))
        tag = f"  ⚠ 逾期 {(today - d).days} 天" if late else (f"  （下次碰它 {d}）" if d else "")
        print(f"\n· {e['title']}{tag}")
        if e["now"]:
            print(f"    現在：{e['now']}")
        if e["next"]:
            print(f"    下一步：{e['next']}")

    if overdue:
        print("")
        for e, days in overdue:
            print(f"逾期：{e['title']}（{days} 天）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

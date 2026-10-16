#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「在別的資料夾跟 Claude 聊的對話」也存到這個資料夾來。

改的是使用者的**全域**設定（~/.claude/settings.json），所以規矩是：
  1. check   —— 把要寫進哪個檔、寫什麼，原樣印出來給他看
  2. install —— 他同意了才跑。改之前自動備份，重跑幾次都不會壞
  3. uninstall —— 還原

用法：install_claude_hook.py {check|install|uninstall}
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = Path.home() / ".claude" / "settings.json"
SCOPE = ROOT / "Sessionlog" / ".scope"
EVENT = "SessionEnd"

PY = ROOT / ".claude" / "hooks" / "py.sh"
EXTRACT = ROOT / ".claude" / "hooks" / "extract.py"
COMMAND = f'sh "{PY}" "{EXTRACT}" --since-days 2 >/dev/null 2>&1 || true'
ENTRY = {
    "hooks": [{
        "type": "command",
        "command": COMMAND,
        "statusMessage": "把這場對話存到你的公司資料夾",
        "timeout": 60,
        "async": True,
    }]
}


def load():
    if not SETTINGS.exists():
        return {}
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"⚠ 讀不到或解析不了 {SETTINGS}：{e}", file=sys.stderr)
        print("  這個檔壞掉的話，Claude 會忽略裡面全部的設定。請先修好再裝。", file=sys.stderr)
        sys.exit(1)


def mine(group) -> bool:
    """這組 hook 是我們裝的嗎？認 extract.py 的絕對路徑。"""
    return any(str(EXTRACT) in str(h.get("command", "")) for h in group.get("hooks", []))


def installed(cfg) -> bool:
    return any(mine(g) for g in cfg.get("hooks", {}).get(EVENT, []))


def cmd_check() -> int:
    cfg = load()
    print("要寫進這個檔：")
    print(f"  {SETTINGS}")
    print(f"  （{'已經存在，會合併進去，不會覆蓋你原本的設定' if SETTINGS.exists() else '還不存在，會新建'}）")
    print("\n要加的就是這一段，加在 hooks → SessionEnd 底下：\n")
    print(json.dumps(ENTRY, ensure_ascii=False, indent=2))
    print(f"\n意思是：每場對話結束，跑一次 {EXTRACT.name}，把對話存進 {ROOT.name}/Sessionlog/。")
    print(f"順手會在 {SCOPE} 記一筆 machine，之後補漏才知道要掃整台電腦。")
    if installed(cfg):
        print("\n→ 狀態：已經裝好了。再跑 install 不會重複加。")
    else:
        existing = len(cfg.get("hooks", {}).get(EVENT, []))
        print(f"\n→ 狀態：還沒裝。你原本的 {EVENT} 有 {existing} 組，會原封不動留著。")
    print("\n他同意了才跑 install。")
    return 0


def cmd_install() -> int:
    cfg = load()
    if installed(cfg):
        SCOPE.parent.mkdir(parents=True, exist_ok=True)
        SCOPE.write_text("machine\n", encoding="utf-8")
        print("已經裝好了，沒有重複加。（.scope 重寫了一次，確保是 machine）")
        return 0

    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    if SETTINGS.exists():
        backup = SETTINGS.with_suffix(f".json.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(SETTINGS, backup)
        print(f"先備份了：{backup}")

    cfg.setdefault("hooks", {}).setdefault(EVENT, []).append(ENTRY)
    SETTINGS.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCOPE.parent.mkdir(parents=True, exist_ok=True)
    SCOPE.write_text("machine\n", encoding="utf-8")
    print(f"裝好了：{SETTINGS}")
    print(f"範圍記到了：{SCOPE}（machine）")
    print("之後不管在哪個資料夾跟 Claude 聊，都會存到這裡來。不想要了跑 uninstall 就還原。")
    return 0


def cmd_uninstall() -> int:
    cfg = load()
    if not installed(cfg):
        print("本來就沒裝，沒有東西要還原。")
        return 0
    backup = SETTINGS.with_suffix(f".json.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(SETTINGS, backup)
    print(f"先備份了：{backup}")
    groups = [g for g in cfg["hooks"][EVENT] if not mine(g)]
    if groups:
        cfg["hooks"][EVENT] = groups
    else:
        del cfg["hooks"][EVENT]
        if not cfg["hooks"]:
            del cfg["hooks"]
    SETTINGS.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if SCOPE.exists():
        SCOPE.write_text("folder\n", encoding="utf-8")
    print("還原了。以後只收「在這個資料夾裡開的對話」。")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    fn = {"check": cmd_check, "install": cmd_install, "uninstall": cmd_uninstall}.get(action)
    if not fn:
        print(__doc__)
        sys.exit(2)
    sys.exit(fn())

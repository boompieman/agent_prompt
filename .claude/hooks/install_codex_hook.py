#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""讓 Codex 的對話也自動存到這個資料夾來。

⚠ 誠實話：Codex 的 hook 設定格式會隨版本改。這支的做法是
**在 ~/.codex/config.toml 後面附加一段用標記包夾的區塊**——
不解析、不重寫你原本的 TOML，所以就算格式對不上也不會弄壞你的設定。
裝完請到 Codex 的 /hooks 面板確認有出現；沒出現就跟 AI 說一聲，
退路是改用 config.toml 的 notify 機制，或純靠 extract.py 手動補。

改的是使用者的設定檔，所以規矩跟 Claude 那支一樣：
  1. check   —— 把要寫進哪個檔、寫什麼，原樣印出來給他看
  2. install —— 他同意了才跑。改之前自動備份，重跑幾次都不會壞
  3. uninstall —— 還原

用法：install_codex_hook.py {check|install|uninstall}
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path.home() / ".codex" / "config.toml"

BEGIN = "# >>> agent_prompt sessionlog BEGIN （這段由 install_codex_hook.py 管理，不要手改）"
END = "# <<< agent_prompt sessionlog END"

PY = ROOT / ".claude" / "hooks" / "py.sh"
EXTRACT = ROOT / ".claude" / "hooks" / "extract.py"

BLOCK = f"""{BEGIN}
[[hooks]]
event = "session_end"
command = ["sh", "{PY}", "{EXTRACT}", "--since-days", "2"]
description = "把這場對話存到 {ROOT.name}/Sessionlog/"
{END}"""


def read() -> str:
    try:
        return CONFIG.read_text(encoding="utf-8")
    except OSError:
        return ""


def installed(text: str) -> bool:
    return BEGIN in text


def strip_block(text: str) -> str:
    if BEGIN not in text:
        return text
    head, _, rest = text.partition(BEGIN)
    _, _, tail = rest.partition(END)
    return (head.rstrip("\n") + "\n" + tail.lstrip("\n")).strip("\n") + "\n"


def cmd_check() -> int:
    text = read()
    print("要寫進這個檔：")
    print(f"  {CONFIG}")
    print(f"  （{'已經存在，只會在後面附加，不動你原本的內容' if CONFIG.exists() else '還不存在，會新建'}）")
    print("\n要加的就是這一段：\n")
    print(BLOCK)
    print(f"\n意思是：每場 Codex 對話結束，跑一次 {EXTRACT.name}，把對話存進 {ROOT.name}/Sessionlog/。")
    print("\n⚠ 要先講清楚的兩件事：")
    print("  · Codex 的 hook 格式會隨版本改。這段是用標記包夾附加的，")
    print("    就算你這版 Codex 不認這個格式，也只是沒作用，不會弄壞你原本的設定。")
    print("  · 裝完 Codex 會再問一次要不要信任；之後如果這些檔案更新了，")
    print("    要回 /hooks 面板重新按一次信任。")
    print(f"\n→ 狀態：{'已經裝好了。再跑 install 不會重複加。' if installed(text) else '還沒裝。'}")
    print("\n他同意了才跑 install。")
    return 0


def cmd_install() -> int:
    text = read()
    if installed(text):
        print("已經裝好了，沒有重複加。")
        return 0
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        backup = CONFIG.with_suffix(f".toml.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(CONFIG, backup)
        print(f"先備份了：{backup}")
    new = (text.rstrip("\n") + "\n\n" + BLOCK + "\n") if text.strip() else (BLOCK + "\n")
    CONFIG.write_text(new, encoding="utf-8")
    print(f"裝好了：{CONFIG}")
    print("提醒他：Codex 會再問一次要不要信任，按同意。")
    print("然後到 /hooks 面板確認這條有出現——沒出現就回報，不要當成裝好了。")
    return 0


def cmd_uninstall() -> int:
    text = read()
    if not installed(text):
        print("本來就沒裝，沒有東西要還原。")
        return 0
    backup = CONFIG.with_suffix(f".toml.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(CONFIG, backup)
    print(f"先備份了：{backup}")
    CONFIG.write_text(strip_block(text), encoding="utf-8")
    print("還原了。")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    fn = {"check": cmd_check, "install": cmd_install, "uninstall": cmd_uninstall}.get(action)
    if not fn:
        print(__doc__)
        sys.exit(2)
    sys.exit(fn())

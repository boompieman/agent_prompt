#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Claude Code / Codex 的對話紀錄清洗成 Sessionlog/*.md。

檔案只寫在本機這個資料夾裡，不上傳任何地方。

用法：
  extract.py --doctor                # 只數數量，不寫任何檔
  extract.py --sample                # 挑一份（訊息數 >=6）清洗到 stdout 給使用者看
  extract.py --since-days 30         # 清洗最近 30 天
  extract.py --month 2026-08         # 清洗某一個月
  extract.py --write-readme          # 產生 Sessionlog/README.md 目錄
"""
import argparse, json, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Sessionlog"
SCOPE_FILE = OUT / ".scope"

SOURCES = [
    ("claude", Path.home() / ".claude" / "projects", "*.jsonl"),
    ("codex", Path.home() / ".codex" / "sessions", "*.jsonl"),
]


def scope() -> str:
    """folder = 只收在這個資料夾裡開的對話；machine = 整台電腦都收。"""
    try:
        v = SCOPE_FILE.read_text(encoding="utf-8").strip().split("\n")[0]
        return "machine" if v == "machine" else "folder"
    except OSError:
        return "folder"


def _text_of(content) -> str:
    """content 可能是字串，也可能是 block 陣列；只取文字，工具呼叫略過。"""
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    out = []
    for b in content:
        if not isinstance(b, dict):
            if isinstance(b, str):
                out.append(b)
            continue
        t = b.get("type")
        if t in ("text", "input_text", "output_text") and b.get("text"):
            out.append(str(b["text"]))
        elif t == "tool_use":
            out.append(f"〔工具：{b.get('name', '?')}〕")
        elif t == "tool_result":
            out.append("〔工具回覆〕")
    return "\n".join(x.strip() for x in out if x and x.strip()).strip()


def parse(path: Path):
    """回傳 (messages, cwd, started_at)。messages = [(role, text), ...]"""
    msgs, cwd, started = [], None, None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise RuntimeError(f"讀不到：{e}")
    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue  # 單行壞掉不影響整份
        if not isinstance(o, dict):
            continue
        cwd = cwd or o.get("cwd") or o.get("workdir")
        ts = o.get("timestamp") or o.get("ts") or o.get("time")
        if ts and not started:
            started = str(ts)
        # Claude Code: {"type":"user","message":{"role":..,"content":..}}
        # Codex:       {"type":"response_item","payload":{"role":..,"content":..}}
        env = o.get("message") or o.get("payload") or o
        if not isinstance(env, dict):
            continue
        role = env.get("role") or (o.get("type") if o.get("type") in ("user", "assistant") else None)
        if role not in ("user", "assistant"):
            continue
        text = _text_of(env.get("content"))
        if text:
            msgs.append((role, text))
    return msgs, cwd, started


def when(started, path: Path) -> datetime:
    if started:
        s = str(started).replace("Z", "+00:00")
        try:
            d = datetime.fromisoformat(s)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def discover():
    """掃出所有對話紀錄。回傳 (items, errors)。"""
    items, errors = [], []
    for engine, base, glob in SOURCES:
        if not base.exists():
            continue
        for p in sorted(base.rglob(glob)):
            try:
                msgs, cwd, started = parse(p)
            except RuntimeError as e:
                errors.append(f"{p}: {e}")
                continue
            if not msgs:
                continue
            items.append({
                "engine": engine, "path": p, "msgs": msgs, "cwd": cwd,
                "at": when(started, p), "n": len(msgs),
                "n_user": sum(1 for r, _ in msgs if r == "user"),
                "n_ai": sum(1 for r, _ in msgs if r == "assistant"),
            })
    return items, errors


def in_scope(it) -> bool:
    if scope() == "machine":
        return True
    cwd = it.get("cwd") or ""
    try:
        return bool(cwd) and Path(cwd).resolve() == ROOT
    except OSError:
        return False


def slug(it) -> str:
    first = next((t for r, t in it["msgs"] if r == "user"), "對話")
    s = re.sub(r"\s+", "-", first.strip())
    s = re.sub(r"[^0-9A-Za-z一-鿿\-]", "", s)[:24].strip("-")
    return s or "對話"


def render(it) -> str:
    head = [
        f"# {it['at'].astimezone().strftime('%Y-%m-%d %H:%M')} · {it['engine']}",
        "",
        f"- 來源：`{it['path']}`",
        f"- 訊息數：{it['n']}（使用者 {it['n_user']} 則／AI {it['n_ai']} 則）",
        f"- 當時的工作資料夾：`{it['cwd'] or '不明'}`",
        "",
        "---",
        "",
    ]
    body = []
    for role, text in it["msgs"]:
        body.append(f"## {'你' if role == 'user' else 'AI'}")
        body.append("")
        body.append(text)
        body.append("")
    return "\n".join(head + body)


def outname(it) -> str:
    sid = re.sub(r"[^0-9a-zA-Z]", "", it["path"].stem)[-8:] or "00000000"
    return f"{it['at'].astimezone().strftime('%Y-%m-%d')}-{it['engine']}-{slug(it)}-{sid}.md"


def write_readme() -> int:
    files = sorted(
        (p for p in OUT.glob("*.md") if p.name != "README.md"),
        key=lambda p: p.name, reverse=True,
    )
    lines = [
        "# Sessionlog — 你跟 AI 的對話存檔",
        "",
        "> 這些檔案只存在本機這個資料夾，不會上傳到任何地方。",
        f"> 共 {len(files)} 份。目錄由 `extract.py --write-readme` 產生。",
        "",
    ]
    cur = None
    for p in files:
        month = p.name[:7]
        if month != cur:
            lines += ["", f"## {month}", ""]
            cur = month
        title = p.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0].lstrip("# ").strip()
        lines.append(f"- [{title or p.stem}]({p.name})")
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(files)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--since-days", type=int)
    ap.add_argument("--month")
    ap.add_argument("--write-readme", action="store_true")
    a = ap.parse_args()

    if a.write_readme and not (a.doctor or a.sample or a.since_days or a.month):
        OUT.mkdir(parents=True, exist_ok=True)
        print(f"Sessionlog/README.md 已更新：{write_readme()} 份")
        return 0

    items, errors = discover()
    mine = [it for it in items if in_scope(it)]

    if a.doctor:
        print(json.dumps({
            "discovered": len(items),
            "in_scope": len(mine),
            "scope": scope(),
            "engines": {e: sum(1 for it in items if it["engine"] == e) for e, _, _ in SOURCES},
            "already_saved": len([p for p in OUT.glob("*.md") if p.name != "README.md"]) if OUT.exists() else 0,
            "errors": errors,
        }, ensure_ascii=False, indent=2))
        return 0

    if a.sample:
        # 判準是「訊息數 >=6」，不是「最近的」——最近那份很可能是開了就關的中斷對話。
        ok = [it for it in mine if it["n"] >= 6] or [it for it in items if it["n"] >= 6]
        if not ok:
            print("找不到訊息數 >=6 的對話，沒有東西可以當樣本。", file=sys.stderr)
            return 1
        print(render(max(ok, key=lambda it: it["at"])))
        return 0

    if a.since_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=a.since_days)
        pick = [it for it in mine if it["at"] >= cutoff]
        label = f"最近 {a.since_days} 天"
    elif a.month:
        if not re.fullmatch(r"\d{4}-\d{2}", a.month):
            print("--month 要寫成 YYYY-MM", file=sys.stderr)
            return 2
        pick = [it for it in mine if it["at"].astimezone().strftime("%Y-%m") == a.month]
        label = a.month
    else:
        ap.print_help()
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    wrote = skipped = 0
    for it in pick:
        dest = OUT / outname(it)
        if dest.exists():
            skipped += 1
            continue
        dest.write_text(render(it), encoding="utf-8")
        wrote += 1
    n = write_readme()
    print(f"{label}：找到 {len(pick)} 份，存了 {wrote} 份，略過 {skipped} 份（已經存過）。目錄共 {n} 份。")
    if errors:
        print(f"讀不到的檔案 {len(errors)} 個：")
        for e in errors[:5]:
            print(f"  · {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

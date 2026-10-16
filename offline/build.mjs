#!/usr/bin/env node
// 產生 offline/index.html：公司儀表板（員工、能力、排程範本、安裝進度）。
// ⚠ SETUP.md §4 的排程表是解析來源——改那張表的欄名或格式，這裡要同步改。
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const read = (f) => { try { return fs.readFileSync(path.join(ROOT, f), 'utf8'); } catch { return ''; } };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// ── 員工：讀 .claude/agents/*.md ─────────────────────────────
function agents() {
  const dir = path.join(ROOT, '.claude', 'agents');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith('.md')).map((f) => {
    const raw = fs.readFileSync(path.join(dir, f), 'utf8');
    const fm = raw.match(/^---\n([\s\S]*?)\n---/);
    const meta = {};
    if (fm) for (const line of fm[1].split('\n')) {
      const m = line.match(/^(\w[\w-]*):\s*(.*)$/);
      if (m) meta[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
    const id = meta.name || path.basename(f, '.md');
    // 能力：`### <id> — <一句話>`
    const abilities = [...raw.matchAll(/^###\s+([a-z0-9][a-z0-9-]*)\s*—\s*(.+)$/gm)]
      .map((m) => ({ id: `${id}.${m[1]}`, what: m[2].trim() }));
    return { id, title: meta.title || id, desc: meta.description || '', abilities };
  }).sort((a, b) => a.id.localeCompare(b.id));
}

// ── 排程範本：解析 SETUP.md §4 那張表 ───────────────────────
function templates() {
  const setup = read('SETUP.md');
  const sec = setup.split(/^## §4/m)[1];
  if (!sec) return [];
  const want = ['範本', '綁定能力／技能', '做什麼', '頻率預設', '車道', '前置連結器'];
  const rows = sec.split('\n').filter((l) => l.trim().startsWith('|')).map((l) => l.split('|').slice(1, -1).map((c) => c.trim()));
  const head = rows.findIndex((r) => want.every((w, i) => r[i] === w));
  if (head < 0) return [];
  return rows.slice(head + 2).filter((r) => r.length === want.length && r[0] && !/^-+$/.test(r[0]))
    .map((r) => Object.fromEntries(want.map((w, i) => [w, r[i]])));
}

// ── 安裝進度：跟 SETUP.md §0.6 的那段 grep 算同一件事 ────────
function progress() {
  const hub = read('HUB.md'), dm = read('資料地圖.md'), ns = read('北極星.md'), rt = read('路由.md');
  const sessionDir = path.join(ROOT, 'Sessionlog');
  const logs = fs.existsSync(sessionDir)
    ? fs.readdirSync(sessionDir).filter((f) => f.endsWith('.md') && f !== 'README.md').length : 0;
  const lines = (s) => s.split('\n');
  const hubCount = lines(hub).filter((l) => l.startsWith('## ')).length;
  const connected = lines(dm).filter((l) => /^\|/.test(l) && /(已驗證|已連線·未實測)/.test(l)).length;
  const verified = lines(dm).filter((l) => /^\|/.test(l) && /已驗證/.test(l)).length;
  const sched = (dm.split(/^## §3/m)[1] || '').split(/^### /m)[0]
    .split('\n').filter((l) => /^\| [^（排]/.test(l)).length;
  const routed = /個人化：\s*([0-9]{4}-[0-9]{2}-[0-9]{2})/.exec(rt);
  return [
    { k: '§1 記憶', ok: logs > 0, v: `${logs} 份對話` },
    { k: '§2 主線', ok: hubCount > 0 && !hub.includes('示範條目'), v: `${hubCount} 條${hub.includes('示範條目') ? '（還是範例）' : ''}` },
    { k: '§3 連結器', ok: connected > 0, v: `${connected} 個已接（實測 ${verified}）` },
    { k: '§4 排程', ok: true, v: `${sched} 顆（選配）` },
    { k: '§5 目標', ok: !ns.includes('示範'), v: ns.includes('示範') ? '還沒寫' : '已寫定' },
    { k: '§6 路由', ok: !!routed, v: routed ? `已個人化 ${routed[1]}` : '出廠預設' },
  ];
}

const A = agents(), T = templates(), P = progress();
const abilityCount = A.reduce((n, a) => n + a.abilities.length, 0);

const html = `<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>你的公司</title>
<style>
  :root{--bg:#fbfaf8;--card:#fff;--ink:#1b1a18;--dim:#6b6762;--line:#e5e1db;--ok:#1f7a4c;--wait:#9a6b12;--accent:#2f5d8a}
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17161a;--card:#201f24;--ink:#ecebe8;--dim:#a09c98;--line:#34323a;--ok:#5dd39e;--wait:#e0b050;--accent:#8ab4e0}}
  :root[data-theme="dark"]{--bg:#17161a;--card:#201f24;--ink:#ecebe8;--dim:#a09c98;--line:#34323a;--ok:#5dd39e;--wait:#e0b050;--accent:#8ab4e0}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,"Noto Sans TC","Microsoft JhengHei",sans-serif}
  .wrap{max-width:900px;margin:0 auto;padding:40px 16px 72px}
  h1{font-size:28px;margin:0 0 6px}
  .sub{color:var(--dim);margin:0 0 32px}
  h2{font-size:18px;margin:40px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
  .grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
  .card h3{margin:0 0 4px;font-size:16px}
  .card .id{font-family:ui-monospace,monospace;font-size:12px;color:var(--accent)}
  .card p{margin:8px 0 0;color:var(--dim);font-size:14px}
  ul.ab{margin:10px 0 0;padding:0;list-style:none;font-size:13px}
  ul.ab li{padding:4px 0;border-top:1px dotted var(--line)}
  ul.ab code{font-size:12px;color:var(--accent)}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
  th{color:var(--dim);font-weight:600;font-size:13px}
  .pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;border:1px solid currentColor}
  .pill.ok{color:var(--ok)} .pill.wait{color:var(--wait)}
  .scroll{overflow-x:auto}
  footer{margin-top:48px;color:var(--dim);font-size:13px}
</style></head><body><div class="wrap">
<h1>你的公司</h1>
<p class="sub">${A.length} 位員工 · ${abilityCount} 項能力 · 產生於 ${new Date().toISOString().slice(0, 10)}</p>

<h2>安裝進度</h2>
<div class="scroll"><table><tbody>
${P.map((p) => `<tr><th style="width:120px">${esc(p.k)}</th><td>${esc(p.v)}</td><td style="width:72px"><span class="pill ${p.ok ? 'ok' : 'wait'}">${p.ok ? '好了' : '還沒'}</span></td></tr>`).join('\n')}
</tbody></table></div>

<h2>員工</h2>
${A.length ? `<div class="grid">${A.map((a) => `<div class="card">
  <h3>${esc(a.title)}</h3><span class="id">${esc(a.id)}</span>
  <p>${esc(a.desc)}</p>
  ${a.abilities.length ? `<ul class="ab">${a.abilities.map((b) => `<li><code>${esc(b.id)}</code><br>${esc(b.what)}</li>`).join('')}</ul>` : ''}
</div>`).join('\n')}</div>` : '<p class="sub">還沒有員工（<code>.claude/agents/</code> 是空的）。</p>'}

<h2>排程範本（隨包附上，不會自動啟用）</h2>
${T.length ? `<div class="scroll"><table><thead><tr>${['範本', '綁定能力／技能', '做什麼', '頻率預設', '車道', '前置連結器'].map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody>
${T.map((r) => `<tr>${['範本', '綁定能力／技能', '做什麼', '頻率預設', '車道', '前置連結器'].map((k) => `<td>${esc(r[k])}</td>`).join('')}</tr>`).join('\n')}
</tbody></table></div>` : '<p class="sub">解析不到 SETUP.md §4 的表格。</p>'}

<footer>
一顆一顆問過、走完六步才建。要開哪顆跟你的助理說一聲就好。<br>
東西在哪 = <code>資料地圖.md</code>　東西該去哪 = <code>路由.md</code>　手上在跑什麼 = <code>HUB.md</code>
</footer>
</div></body></html>
`;

fs.mkdirSync(path.join(ROOT, 'offline'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'offline', 'index.html'), html);
console.log(`offline/index.html 已更新：${A.length} 位員工 / ${abilityCount} 項能力 / ${T.length} 個排程範本`);
for (const p of P) console.log(`  ${p.ok ? '●' : '○'} ${p.k}  ${p.v}`);

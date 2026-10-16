#!/usr/bin/env node
// 健檢：確認這台機器跑得動這包東西，並把 .claude/skills 的別名修好。
// 用法：node ./offline/doctor.mjs [--copy-skills]
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const WANT_COPY = process.argv.includes('--copy-skills');
const WIN = process.platform === 'win32';
const MAC = process.platform === 'darwin';

const notes = [];
const fixes = [];
const errors = [];

function run(cmd, args) {
  try {
    return execFileSync(cmd, args, { stdio: ['ignore', 'pipe', 'ignore'], encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function installHint(what) {
  const table = {
    node: { win: 'winget install OpenJS.NodeJS', mac: 'brew install node', linux: 'sudo apt install nodejs' },
    python: { win: 'winget install Python.Python.3.12', mac: 'brew install python', linux: 'sudo apt install python3' },
    git: { win: 'winget install Git.Git', mac: 'brew install git', linux: 'sudo apt install git' },
  }[what];
  return WIN ? table.win : MAC ? table.mac : table.linux;
}

// ── 1. 三個硬需求 ────────────────────────────────────────────
console.log('【環境】');
console.log(`  node      ${process.version}`);

// Windows 上 python3 常是 Microsoft Store 空殼：優先試 py -3。
let pyCmd = null;
for (const [cmd, args] of WIN ? [['py', ['-3', '-V']], ['python3', ['-V']]] : [['python3', ['-V']], ['py', ['-3', '-V']]]) {
  const out = run(cmd, args);
  if (out && /Python 3/.test(out)) {
    pyCmd = cmd === 'py' ? 'py -3' : 'python3';
    const hint = pyCmd === 'py -3' ? '  （這份文件裡的 python3 … 一律改用 py -3 …）' : '';
    console.log(`  python    ${out}${hint}`);
    break;
  }
}
if (!pyCmd) {
  errors.push(`缺 Python 3。裝它：${installHint('python')}`);
  console.log('  python    ✗ 找不到');
}

const gitV = run('git', ['--version']);
if (gitV) console.log(`  git       ${gitV}`);
else errors.push(`缺 Git。裝它：${installHint('git')}`);

if (WIN) {
  // Git Bash：本包所有指令都用 Bash 跑，不用 PowerShell。
  const bash = run('bash', ['--version']);
  if (bash) console.log(`  bash      ${bash.split('\n')[0]}`);
  else errors.push(`缺 Git Bash（指令要用 Bash 跑，不要用 PowerShell）。裝它：${installHint('git')}`);
}

const claudeV = run('claude', ['--version']);
if (claudeV) console.log(`  claude    ${claudeV}`);
else notes.push('注意：`claude` 不在 PATH（桌面版 Claude Code 的常態）。§3 改用口頭問當資料來源，並在背景裝 CLI：npm install -g @anthropic-ai/claude-code');

// ── 2. 技能別名：skills/ 是本體，.claude/skills/ 是別名 ──────
const SRC = path.join(ROOT, 'skills');
const DST = path.join(ROOT, '.claude', 'skills');
const COPY_MARKER = path.join(DST, '.copy-mode');

function copyDir(from, to) {
  fs.rmSync(to, { recursive: true, force: true });
  fs.cpSync(from, to, { recursive: true });
}

if (fs.existsSync(SRC)) {
  fs.mkdirSync(DST, { recursive: true });
  if (WANT_COPY) fs.writeFileSync(COPY_MARKER, '別名建不起來的環境改用實體副本。每次跑 doctor 會自動重新同步。\n');
  const copyMode = fs.existsSync(COPY_MARKER);

  for (const name of fs.readdirSync(SRC)) {
    if (!fs.statSync(path.join(SRC, name)).isDirectory()) continue;
    const from = path.join(SRC, name);
    const to = path.join(DST, name);
    const rel = path.join('..', '..', 'skills', name);

    if (copyMode) {
      // 實體副本：每次都重新同步，來源改了副本才跟得上。
      copyDir(from, to);
      fixes.push(`.claude/skills/${name}（實體副本已同步）`);
      continue;
    }
    let ok = false;
    try {
      ok = fs.lstatSync(to).isSymbolicLink() && fs.existsSync(to) && fs.readlinkSync(to) === rel;
    } catch { ok = false; }
    if (ok) continue;
    try {
      fs.rmSync(to, { recursive: true, force: true });
      fs.symlinkSync(rel, to, 'junction');
      fixes.push(`.claude/skills/${name}`);
    } catch {
      copyDir(from, to);
      fs.writeFileSync(COPY_MARKER, '別名建不起來，自動改用實體副本。\n');
      fixes.push(`.claude/skills/${name}（別名建不起來，改用實體副本）`);
    }
  }
} else {
  errors.push('找不到 skills/ ——技能本體不在，這包東西不完整。');
}

// ── 3. 隨包件 ────────────────────────────────────────────────
console.log('\n【隨包件】');
for (const f of ['HUB.md', '資料地圖.md', '北極星.md', '路由.md', '機制.md', 'memory/MEMORY.md', 'SETUP.md']) {
  const exists = fs.existsSync(path.join(ROOT, f));
  console.log(`  ${exists ? '✓' : '✗'} ${f}`);
  if (!exists) errors.push(`缺 ${f}`);
}
if (!fs.existsSync(path.join(ROOT, 'Sessionlog'))) fs.mkdirSync(path.join(ROOT, 'Sessionlog'), { recursive: true });

// ── 4. 結論 ──────────────────────────────────────────────────
if (fixes.length) {
  console.log(`\n已修: .claude/skills ${fixes.length} 項`);
  for (const f of fixes) console.log(`  · ${f}`);
  console.log('→ 請關掉 Claude Code 再重開一次，skills 才載得進來。');
}
for (const n of notes) console.log(`\n${n}`);
if (errors.length) {
  console.log('\n【要先處理】');
  for (const e of errors) console.log(`  · ${e}`);
  console.log('\n裝完請重開 Claude Code，再跟我說一次「開始」。');
  process.exit(1);
}
console.log(`\n健檢通過${notes.length ? '（有上面那條注意事項，但不影響繼續）' : ''}。`);

#!/usr/bin/env node
// SubMerge Pro 全功能版（TypeScript / Node）
//
// 版本：A1_II_Φ10_TypeScript_CN
// 对应 HTML 版：projects/submerge-pro/code/A1_II_Φ10/deepseek_html_20261006_d1ca99_Fix.html
//
// Node 无内置 GUI 库（Electron 会让体积膨胀到 100MB+），本版用交互式终端
// 界面覆盖与浏览器版一致的操作流：加载 → 预览条目 → 粘贴译文并应用 →
// 预览双语拆分 → 导出 SRT。
//
// 版权：Copyright (C) 2026-至今 北冥的鱼, DeepSeek
// 许可证：GPLv3
'use strict';

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const C = { reset: '\x1b[0m', bold: '\x1b[1m', dim: '\x1b[2m',
  red: '\x1b[31m', green: '\x1b[32m', yellow: '\x1b[33m', blue: '\x1b[34m', cyan: '\x1b[36m' };

const CJK_SPLIT = /([\u4e00-\u9fff]+)/;
const CJK_TEST = /[\u4e00-\u9fff]/;
const WORD_RE = /[A-Za-z0-9]+(?:'[A-Za-z]+)?/g;
const TIME_RE = /^(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})$/;
const IDX_RE = /^\[(\d+)\]\s*(.*)$/;

const isCjk = (ch) => ch >= '\u4e00' && ch <= '\u9fff';

function tokenize(text) {
  const tokens = [];
  for (const seg of text.split(CJK_SPLIT)) {
    if (!seg) continue;
    if (CJK_TEST.test(seg)) {
      for (let i = 0; i < seg.length; i += 2) tokens.push(seg.substring(i, i + 2));
    } else {
      tokens.push(...(seg.match(/[A-Za-z0-9]+(?:'[A-Za-z]+)?|\S/g) || []));
    }
  }
  return tokens;
}

function joinTokens(tokens) {
  let out = '';
  tokens.forEach((tok, i) => {
    if (i > 0) {
      const p = tokens[i - 1][tokens[i - 1].length - 1];
      const c = tok[0];
      if (!isCjk(p) && !isCjk(c)) out += ' ';
    }
    out += tok;
  });
  return out;
}

function addBoundary(s) {
  return s
    .replace(/([a-zA-Z0-9])([\u4e00-\u9fff])/g, '$1 $2')
    .replace(/([\u4e00-\u9fff])([a-zA-Z0-9])/g, '$1 $2');
}

function splitPaired(orig, trans, maxWords = 10) {
  const o = tokenize(orig);
  const t = tokenize(trans);
  const chunks = [];
  let oi = 0, ti = 0;
  while (oi < o.length || ti < t.length) {
    const oc = [], tc = [];
    let words = 0;
    while ((oi < o.length || ti < t.length) && words < maxWords) {
      const canO = oi < o.length, canT = ti < t.length;
      if (canO && canT) {
        if (words + 2 <= maxWords) { oc.push(o[oi++]); tc.push(t[ti++]); words += 2; }
        else break;
      } else if (canO) {
        if (words + 1 <= maxWords) { oc.push(o[oi++]); words++; } else break;
      } else if (canT) {
        if (words + 1 <= maxWords) { tc.push(t[ti++]); words++; } else break;
      }
    }
    chunks.push([addBoundary(joinTokens(oc)).trim(), addBoundary(joinTokens(tc)).trim()]);
  }
  return chunks.length ? chunks : [[orig, trans]];
}

function timeToMs(s) {
  const parts = s.split(':');
  if (parts.length !== 3) return 0;
  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const sp = parts[2];
  let sec, ms;
  if (sp.includes(',')) {
    const [a, b] = sp.split(',');
    sec = parseInt(a, 10);
    ms = parseInt((b + '000').slice(0, 3), 10);
  } else if (sp.includes('.')) {
    const [a, b] = sp.split('.');
    sec = parseInt(a, 10);
    ms = Math.round(parseInt((b + '00').slice(0, 2), 10) * 40);
  } else {
    sec = parseInt(sp, 10);
    ms = 0;
  }
  return (h * 3600 + m * 60 + sec) * 1000 + ms;
}

function msToTime(ms) {
  const h = Math.floor(ms / 3600000); ms %= 3600000;
  const m = Math.floor(ms / 60000); ms %= 60000;
  const s = Math.floor(ms / 1000);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`;
}

function parseSubtitle(content) {
  const clean = content.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const entries = [];
  const seen = new Set();
  for (const raw of clean.split(/\n\s*\n/)) {
    const lines = raw.split('\n').map((l) => l.trim()).filter((l) => l);
    if (lines.length < 3 || !/^\d+$/.test(lines[0])) continue;
    const m = lines[1].match(TIME_RE);
    if (!m) continue;
    const index = parseInt(lines[0], 10);
    if (seen.has(index)) continue;
    seen.add(index);
    const start = m[1].replace('.', ',');
    let end = m[2].replace('.', ',');
    if (timeToMs(start) >= timeToMs(end)) end = msToTime(timeToMs(start) + 1);
    const text = lines.slice(2).join('\n').trim();
    if (!text) continue;
    entries.push({ index, start, end, text, translated: '' });
  }
  entries.sort((a, b) => a.index - b.index);
  return entries;
}

function applyTranslation(entries, transStr) {
  const map = new Map();
  let cur = null, buf = [];
  const flush = () => { if (cur !== null) map.set(cur, buf.join('\n').trim()); };
  for (const line of transStr.split('\n')) {
    const t = line.trim();
    const m = t.match(IDX_RE);
    if (m) {
      flush();
      cur = parseInt(m[1], 10);
      buf = m[2].trim() ? [m[2].trim()] : [];
      continue;
    }
    if (cur !== null && t) buf.push(t);
  }
  flush();
  let applied = 0;
  for (const e of entries) {
    if (map.has(e.index)) { e.translated = map.get(e.index); applied++; }
  }
  return applied;
}

function exportSrt(entries, mode) {
  let out = '';
  for (const e of entries) {
    let text;
    if (mode === 'orig') text = e.text;
    else if (mode === 'trans') text = e.translated || '';
    else {
      if (e.translated && e.text) text = `${e.text}\n${e.translated}`;
      else if (e.translated) text = e.translated;
      else text = e.text;
    }
    out += `${e.index}\n${e.start} --> ${e.end}\n${text}\n\n`;
  }
  return out;
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise((res) => rl.question(q, (a) => res(a.trim())));

function banner() {
  console.log();
  console.log(C.cyan + '╔══════════════════════════════════════════════╗' + C.reset);
  console.log(C.cyan + '║' + C.reset + C.bold + '      SubMerge Pro 全功能版（TypeScript）    ' + C.reset + C.cyan + '║' + C.reset);
  console.log(C.cyan + '║' + C.reset + C.dim + '         版本 A1_II_Φ10_TypeScript_CN        ' + C.reset + C.cyan + '║' + C.reset);
  console.log(C.cyan + '╚══════════════════════════════════════════════╝' + C.reset);
}

async function main() {
  banner();
  const input = await ask('\n请输入字幕文件路径（回车退出）：');
  if (!input) { rl.close(); return; }

  const filePath = path.resolve(input);
  let content;
  try { content = fs.readFileSync(filePath, 'utf8'); }
  catch (e) { console.error(`${C.red}无法读取：${e.message}${C.reset}`); rl.close(); return; }

  const entries = parseSubtitle(content);
  if (!entries.length) { console.error(`${C.red}解析失败：未找到字幕条目${C.reset}`); rl.close(); return; }

  console.log(`${C.green}✓${C.reset} 已加载 ${entries.length} 条`);
  console.log(`\n${C.bold}条目预览（前 5 条）${C.reset}`);
  entries.slice(0, 5).forEach((e) => {
    console.log(`  ${C.dim}${e.index} ${e.start} --> ${e.end}${C.reset}  ${e.text.slice(0, 50)}`);
  });

  console.log(`\n${C.bold}粘贴译文${C.reset}（格式：[编号] 文本，空行结束）`);
  const lines = [];
  while (true) {
    const line = await ask('');
    if (!line) break;
    lines.push(line);
  }
  const applied = applyTranslation(entries, lines.join('\n'));
  if (applied) console.log(`${C.green}✓${C.reset} 已应用 ${applied} 条译文`);
  else console.log(`${C.yellow}⚠${C.reset}  未检测到 [编号] 格式`);

  const mwInput = await ask('\n每条最多词数（回车默认 10）：');
  const maxWords = parseInt(mwInput, 10) || 10;

  console.log(`\n${C.bold}双语拆分预览（前 5 组）${C.reset}`);
  let shown = 0;
  outer:
  for (const e of entries) {
    for (const [o, t] of splitPaired(e.text, e.translated, maxWords)) {
      if (shown >= 5) break outer;
      const body = t ? `${o}\n${t}` : o;
      console.log(`  ${C.dim}[${e.index}]${C.reset} ${body.replace(/\n/g, ' / ')}`);
      shown++;
    }
  }

  const modeIn = await ask('\n导出内容 1=双语 2=仅原文 3=仅译文（默认 1）：');
  const mode = modeIn === '2' ? 'orig' : modeIn === '3' ? 'trans' : 'both';
  const lang = await ask('目标语言（默认 中文）：') || '中文';

  const base = path.basename(filePath).replace(/\.(srt|bcc|txt)$/i, '');
  const outPath = path.join(path.dirname(filePath), `【已翻译-${lang}】${base}.srt`);
  try {
    fs.writeFileSync(outPath, exportSrt(entries, mode), 'utf8');
    console.log(`\n${C.green}✓${C.reset} 已导出：${outPath}`);
  } catch (e) {
    console.error(`${C.red}导出失败：${e.message}${C.reset}`);
  }

  rl.close();
}

main();

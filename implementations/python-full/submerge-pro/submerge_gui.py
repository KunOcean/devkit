#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SubMerge Pro 全功能版（Python / tkinter）

版本：A1_II_Φ10_Python_CN
对应 HTML 版：projects/submerge-pro/code/A1_II_Φ10/deepseek_html_20261006_d1ca99_Fix.html

图形界面版：加载字幕、条目预览、粘贴译文并应用、双语拆分预览、导出 SRT。

版权：Copyright (C) 2026-至今 北冥的鱼, DeepSeek
许可证：GPLv3
"""
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CJK_SPLIT = re.compile(r"([\u4e00-\u9fff]+)")
CJK_TEST = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")
TIME_RE = re.compile(
    r"^(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})$")
IDX_RE = re.compile(r"^\[(\d+)\]\s*(.*)$")
BOUND1 = re.compile(r"([a-zA-Z0-9])([\u4e00-\u9fff])")
BOUND2 = re.compile(r"([\u4e00-\u9fff])([a-zA-Z0-9])")


def is_cjk(ch):
    return "\u4e00" <= ch <= "\u9fff"


def tokenize(text):
    tokens = []
    for seg in CJK_SPLIT.split(text):
        if not seg:
            continue
        if CJK_TEST.search(seg):
            for i in range(0, len(seg), 2):
                tokens.append(seg[i:i + 2])
        else:
            tokens.extend(WORD_RE.findall(seg))
    return tokens


def join_tokens(tokens):
    out = []
    for i, tok in enumerate(tokens):
        if i > 0 and not is_cjk(tokens[i - 1][-1]) and not is_cjk(tok[0]):
            out.append(" ")
        out.append(tok)
    return "".join(out)


def add_boundary(s):
    s = BOUND1.sub(r"\1 \2", s)
    return BOUND2.sub(r"\1 \2", s)


def split_paired(orig, trans, max_words=10):
    o, t = tokenize(orig), tokenize(trans)
    chunks, oi, ti = [], 0, 0
    while oi < len(o) or ti < len(t):
        oc, tc, words = [], [], 0
        while (oi < len(o) or ti < len(t)) and words < max_words:
            can_o, can_t = oi < len(o), ti < len(t)
            if can_o and can_t:
                if words + 2 <= max_words:
                    oc.append(o[oi]); oi += 1
                    tc.append(t[ti]); ti += 1
                    words += 2
                else:
                    break
            elif can_o:
                if words + 1 <= max_words:
                    oc.append(o[oi]); oi += 1; words += 1
                else:
                    break
            elif can_t:
                if words + 1 <= max_words:
                    tc.append(t[ti]); ti += 1; words += 1
                else:
                    break
        chunks.append((add_boundary(join_tokens(oc)).strip(),
                       add_boundary(join_tokens(tc)).strip()))
    return chunks or [(orig, trans)]


def time_to_ms(s):
    parts = s.split(":")
    if len(parts) != 3:
        return 0
    h, m = int(parts[0]), int(parts[1])
    sp = parts[2]
    if "," in sp:
        a, b = sp.split(",", 1)
        sec, ms = int(a), int((b + "000")[:3])
    elif "." in sp:
        a, b = sp.split(".", 1)
        sec = int(a)
        ms = round(float((b + "00")[:2]) * 40)
    else:
        sec, ms = int(sp), 0
    return (h * 3600 + m * 60 + sec) * 1000 + ms


def ms_to_time(ms):
    h = ms // 3600000; ms %= 3600000
    m = ms // 60000; ms %= 60000
    s = ms // 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms % 1000:03d}"


def parse_subtitle(content):
    clean = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    entries, seen = [], set()
    for block in re.split(r"\n\s*\n", clean):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 3 or not re.fullmatch(r"\d+", lines[0]):
            continue
        mt = TIME_RE.match(lines[1])
        if not mt:
            continue
        idx = int(lines[0])
        if idx in seen:
            continue
        seen.add(idx)
        start = mt.group(1).replace(".", ",", 1)
        end = mt.group(2).replace(".", ",", 1)
        sm = time_to_ms(start)
        if sm >= time_to_ms(end):
            end = ms_to_time(sm + 1)
        text = "\n".join(lines[2:]).strip()
        if not text:
            continue
        entries.append({"index": idx, "start": start, "end": end,
                        "text": text, "translated": ""})
    entries.sort(key=lambda e: e["index"])
    return entries


def export_srt(entries, mode):
    out = []
    for e in entries:
        if mode == "仅原文":
            text = e["text"]
        elif mode == "仅译文":
            text = e["translated"]
        else:
            if e["translated"] and e["text"]:
                text = e["text"] + "\n" + e["translated"]
            elif e["translated"]:
                text = e["translated"]
            else:
                text = e["text"]
        out.append(f"{e['index']}\n{e['start']} --> {e['end']}\n{text}\n")
    return "\n".join(out)


class SubMergeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SubMerge Pro（Python tkinter 版）")
        self.root.geometry("1000x780")

        self.entries = []
        self.filename = ""
        self.lang = tk.StringVar(value="中文")
        self.max_words = tk.IntVar(value=10)
        self.mode = tk.StringVar(value="双语")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        f0 = ttk.Frame(self.root)
        f0.pack(fill="x", **pad)
        ttk.Button(f0, text="打开字幕文件…", command=self.open_file).pack(side="left")
        self.file_label = ttk.Label(f0, text="（未加载）", foreground="#555")
        self.file_label.pack(side="left", padx=10)

        lf = ttk.LabelFrame(self.root, text="条目预览")
        lf.pack(fill="both", expand=True, **pad)
        cols = ("index", "start", "end", "text", "trans")
        self.tree = ttk.Treeview(lf, columns=cols, show="headings", height=12)
        for c, title, w in (("index", "#", 50), ("start", "开始", 110),
                            ("end", "结束", 110), ("text", "原文", 320),
                            ("trans", "译文", 320)):
            self.tree.heading(c, text=title)
            self.tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        f2 = ttk.LabelFrame(self.root, text="译文（[编号] 文本 格式）")
        f2.pack(fill="both", **pad)
        self.trans_text = tk.Text(f2, height=6)
        self.trans_text.pack(fill="both", expand=True, padx=8, pady=4)
        ttk.Button(f2, text="应用译文", command=self.apply_translation).pack(anchor="w", padx=8, pady=4)

        f3 = ttk.LabelFrame(self.root, text="选项")
        f3.pack(fill="x", **pad)
        row = ttk.Frame(f3)
        row.pack(fill="x", padx=8, pady=4)
        ttk.Label(row, text="目标语言：").pack(side="left")
        ttk.Entry(row, textvariable=self.lang, width=12).pack(side="left")
        ttk.Label(row, text="  每条最多词数：").pack(side="left")
        ttk.Spinbox(row, from_=2, to=50, textvariable=self.max_words, width=5).pack(side="left")
        ttk.Label(row, text="  导出内容：").pack(side="left")
        ttk.Combobox(row, textvariable=self.mode, values=["双语", "仅原文", "仅译文"],
                     width=8, state="readonly").pack(side="left")

        f4 = ttk.Frame(self.root)
        f4.pack(fill="x", **pad)
        ttk.Button(f4, text="预览双语拆分", command=self.preview_split).pack(side="left")
        ttk.Button(f4, text="导出 SRT", command=self.export_srt).pack(side="left", padx=6)

        f5 = ttk.LabelFrame(self.root, text="输出")
        f5.pack(fill="both", expand=True, **pad)
        self.out_text = tk.Text(f5, height=8)
        self.out_text.pack(fill="both", expand=True, padx=8, pady=4)

    def open_file(self):
        path = filedialog.askopenfilename(
            title="选择字幕文件",
            filetypes=[("字幕", "*.srt *.bcc *.txt"), ("全部", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror("读取失败", str(e))
            return
        self.entries = parse_subtitle(content)
        if not self.entries:
            messagebox.showerror("解析失败", "未找到任何字幕条目")
            return
        self.filename = os.path.basename(path)
        self.file_label.config(text=f"{self.filename} · {len(self.entries)} 条")
        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for e in self.entries:
            self.tree.insert("", "end", values=(
                e["index"], e["start"], e["end"], e["text"][:80],
                (e["translated"] or "")[:80]))

    def apply_translation(self):
        if not self.entries:
            messagebox.showinfo("提示", "请先加载字幕文件")
            return
        text = self.trans_text.get("1.0", "end")
        mapping, cur, buf = {}, None, []
        for line in text.split("\n"):
            mt = IDX_RE.match(line.strip())
            if mt:
                if cur is not None:
                    mapping[cur] = "\n".join(buf).strip()
                cur = int(mt.group(1))
                buf = [mt.group(2).strip()] if mt.group(2).strip() else []
                continue
            if cur is not None and line.strip():
                buf.append(line.strip())
        if cur is not None:
            mapping[cur] = "\n".join(buf).strip()
        if not mapping:
            messagebox.showwarning("未检测到格式", "未检测到 [编号] 格式的译文")
            return
        applied = 0
        for e in self.entries:
            if e["index"] in mapping:
                e["translated"] = mapping[e["index"]]
                applied += 1
        self.refresh_tree()
        messagebox.showinfo("完成", f"已应用 {applied} 条译文")

    def preview_split(self):
        if not self.entries:
            return
        mw = max(2, int(self.max_words.get()))
        lines = []
        for e in self.entries:
            for orig, trans in split_paired(e["text"], e["translated"] or "", mw):
                body = orig if not trans else f"{orig}\n{trans}"
                lines.append(f"[{e['index']}] {body.strip()}")
        self.out_text.delete("1.0", "end")
        self.out_text.insert("1.0", "\n".join(lines))

    def export_srt(self):
        if not self.entries:
            messagebox.showinfo("提示", "请先加载字幕文件")
            return
        base = os.path.splitext(self.filename)[0] or "subtitle"
        path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            initialfile=f"【已翻译-{self.lang.get()}】{base}.srt",
            filetypes=[("SRT", "*.srt")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(export_srt(self.entries, self.mode.get()))
            messagebox.showinfo("完成", f"已导出：{path}")
        except OSError as e:
            messagebox.showerror("导出失败", str(e))


def main():
    root = tk.Tk()
    SubMergeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

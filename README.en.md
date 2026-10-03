[中文](README.md) | [English](README.en.md)

# AI DevKit (DevKit · Chinese Edition)

Current version: **A1_V_Φ7_Glass_CN** (full-site glassmorphism restyle)
Repository: https://github.com/bmdy1145/devkit

## Overview

DevKit is a **single-file, pure HTML** local developer utility. Open it in any modern browser and it just works: no installation, no build step, no backend dependency. All data lives in browser memory only — nothing is sent anywhere, nothing is uploaded.

The tool organises collaboration around **workflow steps**: for each step you write your inspiration (the requirement) and paste your current code; DevKit combines the step's built-in prompt template with your input into one complete instruction that you can copy in a single click and paste into any AI chat tool.

## Features

- **Workflow tabs**: 22 built-in prompt templates — Version Planning, Requirements Analysis, Security Audit, Performance Audit, Refactoring, Unit Testing, Integration Testing, Version Number Derivation, i18n Adaptation, Deployment & Operations, Performance Monitoring, Data Analysis, Accessibility Audit, Architecture Design, Security Compliance, Full Rewrite — plus a blank tab
- **Multiple projects**: project tab bar with create / switch / close; each project keeps its own tabs and editor state
- **Inspiration sync**: sync the inspiration field across tabs within a project; when turned off, other tabs are cleared
- **Combined preview**: live preview of the full instruction that will be sent to the AI, with copy, copy-requirement-only, and download-and-copy actions
- **Spec prompt**: the project's own *Specification Prompt*, copyable as a whole
- **Code editor**: synchronised line numbers, paste, copy, clear, upload / drag-and-drop import, export code (multiple extensions), and an "Evolve" action that loads DevKit's own source
- **AI result area**: paste what the AI returns and overwrite the code area in one click
- **Version history**: collapsible tree, milestone nodes expanded by default, with expand-all / collapse-all that preserve scroll position
- **Full-site glassmorphism**: translucent layers, background blur and luminous borders over a multi-layer radial glow backdrop
- **Three theme choices**: Dark glass / Light glass / Follow system, with the switcher in the top-left; chosen once in the first-run guide and remembered afterwards
- **Performance mode**: lowers preview refresh frequency (from once per second to on demand)
- **Config import / export**: export `devkit_config.json`; import supports full overwrite restore
- **Quick file rename**: pick a directory and rename files to `Deepseek_ + your text + original extension`
- **Keyboard shortcut**: `Esc` closes the topmost dialog

## Usage

1. Download `code/A1_V_Φ7/deepseek_A1_V_Φ7_Glass_CN.html`
2. Double-click to open it in a browser (Chrome / Edge or any modern browser)
3. Pick a step under "Workflow Steps" → fill in the inspiration and paste your code → click "Copy" → paste into your AI chat tool

> Note: directory selection and original-file deletion rely on the browser's File System Access API (best supported on Chromium-based browsers).

## Version Naming Scheme

The project uses a "four base layers + cyclic extension" version scheme:

| Layer | Identifier | Description |
|-------|-----------|-------------|
| 1st | Branch code (A1, A2) | Specified by the user |
| 2nd | Roman numerals (I, II, III…) | Incremented on a rewrite or major upgrade; lower layers reset |
| 3rd | Φ + number (Φ1, Φ2…) | Incremental changes on the same Roman-numeral version |
| 4th | English tag (Fix, Perf, Glass…) | Minor tweaks; appended when the change is below incremental scale, without bumping Φ |

Beyond the 4th layer the scheme cycles as `B1 → I → Ψ1 → English tag → C1 …`, e.g. `A1_I_Φ1_Fix_B1_I_Ψ1_Fix_C1`.

The project maintains two language variants in parallel. They share the same main-line version number and differ only by a trailing suffix: `_CN` (Chinese edition) and `_GLOBAL` (multilingual edition). This repository is the **Chinese edition**.

## Repository Layout

```
devkit/
├── README.md / README.en.md        # Documentation (must stay at root for GitHub to render it)
├── SECURITY.md / SECURITY.en.md    # Security policy (must stay at root for the Security tab)
├── LICENSE                          # Full text of the GPLv3 license (must stay at root)
├── index.html                       # GitHub Pages entry page, redirects to the latest version file
├── docs/
│   └── .gitkeep                     # Placeholder only (git cannot track empty folders); currently unused
├── code/
│   └── A1_V_Φ7/                     # One folder per main-line version
│       └── deepseek_A1_V_Φ7_Glass_CN.html   # Current latest (full-site glassmorphism)
└── .claude/skills/devkit-spec/      # Claude Code skill (version & collaboration spec + version templates)
```

> Only the HTML files under `code/` are versioned project artifacts; the three root documents plus `docs/` and `.claude/` are outside the version-numbering scheme.

### Pages deployment note

The site entry is the **root-level** `index.html`, which redirects to `code/A1_V_Φ7/deepseek_A1_V_Φ7_Glass_CN.html`. GitHub Pages must therefore publish from **`/ (root)`**:

> Settings → Pages → Deploy from a branch → Branch: `main` → folder **`/ (root)`** → Save

Do **not** set the publish folder to `/docs`: with `/docs`, GitHub Pages only publishes files inside the `docs/` directory, so neither the root `index.html` nor `code/` would go live, and the site would return 404.

## License

AI DevKit  Copyright (C) 2026-present  北冥的鱼, DeepSeek

This program is free software, released under GPLv3, with no warranty. You should have received a copy of the GNU General Public License.

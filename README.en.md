[中文](README.md) | [English](README.en.md)

# AI DevKit (DevKit · Chinese Edition)

Current version: **A1_V_Φ8_Mono_Fix_CN** (full-site monospace skin · two-axis light/dark × accent, six palettes)
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
- **Full-site visual skins**: the four skins share identical functional logic and differ only in the visual layer — see "Visual skins" below
- **Theme switching**: the switcher sits in the top-left; chosen once in the first-run guide and remembered afterwards. Which dimensions are available depends on the skin
- **Performance mode**: lowers preview refresh frequency (from once per second to on demand)
- **Config import / export**: export `devkit_config.json`; import supports full overwrite restore
- **Quick file rename**: pick a directory and rename files to `Deepseek_ + your text + original extension`
- **Keyboard shortcut**: `Esc` closes the topmost dialog

## Visual skins

The same functional code ships with four skins. Each is an independent single-file version; they do not affect one another:

| Version | Skin | Theme dimensions |
|---------|------|------------------|
| `A1_V_Φ8_Mono_Fix_CN` (latest) | Full-site monospace: Space Mono + JetBrains Mono, no glow, 1px hard borders, tight corners | Light/dark (dark / light / auto) × accent (matrix green / cold white / amber) — 6 palettes |
| `A1_V_Φ8_Neon_Fix_CN` | Electric neon: near-opaque panels, coloured borders, layered outer glow, no backdrop blur | Dark neon / Light neon / Follow system |
| `A1_V_Φ8_Glass_Fix_CN` | Glassmorphism: translucent layers, background blur, luminous borders | Dark glass / Light glass / Follow system |
| `A1_V_Φ8_Fix_CN` | Baseline skin (no skin; numeric theme system) | Original `theme` system |

All four belong to main line `A1_V_Φ8`, an incremental change on top of Φ7. In the version string, `Glass` / `Neon` / `Mono` are **variant markers** (they occupy no layer) while `Fix` is the actual 4th-layer English tag — this release is a cross-skin synchronised defect fix.

The previous generation `A1_V_Φ7` remains under `code/A1_V_Φ7/` with three skins (glass / neon / monospace).

## Usage

1. Pick a skin from the site home page, or download `code/A1_V_Φ8/deepseek_A1_V_Φ8_Mono_Fix_CN.html` directly
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

**Variant markers occupy no layer**: skin names (Glass / Neon / Mono) denote "parallel skins of the same version". They are variant markers rather than iteration layers, and sit after the Φ layer and before the language suffix. So in `A1_V_Φ8_Glass_Fix_CN`, `Glass` is the variant marker and `Fix` is the actual 4th-layer English tag — the version string is valid. Variant markers must not be used to express iteration (e.g. `Glass2`).

The project maintains two language variants in parallel. They share the same main-line version number and differ only by a trailing suffix: `_CN` (Chinese edition) and `_GLOBAL` (multilingual edition). This repository is the **Chinese edition**.

## Repository Layout

```
devkit/
├── README.md / README.en.md        # Documentation (must stay at root for GitHub to render it)
├── SECURITY.md / SECURITY.en.md    # Security policy (must stay at root for the Security tab)
├── LICENSE                          # Full text of the GPLv3 license (must stay at root)
├── index.html                       # GitHub Pages landing page (version picker)
├── docs/
│   └── .gitkeep                     # Placeholder only (git cannot track empty folders); currently unused
├── code/
│   ├── index.html                   # Index for /code/, lists the branches
│   ├── A1_V_Φ8/                     # Current main line (incremental change over Φ7)
│   │   ├── index.html                            # Version list for this branch
│   │   ├── deepseek_A1_V_Φ8_Mono_Fix_CN.html     # Latest: monospace + two-axis themes
│   │   ├── deepseek_A1_V_Φ8_Neon_Fix_CN.html     # Electric neon
│   │   ├── deepseek_A1_V_Φ8_Glass_Fix_CN.html    # Glassmorphism
│   │   └── deepseek_A1_V_Φ8_Fix_CN.html          # Baseline skin
│   └── A1_V_Φ7/                     # Previous main line
│       ├── index.html                            # Version list for this branch
│       ├── deepseek_A1_V_Φ7_Mono_CN.html         # Monospace + two-axis themes
│       ├── deepseek_A1_V_Φ7_Neon_CN.html         # Electric neon
│       └── deepseek_A1_V_Φ7_Glass_CN.html        # Glassmorphism
└── .claude/skills/devkit-spec/      # Claude Code skill (version & collaboration spec + version templates)
```

> Only the versioned HTML files under `code/` are project artifacts; the three root documents, the three navigation `index.html` files, `docs/` and `.claude/` are all outside the version-numbering scheme.

### Pages deployment note

The site entry is the **root-level** `index.html`. It is a **version picker** (landing page) listing the branches and a direct link to the latest version; the site is browsable level by level:

| Path | Content |
|------|---------|
| `/` | Landing page: latest-version shortcut + branch cards |
| `/code/` | Branch index (Φ8 / Φ7) |
| `/code/A1_V_Φ8/` | Version list for the current main line (four skins) |
| `/code/A1_V_Φ7/` | Version list for the previous main line (three skins) |

GitHub Pages must therefore publish from **`/ (root)`**:

> Settings → Pages → Deploy from a branch → Branch: `main` → folder **`/ (root)`** → Save

Do **not** set the publish folder to `/docs`: with `/docs`, GitHub Pages only publishes files inside the `docs/` directory, so neither the root `index.html` nor `code/` would go live, and the site would return 404.

> Also note: GitHub Pages does **not** generate directory listings. A directory without an `index.html` returns 404, which is why `code/`, `code/A1_V_Φ8/` and `code/A1_V_Φ7/` each contain an explicit `index.html`.

## License

AI DevKit  Copyright (C) 2026-present  北冥的鱼, DeepSeek

This program is free software, released under GPLv3, with no warranty. You should have received a copy of the GNU General Public License.

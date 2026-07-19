---
name: minimax-docx
license: MIT
metadata:
  version: "1.0.0"
  category: document-processing
  author: MiniMaxAI
  sources:
    - "ECMA-376 Office Open XML File Formats"
    - "GB/T 9704-2012 Layout Standard for Official Documents"
    - "IEEE / ACM / APA / MLA / Chicago / Turabian Style Guides"
    - "Springer LNCS / Nature / HBR Document Templates"
description: >
  Professional DOCX document creation, editing, and formatting using OpenXML SDK (.NET).
  Three pipelines: (A) create new documents from scratch, (B) fill/edit content in existing
  documents, (C) apply template formatting with XSD validation gate-check.
  MUST use this skill whenever the user wants to produce, modify, or format a Word document —
  including when they say "write a report", "draft a proposal", "make a contract",
  "fill in this form", "reformat to match this template", or any task whose final output
  is a .docx file. Even if the user doesn't mention "docx" explicitly, if the task
  implies a printable/formal document, use this skill.
triggers:
  - Word
  - docx
  - document
  - 文档
  - Word文档
  - 报告
  - 合同
  - 公文
  - 排版
  - 套模板
---

# minimax-docx

Create, edit, and format DOCX documents via CLI tools or direct C# scripts built on OpenXML SDK (.NET).

## Setup

**First time:** `bash scripts/setup.sh` (or `powershell scripts/setup.ps1` on Windows, `--minimal` to skip optional deps).

**First operation in session:** `scripts/env_check.sh` — do not proceed if `NOT READY`. (Skip on subsequent operations within the same session.)

### ⚠️ Windows git-bash setup pitfalls (verified 2026-07-19)

`scripts/setup.sh` detects `MINGW*` and **refuses to install .NET SDK automatically** — it falls through the `none` branch which only succeeds on Linux/macOS (Windows line: `fail "On Windows, install .NET SDK from: https://dotnet.microsoft.com/download"; return 1`). On Windows git-bash you must install the SDK yourself before `setup.sh` can finish.

**Working recipe (use Microsoft official `dotnet-install.ps1`, install to `~/.dotnet`, then run setup.sh):**

```bash
# 1. Download official install script (URL is HTTP 301-redirected — curl follows automatically)
curl -sSL "https://dot.net/v1/dotnet-install.ps1" -o /tmp/dotnet-install.ps1

# 2. Install .NET 8 SDK into %USERPROFILE%\.dotnet (does not require admin)
#    IMPORTANT: invoke via pwsh (PowerShell 7), NOT system32\powershell.exe, on git-bash.
#    System32 PowerShell 5 under MSYS silently fails (output goes nowhere, no error).
pwsh -NoProfile -ExecutionPolicy Bypass -File /tmp/dotnet-install.ps1 \
     -Channel 8.0 -InstallDir "$HOME/.dotnet"

# 3. Persist to user PATH so future git-bash sessions see it (does not affect current session)
powershell -NoProfile -Command \
  '[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\<you>\.dotnet", "User")'

# 4. Set PATH for current shell + run setup.sh (which will skip optional deps on its own)
export PATH="/c/Users/<you>/.dotnet:$PATH"
bash scripts/setup.sh
```

After setup, `env_check.sh` should report `Status: READY`.

### ⚠️ `MiniMaxAIDocx.slnx` requires .NET 9 SDK (verified 2026-07-19)

The bundled `scripts/dotnet/MiniMaxAIDocx.slnx` uses the new slnx v2 format (`<Solution>...</Solution>`) which MSBuild only recognizes starting in **.NET 9 SDK**. `setup.sh` installs .NET 8 (`--channel 8.0`) so a naive `dotnet restore MiniMaxAIDocx.slnx` fails with:

```
error MSB4068: 无法识别元素 <Solution>，或者在此上下文中不支持该元素。
```

**Workaround that doesn't require upgrading the SDK** — restore each project directly, bypassing the solution file:

```bash
export PATH="/c/Users/<you>/.dotnet:$PATH"
cd scripts/dotnet/MiniMaxAIDocx.Core && dotnet restore && dotnet build --no-restore
cd ../MiniMaxAIDocx.Cli && dotnet restore && dotnet build --no-restore
```

`dotnet run --project MiniMaxAIDocx.Cli -- <command>` still works after this — the slnx file is only used by `dotnet build`/`restore` at the solution level, not by `--project` invocations.

If you want `dotnet build` at the slnx level to work, install .NET 9 SDK alongside 8.0 (the install script's `-Channel 9.0` flag does side-by-side install).

### Verifying after install

Smoke test that the CLI actually generates a docx (catches PATH/SDK/runtime mismatches that env_check can miss):

```bash
dotnet run --project scripts/dotnet/MiniMaxAIDocx.Cli -- create \
  --type report --output /tmp/setup-smoke-test.docx --title "Setup Verify"
ls -la /tmp/setup-smoke-test.docx   # expect ~2 KB file
rm /tmp/setup-smoke-test.docx
```

See `references/windows-setup.md` for the full transcript including `dotnet --list-sdks` output, expected warning counts (Core: 24 nullable warnings / 0 errors, CLI: 0/0), the dual-copy trap (`AppData/Local/hermes/skills/minimax-docx/` and `~/.agents/skills/minimax-docx/` are two identical copies; either works for build but pick one to maintain), and a suggested upstream patch to `scripts/setup.sh`.

## Quick Start: Direct C# Path

When the task requires structural document manipulation (custom styles, complex tables, multi-section layouts, headers/footers, TOC, images), write C# directly instead of wrestling with CLI limitations. Use this scaffold:

```csharp
// File: scripts/dotnet/task.csx  (or a new .cs in a Console project)
// dotnet run --project scripts/dotnet/MiniMaxAIDocx.Cli -- run-script task.csx
#r "nuget: DocumentFormat.OpenXml, 3.2.0"

using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

using var doc = WordprocessingDocument.Create("output.docx", WordprocessingDocumentType.Document);
var mainPart = doc.AddMainDocumentPart();
mainPart.Document = new Document(new Body());

// --- Your logic here ---
// Read the relevant Samples/*.cs file FIRST for tested patterns.
// See Samples/ table in References section below.
```

**Before writing any C#, read the relevant `Samples/*.cs` file** — they contain compilable, SDK-version-verified patterns. The Samples table in the References section below maps topics to files.

## CLI shorthand

All CLI commands below use `$CLI` as shorthand for:
```bash
dotnet run --project scripts/dotnet/MiniMaxAIDocx.Cli --
```

## Pipeline routing

Route by checking: does the user have an input .docx file?

```
User task
├─ No input file → Pipeline A: CREATE
│   signals: "write", "create", "draft", "generate", "new", "make a report/proposal/memo"
│   → Read references/scenario_a_create.md
│
└─ Has input .docx
    ├─ Replace/fill/modify content → Pipeline B: FILL-EDIT
    │   signals: "fill in", "replace", "update", "change text", "add section", "edit"
    │   → Read references/scenario_b_edit_content.md
    │
    └─ Reformat/apply style/template → Pipeline C: FORMAT-APPLY
        signals: "reformat", "apply template", "restyle", "match this format", "套模板", "排版"
        ├─ Template is pure style (no content) → C-1: OVERLAY (apply styles to source)
        └─ Template has structure (cover/TOC/example sections) → C-2: BASE-REPLACE
            (use template as base, replace example content with user content)
        → Read references/scenario_c_apply_template.md
```

If the request spans multiple pipelines, run them sequentially (e.g., Create then Format-Apply).

## Pre-processing

Convert `.doc` → `.docx` if needed: `scripts/doc_to_docx.sh input.doc output_dir/`

Preview before editing (avoids reading raw XML): `scripts/docx_preview.sh document.docx`

Analyze structure for editing scenarios: `$CLI analyze --input document.docx`

## Scenario A: Create

Read `references/scenario_a_create.md`, `references/typography_guide.md`, and `references/design_principles.md` first. Pick an aesthetic recipe from `Samples/AestheticRecipeSamples.cs` that matches the document type — do not invent formatting values. For CJK, also read `references/cjk_typography.md`.

**Choose your path:**
- **Simple** (plain text, minimal formatting): use CLI — `$CLI create --type report --output out.docx --config content.json`
- **Structural** (custom styles, multi-section, TOC, images, complex tables): write C# directly. Read the relevant `Samples/*.cs` first.

CLI options: `--type` (report|letter|memo|academic), `--title`, `--author`, `--page-size` (letter|a4|legal|a3), `--margins` (standard|narrow|wide), `--header`, `--footer`, `--page-numbers`, `--toc`, `--content-json`.

Then run the **validation pipeline** (below).

## Scenario B: Edit / Fill

Read `references/scenario_b_edit_content.md` first. Preview → analyze → edit → validate.

**Choose your path:**
- **Simple** (text replacement, placeholder fill): use CLI subcommands.
- **Structural** (add/reorganize sections, modify styles, manipulate tables, insert images): write C# directly. Read `references/openxml_element_order.md` and the relevant `Samples/*.cs`.

Available CLI edit subcommands:
- `replace-text --find "X" --replace "Y"`
- `fill-placeholders --data '{"key":"value"}'`
- `fill-table --data table.json`
- `insert-section`, `remove-section`, `update-header-footer`

```bash
$CLI edit replace-text --input in.docx --output out.docx --find "OLD" --replace "NEW"
$CLI edit fill-placeholders --input in.docx --output out.docx --data '{"name":"John"}'
```

Then run the **validation pipeline**. Also run diff to verify minimal changes:
```bash
$CLI diff --before in.docx --after out.docx
```

## Scenario C: Apply Template

Read `references/scenario_c_apply_template.md` first. Preview and analyze both source and template.

```bash
$CLI apply-template --input source.docx --template template.docx --output out.docx
```

For complex template operations (multi-template merge, per-section headers/footers, style merging), write C# directly — see Critical Rules below for required patterns.

Run the **validation pipeline**, then the **hard gate-check**:
```bash
$CLI validate --input out.docx --gate-check assets/xsd/business-rules.xsd
```
Gate-check is a **hard requirement**. Do NOT deliver until it passes. If it fails: diagnose, fix, re-run.

Also diff to verify content preservation: `$CLI diff --before source.docx --after out.docx`

## Validation pipeline

Run after every write operation. For Scenario C the full pipeline is **mandatory**; for A/B it is **recommended** (skip only if the operation was trivially simple).

```bash
$CLI merge-runs --input doc.docx                                    # 1. consolidate runs
$CLI validate --input doc.docx --xsd assets/xsd/wml-subset.xsd     # 2. XSD structure
$CLI validate --input doc.docx --business                           # 3. business rules
```

If XSD fails, auto-repair and retry:
```bash
$CLI fix-order --input doc.docx
$CLI validate --input doc.docx --xsd assets/xsd/wml-subset.xsd
```

If XSD still fails, fall back to business rules + preview:
```bash
$CLI validate --input doc.docx --business
scripts/docx_preview.sh doc.docx
# Verify: font contamination=0, table count correct, drawing count correct, sectPr count correct
```

Final preview: `scripts/docx_preview.sh doc.docx`

## Critical rules

These prevent file corruption — OpenXML is strict about element ordering.

**Element order** (properties always first):

| Parent | Order |
|--------|-------|
| `w:p`  | `pPr` → runs |
| `w:r`  | `rPr` → `t`/`br`/`tab` |
| `w:tbl`| `tblPr` → `tblGrid` → `tr` |
| `w:tr` | `trPr` → `tc` |
| `w:tc` | `tcPr` → `p` (min 1 `<w:p/>`) |
| `w:body` | block content → `sectPr` (LAST child) |

**Direct format contamination:** When copying content from a source document, inline `rPr` (fonts, color) and `pPr` (borders, shading, spacing) override template styles. Always strip direct formatting — keep only `pStyle` reference and `t` text. Clean tables too (including `pPr/rPr` inside cells).

**Track changes:** `<w:del>` uses `<w:delText>`, never `<w:t>`. `<w:ins>` uses `<w:t>`, never `<w:delText>`.

**Font size:** `w:sz` = points × 2 (12pt → `sz="24"`). Margins/spacing in DXA (1 inch = 1440, 1cm ≈ 567).

**Heading styles MUST have OutlineLevel:** When defining heading styles (Heading1, ThesisH1, etc.), always include `new OutlineLevel { Val = N }` in `StyleParagraphProperties` (H1→0, H2→1, H3→2). Without this, Word sees them as plain styled text — TOC and navigation pane won't work.

**Multi-template merge:** When given multiple template files (font, heading, breaks), read `references/scenario_c_apply_template.md` section "Multi-Template Merge" FIRST. Key rules:
- Merge styles from all templates into one styles.xml. Structure (sections/breaks) comes from the breaks template.
- Each content paragraph must appear exactly ONCE — never duplicate when inserting section breaks.
- NEVER insert empty/blank paragraphs as padding or section separators. Output paragraph count must equal input. Use section break properties (`w:sectPr` inside `w:pPr`) and style spacing (`w:spacing` before/after) for visual separation.
- Insert oddPage section breaks before EVERY chapter heading, not just the first. Even if a chapter has dual-column content, it MUST start with oddPage; use a second continuous break after the heading for column switching.
- Dual-column chapters need THREE section breaks: (1) oddPage in preceding para's pPr, (2) continuous+cols=2 in the chapter HEADING's pPr, (3) continuous+cols=1 in the last body para's pPr to revert.
- Copy `titlePg` settings from the breaks template for EACH section. Abstract and TOC sections typically need `titlePg=true`.

**Multi-section headers/footers:** Templates with 10+ sections (e.g., Chinese thesis) have DIFFERENT headers/footers per section (Roman vs Arabic page numbers, different header text per zone). Rules:
- Use C-2 Base-Replace: copy the TEMPLATE as output base, then replace body content. This preserves all sections, headers, footers, and titlePg settings automatically.
- NEVER recreate headers/footers from scratch — copy template header/footer XML byte-for-byte.
- NEVER add formatting (borders, alignment, font size) not present in the template header XML.
- Non-cover sections MUST have header/footer XML files (at least empty header + page number footer).
- See `references/scenario_c_apply_template.md` section "Multi-Section Header/Footer Transfer".

## References

Load as needed — don't load all at once. Pick the most relevant files for the task.

**The C# samples and design references below are the project's knowledge base ("encyclopedia").** When writing OpenXML code, ALWAYS read the relevant sample file first — it contains compilable, SDK-version-verified patterns that prevent common errors. When making aesthetic decisions, read the design principles and recipe files — they encode tested, harmonious parameter sets from authoritative sources (IEEE, ACM, APA, Nature, etc.), not guesses.

### Scenario guides (read first for each pipeline)

| File | When |
|------|------|
| `references/scenario_a_create.md` | Pipeline A: creating from scratch |
| `references/scenario_b_edit_content.md` | Pipeline B: editing existing content |
| `references/scenario_c_apply_template.md` | Pipeline C: applying template formatting |

### C# code samples (compilable, heavily commented — read when writing code)

| File | Topic |
|------|-------|
| `Samples/DocumentCreationSamples.cs` | Document lifecycle: create, open, save, streams, doc defaults, settings, properties, page setup, multi-section |
| `Samples/StyleSystemSamples.cs` | Styles: Normal/Heading chain, character/table/list styles, DocDefaults, latentStyles, CJK 公文, APA 7th, import, resolve inheritance |
| `Samples/CharacterFormattingSamples.cs` | RunProperties: fonts, size, bold/italic, all underlines, color, highlight, strike, sub/super, caps, spacing, shading, border, emphasis marks |
| `Samples/ParagraphFormattingSamples.cs` | ParagraphProperties: justification, indentation, line/paragraph spacing, keep/widow, outline level, borders, tabs, numbering, bidi, frame |
| `Samples/TableSamples.cs` | Tables: borders, grid, cell props, margins, row height, header repeat, merge (H+V), nested, floating, three-line 三线表, zebra striping |
| `Samples/HeaderFooterSamples.cs` | Headers/footers: page numbers, "Page X of Y", first/even/odd, logo image, table layout, 公文 "-X-", per-section |
| `Samples/ImageSamples.cs` | Images: inline, floating, text wrapping, border, alt text, in header/table, replace, SVG fallback, dimension calc |
| `Samples/ListAndNumberingSamples.cs` | Numbering: bullets, multi-level decimal, custom symbols, outline→headings, legal, Chinese 一/（一）/1./(1), restart/continue |
| `Samples/FieldAndTocSamples.cs` | Fields: TOC, SimpleField vs complex field, DATE/PAGE/REF/SEQ/MERGEFIELD/IF/STYLEREF, TOC styles |
| `Samples/FootnoteAndCommentSamples.cs` | Footnotes, endnotes, comments (4-file system), bookmarks, hyperlinks (internal + external) |
| `Samples/TrackChangesSamples.cs` | Revisions: insertions (w:t), deletions (w:delText!), formatting changes, accept/reject all, move tracking |
| `Samples/AestheticRecipeSamples.cs` | 13 aesthetic recipes from authoritative sources: ModernCorporate, AcademicThesis, ExecutiveBrief, ChineseGovernment (GB/T 9704), MinimalModern, IEEE Conference, ACM sigconf, APA 7th, MLA 9th, Chicago/Turabian, Springer LNCS, Nature, HBR — each with exact values from official style guides |

Note: `Samples/` path is relative to `scripts/dotnet/MiniMaxAIDocx.Core/`.

### Markdown references (read when you need specifications or design rules)

| File | When |
|------|------|
| `references/openxml_element_order.md` | XML element ordering rules (prevents corruption) |
| `references/openxml_units.md` | Unit conversion: DXA, EMU, half-points, eighth-points |
| `references/openxml_encyclopedia_part1.md` | Detailed C# encyclopedia: document creation, styles, character & paragraph formatting |
| `references/openxml_encyclopedia_part2.md` | Detailed C# encyclopedia: page setup, tables, headers/footers, sections, doc properties |
| `references/openxml_encyclopedia_part3.md` | Detailed C# encyclopedia: TOC, footnotes, fields, track changes, comments, images, math, numbering, protection |
| `references/typography_guide.md` | Font pairing, sizes, spacing, page layout, table design, color schemes |
| `references/cjk_typography.md` | CJK fonts, 字号 sizes, RunFonts mapping, GB/T 9704 公文 standard |
| `references/cjk_university_template_guide.md` | Chinese university thesis templates: numeric styleIds (1/2/3 vs Heading1), document zone structure (cover→abstract→TOC→body→references), font expectations, common mistakes |
| `references/design_principles.md` | **Aesthetic foundations**: 6 design principles (white space, contrast/scale, proximity, alignment, repetition, hierarchy) — teaches WHY, not just WHAT |
| `references/design_good_bad_examples.md` | **Good vs Bad comparisons**: 10 categories of typography mistakes with OpenXML values, ASCII mockups, and fixes |
| `references/track_changes_guide.md` | Revision marks deep dive |
| `references/troubleshooting.md` | **Symptom-driven fixes**: 13 common problems indexed by what you SEE (headings wrong, images missing, TOC broken, etc.) — search by symptom, find the fix |
| `references/windows-setup.md` | **Windows git-bash setup recipe**: verified end-to-end transcript for installing .NET 8 SDK via official `dotnet-install.ps1`, the slnx v2 / .NET 8 MSBuild incompatibility, dual-copy trap, and a suggested upstream patch to `scripts/setup.sh`. Load when `setup.sh` reports `NOT READY` on Windows or `dotnet restore MiniMaxAIDocx.slnx` fails with `MSB4068`. |

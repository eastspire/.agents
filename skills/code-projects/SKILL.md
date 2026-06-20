---
name: code-projects
description: Map project names to their D:\code directory paths. Use when user mentions a project name (e.g. "euv", "hyperlane") and you need to know its filesystem path. Triggers on any reference to code projects under D:\code — e.g. "go to euv", "open hyperlane", "where is ltpp", "修改euv的代码".
---

# Code Projects

Map short project names to full paths under `D:\code`.

## Quick Reference

Run the lookup script:

```bash
node <skill_dir>/scripts/projects.js <name>
```

Examples:
```bash
node <skill_dir>/scripts/projects.js euv       # → D:\code\euv
node <skill_dir>/scripts/projects.js hyperlane  # → all hyperlane-* dirs
node <skill_dir>/scripts/projects.js --list     # → all projects
node <skill_dir>/scripts/projects.js --json euv # → JSON with metadata
```

## Common Projects

| Name | Path | Type |
|------|------|------|
| euv | `D:\code\euv` | Rust/WASM UI framework |
| hyperlane | `D:\code\hyperlane` | Rust web framework |
| ltpp-docs | `D:\code\ltpp-docs` | Documentation |
| LTPP | `D:\code\LTPP` | Project |
| agency-agents | `D:\code\agency-agents` | Agent collection |

## Lookup Strategy

1. Try exact match (case-insensitive)
2. Try prefix match (e.g. "hyper" matches "hyperlane")
3. Try substring match (returns all matches)
4. If ambiguous, list matches and ask user to clarify

## Notes

- The script auto-detects project type (git, Cargo, package.json) in `--json` mode
- All directories under `D:\code` are valid projects — no fixed list needed
- When user says "go to X" or "open X", resolve X to a path first

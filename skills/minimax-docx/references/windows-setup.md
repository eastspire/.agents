# Windows git-bash setup transcript (verified 2026-07-19)

What `scripts/setup.sh` does on Windows git-bash is: it detects `MINGW*`, falls through to the `none` package-manager branch, and that branch explicitly exits with `fail "On Windows, install .NET SDK from: https://dotnet.microsoft.com/download"`. So on Windows you must install the SDK yourself, then re-run setup.sh to build the .NET project.

This file is the verified end-to-end recipe. Output reproduced verbatim from a real session.

## Step 1 — Confirm nothing is installed yet

```bash
$ which dotnet
/c/Program Files/dotnet/dotnet       # the launcher exists but finds no SDK

$ dotnet --version
The command could not be loaded, possibly because:
  * You intended to execute a .NET application:
      The application '--version' does not exist.
  * You intended to execute an .NET SDK command:
      No .NET SDKs were found.
Download a .NET SDK:
https://aka.ms/dotnet-download

$ bash scripts/env_check.sh
[FAIL]    dotnet         0.0.0 (requires >= 8.0)
[FAIL]    nuget          restore failed
Status: NOT READY
```

## Step 2 — Download official install script

The URL `https://dot.net/v1/dotnet-install.ps1` returns `HTTP/1.1 301 Moved Permanently` → `https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.ps1`. `curl -L` follows it automatically.

```bash
$ curl -sSL "https://dot.net/v1/dotnet-install.ps1" -o /tmp/dotnet-install.ps1
$ ls -la /tmp/dotnet-install.ps1
-rw-r--r-- 1 14915 197609 76680  7月 19 11:54 /tmp/dotnet-install.ps1
```

If writing to `$HOME` instead of `/tmp` fails with `curl: (23) client returned ERROR on write`, use `/tmp` (Windows git-bash `~` expansion can produce a path the curl writer can't open).

## Step 3 — Install SDK 8.0 (use pwsh, NOT system32 powershell)

```bash
$ pwsh -NoProfile -ExecutionPolicy Bypass -File /tmp/dotnet-install.ps1 \
       -Channel 8.0 -InstallDir "C:/Users/14915/.dotnet"
dotnet-install: Downloaded file https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.423/dotnet-sdk-8.0.423-win-x64.zip size is 285072593 bytes.
dotnet-install: Extracting the archive.
dotnet-install: Adding to current process PATH: "C:\Users\14915\.dotnet\". ...
dotnet-install: Installed version is 8.0.423
dotnet-install: Installation finished
```

**Pitfall**: don't invoke via `powershell` (system32 PowerShell 5.1). Under MSYS git-bash it silently fails — the install log stays empty and no `.dotnet` directory is created. Use `pwsh` (PowerShell 7) which is already on PATH for most Windows dev boxes (`C:\Program Files\PowerShell\7\`).

Background install via `terminal(background=true)` also works but you must use `pwsh` and watch the log file — `powershell` backgrounded via `&` redirection hits the same silent failure.

## Step 4 — Add to PATH for current shell + persist for future shells

```bash
$ export PATH="/c/Users/14915/.dotnet:$PATH"

$ dotnet --version
8.0.423

$ dotnet --list-sdks
8.0.423 [C:\Users\14915\.dotnet\sdk]
```

To persist for all future git-bash sessions (does not affect the current shell — re-`export` if you open a new tab):

```bash
powershell -NoProfile -Command \
  '[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\14915\.dotnet", "User")'
```

(Use single-quoted PowerShell — double-quoted gets `$env` consumed by bash.)

## Step 5 — Build the project (workaround the slnx issue)

The bundled `scripts/dotnet/MiniMaxAIDocx.slnx` is .NET 9 slnx v2 format. .NET 8 MSBuild doesn't recognize `<Solution>`:

```bash
$ cd scripts/dotnet && dotnet restore MiniMaxAIDocx.slnx
... error MSB4068: 无法识别元素 <Solution>，或者在此上下文中不支持该元素。
```

**Workaround** — restore each csproj individually:

```bash
$ cd scripts/dotnet/MiniMaxAIDocx.Core && dotnet restore --verbosity quiet && \
  dotnet build --verbosity quiet --no-restore
    24 个警告        # all CS8602 nullable-reference warnings, harmless
    0 个错误
已用时间 00:00:02.43

$ cd ../MiniMaxAIDocx.Cli && dotnet restore --verbosity quiet && \
  dotnet build --verbosity quiet --no-restore
已成功生成。
    0 个警告
    0 个错误
已用时间 00:00:01.13
```

After this `dotnet run --project MiniMaxAIDocx.Cli -- <subcommand>` works normally — `--project` doesn't touch the slnx file.

## Step 6 — Verify

```bash
$ bash scripts/env_check.sh
[OK]      dotnet         8.0.423 (>= 8.0)
[OK]      project        built
[WARN]    pandoc         not found — docx_preview.sh will use fallback
[WARN]    soffice        not found — .doc files cannot be converted
[WARN]    zip            not found (optional, .NET handles DOCX natively)
[OK]      locale         zh_CN.UTF-8
[OK]      permissions    all scripts executable

Status: READY (with 3 warning(s) — optional features may be limited)
```

The 3 warnings are all optional: pandoc (preview), soffice (.doc→.docx), zip (.NET handles docx natively).

## Step 7 — Smoke test the CLI

```bash
$ cd scripts/dotnet/MiniMaxAIDocx.Cli && \
  dotnet run -- create --type report --output /tmp/setup-smoke-test.docx --title "Setup Verify"
Created report document: C:/Users/14915/AppData/Local/Temp/setup-smoke-test.docx

$ ls -la /tmp/setup-smoke-test.docx
-rw-r--r-- 1 14915 197609 2015  7月 19 12:05 /tmp/setup-smoke-test.docx

$ rm /tmp/setup-smoke-test.docx
```

A ~2 KB docx from `--type report --title X` is the success signal. If you get 0 bytes or an exception, the SDK install didn't actually take effect — re-export PATH and retry.

## Dual-copy trap

Skill lives in two identical locations on this machine:

- `C:\Users\14915\AppData\Local\hemes\skills\minimax-docx\` — the canonical install (skill_view resolves here)
- `C:\Users\14915\.agents\skills\minimax-docx\` — a duplicate with the same content

MSBuild picks whichever one the working directory resolves to. If you `cd scripts/dotnet` and `dotnet build`, the warning output will name whichever copy MSBuild found first. Functionally identical today, but if you patch one and not the other, future builds may surprise you. **Pick one and maintain only that one.**

## What setup.sh's "Windows" fallback should look like (TODO upstream)

If you can edit `scripts/setup.sh`, the `none` branch on Windows should mirror the Linux `none` branch — call `dotnet-install.ps1` directly. Suggested patch:

```bash
none)
    if [ "$OS" = "windows-git-bash" ]; then
        info "Installing .NET SDK via official install script..."
        # curl writes are unreliable to $HOME on git-bash — use /tmp
        curl -sSL "https://dot.net/v1/dotnet-install.ps1" -o /tmp/dotnet-install.ps1
        pwsh -NoProfile -ExecutionPolicy Bypass -File /tmp/dotnet-install.ps1 \
             -Channel 8.0 -InstallDir "$HOME/.dotnet"
        export PATH="$HOME/.dotnet:$PATH"
        # Persist for future sessions
        powershell -NoProfile -Command \
          "[Environment]::SetEnvironmentVariable('Path', \$env:Path + ';$(cygpath -w $HOME)/.dotnet', 'User')"
    else
        # existing Linux/macOS fallback ...
    fi
    ;;
```

Until that lands upstream, follow the manual recipe above.
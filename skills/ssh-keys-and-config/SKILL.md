---
name: ssh-keys-and-config
description: SSH keypairs and ~/.ssh/config host aliases. Publickey auth.
---

# SSH Keys and Config Management

## When to use
- Adding a newly downloaded or generated keypair to `~/.ssh` without disturbing existing keys
- Registering a host alias in `~/.ssh/config` for passwordless/quick login
- Diagnosing `Permission denied (publickey)` after a config change
- Verifying an SSH setup end-to-end without an interactive password prompt

## Procedure

### 1. Inventory and protect existing state
Before touching `~/.ssh`, snapshot hashes of every existing file. The user often has prior keys, `known_hosts`, and possibly an `agent/` dir that must not change.
```bash
shasum -a 256 ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub ~/.ssh/known_hosts ~/.ssh/known_hosts.old
ls -la ~/.ssh/
```
Re-run the same `shasum` after changes — unchanged hashes prove the existing set was untouched.

### 2. Resolve naming for the new keypair
Diff the incoming key's hash against any existing same-name key in `~/.ssh`. Three cases:
- **Different hash** → distinct keypair. Create a subdirectory (e.g. `~/.ssh/<host>/`) to hold it. Do NOT overwrite the existing same-name file.
- **Same hash** → duplicate of an existing key; skip the copy and point the config at the existing file.
- **No existing same-name** → copy as-is.

Use `cp -p` to preserve mtimes (helpful for later auditing).

**Filename can lie about algorithm.** A file named `id_rsa` may contain an ed25519 key (or vice versa). Before deciding which file to write, inspect content:
```bash
head -1 <keyfile>                          # look at the header
ssh-keygen -lf <keyfile>.pub               # reports type (RSA / ED25519 / ECDSA) + fingerprint
ssh-keygen -l -f <keyfile>                 # works on private key too
```
The fingerprint + `key type` field is what matches, not the filename.

### 3. Set permissions correctly
```bash
chmod 600 ~/.ssh/<host>/id_*        # private key
chmod 644 ~/.ssh/<host>/id_*.pub    # public key
chmod 600 ~/.ssh/config             # config must not be world-readable
```

### 4. Add the host to `~/.ssh/config`
If `~/.ssh/config` is absent, create it. When it exists, APPEND — other Host entries are likely already there.

Minimal template:
```
Host <alias>
    HostName <host-or-ip>
    User <user>
    Port <port>
    IdentityFile ~/.ssh/<subdir>/id_<type>
    IdentitiesOnly yes
```
`IdentitiesOnly yes` is critical when ssh-agent holds other keys — it forces ssh to try ONLY the listed key and stops it looping through every agent key on failure.

### 5. Verify config parsing without connecting
```bash
ssh -G <alias> | grep -E "^(hostname|user|port|identityfile|identityonly)"
```
This resolves the config and shows what ssh would actually use.

### 6. End-to-end auth test (no password prompt)
```bash
ssh -v -o BatchMode=yes -o ConnectTimeout=10 <alias> exit 2>&1 | tail -40
```
- `-v`: shows key offerings and host key matching
- `BatchMode=yes`: refuses to ask for password — fails fast if auth can't complete
- `exit`: forces a clean remote exit after auth so you don't drop into a shell
- `tail -40`: drops the kex noise

Key markers to look for in the output:
- `Will attempt key: <path>` and `Offering public key: <path> explicit` — confirms `IdentityFile` is being used
- `Host '<alias>' is known and matches` — host key trusted
- `Permission denied (publickey,…)` — config worked, server rejected the key (server-side issue; see Pitfalls)
- `Connection refused` / `Connection timed out` — network/host issue, not auth

## Pitfalls

**Never overwrite an existing key in `~/.ssh/` without explicit confirmation.** Same-name keys almost always differ (different hash) and the user usually wants both. Always diff the hash first; on conflict, default to a subdirectory layout and ASK before any path that would replace an existing file. The macOS sandbox approval gate will catch writes under `~/.ssh/` regardless — treat it as confirmation, not as blanket permission to overwrite.

**Don't auto-create backups the user didn't ask for.** The user may explicitly say "覆盖" (overwrite) meaning "delete the old, replace with new, no backup." Making a backup first without asking is overreach — they will tell you to delete it later. ASK before backing up an existing file the user has already agreed to replace. If you do create a backup, name it so it's obvious and easy to clean up, and tell the user where it is.

**Whether to keep `.pub` is the user's call, not yours.** The `.pub` file is only useful for two things: writing to a server's `authorized_keys`, and fingerprint auditing. If the server is independently backed up or the key is single-purpose, the user may want to delete `.pub` to keep only the private key. Don't assume both must stay — offer and let them decide.

**`Permission denied (publickey)` with a correct client config is almost always server-side, not client-side.** The client offered the right key, the server said no. The fix is to install the matching public key on the server's `~/.ssh/authorized_keys` for the correct user (and remember the target user may not be `root`). Print `cat ~/.ssh/<host>/id_*.pub` and hand the single line to whoever manages the server. Do NOT loop on client-side changes.

**`IdentitiesOnly yes` may NOT appear in `ssh -G` output** even when set — known OpenSSH quirk. The rule still applies at connection time; do not conclude it is missing because the grep returned nothing.

**`known_hosts` host key mismatches abort before auth.** If the server was rebuilt, `known_hosts` has the old fingerprint and SSH refuses to connect. Confirm the new fingerprint out-of-band, then `ssh-keygen -R <host>` to clear it. Never blindly accept an unknown host key.

**"Move" almost never means "delete the source".** When the user says move a key from `~/Downloads` into `~/.ssh`, copy it and ASK before any `rm` of the original. Same applies to "install this key" — they usually want both the source and the installed copy until they've confirmed the install works.

**`BatchMode=yes` is the only honest end-to-end test.** An interactive `ssh <alias>` that drops into a shell proves nothing about key auth — it could have fallen back to password. Always include `BatchMode=yes` so a password prompt becomes a real, visible failure.

**Ask before guessing host-specific unknowns.** Username, port, and key naming are user decisions, not yours. Default to asking rather than picking a common value silently — a wrong guess wastes a round trip and can trigger server-side lockouts.

**macOS approval gate fires per write under sensitive paths.** Plan to receive exactly one confirmation per sensitive write; batch independent writes into one terminal call when possible to minimize prompts.
#!/usr/bin/env python3
"""Set a GitHub Actions repo secret via the REST API.

GitHub requires the secret value to be sealed-box encrypted with the repo's
public X25519 key. Fetches the public key per-repo (never cache across repos),
encrypts the value, PUTs it. Returns the new SHA on success.

Usage:
    secret-encryption.py REPO SECRET_NAME TOKEN_VALUE [GITHUB_TOKEN]

Environment:
    GITHUB_TOKEN    default token source if arg not given

Requires: pynacl  (`pip3 install pynacl`)
"""
import base64, json, os, sys, urllib.request

try:
    from nacl import encoding, public
except ImportError:
    sys.stderr.write("pynacl not installed. Run: pip3 install pynacl\n")
    sys.exit(2)

if len(sys.argv) < 4:
    sys.stderr.write("usage: secret-encryption.py REPO SECRET_NAME TOKEN_VALUE [GITHUB_TOKEN]\n")
    sys.exit(2)

repo, secret_name, secret_value = sys.argv[1], sys.argv[2], sys.argv[3]
gh_token = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("GITHUB_TOKEN")
if not gh_token:
    sys.stderr.write("GITHUB_TOKEN not set\n")
    sys.exit(2)

# 1) fetch repo's public key
req = urllib.request.Request(
    f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
    headers={"Authorization": f"Bearer {gh_token}",
             "Accept": "application/vnd.github+json"})
key = json.loads(urllib.request.urlopen(req, timeout=15).read())
if "key" not in key or "key_id" not in key:
    sys.stderr.write(f"unexpected public-key response: {key}\n")
    sys.exit(1)

# 2) encrypt with sealed box
pk = public.PublicKey(base64.b64decode(key["key"]))
sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
encrypted = base64.b64encode(sealed).decode("utf-8")

# 3) PUT the encrypted secret
req = urllib.request.Request(
    f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}",
    method="PUT",
    headers={"Authorization": f"Bearer {gh_token}",
             "Content-Type": "application/json",
             "Accept": "application/vnd.github+json"},
    data=json.dumps({
        "encrypted_value": encrypted,
        "key_id": key["key_id"],
    }).encode("utf-8"))
try:
    urllib.request.urlopen(req, timeout=15).read()
except urllib.error.HTTPError as e:
    sys.stderr.write(f"PUT failed: HTTP {e.code} {e.reason}\n")
    sys.exit(1)

print(f"set {secret_name} on {repo} (key_id {key['key_id']})")
# Auto-starting the gateway without systemd

The intended path:

```bash
hermes gateway install
systemctl --user enable --now hermes-gateway
```

This requires a working user systemd. Many environments (containers, some VPS images, WSL without `systemd=true`, Docker hosts) report instead:

```
Failed to connect to bus: No medium found
✗ User gateway service is stopped
  Run: hermes gateway start
```

`hermes gateway install` writes a `--user` unit; without a reachable user D-Bus it cannot start. **Don't try to debug systemd** — pick a different boot mechanism.

## Recommended fallback: `@reboot` cron

Cron runs as an independent daemon (`crond`); it does NOT need user systemd, D-Bus, or `loginctl enable-linger`. The `@reboot` schedule is built in.

### 1. Write a starter script

`/usr/local/bin/hermes-gateway-start.sh`:

```bash
#!/bin/bash
# Wait for network/DNS (Feishu WebSocket and friends need outbound).
for i in 1 2 3 4 5 6 7 8 9 10; do
  ping -c1 -W2 open.feishu.cn >/dev/null 2>&1 && break
  sleep 3
done

# Use the Hermes-bundled venv python; no PATH dependency.
exec /usr/local/lib/hermes-agent/venv/bin/python \
  /usr/local/lib/hermes-agent/hermes gateway run
```

```bash
chmod +x /usr/local/bin/hermes-gateway-start.sh
```

### 2. Install the cron job

```bash
crontab -e
# add:
@reboot /usr/local/bin/hermes-gateway-start.sh >> /var/log/hermes-gateway.log 2>&1
```

### 3. Verify after reboot

```bash
sudo reboot
# wait for boot, then:
ps aux | grep -E "hermes gateway" | grep -v grep
tail -20 /var/log/hermes-gateway.log
hermes gateway status
```

## Container alternative

If you're inside Docker, bake the gateway into the image's `CMD`:

```dockerfile
CMD ["/usr/local/lib/hermes-agent/venv/bin/python",
     "/usr/local/lib/hermes-agent/hermes", "gateway", "run"]
```

Container restart = gateway restart. Combined with the host's `--restart=unless-stopped`, this is the most reliable option.

## SysV init (rare)

Some hosts preserve `/etc/rc.local`. To use it:

```bash
ls -la /etc/rc.local /etc/rc.d/rc.local 2>/dev/null
```

If present, add before `exit 0`:

```bash
/usr/local/bin/hermes-gateway-start.sh >> /var/log/hermes-gateway.log 2>&1 &
```

If absent but SysV init compat is available, drop a script in `/etc/init.d/` and run `update-rc.d hermes-gateway defaults`.

## Detecting which path to use

```bash
# Will hermes's own install work?
systemctl --user status hermes-gateway 2>&1 | head -3
loginctl show-user $(whoami) | grep Linger
ls -la /run/user/$(id -u)/bus 2>&1
```

- All three return usable values → use `hermes gateway install`.
- `Failed to connect to bus` → use `@reboot` cron fallback.
- Inside a container without `systemd=true` → bake into `CMD`.

## Pitfalls specific to the cron fallback

- **PATH inside cron is empty**. The starter script must use absolute paths to `python`, `hermes`, and `uv`. Don't rely on `hermes` being on PATH.
- **Race with network bring-up**. The retry loop in the starter script handles the case where the network interface isn't up yet at boot.
- **One-instance enforcement**. The gateway uses a lockfile (`~/.hermes/gateway.lock`) so accidental double-starts are safe — `hermes gateway run` will refuse if another instance is alive.

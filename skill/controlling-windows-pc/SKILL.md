---
name: controlling-windows-pc
description: Use when the user asks to control, inspect, or automate their Windows PC from this phone — run commands on it, screenshot its desktop, move/click the mouse, type text, list or focus windows, launch or kill apps, read/write/transfer files, drive its browser, or check/fix the bridge daemon, logs, screen-share channel, LAN mode, autostart and lock-screen hardening.
keywords: [pcc, windows, remote, remote-control, screenshot, mouse, keyboard, powershell, clipboard, playwright, pcrelay, relay, agent_bridge, supervisor, client_relay, tailscale, ssh, winctl, rdp, rustdesk]
tools: [shell, local_shell, read_file, write_file, edit_file, search, view_image]
---

# Controlling a Windows PC from this phone

## Overview

Two live channels to the user's Windows machine. **Use A unless it's dead.**

| | A. `pcc` (relay) | B. `winctl` (SSH) |
|---|---|---|
| Works from anywhere | yes (4G/5G) | needs Tailscale or same WiFi |
| Command / files / keys | all | all |
| Desktop screenshot | yes (~2 s) | no |
| Best for | almost everything | stable shell, big transfers, when relay is down |

Toolkit lives at `/workspace/phone-control-pc` (also on GitHub: `fu-anxiang/agentphone-control-pc`).
`pcc` is installed at `/usr/local/bin/pcc`; config in `~/.pcc.env` (two 32-bit room tokens).

## First move, every session

```sh
pcc conf      # are the tokens there?
pcc diag      # 10-point health check: relay / info / session / daemon / channels / startup / screenshot / shell / fs
```

All green → work directly. Any red → see **Repair** below. Do not guess.

## Quick reference

```sh
pcc info | session | health          # host, resolution, lock state, idle, relay health
pcc sh '<PowerShell>'                # stdout+stderr+exit code come back
pcc shot [file] [max_width]          # full desktop JPEG
pcc move <x> <y> | --norm 0.5 0.5    # pixels by default
pcc click [left|right|middle] [n] [x y] ; pcc dblclick ; pcc scroll -120 ; pcc drag x1 y1 x2 y2
pcc type "你好"                       # Unicode, CJK works
pcc key enter  |  pcc key c ctrl     # combos
pcc win list ; pcc win focus <title> ; pcc win click <title> [fx] [fy]
pcc app start notepad.exe ; pcc app kill <pid|name>
pcc fs ls|read|write|mkdir|rm ; pcc fs get <remote> <local> ; pcc fs put <local> <remote>
pcc clip get ; pcc clip set "text"
pcc pw goto url=… ; pcc pw fill selector=#kw value=… ; pcc pw eval js=… ; pcc pw screenshot
pcc pwscript 'await page.title()'
pcc raw '{"m":"shell","p":{"cmd":"hostname"}}'
```

Ops (the daemon side):

```sh
pcc svc status|restart|start   # stop needs --yes: it kills the channel you're talking through
pcc logs [bridge|view|supervisor|all] -n 50 -g 关键字
pcc view status|url|qr         # screen-share channel
pcc room                       # compare PC's ROOM.txt with local tokens
pcc lan status|start|stop      # LAN direct :8765, smoother on same WiFi
pcc startup status|install|remove
pcc nolock status|apply        # apply pops UAC on the PC — user must click 是
pcc net
```

## The four traps (all cost real debugging time)

1. **Parameter names are non-obvious and fail silently.**
   `input.type` reads `value` (not `text`); `focus` reads `match` (not `title`);
   click count is `count` (not `n`); clipboard write is `set`; `fs.write` takes `content`;
   `fs` actions are `list`/`read`/`write`/`mkdir`/`delete`; scroll is `scroll` (not `wheel`).
   Wrong name → `{"ok":true}` and **nothing happens**. `pcc` already handles this — only matters
   when writing raw calls via `pcc raw` or `pcc pwscript`.
2. **`shell` steals foreground focus** (it spawns a PowerShell console). Chain
   "focus window → click → type" in one sequence; never interleave `shell`.
   Prefer `pcc win click <title> fx fy` which focuses *and* clicks in a single call.
3. **`pw` drives a headless Chrome** — its own page, not the visible desktop. SendInput can't
   reach it. To fill a web form use `pcc pw fill`; to type into a visible window use `pcc type`.
4. **Wide screenshots need downscaling**: `pcc shot /tmp/x.jpg 1280`. 3840×2160 raw is slow and large.

## Lock screen (Windows security boundary, not a bug)

`pcc session` → `locked: true` means desktop capture and mouse/keyboard are **dropped by the OS**
(`session_locked`). Still working: `shell`, `app`, `fs`, `clip(set)`, `pw`, `pwscript`.

The fix is "don't let it lock", not "bypass it":

```sh
pcc awake on        # 20s SetThreadExecutionState + 1px mouse jiggle when idle ≥45s
pcc nolock apply    # disable screensaver / inactivity lock (UAC prompt on the PC)
```

## Credentials (paths only — never paste secrets into replies or commits)

| What | Where |
|---|---|
| Relay room tokens | `~/.pcc.env` (written by `pcc init`) |
| GitHub PAT + repo + key paths | `~/.config/pcc/secrets.env` (600) |
| GitHub SSH key (works) | `~/.ssh/id_ed25519` |
| Repo deploy key (backup) | `~/.ssh/gh_agentphone_deploy` |
| PC-side bridge dir | `C:/Users/24335/Documents/for_phone/pcremote` |

```sh
set -a; . ~/.config/pcc/secrets.env; set +a    # then $GITHUB_TOKEN, $GH_OWNER, $GH_REPO
```

The PAT has no expiry and has been exposed in chat before — if it's ever misused or the repo
starts rejecting it, tell the user to revoke at `https://github.com/settings/tokens?type=beta`
and generate a fresh one with an expiry. Never write the token into a tracked file: repo has
`.gitignore` entries for `config.json`, `ROOM.txt`, `.pcc.env`, `logs/`, `dist/`.

## Repair playbook

| Symptom | Do |
|---|---|
| `电脑离线 / pc_disconnected` | `pcc svc status`; if dead → `pcc svc restart` (detached, survives the kill-tree); then `pcc info` |
| `电脑端报错：None` or silent no-op | wrong parameter name — check the table in trap 1 |
| `pc_offline` but daemon looks alive | tokens don't match: `pcc room` compares PC's `ROOM.txt` vs local |
| `404 / 1010 / 403` | relay issue — `pcc health`; 1010 = blocked UA (only if writing raw HTTP) |
| Screenshot huge/slow | add `max_width` (1280) |
| `pcc init` can't parse | paste **both** lines from the PC banner at once, or give two bare tokens |
| Relay dead entirely | fall back to channel B: `winctl test` |

**`pcc svc stop` kills the channel you're using.** It requires `--yes` on purpose; prefer
`pcc svc restart`. Never stop the daemon while the user isn't physically at the PC.

## After changing code

```sh
cp bin/pcc /tmp/pccmod.py     # suites import from this fixed path
python3 dev/suite_real.py     # 24 interface tests
python3 dev/suite_ops.py      # 9 ops commands
```

Both must be 33/33 green before pushing. Then `git push origin main` (see `docs/PUBLISH.md`).

## Reference

- `docs/PROTOCOL.md` — every method with its *real* parameter names and error codes.
- `relay/README.md` — the Cloudflare Pages + Durable Object relay source; deploy your own.
- `win/agent_bridge.py` + `win/install-bridge.ps1` — drop-in bridge if the official client is gone.
- `docs/OPS.md`, `docs/WINDOWS.md`, `docs/SSH-TAILSCALE.md`, `docs/PUBLISH.md`.

# slither.io Bot Control — Chromium Extension

Auto-detect your game server and control slither.io bots from your browser.

## Install

1. Open Chrome/Edge/Brave → `chrome://extensions`
2. Enable **Developer mode** (top right)
3. **Load unpacked** → select the `extension` folder
4. Pin the extension to your toolbar

## Usage

1. Play slither.io in a tab
2. Click the extension icon
3. Set **Groups** (× 4 bots each)
4. Hit **▶ Start** — bots connect, authenticate, and steer

### Follow Me

Toggle **Follow me** on — the extension intercepts your snake's position from the game's WebSocket and auto-updates the target. Bots chase your snake in real time with 400ms throttle.

### Manual mode

Not on slither.io? Click **Manual server config** to type IP/port/path.

## Prerequisites

`main.py` must be running on `doubleaaguy.duckdns.org:8081`.

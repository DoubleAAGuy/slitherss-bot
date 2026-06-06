# slither.io Bot

Multi-proxy slither.io bot client. Bots authenticate through the server challenge, group via proxies, and steer toward a live-updating target.

**Chromium Extension:** [slitherss-bot-control](https://github.com/DoubleAAGuy/slitherss-bot-control) — control bots from your browser.

## Quickstart (Windows PowerShell)

```powershell
# 1. Install Python 3.10+ from https://python.org

# 2. Clone and enter the repo
Remove-Item -Recurse -Force slitherss-bot -ErrorAction SilentlyContinue
git clone https://github.com/DoubleAAGuy/slitherss-bot.git
cd slitherss-bot

# 3. Install requirements
pip install aiohttp

# 4. Run the web server
python main.py
```

## Usage

### Start the control server

```powershell
python main.py
```

This starts a web server on `0.0.0.0:8081`.

### Control endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /start/{ip}:{port}/{groups}` | Spawn bots through that server (groups x 4 bots) |
| `GET /edit?x=10000&y=20000` | Update target — bots steer to new coords live |
| `POST /edit` with `{"x": 10000, "y": 20000}` | Same via JSON body |
| `GET /target` | Current target coordinates |
| `GET /status` | Running bot count, target, groups |
| `GET /stop` | Kill all bot tasks |

### Example

```powershell
# In one terminal:
python main.py

# In another terminal or browser:
curl "http://doubleaaguy.duckdns.org:8081/start/15.204.212.200:444/25"
# → 100 bots across 25 proxies, steering toward (30000, 30000)

curl "http://doubleaaguy.duckdns.org:8081/edit?x=40000&y=40000"
# → all bots change course immediately
```

### Standalone CLI (no web server)

```powershell
python bot.py
# Prompts for server, port, path, group count
# Steers toward (30000, 30000) by default
```

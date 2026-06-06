# slither.io Bot

Multi-proxy slither.io bot client. Bots authenticate through the server challenge, group via proxies, and steer toward a target coordinate.

## Quickstart (Windows PowerShell)

```powershell
# 1. Install Python 3.10+ from https://python.org

# 2. Install requirements
pip install aiohttp

# 3. Run
python bot.py
```

You'll be prompted for the server, port, path, and number of groups (4 bots per proxy).

### Example

```powershell
python bot.py
# Server IP (default 192.211.52.146): 15.204.212.200
# Server port (default 444): 444
# Path (default /slither): /slither
# Number of groups (4 bots each, default 4): 25
```

This connects 100 bots across 25 proxies, all steering toward (30000, 30000).

#!/usr/bin/env python3
import asyncio
import math
import random
import struct
import sys
import time

PI = math.pi
M_2PI = 2.0 * PI

PROTOCOL_VERSION = 30
CLIENT_VERSION = 291
PING_BYTE = 251


def normalize_angle(ang):
    return ang - M_2PI * math.floor(ang / M_2PI)


def read_uint16_be(data, offset=0):
    return struct.unpack_from('>H', data, offset)[0], offset + 2


def encode_name(name):
    s = name.encode('ascii', errors='replace')[:24]
    cv = 5
    cpw = bytes([54, 206, 204, 169, 97, 178, 74, 136, 124, 117, 14,
                 210, 106, 236, 8, 208, 136, 213, 140, 111])
    return cpw + bytes([cv, len(s)]) + s + bytes([0, 255])


def js_mod(a, b):
    if a >= 0:
        return a % b
    return -(abs(a) % b)


def decode_server_version(data):
    a = ""
    d = 0
    e = 23
    f = 0
    for g in range(len(data)):
        b = data[g]
        if b <= 96:
            b += 32
        b = (b - 97 - e) % 26
        if b < 0:
            b += 26
        d = d * 16 + b
        e += 17
        if f == 1:
            a += chr(d)
            f = 0
            d = 0
        else:
            f += 1
    return a


def extract_seed(js):
    if len(js) < 43 or js[8] != '"' or js[19] != '"':
        raise ValueError(f"Unexpected JS format: {js[:50]}")
    return js[9:14] + js[20:42]


def qff9x_transform(seed_str):
    out = [ord(c) for c in seed_str]
    roll = 0
    for c in range(len(out)):
        base = 65
        a = out[c]
        if a >= 97:
            base += 32
            a -= 32
        a -= 65
        if c == 0:
            roll = 3 + a
        e = js_mod(a + roll, 26)
        roll += 2 + a
        out[c] = e + base
    return bytes(out)


def solve_challenge(challenge_bytes):
    if len(challenge_bytes) > 27:
        js = decode_server_version(challenge_bytes[1:])
        if js.startswith('var a'):
            seed = extract_seed(js)
            return qff9x_transform(seed)
    js = decode_server_version(challenge_bytes)
    seed = extract_seed(js)
    return qff9x_transform(seed)


class Bot:
    def __init__(self, ws, name, game_radius=21600, target_x=None, target_y=None):
        self.ws = ws
        self.name = name
        self.game_radius = game_radius
        self.snake_id = 0
        self.x = game_radius
        self.y = game_radius
        self.wangle = 0.0
        self.target_x = target_x
        self.target_y = target_y

    def steer(self):
        if self.target_x is not None and self.target_y is not None:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
        else:
            dx = self.game_radius - self.x
            dy = self.game_radius - self.y
        dist = math.hypot(dx, dy)
        if dist < 200:
            return None
        aim = math.atan2(dy, dx)
        aim = normalize_angle(aim)
        if abs(self.wangle - aim) > 0.01:
            self.wangle = aim
        return max(0, min(250, int(self.wangle * 125.0 / PI)))


_ws_test_sem = asyncio.Semaphore(200)

async def fetch_proxies():
    import aiohttp
    urls = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies.txt",
    ]
    seen = set()
    async with aiohttp.ClientSession() as s:
        for url in urls:
            try:
                async with s.get(url, timeout=10) as r:
                    txt = await r.text()
                    for line in txt.splitlines():
                        line = line.strip()
                        if ':' in line and not any(c in line for c in ' /#'):
                            seen.add(line)
            except Exception:
                pass
    return list(seen)


async def test_proxy_ws(proxy, test_host, test_port):
    import aiohttp
    async with _ws_test_sem:
        try:
            async with aiohttp.ClientSession() as s:
                ws = await asyncio.wait_for(
                    s.ws_connect(
                        f"ws://{test_host}:{test_port}/slither",
                        proxy=f"http://{proxy}",
                        headers={"Origin": "http://slither.io"},
                        timeout=aiohttp.ClientWSTimeout(ws_close=5)
                    ),
                    timeout=4
                )
                await ws.send_bytes(bytes([1]))
                await ws.send_bytes(bytes([99, 0]))
                msg = await asyncio.wait_for(ws.receive(), timeout=2)
                ok = msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 0
                await ws.close()
            return ok
        except Exception:
            return False


async def run_bot(name, host, port, path, proxy=None, target_x=None, target_y=None):
    import aiohttp

    headers = {
        "Origin": "http://slither.io",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }

    retries = 0

    session = None
    ws = None

    while True:
        try:
            uri = f"ws://{host}:{port}{path}"

            kw = dict(headers=headers, heartbeat=5, timeout=aiohttp.ClientWSTimeout(ws_close=30), max_msg_size=2**20)
            if proxy:
                kw["proxy"] = f"http://{proxy}"
            session = aiohttp.ClientSession()
            ws = await session.ws_connect(uri, **kw)
            bot = Bot(ws, name, target_x=target_x, target_y=target_y)
            print(f"[{name}] Connected ({'proxy ' + proxy if proxy else 'direct'})", flush=True)

            await ws.send_bytes(bytes([1]))
            await ws.send_bytes(bytes([99, 0]))

            challenge = None
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=3)
                if msg.type == aiohttp.WSMsgType.BINARY:
                    challenge = msg.data
                    print(f"[{name}] Got challenge ({len(challenge)}B)", flush=True)
            except asyncio.TimeoutError:
                print(f"[{name}] No challenge received, proceeding...", flush=True)

            if challenge:
                response = solve_challenge(challenge)
                await ws.send_bytes(response)

            name_data = encode_name(bot.name)
            cv_h = CLIENT_VERSION >> 8
            cv_l = CLIENT_VERSION & 255
            username_pkt = bytes([ord('s'), PROTOCOL_VERSION, cv_h, cv_l]) + name_data
            await ws.send_bytes(username_pkt)

            init_msg = await asyncio.wait_for(ws.receive(), timeout=10)
            if init_msg.type != aiohttp.WSMsgType.BINARY or len(init_msg.data) < 4:
                print(f"[{name}] Bad init packet", flush=True)
                raise ConnectionError("Bad init packet")
            init_raw = init_msg.data

            found_id = False
            lpo_x = bot.x
            lpo_y = bot.y

            def parse_raw_message(data):
                if len(data) < 1:
                    return
                if data[0] < 32:
                    m = 0
                    while m < len(data):
                        if data[m] < 32:
                            if m + 2 > len(data):
                                break
                            plen = (data[m] << 8) | data[m+1]
                            m += 2
                        else:
                            plen = data[m] - 32
                            m += 1
                        if m + plen > len(data):
                            break
                        yield data[m:m+plen]
                        m += plen
                else:
                    yield data

            bot_msl = 16
            for sub in parse_raw_message(init_raw):
                if sub[0] == ord('a') and len(sub) >= 27:
                    grd = (sub[1] << 16) | (sub[2] << 8) | sub[3]
                    bot.game_radius = grd
                    if len(sub) >= 25:
                        bot_msl = sub[24]
                    if len(sub) >= 27:
                        bot.snake_id = (sub[25] << 8) | sub[26]
                        found_id = True
                        print(f"[{name}] Snake ID: {bot.snake_id}, grd: {grd}, msl: {bot_msl}", flush=True)

            retries = 0
            last_cord_log = time.monotonic()
            last_ping = time.monotonic()
            last_angle_send = 0.0

            while True:
                now = time.monotonic()
                if now - last_cord_log > 1:
                    print(f"[{name}] x={bot.x} y={bot.y}", flush=True)
                    last_cord_log = now
                if now - last_ping > 0.5:
                    await ws.send_bytes(bytes([PING_BYTE]))
                    last_ping = now

                if now - last_angle_send > 0.06:
                    angle_byte = bot.steer()
                    if angle_byte is not None:
                        await ws.send_bytes(bytes([angle_byte]))
                    last_angle_send = now

                lpo_x = bot.x
                lpo_y = bot.y

                for _ in range(3):
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=0.02)
                    except asyncio.TimeoutError:
                        break
                    if msg.type != aiohttp.WSMsgType.BINARY:
                        if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                            raise ConnectionError("Connection closed")
                        continue
                    d = msg.data
                    if len(d) < 1:
                        continue

                    def process_sub(sub):
                        nonlocal found_id, lpo_x, lpo_y
                        if len(sub) < 1:
                            return
                        ptype = sub[0]
                        sl = len(sub)

                        if ptype == ord('s') and sl >= 27:
                            sid = (sub[1] << 8) | sub[2]
                            nl = sub[24]
                            name_off = 25
                            if name_off + nl <= sl and sub[name_off:name_off+nl].decode('latin-1', errors='replace') == bot.name:
                                snx = (sub[18] << 16 | sub[19] << 8 | sub[20]) / 5.0
                                sny = (sub[21] << 16 | sub[22] << 8 | sub[23]) / 5.0
                                bot.snake_id = sid
                                bot.x = int(snx)
                                bot.y = int(sny)
                                lpo_x = bot.x
                                lpo_y = bot.y
                                found_id = True
                            return

                        if not found_id:
                            return

                        if ptype == ord('g') and sl >= 5:
                            gsid = (sub[1] << 8) | sub[2]
                            if gsid == bot.snake_id:
                                iang = (sub[3] << 8) | sub[4]
                                ang = iang * M_2PI / 65536.0
                                lpo_x = bot.x
                                lpo_y = bot.y
                                bot.x = int(lpo_x + math.cos(ang) * bot_msl)
                                bot.y = int(lpo_y + math.sin(ang) * bot_msl)
                            return

                        if ptype == ord('G') and sl >= 3:
                            iang = (sub[1] << 8) | sub[2]
                            ang = iang * M_2PI / 65536.0
                            lpo_x = bot.x
                            lpo_y = bot.y
                            bot.x = int(lpo_x + math.cos(ang) * bot_msl)
                            bot.y = int(lpo_y + math.sin(ang) * bot_msl)
                            return

                        if ptype == ord('=') and sl == 7:
                            bx = (sub[3] << 8) | sub[4]
                            by = (sub[5] << 8) | sub[6]
                            bot.x = bx
                            bot.y = by
                            lpo_x = bx
                            lpo_y = by
                            return

                    if d[0] < 32:
                        m = 0
                        while m < len(d):
                            if d[m] < 32:
                                if m + 2 > len(d):
                                    break
                                plen = (d[m] << 8) | d[m+1]
                                m += 2
                            else:
                                plen = d[m] - 32
                                m += 1
                            if m + plen > len(d):
                                break
                            process_sub(d[m:m+plen])
                            m += plen
                    else:
                        process_sub(d)

                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            break
        except Exception as e:
            retries += 1
            delay = 3 + random.uniform(0, 2)
            print(f"[{name}] Disconnected ({e}), reconnecting in {delay:.1f}s...", flush=True)
            await asyncio.sleep(delay)
        finally:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass
                ws = None
            if session:
                try:
                    await session.close()
                except Exception:
                    pass
                session = None


async def main():
    import aiohttp

    print("slither.io Bot Client")
    print("=" * 35)

    host = input("Server IP (default 192.211.52.146): ").strip() or "192.211.52.146"
    port_str = input("Server port (default 444): ").strip() or "444"
    try:
        port = int(port_str)
    except ValueError:
        print("Invalid port, using 444")
        port = 444

    path = input("Path (default /slither): ").strip() or "/slither"
    if not path.startswith("/"):
        path = "/" + path

    groups_str = input("Number of groups (4 bots each, default 4): ").strip() or "4"
    try:
        num_groups = int(groups_str)
        if num_groups < 1:
            num_groups = 1
    except ValueError:
        num_groups = 4

    print("\nFetching proxies...", flush=True)

    proxies_for_groups = []
    fetch_round = 0

    while len(proxies_for_groups) < num_groups:
        raw = await fetch_proxies()
        random.shuffle(raw)
        fetch_round += 1
        print(f"[Round {fetch_round}] Found {len(raw)} total proxies", flush=True)

        sample = raw[:5000]

        print(f"  Testing {len(sample)} against game WS...", flush=True)
        try:
            ws_results = await asyncio.wait_for(
                asyncio.gather(*[test_proxy_ws(p, host, port) for p in sample], return_exceptions=True),
                timeout=300
            )
        except asyncio.TimeoutError:
            ws_results = [False] * len(sample)

        good = [p for p, ok in zip(sample, ws_results) if ok is True]
        random.shuffle(good)
        print(f"  WS-working: {len(good)}", flush=True)

        for p in good:
            if len(proxies_for_groups) >= num_groups:
                break
            if p not in proxies_for_groups:
                proxies_for_groups.append(p)
                print(f"  -> Using proxy {p} ({len(proxies_for_groups)}/{num_groups})", flush=True)

        if len(proxies_for_groups) < num_groups:
            print(f"  Only have {len(proxies_for_groups)}/{num_groups} proxies, retrying...", flush=True)

    bots_per_group = 4
    count = num_groups * bots_per_group
    print(f"\nSpawning {count} bots in {num_groups} groups of {bots_per_group}\n", flush=True)

    tasks = []
    for i in range(count):
        proxy = proxies_for_groups[i // bots_per_group]
        name = f"Bot_{i + 1}"
        tasks.append(asyncio.create_task(
            run_bot(name, host, port, path, proxy=proxy, target_x=30000, target_y=30000)
        ))
        await asyncio.sleep(1.5)

    print(f"{count} bot(s) running. Press Ctrl+C to stop.\n")

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)

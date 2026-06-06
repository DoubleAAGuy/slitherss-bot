import asyncio
import sys

from aiohttp import web

import bot


def create_app():
    app = web.Application(middlewares=[cors_middleware])

    app['target'] = {"x": 30000, "y": 30000}
    app['bot_tasks'] = set()
    app['num_groups'] = 0

    def target_getter():
        t = app['target']
        return (t['x'], t['y'])

    app['target_getter'] = target_getter

    async def cancel_bots(app):
        for t in app['bot_tasks']:
            t.cancel()
        if app['bot_tasks']:
            await asyncio.gather(*app['bot_tasks'], return_exceptions=True)
        app['bot_tasks'].clear()

    app.on_shutdown.append(cancel_bots)

    async def handle_target(request):
        return web.json_response(app['target'])

    async def handle_edit(request):
        if request.method == 'POST':
            body = await request.json()
            x = int(body.get('x', app['target']['x']))
            y = int(body.get('y', app['target']['y']))
        else:
            x = int(request.query.get('x', app['target']['x']))
            y = int(request.query.get('y', app['target']['y']))
        app['target']['x'] = x
        app['target']['y'] = y
        print(f"[server] Target updated to ({x}, {y})", flush=True)
        return web.json_response(app['target'])

    async def handle_start(request):
        ip_port = request.match_info.get('ip_port')
        group_count = int(request.match_info.get('group_count'))

        if ':' not in ip_port:
            return web.json_response({"error": "format: ip:port"}, status=400)
        host, port_str = ip_port.rsplit(':', 1)
        port = int(port_str)
        path = "/slither"

        if app['bot_tasks']:
            await cancel_bots(app)

        app['num_groups'] = group_count

        async def run():
            try:
                tasks = await bot.run_bots(host, port, path, group_count, target_getter)
                for t in tasks:
                    app['bot_tasks'].add(t)
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass
            finally:
                for t in list(app['bot_tasks']):
                    if t.done():
                        app['bot_tasks'].discard(t)

        task = asyncio.create_task(run())
        app['bot_tasks'].add(task)

        total = group_count * 4
        return web.json_response({"status": "ok", "groups": group_count, "bots": total, "target": app['target']})

    async def handle_stop(request):
        count = len(app['bot_tasks'])
        await cancel_bots(app)
        print(f"[server] Stopped {count} bot tasks", flush=True)
        return web.json_response({"status": "stopped", "bots_killed": count})

    async def handle_status(request):
        running = sum(1 for t in app['bot_tasks'] if not t.done())
        return web.json_response({
            "running": running,
            "target": app['target'],
            "groups": app['num_groups'],
            "total_bots": app['num_groups'] * 4,
        })

    app.router.add_get('/target', handle_target)
    app.router.add_get('/edit', handle_edit)
    app.router.add_post('/edit', handle_edit)
    app.router.add_get('/start/{ip_port}/{group_count}', handle_start)
    app.router.add_get('/stop', handle_stop)
    app.router.add_get('/status', handle_status)

    return app


@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        resp = web.Response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp
    resp = await handler(request)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


if __name__ == '__main__':
    web.run_app(create_app(), host='0.0.0.0', port=8081)

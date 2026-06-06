#!/usr/bin/env python3
if __name__ == '__main__':
    from server import create_app
    from aiohttp import web
    web.run_app(create_app(), host='0.0.0.0', port=8081)

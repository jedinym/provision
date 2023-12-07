import asyncio
import os

from endpoint.service import EndpointService
from grpclib.server import Server
from grpclib.utils import graceful_exit
from loguru import logger

PORT = int(os.environ.get("ENDPOINT_PORT", 5000))

async def main():
    server = Server([EndpointService()])
    with graceful_exit([server]):
        await server.start("127.0.0.1", PORT)
        logger.info(f"Server listening at {PORT}")
        await server.wait_closed()
        logger.info("Server shutdown")

if __name__ == '__main__':
    asyncio.run(main())

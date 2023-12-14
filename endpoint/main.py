import asyncio
import os

from grpclib.server import Server
from grpclib.utils import graceful_exit
from loguru import logger
from common.repo import StructRepository

from endpoint.service import EndpointService

PORT = int(os.environ.get("ENDPOINT_PORT", 5000))

async def _main():
    repo = StructRepository()
    endpoint = EndpointService(repo)

    server = Server([endpoint])
    with graceful_exit([server]):
        await server.start("127.0.0.1", PORT)
        logger.info(f"Server listening at {PORT}")
        await server.wait_closed()
        logger.info("Server shutdown")


def main():
    asyncio.run(_main())

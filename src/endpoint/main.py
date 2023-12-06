import asyncio
from sys import stdout
import os
import logging

from endpoint.service import EndpointService
from grpclib.server import Server
from grpclib.utils import graceful_exit

PORT = int(os.environ.get("ENDPOINT_PORT", 5000))
logger = logging.getLogger(__name__)

async def main():
    server = Server([EndpointService()])
    with graceful_exit([server]):
        await server.start("127.0.0.1", PORT)
        logger.info("Starting server")
        await server.wait_closed()
        logger.info("Server closed")

if __name__ == '__main__':
    logging.basicConfig(stream=stdout, format='[%(asctime)s] %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.DEBUG)
    asyncio.run(main())

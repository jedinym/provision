import os
import threading
from time import sleep
import signal

from structlog import get_logger
import minio

from sqc.repository import MinioRepo
from sqc.worker import Worker

SHOULD_STOP = False

logger = get_logger()


def handler(_, __) -> None:
    global SHOULD_STOP
    SHOULD_STOP = True


def main() -> None:
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    minio_conn = minio.Minio(
        endpoint=os.environ["MINIO_URL"].strip('"'),
        access_key=os.environ.get("MINIO_USER", "minioadmin"),
        secret_key=os.environ.get("MINIO_PASSWORD", "minioadmin"),
        secure=False,
    )

    repo = MinioRepo(minio_conn)

    nthreads = int(os.environ.get("NTHREADS", 1))
    threads: list[threading.Thread] = []
    workers: list[Worker] = []

    for _ in range(nthreads):
        worker = Worker(repo)
        workers.append(worker)

        logger.info("Starting worker")
        t = threading.Thread(target=worker.run, args=[])
        threads.append(t)
        t.start()

    global SHOULD_STOP
    while True:
        sleep(1)  # TODO: smaller period
        for thread in threads:
            if not thread.is_alive():
                SHOULD_STOP = True
                logger.error("Worker thread died during execution")

        if SHOULD_STOP:
            logger.warning("Stopping all workers")
            for worker in workers:
                worker.should_stop = True

            for thread in threads:
                thread.join()

            exit(1)


if __name__ == "__main__":
    main()

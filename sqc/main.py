import os
import threading
from time import sleep
import signal

from loguru import logger
import minio

from sqc.repository import MinioRepo
from sqc.worker import Worker

should_stop = False


def handler(_, __) -> None:
    global should_stop
    should_stop = True


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

    global should_stop
    while True:
        sleep(1)  # TODO: smaller period
        for thread in threads:
            if not thread.is_alive():
                should_stop = True
                logger.error("Worker thread died during execution")

        if should_stop:
            logger.warning("Stopping all workers")
            for worker in workers:
                worker.should_stop = True

            for thread in threads:
                thread.join()

            exit(1)


if __name__ == "__main__":
    main()

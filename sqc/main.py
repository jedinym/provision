import os
import threading
from time import sleep
import signal

from kombu import Connection
from loguru import logger
import minio

from sqc.repository import MinioRepo
from sqc.validation import Validator
from sqc.worker import Worker

should_stop = False

def handler(_, __):
    global should_stop
    should_stop = True


def main():
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    local_env = os.environ.get("LOCAL_ENV", "false").lower() == "true"

    minio_conn = minio.Minio(
        endpoint=os.environ["MINIO_ENDPOINT"].strip('"'),
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False if local_env else True,
    )

    repo = MinioRepo(minio_conn)
    validator = Validator(repo)

    nthreads = 2
    threads: list[threading.Thread] = []
    workers: list[Worker] = []

    for _ in range(nthreads):
        worker = Worker(validator)
        workers.append(worker)

        t = threading.Thread(target=worker.run, args=[])
        threads.append(t)
        t.start()

    global should_stop
    while True:
        sleep(1)
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

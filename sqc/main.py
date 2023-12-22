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

stop_event = threading.Event()

def handler(signum, _frame):
    print("COCK!")
    global stop_event
    stop_event.set()


def start_worker(validator: Validator, stop_event: threading.Event) -> None:
    with Connection("amqp://guest:guest@localhost:5672//") as conn:
        worker = Worker(conn, validator)
        logger.info(f"Starting worker {threading.get_ident()}")
        worker.run(stop_event)


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

    for _ in range(nthreads):
        t = threading.Thread(target=start_worker, args=[validator, stop_event])
        threads.append(t)
        t.start()

    while True:
        sleep(1)
        for thread in threads:
            if not thread.is_alive():
                stop_event.set()
                logger.error("Worker thread died during execution")

        if stop_event.is_set():
            print("Stopping")
            for thread in threads:
                thread.join()

            exit(1)


if __name__ == "__main__":
    main()

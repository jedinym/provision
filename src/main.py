import os

from kombu import Connection
from loguru import logger
import minio
from repository import RequestRepo
from validation import Validator

from worker import Worker


def main():
    local_env = os.environ.get("LOCAL_ENV", "false").lower() == "true"

    minio_conn = minio.Minio(
        endpoint=os.environ["MINIO_ENDPOINT"],
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False if local_env else True,
    )

    repo = RequestRepo(minio_conn)
    validator = Validator(repo)

    with Connection("amqp://guest:guest@localhost:5672//") as conn:
        worker = Worker(conn, validator)
        logger.info("Starting worker")
        worker.run()


if __name__ == "__main__":
    main()

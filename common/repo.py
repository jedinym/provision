import os

from minio import Minio
from loguru import logger

class StructRepository:
    def __init__(self):
        local_env = os.environ.get("LOCAL_ENV", "false").lower() == "true"
        self.minio = Minio(
            endpoint=os.environ["MINIO_ENDPOINT"],
            access_key='minioadmin',
            secret_key='minioadmin',
            secure=False if local_env else True
        )

        self._ensure_bucket("requests")
        self._ensure_bucket("results")

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.minio.bucket_exists(bucket):
            logger.info(f"Creating bucket {bucket}")
            self.minio.make_bucket(bucket)

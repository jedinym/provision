import tempfile

from loguru import logger
import minio


class RequestRepo:
    def __init__(self, minio: minio.Minio):
        # TODO: set bucket notifications
        self.minio = minio

        self._ensure_bucket("requests")
        self._ensure_bucket("results")

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.minio.bucket_exists(bucket):
            logger.info(f"Creating bucket {bucket}")
            self.minio.make_bucket(bucket)
        else:
            logger.info(f"Bucket {bucket} already exists")

    def download_request(self, request: str) -> str:
        path = tempfile.mktemp(suffix=".mmcif")
        path = f"/tmp/{request}"
        logger.info(f"Downloading {request} to {path}")
        self.minio.fget_object("requests", request, path)
        return path

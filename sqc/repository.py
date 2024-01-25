import json
import io
from dataclasses import dataclass

from loguru import logger
import minio
from minio.notificationconfig import QueueConfig, NotificationConfig

from sqc.validation import Result


@dataclass
class SQCResponse:
    error: str | None
    result: Result | None

    @staticmethod
    def ok(result: Result):
        return SQCResponse(None, result)

    @staticmethod
    def err(msg: str):
        return SQCResponse(msg, None)


class MinioRepo:
    request_bucket = "requests"
    result_bucket = "results"

    def __init__(self, minio: minio.Minio):
        self.minio = minio

        self._ensure_bucket(self.request_bucket)
        self._ensure_bucket(self.result_bucket)

        notif_cfg = NotificationConfig(
            queue_config_list=[
                QueueConfig(
                    "arn:minio:sqs::PRIMARY:amqp",
                    ["s3:ObjectCreated:Put"]
                )
            ]
        )
        minio.set_bucket_notification(self.request_bucket, notif_cfg)

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.minio.bucket_exists(bucket):
            logger.info(f"Creating bucket {bucket}")
            self.minio.make_bucket(bucket)
        else:
            logger.info(f"Bucket {bucket} already exists")

    def download_request(self, request: str) -> str:
        path = f"/tmp/{request}"
        logger.debug(f"Downloading {request} to {path}")
        # TODO: wrap this in a try block
        self.minio.fget_object("requests", request, path)
        return path

    def write_response(self, request: str, response: SQCResponse) -> None:
        logger.info(f"Writing response {request} to Minio: {response}")

        metadata = dict()
        if response.error:
            metadata["sqc-error"] = response.error

        if response.result:
            body = json.dumps(response.result.__dict__).encode("UTF-8")
            stream = io.BytesIO(body)
            self._write_object(
                self.result_bucket, f"{request}.json", stream, len(body), metadata
            )

    def _write_object(
        self,
        bucket: str,
        obj_name: str,
        data: io.BytesIO,
        data_len: int,
        metadata: dict[str, str],
    ):
        retries = 3
        last_err = None
        success = False
        while retries != 0:
            logger.debug(f"Writing result to minio with metadata {metadata}")
            try:
                self.minio.put_object(
                    bucket,
                    obj_name,
                    data,
                    data_len,
                    metadata=metadata,
                )
                success = True
                break
            except minio.S3Error as err:
                logger.warning("Failed to write response to minio, retrying")
                retries -= 1
                last_err = err

        if not success:
            logger.exception(
                f"Failed to write response to minio after retrying: {last_err}"
            )

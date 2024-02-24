import json
import io
from dataclasses import dataclass
from typing import Any
import functools
import subprocess

from structlog import get_logger
import minio
from minio.notificationconfig import QueueConfig, NotificationConfig

from sqc.validation import Result

logger = get_logger()


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


class InternalError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class ConversionError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


def mask_minio_action(name: str, raise_error: bool = True):
    def wrapper(action):
        @functools.wraps(action)
        def inner(*args, **kwargs):
            retries = 3
            last_err = None
            result = None
            while retries != 0:
                try:
                    result = action(*args, **kwargs)
                    break
                except minio.S3Error as err:
                    logger.warning(f"Failed to execute action: {name}")
                    retries -= 1
                    last_err = err

            if last_err:
                logger.exception(
                    f"Failed to execute action {name} after retrying: {last_err}"
                )
                if raise_error:
                    raise InternalError from last_err

            return result

        return inner

    return wrapper


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
                    [
                        "s3:ObjectCreated:Put",
                        "s3:ObjectCreated:CompleteMultipartUpload",
                    ],
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

    @staticmethod
    def _convert_to_pdb(path: str) -> str:
        new_path = f"{path.split('.')[-1]}.pdb"
        logger.debug(f"Converting {path} to PDB format")

        try:
            proc = subprocess.run(
                ["gemmi", "convert", path, new_path], capture_output=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            logger.warning("Gemmi conversion timed out")
            raise ConversionError("Failed to convert .mmcif file to PDB format in time")

        if proc.returncode != 0:
            logger.info(
                f"Failed to convert MMCIF to PDB format",
                gemmi_msg=str(proc.stderr),
                path=path,
            )
            raise ConversionError("Failed to convert .mmcif file to PDB format")

        return new_path

    def download_request(self, request: str) -> str:
        logger.debug(f"Fetching request")
        path, ftype = self._download_request(request)
        if ftype != "pdb":
            path = MinioRepo._convert_to_pdb(path)

        return path

    @mask_minio_action("download_request")
    def _download_request(self, request: str) -> tuple[str, str]:
        stat = self.minio.stat_object(self.request_bucket, request)
        if not stat.metadata:
            logger.error(f"Request {request} does not contain metadata")
            raise InternalError()

        ftype = stat.metadata.get("X-Amz-Meta-Ftype")
        if not ftype:
            logger.error(f"Request {request} does not contain file type")
            raise InternalError()

        path = f"{request}.{ftype}"
        self.minio.fget_object(self.request_bucket, request, path)
        return path, ftype

    @mask_minio_action("delete_request", raise_error=False)
    def delete_request(self, request: str) -> None:
        logger.debug(f"Deleting request from Minio")
        self.minio.remove_object(self.request_bucket, request)

    def write_response(self, request: str, response: SQCResponse) -> None:
        logger.info(f"Writing response to Minio", response=response)

        metadata = dict()
        if response.error:
            metadata["sqc-error"] = response.error

        if response.result:
            body = json.dumps(response.result.__dict__).encode("UTF-8")
        else:
            body = bytes()

        self._write_response(f"{request}.json", body, metadata)

    @mask_minio_action("write_response", raise_error=False)
    def _write_response(
        self, object_name: str, body: bytes, metadata: dict[Any, Any]
    ) -> None:
        stream = io.BytesIO(body)

        logger.debug(f"Writing result to minio", metadata=metadata)
        self.minio.put_object(
            self.result_bucket,
            object_name,
            stream,
            len(body),
            metadata=metadata,
        )

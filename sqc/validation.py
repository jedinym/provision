from loguru import logger

from sqc.repository import MinioRepo


class Validator:
    def __init__(self, repo: MinioRepo):
        self.repo = repo

    def validate(self, request: str) -> None:
        path = self.repo.download_request(request)
        # TODO: run validation
        logger.info(f"Starting validation of {request}")

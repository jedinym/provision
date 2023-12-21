from loguru import logger
from repository import RequestRepo


class Validator:
    def __init__(self, repo: RequestRepo):
        self.repo = repo

    def validate(self, request: str) -> None:
        path = self.repo.download_request(request)
        # TODO: run validation
        logger.info(f"Starting validation of {request}")

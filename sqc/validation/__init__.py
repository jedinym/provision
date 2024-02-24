from dataclasses import dataclass

from structlog import get_logger

logger = get_logger()


@dataclass
class Result:
    mock_msg: str


class ValidationError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class Validator:
    @staticmethod
    def validate(path: str) -> Result:
        logger.debug(f"Starting validation of {path}")

        # TODO: run validation
        mock_result = Result(mock_msg="Successful validation!")

        return mock_result

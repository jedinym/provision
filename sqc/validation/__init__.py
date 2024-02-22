from dataclasses import dataclass
import subprocess

from loguru import logger


@dataclass
class Result:
    mock_msg: str


class ValidationError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class Validator:
    @staticmethod
    def convert_to_pdb(path: str) -> str:
        proc = subprocess.run(["BeEM", path], capture_output=True, timeout=60)

        if proc.returncode != 0:
            raise ValidationError("Failed to convert .mmcif file to PDB format")

        return proc.stdout.decode().strip()

    @staticmethod
    def validate(path: str, ftype: str) -> Result:
        logger.debug(f"Starting validation of {path} with file type {ftype}")

        if ftype == "mmcif":
            logger.debug(f"Received MMCIF, converting to PDB format")
            path = Validator.convert_to_pdb(path)

        # TODO: run validation
        mock_result = Result(mock_msg="Successful validation!")

        return mock_result

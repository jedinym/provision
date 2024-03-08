from dataclasses import dataclass
import json
from typing import Any
import subprocess
import csv

from structlog import get_logger

from sqc.repository import InternalError

logger = get_logger()


@dataclass
class Result:
    residue_analysis: dict[str, Any]


class ValidationError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class MolProbity:
    def __init__(self, timeout=600) -> None:
        self.timeout = timeout

    def _residue_analysis_output(self, path: str) -> str:
        try:
            proc = subprocess.run(
                ["residue-analysis", path], capture_output=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "Failed to run molprobity residue-analysis in time",
                timeout=self.timeout,
            )
            raise ValidationError("Failed to run residue analysis in time")

        if proc.returncode != 0:
            logger.error(
                "residue-analysis exited with non-zero code", stderr=proc.stderr
            )
            raise InternalError()

        return proc.stdout.decode(encoding="utf-8")

    @staticmethod
    def _nullify_row(row: dict[str, Any]) -> None:
        """Changes dict values from empty strings to None"""
        for key, val in row.items():
            if val == "":
                row[key] = None

    def residue_analysis(self, path: str) -> dict[str, Any]:
        output = self._residue_analysis_output(path).splitlines()
        reader = csv.DictReader(output, dialect="unix")

        per_residue_analysis: dict[str, Any] = {}
        for residue_row in reader:
            residue = residue_row.pop("residue")
            self._nullify_row(residue_row)
            per_residue_analysis[residue] = residue_row

        return per_residue_analysis


def validate(path: str) -> str:
    logger.debug(f"Starting validation of {path}")

    mp = MolProbity()

    result = Result(residue_analysis=mp.residue_analysis(path))

    return json.dumps(result.__dict__)

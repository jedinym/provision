from typing import Any
import subprocess
import csv

from structlog import get_logger
import git

from sqc.repository import InternalError
from sqc.validation.model import (
    DataVersion,
    MolProbityVersions,
    Residue,
    WorstBondAngle,
    WorstBondLength,
    WorstClash,
)

logger = get_logger()


class MolProbityError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class MolProbity:
    GEOSTD_REPO_PATH = "/molprobity/modules/chem_data/geostd"
    MON_LIB_REPO_PATH = "/molprobity/modules/chem_data/mon_lib"
    ROTARAMA_DATA_REPO_PATH = "/molprobity/modules/chem_data/rotarama_data"
    CABLAM_DATA_REPO_PATH = "/molprobity/modules/chem_data/cablam_data"
    RAMA_Z_REPO_PATH = "/molprobity/modules/chem_data/rama_z"

    def __init__(self, timeout=600) -> None:
        self.timeout = timeout
        self.geostd_repo = git.Repo(self.GEOSTD_REPO_PATH)
        self.mon_lib_repo = git.Repo(self.MON_LIB_REPO_PATH)
        self.rotarama_data_repo = git.Repo(self.ROTARAMA_DATA_REPO_PATH)
        self.cablam_data_repo = git.Repo(self.CABLAM_DATA_REPO_PATH)
        self.rama_z_repo = git.Repo(self.RAMA_Z_REPO_PATH)

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
            raise MolProbityError("Failed to run residue analysis in time")

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

    def _get_analysis_dict(self, path: str) -> dict[str, Any]:
        output = self._residue_analysis_output(path).splitlines()
        reader = csv.DictReader(output, dialect="unix")

        per_residue_analysis: dict[str, Any] = {}
        for residue_row in reader:
            residue = residue_row.pop("residue")
            self._nullify_row(residue_row)
            per_residue_analysis[residue] = residue_row

        return per_residue_analysis

    @staticmethod
    def _parse_residue(residue: str) -> Residue:
        split = residue.split()
        chain = split[0].strip()
        number = int(split[1].strip())
        type = split[2].strip()
        return Residue(number=number, chain=chain, residue_type=type)

    @staticmethod
    def _get_data_version(repo: git.Repo) -> DataVersion:
        url = repo.remote().url
        sha = repo.commit().hexsha
        return DataVersion(url=url, commit_sha=sha)

    def get_data_versions(self) -> MolProbityVersions:
        return MolProbityVersions(
            geostd_version=self._get_data_version(self.geostd_repo),
            mon_lib_version=self._get_data_version(self.mon_lib_repo),
            rotarama_version=self._get_data_version(self.rotarama_data_repo),
            cablam_version=self._get_data_version(self.cablam_data_repo),
            rama_z_version=self._get_data_version(self.rama_z_repo),
        )

    def _parse_worst_length(self, analysis: dict[str, Any]) -> WorstBondLength:
        first_atom, second_atom = analysis["worst_length"].split("--")
        length = analysis["worst_length_value"]
        sigma = analysis["worst_length_sigma"]

        return WorstBondLength(
            first_atom=first_atom, second_atom=second_atom, length=length, sigma=sigma
        )

    def _parse_worst_angle(self, analysis: dict[str, Any]) -> WorstBondAngle:
        first_atom, second_atom, third_atom = analysis["worst_angle"].split("-")
        angle = analysis["worst_angle_value"]
        sigma = analysis["worst_angle_sigma"]

        return WorstBondAngle(
            first_atom=first_atom,
            second_atom=second_atom,
            third_atom=third_atom,
            angle=angle,
            sigma=sigma,
        )

    def residue_analysis(self, path: str) -> list[Residue] | None:
        logger.debug("Running residue-analysis", path=path)
        all_analysis = self._get_analysis_dict(path)
        residues = []

        for residue_id, analysis in all_analysis.items():
            residue = self._parse_residue(residue_id)

            if analysis["worst_clash"] is not None:
                magnitude = float(analysis["worst_clash"])
                atom = analysis["src_atom"].strip()
                other_atom = analysis["dst_atom"].strip()
                dst_residue = self._parse_residue(analysis["dst_residue"])

                residue.worst_clash = WorstClash(
                    magnitude=magnitude,
                    atom=atom,
                    other_atom=other_atom,
                    other_residue=dst_residue,
                )

            if analysis["num_length_out"] is not None:
                residue.bond_length_outlier_count = int(analysis["num_length_out"])
                residue.worst_bond_length = self._parse_worst_length(analysis)

            if analysis["num_angle_out"] is not None:
                residue.bond_angle_outlier_count = int(analysis["num_angle_out"])
                residue.worst_bond_angle = self._parse_worst_angle(analysis)

            residues.append(residue)

        return residues

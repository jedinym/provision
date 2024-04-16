from typing import Any
import subprocess
import csv

from structlog import get_logger
import git

from sqc.repository import InternalError
from sqc.validation.model import (
    Atom,
    Clash,
    DataVersion,
    MolProbityVersions,
    OmegaTorsion,
    RamaTorsion,
    Residue,
    SidechainTorsion,
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

    CLASHSCORE_LINE_ATOMS_LEN = 34

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

    def _clashscore_output(self, path: str) -> str:
        try:
            proc = subprocess.run(
                ["clashscore", path], capture_output=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "Failed to run molprobity clashscore in time",
                timeout=self.timeout,
            )
            raise MolProbityError("Failed to run residue analysis in time")

        if proc.returncode != 0:
            logger.error("clashscore exited with non-zero code", stderr=proc.stderr)
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

        # When the residue number is 4 digits long, it gets joined with the
        # chain ID in the residue-analysis output. "X1194 TYR" instead of
        # "X 1194 TYR"
        # FIXME: this parsing logic is broken for some residue types
        if len(split) == 2:
            chain = split[0][0]
            number = int(split[0][1:])
            type = split[1].strip()
        else:
            chain = split[0].strip()
            number = int(split[1].strip())
            type = split[2].strip()

        # if the residue is not 3 characters long (e.g. LYS, ARG),
        # it has the altcode prepended (e.g. ALYS, BARG)
        alt_code = None
        if len(type) != 3:
            alt_code = type[: len(type) - 3]
            type = type[len(alt_code) :]

        return Residue(number=number, chain=chain, residue_type=type, alt_code=alt_code)

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

    @staticmethod
    def _parse_clash_atom(raw: str) -> Atom:
        """
        Parse a clash atom from molprobity clashscore output

        When the residue number is 4 digits long, it gets joined with the
        chain ID in the output. "X1194 TYR G2" instead of
        "X 1194 TYR G2"

        Input examples:
            - "A   9  LYS  CA"
            - "X1034  ASP  C"

        Outputs:
            - Atom(chain="A", residue_number=9, atom="CA")
            - Atom(chain="X", residue_number=1034, atom="C")
        """
        chain = raw[0]
        split = raw.split()

        # chain is 5 characters long only when the residue
        # number invades its space
        if len(raw.split()[0]) == 5:
            chain = chain[0]
            residue_number = int(split[0][1:])
            atom = split[2]
        else:
            residue_number = int(split[1])
            atom = split[3]

        return Atom(chain=chain, residue_number=residue_number, atom=atom)

    def clashscore(self, path: str) -> list[Clash]:
        logger.debug("Running clashscore", path=path)
        output = self._clashscore_output(path)
        clashes = []

        # since the clashscore program has no specified output format,
        # we need to do ugly magic to the output to remove garbage
        # TODO: refactor this to make it more apparent
        output_lines = output.splitlines()[:-2]
        if "hydrogen addition" in output_lines[2]:
            garbage_lines = 5
        else:
            garbage_lines = 4

        for clash_line in output_lines[garbage_lines:]:
            first_atom_part = clash_line[: self.CLASHSCORE_LINE_ATOMS_LEN // 2].strip()

            second_atom_part = clash_line[
                (self.CLASHSCORE_LINE_ATOMS_LEN // 2) + 1 :
            ].strip()

            first_atom = self._parse_clash_atom(first_atom_part)
            second_atom = self._parse_clash_atom(second_atom_part)

            # remove colon from magnitude field
            magnitude = float(clash_line[self.CLASHSCORE_LINE_ATOMS_LEN + 1 :])

            clashes.append(
                Clash(
                    first_atom=first_atom, second_atom=second_atom, magnitude=magnitude
                )
            )

        return clashes

    def residue_analysis(self, path: str) -> list[Residue]:
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

            if analysis["omega"] is not None:
                angle = float(analysis["omega"])
                angle_range = analysis["omega_eval"]
                residue.omega_torsion = OmegaTorsion(
                    angle=angle, angle_range=angle_range
                )

            if analysis["rama_eval"] is not None:
                residue.rama_torsion = RamaTorsion(
                    angle_combo_range=analysis["rama_eval"]
                )

            if analysis["rotamer_eval"] is not None:
                residue.sidechain_torsion = SidechainTorsion(
                    angle_range=analysis["rotamer_eval"], rotamer=analysis["rotamer"]
                )

            # skip residue if no outliers found
            if (
                residue.bond_angle_outlier_count is not None
                or residue.bond_length_outlier_count is not None
                or residue.omega_torsion is not None
                or residue.sidechain_torsion is not None
                or residue.rama_torsion is not None
            ):
                residues.append(residue)

        return residues

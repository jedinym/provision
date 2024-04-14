import json

from pydantic import BaseModel


class WorstClash(BaseModel):
    magnitude: float
    atom: str
    other_atom: str
    other_residue: "Residue"


class WorstBondLength(BaseModel):
    first_atom: str
    second_atom: str
    length: float
    sigma: float


class WorstBondAngle(BaseModel):
    first_atom: str
    second_atom: str
    third_atom: str
    angle: float
    sigma: float


class OmegaTorsion(BaseModel):
    angle_range: str
    angle: float


class RamaTorsion(BaseModel):
    angle_combo_range: str


class Residue(BaseModel):
    number: int
    chain: str
    residue_type: str
    worst_clash: WorstClash | None = None
    bond_length_outlier_count: int | None = None
    worst_bond_length: WorstBondLength | None = None
    bond_angle_outlier_count: int | None = None
    worst_bond_angle: WorstBondAngle | None = None
    omega_torsion: OmegaTorsion | None = None
    rama_torsion: RamaTorsion | None = None


class Atom(BaseModel):
    residue_number: int
    chain: str
    atom: str


class Clash(BaseModel):
    first_atom: Atom
    second_atom: Atom
    magnitude: float


class Model(BaseModel):
    number: int
    residues: list[Residue] | None = None
    clashes: list[Clash] | None = None


class DataVersion(BaseModel):
    url: str
    commit_sha: str


class MolProbityVersions(BaseModel):
    geostd_version: DataVersion
    mon_lib_version: DataVersion
    rotarama_version: DataVersion
    cablam_version: DataVersion
    rama_z_version: DataVersion


class Status(BaseModel):
    residue_analysis: bool = True
    clashscore: bool = True
    molprobity_versions: MolProbityVersions


class Result(BaseModel):
    status: Status
    pdb_id: str
    filename: str
    models: list[Model]


def print_jsonschema():
    print(json.dumps(Result.model_json_schema()))

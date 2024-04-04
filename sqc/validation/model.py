import json

from pydantic import BaseModel


class WorstClash(BaseModel):
    magnitude: float
    atom: str
    other_atom: str
    other_residue: "Residue"


class Residue(BaseModel):
    number: int
    chain: str
    residue_type: str
    worst_clash: WorstClash | None = None


class Model(BaseModel):
    number: int
    residues: list[Residue] | None = None


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
    molprobity_versions: MolProbityVersions


class Result(BaseModel):
    status: Status
    pdb_id: str
    models: list[Model]


def print_jsonschema():
    print(json.dumps(Result.model_json_schema()))

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


class Result(BaseModel):
    pdb_id: str
    models: list[Model]


def print_jsonschema():
    print(json.dumps(Result.model_json_schema()))

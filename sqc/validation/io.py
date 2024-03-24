from Bio.PDB.PDBParser import PDBParser
from Bio.PDB.parse_pdb_header import parse_pdb_header
from Bio.PDB.PDBIO import PDBIO, Select
from Bio.PDB.Model import Model

from structlog import get_logger

logger = get_logger()


class ModelSelector(Select):
    def __init__(self, serial_num: int) -> None:
        super().__init__()
        self.serial_num = serial_num

    def accept_model(self, model: Model):
        return 1 if model.serial_num == self.serial_num else 0


def get_pdb_id(path: str) -> str | None:
    with open(path, "r") as pdb_file:
        header = parse_pdb_header(pdb_file)
        return header.get("name")


def split_models(path: str) -> list[tuple[int, str]]:
    """Splits multimodel PDB files into multiple files (one per model)"""
    pdb_id = get_pdb_id(path) or "unknown_pdb_id"
    parser = PDBParser()
    structure = parser.get_structure(pdb_id, path)
    io = PDBIO()
    io.set_structure(structure)
    models = []

    for model in structure.get_models():
        selector = ModelSelector(model.serial_num)
        new_path = f"{path}-model-{model.serial_num}.pdb"
        io.save(new_path, select=selector)
        models.append((model.serial_num, new_path))

    if len(models) != 1:
        logger.debug("Split models into new PDB files", paths=models)

    return models

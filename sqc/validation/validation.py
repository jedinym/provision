from structlog import get_logger

from sqc.validation.io import get_pdb_id, split_models
from sqc.validation.model import (
    Model,
    Result,
    Status,
)
from sqc.validation.molprobity import MolProbity, MolProbityError

logger = get_logger()


class ValidationError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


def validate(path: str) -> str:
    logger.debug(f"Starting validation of {path}")
    pdb_id = get_pdb_id(path) or "unknown_pdb_id"
    model_paths = split_models(path)
    output_models = []
    mp = MolProbity()

    status = Status(molprobity_versions=mp.get_data_versions())

    for model_num, model_path in model_paths:
        model = Model(number=model_num)

        try:
            model.residues = mp.residue_analysis(model_path)
        except MolProbityError:
            status.residue_analysis = False

        try:
            model.clashes = mp.clashscore(model_path)
        except MolProbityError:
            status.clashscore = False

        output_models.append(model)

    result = Result(status=status, pdb_id=pdb_id, models=output_models)
    return result.model_dump_json(exclude_none=True)

from dataclasses import dataclass
from typing import Any
import json
import os
import sys
import xml.etree.ElementTree as ET
import glob

import sqclib

from sqc.validation.model import Residue, Result


@dataclass
class Discrepancy:
    residue: Residue
    name: str
    sqc_value: Any
    pdb_value: Any


def find_pdb_residue(
    sqc_residue: Residue, pdb_residues: list[ET.Element]
) -> ET.Element | None:
    for pdb_residue in pdb_residues:
        attrib = pdb_residue.attrib
        if (
            attrib["resname"] == sqc_residue.residue_type
            and attrib["resnum"] == str(sqc_residue.number)
            and attrib["chain"] == sqc_residue.chain
        ):
            return pdb_residue

    return None


def compare_results(sqc_results, pdb_results: ET.ElementTree) -> list[Discrepancy]:
    sqc_result = Result.model_validate_json(json.dumps(sqc_results))
    residues = sqc_result.models[0].residues
    assert residues is not None

    subgroups = pdb_results.getroot().findall("./ModelledSubgroup")
    discrepancies = []

    for residue in residues:
        pdb_residue = find_pdb_residue(residue, subgroups)
        if pdb_residue is None:
            print(
                f"ERROR: Could not find residue {residue} in XML file", file=sys.stderr
            )
            continue

        discrepancies.extend(compare_residue(residue, pdb_residue))

    return discrepancies


def compare_residue(sqc_residue: Residue, pdb_residue: ET.Element) -> list[Discrepancy]:
    discrepancies = []

    if sqc_residue.rama_torsion is not None:
        sqc_rama = sqc_residue.rama_torsion.angle_combo_range
        pdb_rama = pdb_residue.attrib["rama"]

        if sqc_rama != pdb_rama:
            discrepancies.append(
                Discrepancy(
                    residue=sqc_residue,
                    name="rama_torsion",
                    sqc_value=sqc_rama,
                    pdb_value=pdb_rama,
                )
            )

    return discrepancies


def get_structure_report_pairs(dirpath: str) -> list[tuple[str, str]]:
    pairs = []
    reports = glob.glob(f"{dirpath}/*.xml")

    for structure in glob.iglob(f"{dirpath}/*.cif"):
        pdb_id = os.path.basename(structure)[:4]

        report = next(
            (
                report
                for report in reports
                if os.path.basename(report).startswith(pdb_id)
            ),
            None,
        )
        if not report:
            print(f"ERROR: No report found for structure: {structure}", file=sys.stderr)
            continue

        pairs.append((structure, report))

    return pairs


def main():
    dirpath = sys.argv[1]
    pairs = get_structure_report_pairs(dirpath)
    client = sqclib.SQCClient("localhost:9000", "minioadmin", "minioadmin", False)

    for structure, report in pairs:
        pdb_id = os.path.basename(structure)[:4]
        pdb_results = ET.parse(report)
        sqc_results = client.validate(structure)

        print(f"INFO: comparing pair {(structure, report)}")

        discrepancies = compare_results(sqc_results, pdb_results)
        if discrepancies:
            disc_filepath = os.path.join(dirpath, f"{pdb_id}.disc")
            print(f"INFO: Discrepancies found, writing to: {disc_filepath}")

            with open(disc_filepath, "w") as file:
                file.write(repr(discrepancies))

from dataclasses import dataclass
import pprint
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
    residue: str
    name: str
    sqc_value: Any
    pdb_value: Any


def mk_discrepancy(
    residue: Residue, name: str, sqc_value: Any, pdb_value: Any
) -> Discrepancy:
    return Discrepancy(
        residue=f"{residue.chain} {residue.number} {residue.residue_type} {residue.alt_code}",
        name=name,
        sqc_value=sqc_value,
        pdb_value=pdb_value,
    )


def find_pdb_residue(
    sqc_residue: Residue, pdb_residues: list[ET.Element]
) -> ET.Element | None:
    for pdb_residue in pdb_residues:
        attrib = pdb_residue.attrib
        sqc_alt_code = " " if not sqc_residue.alt_code else sqc_residue.alt_code
        if (
            attrib["resname"] == sqc_residue.residue_type
            and attrib["resnum"] == str(sqc_residue.number)
            and attrib["chain"] == sqc_residue.chain
            and attrib["altcode"] == sqc_alt_code
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
                f"ERROR: Could not find {residue.chain} {residue.number} {residue.residue_type} "
                f"{f'alt: {residue.alt_code}' if residue.alt_code else ''} in XML file",
                file=sys.stderr,
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
                mk_discrepancy(sqc_residue, "rama", sqc_rama, pdb_rama)
            )
    elif "rama" in pdb_residue.attrib:
        discrepancies.append(
            mk_discrepancy(sqc_residue, "rama", None, pdb_residue.attrib["rama"])
        )

    if sqc_residue.sidechain_torsion is not None:
        sqc_rota = sqc_residue.sidechain_torsion
        pdb_rota = pdb_residue.attrib["rota"]

        if pdb_rota == "OUTLIER" and sqc_rota.angle_range != "OUTLIER":
            discrepancies.append(
                mk_discrepancy(
                    sqc_residue, "sidechain_torsion", sqc_rota.angle_range, pdb_rota
                )
            )

        if sqc_rota.angle_range == "Allowed":
            if sqc_rota.rotamer != pdb_rota:
                discrepancies.append(
                    mk_discrepancy(
                        sqc_residue, "sidechain_torsion", sqc_rota.rotamer, pdb_rota
                    )
                )
    elif "rota" in pdb_residue.attrib:
        discrepancies.append(
            mk_discrepancy(sqc_residue, "sidechain_torsion", None, pdb_residue.attrib["rota"])
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
        print(f"INFO: comparing pair {(structure, report)}")
        pdb_id = os.path.basename(structure)[:4]
        pdb_results = ET.parse(report)
        sqc_results = client.validate(structure)

        discrepancies = compare_results(sqc_results, pdb_results)
        if discrepancies:
            disc_filepath = os.path.join(dirpath, f"{pdb_id}.disc")
            print(f"INFO: Discrepancies found, writing to: {disc_filepath}")

            with open(disc_filepath, "w") as file:
                file.write(pprint.pformat(discrepancies))

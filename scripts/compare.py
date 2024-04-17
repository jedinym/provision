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

COMPARE_SIDECHAIN_OUTLIERS = False
COMPARE_RAMA_OUTLIERS = False
COMPARE_LENGTH_OUTLIERS = True
COMPARE_ANGLE_OUTLIERS = False


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


def get_worst_length_outlier(pdb_residue: ET.Element) -> ET.Element:
    outliers = pdb_residue.findall("./bond-outlier")
    return max(outliers, key=lambda x: abs(float(x.attrib["z"])))


def compare_residue(sqc_residue: Residue, pdb_residue: ET.Element) -> list[Discrepancy]:
    discrepancies = []

    if COMPARE_RAMA_OUTLIERS:
        if sqc_residue.rama_torsion is not None:
            sqc_rama = sqc_residue.rama_torsion.angle_combo_range
            pdb_rama = pdb_residue.attrib["rama"]

            if sqc_rama != pdb_rama:
                discrepancies.append(
                    mk_discrepancy(sqc_residue, "rama", sqc_rama, pdb_rama)
                )
            elif "rama" in pdb_residue.attrib:
                discrepancies.append(
                    mk_discrepancy(
                        sqc_residue, "rama", None, pdb_residue.attrib["rama"]
                    )
                )

    if COMPARE_SIDECHAIN_OUTLIERS:
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
                mk_discrepancy(
                    sqc_residue, "sidechain_torsion", None, pdb_residue.attrib["rota"]
                )
            )

    if COMPARE_LENGTH_OUTLIERS:
        if sqc_residue.bond_length_outlier_count != 0:
            assert sqc_residue.worst_bond_length is not None

            if (
                len(pdb_residue.findall("./bond-outlier"))
                != sqc_residue.bond_length_outlier_count
            ):
                discrepancies.append(
                    mk_discrepancy(
                        sqc_residue,
                        "bond length outlier count",
                        sqc_residue.bond_length_outlier_count,
                        len(pdb_residue.findall("./bond-outlier")),
                    )
                )

            pdb_worst_outlier = get_worst_length_outlier(pdb_residue)
            sqc_worst_outlier = sqc_residue.worst_bond_length

            if (
                pdb_worst_outlier.attrib["atom0"] == sqc_worst_outlier.first_atom
                and pdb_worst_outlier.attrib["atom1"] == sqc_worst_outlier.second_atom
            ):
                if pdb_worst_outlier.attrib["z"] != str(sqc_worst_outlier.sigma):
                    discrepancies.append(
                        mk_discrepancy(
                            sqc_residue,
                            "no match in bond outlier sigma",
                            sqc_worst_outlier,
                            pdb_worst_outlier.attrib,
                        )
                    )
            else:
                discrepancies.append(
                    mk_discrepancy(
                        sqc_residue,
                        "no matching bond outlier",
                        sqc_worst_outlier,
                        pdb_worst_outlier.attrib,
                    )
                )

        elif len(pdb_residue.findall("./bond-outlier")) != 0:
            discrepancies.append(
                mk_discrepancy(
                    sqc_residue,
                    "bond outlier",
                    sqc_residue.worst_bond_length,
                    get_worst_length_outlier(pdb_residue),
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

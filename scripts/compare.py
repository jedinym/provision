import json
import os
import sys
import xml.etree.ElementTree as ET

import sqclib

from sqc.validation.model import Residue, Result


def get_sqc_results(dirpath: str):
    client = sqclib.SQCClient("localhost:9000", "minioadmin", "minioadmin", False)

    struct_path = None

    for entry in os.scandir(dirpath):
        if entry.name.endswith(".cif"):
            struct_path = entry.path

    if struct_path is None:
        print("No cif file found in directory", file=sys.stderr)
        exit(1)

    return client.validate(struct_path)


def get_pdb_results(dirpath: str):
    result_path = None

    for entry in os.scandir(dirpath):
        if entry.name.endswith(".xml"):
            result_path = entry.path

    if result_path is None:
        print("No pdb xml file found in directory", file=sys.stderr)
        exit(1)

    return ET.parse(result_path)


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


def compare_results(sqc_results, pdb_results: ET.ElementTree):
    sqc_result = Result.model_validate_json(json.dumps(sqc_results))

    residues = sqc_result.models[0].residues
    assert residues is not None

    subgroups = pdb_results.getroot().findall("./ModelledSubgroup")

    for residue in residues:
        pdb_residue = find_pdb_residue(residue, subgroups)
        if pdb_residue is None:
            print(f"Could not find residue {residue} in XML file")
            continue

        compare_residue(residue, pdb_residue)


def compare_residue(sqc_residue: Residue, pdb_residue: ET.Element):
    if sqc_residue.rama_torsion is not None:
        sqc_rama = sqc_residue.rama_torsion.angle_combo_range
        pdb_rama = pdb_residue.attrib["rama"]

        assert sqc_rama == pdb_rama


def main():
    pdb_results = get_pdb_results(sys.argv[1])
    sqc_results = get_sqc_results(sys.argv[1])

    compare_results(sqc_results, pdb_results)

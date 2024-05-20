from onedep import __apiUrl__
from onedep.api.Validate import Validate
from os import environ
from sqclib import SQCClient

import time

MAX_STRUCTURES = [1, 2, 5, 10, 15, 20, 30, 50, 100]
STRUCTURE = "./test-data/183d.cif"

def run_onedep(n_structures: int) -> None:
    val = Validate(apiUrl=__apiUrl__)

    val.newSession()

    for _ in range(n_structures):
        val.inputModelXyzFile(STRUCTURE)

    val.run()

    while (True):
        time.sleep(1)
        rD = val.getStatus()
        if rD['status'] in ['completed', 'failed']:
            break

def run_sqc(n_structures: int) -> None:
    client = SQCClient(
        access_key=environ["SQC_ACCESS_KEY"],
        secret_key=environ["SQC_SECRET_KEY"],
     )

    ids = []
    for _ in range(n_structures):
        ids.append(client.submit(STRUCTURE))

    for id in ids:
        client.get_result(id)

def main():
    print("N\tOneDep\tSQC")
    for n_structures in MAX_STRUCTURES:

        onedep_start = time.time()
        run_onedep(n_structures)
        onedep_elapsed = time.time() - onedep_start

        sqc_start = time.time()
        run_sqc(n_structures)
        sqc_elapsed = time.time() - sqc_start

        print(f"{n_structures}\t{onedep_elapsed:.2f}\t{sqc_elapsed:.2f}")

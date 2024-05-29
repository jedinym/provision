# SQC
SQC (Structure Quality Control) is a validation service replicating the PDB
standalone validation server.

## First setup
To set up your system for development, create a Python virtual environment and
install PDM:
``` sh
$ python -m venv venv
$ source venv/bin/activate
$ python -m pip install pdm
```

Once you have PDM installed, you can install all of SQC's dependencies:
``` sh
pdm install -G:all
```

## Local development
To create a locally running instance of SQC, you can utilize `docker compose`:

``` sh
docker compose up
```

After the images are fetched and built (building MolProbity can take up to an
hour), the MinIO instance will be available at `localhost:9000` and accessible
using the SQCLib library.

## Deployment
To deploy SQC, first make sure you're still in the virtual environment:
``` sh
$ source venv/bin/activate
```

If you have already installed all the dependencies and want to deploy SQC using
the default configuration, you can run the deployment playbook using the
following command:

``` sh
$ ansible-playbook --inventory ansible/inventory/ ansible/deploy-sqc.yaml --ask-vault-pass
```

You will be prompted for the password to the Ansible vault before continuing.

You do NOT have to tear down SQC to redeploy a new version, 
but if it's necessary, it's a similar process:
``` sh
$ ansible-playbook --inventory ansible/inventory/ ansible/teardown-sqc.yaml --ask-vault-pass
```

### Configuration
To edit SQC's deploy configuration, see [the metacentrum inventory
file](ansible/inventory/host_vars/metacentrum.yaml).

## Management
To access the MinIO management server, visit [MinIO
management](https://sqc-management.dyn.cloud.e-infra.cz) in a browser.

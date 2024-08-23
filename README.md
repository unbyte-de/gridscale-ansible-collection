# Ansible Collection for gridscale

An ansible collection for gridscale.

## Python Version Requirement

This collection requires python version >= 3.12.

## Installation

```sh
ansible-galaxy collection install git+https://github.com/bitnik/gridscale-ansible-collection.git,0.1.0
```

```sh
collections:
  - name: https://github.com/bitnik/gridscale-ansible-collection.git
    type: git
    version: 0.1.0
```

## Development

Install pre-commit.

```sh
# Install the collection from local.
ansible-galaxy collection install ../ --force

# Run the inventory plugin with example configuration.
ansible-inventory -i gs_inventory.yaml --list --yaml

# View the inventory docu in terminal
ansible-doc -t inventory bitnik.gridscale.gs_inventory

# Linting and tests
pre-commit run --all-files
# ansible-test sanity --docker default -v
ansible-test sanity -v
```

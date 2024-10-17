# Ansible Collection for gridscale

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/unbyte-de/gridscale-ansible-collection/main.svg)](https://results.pre-commit.ci/latest/github/unbyte-de/gridscale-ansible-collection/main)

An ansible collection for gridscale.

Currently only an inventory plugin is implemented.

Documentation: https://unbyte-de.github.io/gridscale-ansible-collection/

## Installation

```sh
ansible-galaxy collection install git+https://github.com/unbyte-de/gridscale-ansible-collection.git,0.1.3
```

```sh
collections:
  - name: https://github.com/unbyte-de/gridscale-ansible-collection.git
    type: git
    version: 0.1.3
```

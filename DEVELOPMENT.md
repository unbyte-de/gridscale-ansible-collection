# Development

* https://docs.ansible.com/ansible/latest/dev_guide/developing_plugins.html
* https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html
* https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html

```sh
# Install dependencies
pip install -r requirements_dev.txt

# Install the collection from local.
ansible-galaxy collection install ../ --force

# Run the inventory plugin with example configuration.
ansible-inventory -i gs_inventory.yaml --list --yaml
# ansible-inventory -i gs_inventory.yaml --graph --vars

# View the inventory docu in terminal
ansible-doc -t inventory bitnik.gridscale.gs_inventory
```

## Linting

Install [pre-commit](https://pre-commit.com/).

```sh
pre-commit run --all-files
# ansible-test sanity --docker default -v
ansible-test sanity -v
# https://ansible.readthedocs.io/projects/antsibull-docs/collection-docs/#linting-collection-docs
# antsibull-docs lint-collection-docs --plugin-docs .
```

## Documentation

https://ansible.readthedocs.io/projects/antsibull-docs/collection-docs/#building-a-docsite

```sh
# Create a subdirectory which should contain the docsite:
mkdir built-docs

# Install the collection from local. So we can use `--use-current` flag in the next step.
ansible-galaxy collection install ../ --force

# Create a Sphinx project for the collection:
antsibull-docs sphinx-init --use-current --squash-hierarchy bitnik.gridscale --dest-dir built-docs

# Copy conf files
cp .github/workflows/docs/conf.py built-docs/
cp .github/workflows/docs/antsibull-docs.cfg built-docs/

# Install requirements for the docsite build
# (if you don't have an active venv, create one!)
cd built-docs
python -m pip install -r requirements.txt

# Build the docsite by:
#  1. running antsibull-docs to create the RST files for the collection,
#  2. running Sphinx to compile everything to HTML
./build.sh

# Open the built HTML docsite in a browser like Firefox:
firefox build/html/index.html
```

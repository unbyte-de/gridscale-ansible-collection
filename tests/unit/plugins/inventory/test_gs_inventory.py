import json
from pathlib import Path

import pytest
from ansible.inventory.data import InventoryData
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from ansible_collections.unbyte.gridscale.plugins.inventory.gs_inventory import InventoryModule


@pytest.fixture(scope="module")
def inventory():
    r = InventoryModule()
    r.inventory = InventoryData()
    r.loader = DataLoader()
    r.templar = Templar(loader=r.loader)
    return r


def test_verify_file(tmp_path, inventory):
    file = tmp_path / "test.gs_inventory.yaml"
    file.touch()
    assert inventory.verify_file(str(file)) is True


def test_verify_file_bad_name(inventory):
    assert inventory.verify_file("test.gs_inventory.ini") is False


def test_verify_file_bad_config(inventory):
    assert inventory.verify_file("test.gs_inventory.yaml") is False


DEFAULT_OPTIONS = {
    "compose": {},
    "groups": {},
    "groups_filter": [],
    "host_vars_filter": ["uuid", "hostname", "location", "labels", "status", "public_ips", "ansible_host"],
    "hostname_template": "",
    "hostvars_prefix": "",
    "hostvars_suffix": "",
    "keyed_groups": [],
    "locations_filter": [],
    "main_group": "",
    "status_filter": [],
    "strict": False,
    "use_extra_vars": False,
}


def get_option(options):
    options = DEFAULT_OPTIONS | options

    def f(option):
        return options.get(option)

    return f


@pytest.mark.parametrize(
    "input_file, options, expected_file",
    [
        # Doesn't filter anything out (no options defined)
        ("servers.json", {}, "servers_expected_all.json"),
        # Doesn't filter anything out
        (
            "servers.json",
            {"locations_filter": ["de/fra", "de/ha"], "status_filter": ["active", "paused"]},
            "servers_expected_all.json",
        ),
        # Filters everything out (status)
        ("servers.json", {"locations_filter": ["de/fra"], "status_filter": ["invalid"]}, "servers_expected_empty.json"),
        # Filters everything out (location)
        ("servers.json", {"locations_filter": ["de/x"], "status_filter": ["active"]}, "servers_expected_empty.json"),
        # Doesn't filter anything out
        (
            "servers.json",
            {"locations_filter": ["de/fra", "de/ha", "de/x"], "status_filter": ["active", "paused", "invalid"]},
            "servers_expected_all.json",
        ),
        # Filters based on location and status
        ("servers.json", {"locations_filter": ["de/fra"], "status_filter": ["active"]}, "servers_expected_one.json"),
    ],
)
def test_fetch_servers(inventory, mocker, input_file, options, expected_file):
    inventory._configure_gridscale_client = mocker.Mock()
    # Read servers from json
    with open(Path(__file__).parent.joinpath(f"files/test_fetch_servers/{input_file}")) as f:
        inventory._servers = json.load(f)

    inventory.get_option = mocker.Mock(side_effect=get_option(options))

    # Fetch servers
    servers = inventory._fetch_servers()
    # Read expected result from file
    with open(Path(__file__).parent.joinpath(f"files/test_fetch_servers/{expected_file}")) as f:
        servers_expected = json.load(f)
    # Compare
    assert servers == servers_expected


@pytest.mark.parametrize(
    "input_file, options, expected_file",
    [
        (
            "servers.json",
            # No options are defined. Everything is in the inventory.
            {},
            "servers_expected_01.json",
        ),
        (
            "servers.json",
            {
                # Main group is added (instead of using "all" as main group).
                "main_group": "gridscale",
                # Filter host vars with following.
                "host_vars_filter": ["ansible_host", "location"],
                # These 2 options shouldn't have affect here. They are used in `_fetch_servers`.
                "locations_filter": ["de/x"],
                "status_filter": ["invalid"],
            },
            "servers_expected_02.json",
        ),
        (
            "servers.json",
            {
                # Main group is added (instead of using "all" as main group).
                "main_group": "gridscale",
                # "keyed_groups": [{"key": "location", "separator": ""}],
                # Generate a new group "cp" based on hostname.
                "groups": {"cp": "'master' in hostname"},
            },
            "servers_expected_03.json",
        ),
        (
            "servers.json",
            {
                # Main group is added (instead of using "all" as main group).
                "main_group": "gridscale",
                # Generate new groups based on hostname.
                "groups": {"cp": "'master' in hostname", "node": "'master' not in hostname and 'node' in hostname"},
                # Filter out all hosts except ones in "cp" group.
                "groups_filter": ["cp"],
            },
            "servers_expected_04.json",
        ),
        (
            "servers.json",
            {
                # Main group is added (instead of using "all" as main group).
                "main_group": "gridscale",
                # Template hostname.
                "hostname_template": "example-{{ location.replace('/', '-') }}-{{ hostname }}",
                # Add suffix and prefix to host vars.
                "hostvars_prefix": "prefix_",
                "hostvars_suffix": "_suffix",
                # Filter host vars with following. Note that host var name must included the prefix and the suffix.
                "host_vars_filter": ["ansible_host", "prefix_location_suffix"],
            },
            "servers_expected_05.json",
        ),
    ],
)
def test_populate(inventory, mocker, input_file, options, expected_file):
    with open(Path(__file__).parent.joinpath(f"files/test_populate/{input_file}")) as f:
        servers = json.load(f)

    inventory.get_option = mocker.Mock(side_effect=get_option(options))

    inventory._populate(servers)

    # Serialize inventory to compare
    inventory_data = {}
    for k, v in inventory.inventory.serialize().items():
        if k in ["groups", "hosts"]:
            inventory_data[k] = {}
            for kk, vv in v.items():
                data = vv.serialize()
                if k == "groups":
                    data["hosts"] = [h.name for h in data["hosts"]]
                    data["parent_groups"] = [p["name"] for p in data["parent_groups"]]
                if k == "hosts":
                    data["groups"] = [g["name"] for g in data["groups"]]
                    data.pop("uuid")
                inventory_data[k][kk] = data

    with open(Path(__file__).parent.joinpath(f"files/test_populate/{expected_file}")) as f:
        e = json.load(f)

    # from pprint import pprint
    # pprint(inventory_data)
    # pprint(e)

    assert e == inventory_data

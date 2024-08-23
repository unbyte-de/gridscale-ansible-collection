# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#documentation-block
# The DOCUMENTATION block must be valid YAML.
DOCUMENTATION = """
name: gs_inventory
short_description: Ansible dynamic inventory plugin for gridscale.

description:
  - Reads the inventory from gridscale API.
  - Uses a YAML configuration file that ends with C(gs_inventory.yml) or C(gs_inventory.yaml).

author:
  - Kenan Erdogan (@bitnik)

requirements:
  - gs_api_client >= 2.2.1

extends_documentation_fragment:
  - constructed
  - inventory_cache

options:
  plugin:
    description: gridscale inventory plugin name.
    required: true
    choices: [gs_inventory, bitnik.gridscale.gs_inventory]
  api_token:
    description:
      - The token for gridscale API.
    type: str
    required: true
    aliases: [token]
    env:
      - name: GRIDSCALE_API_TOKEN
  user_uuid:
    description:
      - The user UUID for gridscale API.
    type: str
    required: true
    env:
      - name: GRIDSCALE_USER_UUID
  host_vars_filter:
    description: |
      Add only these vars to hosts in inventory.
      This doesn't filter vars generated via O(compose).
    default: ["uuid", "hostname", "location", "labels", "status", "public_ips", "ansible_host"]
    type: list
    elements: str
    required: false
  locations_filter:
    description: Populate inventory with instances in this location.
    default: []
    type: list
    elements: str
    required: false
  status_filter:
    description: Populate inventory with instances with this status.
    default: []
    type: list
    elements: str
    required: false
  main_group:
    description: The group all servers are automatically added to.
    type: str
    required: false
  groups_filter:
    description: |
      Populate inventory with instances in this group.
      This doesn't filter default groups "all" and "ungrouped", and also groups defined via O(main_group) and O(groups), but O(keyed_groups).
    default: []
    type: list
    elements: str
    required: false
  hostname_template:
    description: |
      A template for the server hostname.
      Variables are the host variables.
      If not defined, the server name from gridscale is used.
    type: str
  hostvars_prefix:
    description: The prefix for host variable names that are coming from gridscale.
    type: str
    default: ""
    required: false
  hostvars_suffix:
    description: The suffix for host variable names that are coming from gridscale.
    type: str
    default: ""
    required: false
"""

EXAMPLES = """
TODO
"""

from importlib.metadata import PackageNotFoundError, version

from ansible.errors import AnsibleError
from ansible.inventory.data import InventoryData
from ansible.module_utils.common.text.converters import to_native
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible.utils.vars import combine_vars

from ..module_utils.version import compare_version

try:
    from gs_api_client import Configuration, SyncGridscaleApiClient
except ImportError as e:
    # Added this to satisfy `ansible-test sanit`.
    # This is hanled better in `InventoryModule._check_required method`.
    pass


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "bitnik.gridscale.gs_inventory"

    def __init__(self):
        super().__init__()
        self._check_required()

    def _check_required(self):
        # return super()._check_required()
        requirements_found = False
        for l in DOCUMENTATION.splitlines():
            if l == "requirements:":
                requirements_found = True
                continue
            elif requirements_found is True and l not in ["", "extends_documentation_fragment:"]:
                l = l.strip("- ")
                req = l.split(" ")[0].strip()
                req_version = l.split(" ")[-1].strip()
                try:
                    v = version(req)
                except PackageNotFoundError as e:
                    raise AnsibleError(f"Required package '{req}' is not installed: {to_native(e)}")
                if not compare_version(v, req_version):
                    raise AnsibleError(
                        f"Required package '{req}' must have version >= {req_version}. It has version {v} now."
                    )
            else:
                break

    def _get_client(self):
        # Initiate the configuration
        config = Configuration()
        config.api_key["X-Auth-Token"] = self.get_option("api_token")
        config.api_key["X-Auth-UserId"] = self.get_option("user_uuid")

        # Setup the client
        api_client = SyncGridscaleApiClient(configuration=config)

        return api_client

    def _configure_gridscale_client(self) -> None:
        self.client = self._get_client()
        # Ensure credentials are valid.
        try:
            self._servers = self.client.get_servers()
        except Exception as e:
            # raise AnsibleError('Invalid gridscale API credentials.') from e
            raise AnsibleError(f"Invalid gridscale API credentials: {to_native(e)}")

    def _fetch_servers(self) -> list[dict]:
        # Configure the client to connect gridscale API.
        self._configure_gridscale_client()
        # Fetch servers
        servers = list(self._servers.get("servers", {}).values())
        # Filter servers by location and status
        if locations := self.get_option("locations_filter"):
            servers = [s for s in servers if s["location_name"] in locations]
        if status := self.get_option("status_filter"):
            servers = [s for s in servers if s["status"] in status]
        return servers

    def verify_file(self, path: str) -> bool:
        valid = False
        if super().verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(("gs_inventory.yaml", "gs_inventory.yml")):
                valid = True
        return valid

    def parse(
        self,
        inventory: InventoryData,
        loader: DataLoader,
        path: str,
        cache: bool = True,
    ) -> None:
        """ "
        This method does the bulk of the work in the plugin. It takes the following parameters:

        * inventory: inventory object with existing data and the methods to add hosts/groups/variables to inventory
        * loader: Ansible's DataLoader. The DataLoader can read files, auto load JSON/YAML and decrypt vaulted data, and cache read files.
        * path: string with inventory source (this is usually a path, but is not required)
        * cache: indicates whether the plugin should use or avoid caches (cache plugin and/or loader).
          This value comes from the inventory manager and indicates whether the inventory is being refreshed
          (such as by the --flush-cache or the meta task refresh_inventory).
        """
        # Call base method to ensure properties are available for use with other helper methods.
        super().parse(inventory, loader, path, cache)

        # Read inventory config.
        # This method will parse 'common format' inventory sources and
        # update any options declared in DOCUMENTATION as needed.
        self._read_config_data(path)

        # Fetch servers with or without caching
        # Retrieve a unique cache key.
        # The cache is enabled and the cache plugin is loaded within `_read_config_data` method.
        cache_key = self.get_cache_key(path)
        # Get the user's cache option to see if we should save the cache if it is changing.
        user_cache_setting = self.get_option("cache")
        # Check if the user has caching enabled and the cache isn't being refreshed (`cache`=True).
        attempt_to_read_cache = user_cache_setting and cache
        # Check if the user has caching enabled and the cache is being refreshed (`cache`=False).
        cache_needs_update = user_cache_setting and not cache
        if attempt_to_read_cache:
            try:
                servers = self._cache[cache_key]
            except KeyError:
                # This occurs if the cache_key is not in the cache or if the cache_key expired, so the cache needs to be updated.
                cache_needs_update = True

        if not attempt_to_read_cache or cache_needs_update:
            servers = self._fetch_servers()
        if cache_needs_update:
            self._cache[cache_key] = servers

        # Populate the inventory
        # Add a top group
        if main_group := self.get_option("main_group"):
            self.inventory.add_group(group=main_group)

        # Add hosts and host vars
        hostname_template = self.get_option("hostname_template")
        hostvars_prefix = self.get_option("hostvars_prefix")
        hostvars_suffix = self.get_option("hostvars_suffix")
        strict = self.get_option("strict")
        for s in servers:
            public_ips: list[str] = [ip["ip"] for ip in s["relations"]["public_ips"]]
            host_vars = {
                "uuid": s["object_uuid"],
                "hostname": s["name"],
                "location": s["location_name"],
                "labels": s["labels"],
                "status": s["status"],
                "public_ips": public_ips,
                "ansible_host": public_ips[0] if public_ips else s["name"],
            }
            if hostname_template:
                templar = self.templar
                templar.available_variables = combine_vars(host_vars, self._vars)
                hostname = templar.template(hostname_template)
                host_vars.update(
                    {
                        "hostname": hostname,
                        "hostname_remote": s["name"],
                    }
                )

            # Update host vars with given prefix and suffix
            if hostvars_prefix or hostvars_suffix:
                for k in list(host_vars.keys()):
                    if k != "ansible_host":
                        host_vars[f"{hostvars_prefix}{k}{hostvars_suffix}"] = host_vars.pop(k)

            # Add host
            if main_group:
                self.inventory.add_host(host_vars["hostname"], group=main_group)
            else:
                self.inventory.add_host(host_vars["hostname"], group="all")
            # Add host variables
            for var_name, var_value in host_vars.items():
                # if not host_vars_filter or (host_vars_filter and var_name in host_vars_filter):
                if (host_vars_filter := self.get_option("host_vars_filter")) and (var_name in host_vars_filter):
                    self.inventory.set_variable(host_vars["hostname"], var_name, var_value)

            # Add variables created by the user's Jinja2 expressions to the host
            self._set_composite_vars(self.get_option("compose"), host_vars, host_vars["hostname"], strict=strict)
            # Create user-defined groups using variables and Jinja2 conditionals
            self._add_host_to_composed_groups(
                self.get_option("groups"), host_vars, host_vars["hostname"], strict=strict
            )
            self._add_host_to_keyed_groups(
                self.get_option("keyed_groups"), host_vars, host_vars["hostname"], strict=strict
            )

        # Filter out all hosts that is not in any group defined in groups_filter.
        if groups_filter := self.get_option("groups_filter"):
            for host_name in list(self.inventory.hosts):
                host = self.inventory.get_host(host_name)
                delete = True
                for group in host.groups:
                    if group.name in groups_filter:
                        delete = False
                if delete is True:
                    self.inventory.remove_host(host)
            for group_name in list(self.inventory.groups):
                _groups_filter = (
                    groups_filter
                    + ["all", "ungrouped"]
                    + ([main_group] if main_group else [])
                    + list(self.get_option("groups"))
                )
                if group_name not in _groups_filter:
                    self.inventory.remove_group(group_name)

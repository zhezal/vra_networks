"""Class for generating VRA test/preview network infrastructure
configuration."""

__author__ = "ZHEZLYAEV Aleksandr"
__version__ = "1.0"

# -*- coding: utf-8 -*-

import ipaddress
from typing import Final, Optional

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

from Utils.zlogger import zLogger


class ExceptionVra(Exception):
    """General exception class for network VRA."""


class ExceptionGenerateConfig(ExceptionVra):
    """Exception class for generating the VRA network configuration."""

    def __init__(self, *args):
        self.message = args[0] if args else "Undefined error."

    def __str__(self):
        return f"Error: {self.message}"


class Vra:
    """Base class for creating VRA test/preview network configurations."""

    __slots__ = (
        "__vlan_id",
        "__subnet_with_prefix_len",
        "__rd_extended_part",
        "rd",
        "intf_gateway_ip_and_netmask",
        "network_ip_and_netmask",
        "vlan_name",
        "vrf_name",
        "logger",
        "__intf_in_scope_d",
    )

    DC_CORE: Final = ["MS", "ms"]
    DC_ACCESS: Final = ["SW", "NX", "sw", "nx"]
    VLAN_SCOPE: Final = "SCOPE_VRA"
    RD_BASE_PART: Final = "172.31.255.255"

    def __init__(
        self,
        vlan_id: int,
        subnet_with_prefix_len: str,
        rd_extended_part: int,
        intf_in_scope_d: dict,
    ) -> None:
        """Class Vra __init__."""

        self.vlan_id = vlan_id
        self.subnet_with_prefix_len = subnet_with_prefix_len
        self.rd_extended_part = rd_extended_part
        self.rd = self.RD_BASE_PART + ":" + str(rd_extended_part)
        self.intf_gateway_ip_and_netmask = self._gateway_and_netmask_from_cidr(subnet_with_prefix_len)
        self.network_ip_and_netmask = self._network_with_netmask_from_cidr(subnet_with_prefix_len)
        self.intf_in_scope_d = intf_in_scope_d
        self.logger = zLogger()

    def __repr__(self):
        return f"{self.__class__}"

    def __str__(self):
        return f"{self.__class__.__name__}"

    def generate_config(self):
        raise NotImplementedError("The method generate_config() must be redefined in the child class.")

    @property
    def vlan_id(self):
        """Getter for vlan id."""
        return self.__vlan_id

    @vlan_id.setter
    def vlan_id(self, vlan_id):
        """Setter for vlan id."""
        self._verify_vlan_id(vlan_id)
        self.__vlan_id = vlan_id

    @property
    def rd_extended_part(self):
        """Getter for rd extended part."""
        return self.__rd_extended_part

    @rd_extended_part.setter
    def rd_extended_part(self, rd_extended_part):
        """Setter for rd."""
        self._verify_rd_extended_part(rd_extended_part)
        self.__rd_extended_part = rd_extended_part

    @property
    def subnet_with_prefix_len(self):
        """Getter for network address with the prefix length."""
        return self.__subnet_with_prefix_len

    @subnet_with_prefix_len.setter
    def subnet_with_prefix_len(self, subnet_with_prefix_len):
        """Setter for network address with the prefix length."""
        self._verify_subnet_with_prefix_len(subnet_with_prefix_len)
        self.__subnet_with_prefix_len = subnet_with_prefix_len

    @property
    def intf_in_scope_d(self):
        """Getter for interfaces scope dict."""
        return self.__intf_in_scope_d

    @intf_in_scope_d.setter
    def intf_in_scope_d(self, intf_in_scope_d):
        """ "Setter for interfaces scope dict."""
        self._verify_intf_in_scope_d(intf_in_scope_d)
        self.__intf_in_scope_d = intf_in_scope_d

    @staticmethod
    def _verify_subnet_with_prefix_len(subnet_with_prefix_len: str) -> None:
        """The internal method checks the correctness of the network address
        with the prefix length."""
        if not isinstance(subnet_with_prefix_len, str):
            raise TypeError("The network address with the prefix length must be a string.")

        net_with_pf = subnet_with_prefix_len.split("/")
        if len(net_with_pf) != 2:
            raise TypeError("Invalid format for recording the network address with prefix length.")

        try:
            subnet = ipaddress.ip_network(subnet_with_prefix_len)
        except ValueError:
            raise ValueError(f"{subnet_with_prefix_len} does not appear to be an IPv4 network.")

        if not subnet.network_address.is_private:
            raise ValueError(f"{subnet_with_prefix_len} is not in the RFС1918 address space.")

    @staticmethod
    def _verify_vlan_id(vlan_id: int) -> None:
        """The internal method for checking valid vlan id value."""
        if not isinstance(vlan_id, int):
            raise TypeError("The vlan id value must be an integer.")

        if vlan_id not in range(1, 1002) and vlan_id not in range(1006, 4095):
            raise ValueError("The vlan id value must be in the range from 1 to 1001 or in the range from 1006 to 4094.")

    @staticmethod
    def _verify_rd_extended_part(rd_extended_part: int) -> None:
        """The internal method for checking valid route distinguisher (rd)
        value."""
        if not isinstance(rd_extended_part, int):
            raise TypeError("The extended part of route distinguisher (rd) value must be an integer.")

        if rd_extended_part <= 0:
            raise ValueError(
                "The extended part of the route distinguisher (rd) after the colon must be a positive integer."
            )

    @staticmethod
    def _verify_subnet_with_prefix_len(subnet_with_prefix_len: str) -> None:
        """The internal method checks the correctness of the network address
        with the prefix length."""
        if not isinstance(subnet_with_prefix_len, str):
            raise TypeError("The network address with the prefix length must be a string.")

    @staticmethod
    def _verify_intf_in_scope_d(intf_in_scope_d):
        """The method checks the correctness of the structure of the
        transmitted dictionary."""
        if not isinstance(intf_in_scope_d, dict):
            raise TypeError("Interfaces parameters should be a dictionary.")

        for netdev_hostname, intfs_dict in intf_in_scope_d.items():
            if not isinstance(netdev_hostname, str):
                raise TypeError("Incorrect interface dictionary format. Network Device hostname must be a string.")
            if not isinstance(intfs_dict, dict):
                raise TypeError("Incorrect interface dictionary format.")

            for intf, intf_params_dict in intfs_dict.items():
                if not isinstance(intf, str):
                    raise TypeError("Incorrect interface dictionary format. Interface name value must be a string.")

                if not isinstance(intf_params_dict.get("intf_mode"), str):
                    raise TypeError("Incorrect interface dictionary format. Interface mode value must be a string.")

                if not isinstance(intf_params_dict.get("allowed_vlans"), list):
                    raise TypeError("Incorrect interface dictionary format. Allowed vlans value must be a list.")

                for vlan_id in intf_params_dict.get("allowed_vlans"):
                    if not isinstance(vlan_id, int):
                        raise TypeError(
                            "Incorrect interface dictionary format. Vlan id value in allowed vlans list must be an integer."
                        )

    @staticmethod
    def _gateway_and_netmask_from_cidr(subnet_with_prefix_len: str) -> str:
        """The method converts a network with a prefix len into a gateway
        address and gateway mask."""

        subnet = ipaddress.ip_network(subnet_with_prefix_len)
        gateway_ip = str(subnet.network_address + 1)
        gateway_netmask = str(subnet.netmask)
        return gateway_ip + " " + gateway_netmask

    @staticmethod
    def _network_with_netmask_from_cidr(subnet_with_prefix_len: str) -> str:
        """The method converts a network with a prefix len into a network
        address and network mask."""

        subnet = ipaddress.ip_network(subnet_with_prefix_len)
        ip_address_net = str(subnet.network_address)
        ip_address_netmask = str(subnet.netmask)
        return ip_address_net + " " + ip_address_netmask

    def _jinja2_generate_template(self, template: str, init_dict: dict) -> str:
        """The method generates the specified configuration through jinja2
        templates."""

        jinja2_env = Environment(
            loader=FileSystemLoader("net_templates"),
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=["jinja2.ext.loopcontrols"],
        )

        try:
            jinja2_template = jinja2_env.get_template(template)
            generated_config: str = jinja2_template.render(init_dict)
            return generated_config

        except TemplateSyntaxError as jinja2_error:
            self.logger.log("all").error(
                f"Jinja2 template syntax error during render: {jinja2_error.filename}:{jinja2_error.lineno} error: {jinja2_error.message}."
            )

    def _create_vlan_config(self, verbose: Optional[bool] = False) -> str:
        """Create vlan vra config with Jinja2."""

        vlan_data = {
            "vlan_id": self.vlan_id,
            "vlan_name": self.vlan_name,
            "environment": self.environment,
        }

        generated_vlan_config: str = self._jinja2_generate_template("vlan_template.jinja2", vlan_data)

        if generated_vlan_config:
            if verbose:
                self.logger.log("all").info(f"The vlan {self.vlan_id} configuration was completed successfully.")
            return generated_vlan_config
        else:
            raise ExceptionGenerateConfig(f"Error generating vlan {self.vlan_id} configuration.")

    def _create_vrf_config(self, verbose: Optional[bool] = False) -> str:
        """Create vrf vra config with Jinja2."""

        vrf_data = {
            "vrf_name": self.vrf_name,
            "rd": self.rd,
            "rd_extended_part": self.rd_extended_part,
            "rt_export": self.rt_export,
            "rt_import": self.rt_import,
        }

        generated_vrf_config: str = self._jinja2_generate_template("vrf_template.jinja2", vrf_data)

        if generated_vrf_config:
            if verbose:
                self.logger.log("all").info(f"The vrf {self.vrf_name} configuration was completed successfully.")
            return generated_vrf_config
        else:
            raise ExceptionGenerateConfig(f"Error generating vrf {self.vrf_name} configuration.")

    def _create_l3_intf_config(self, verbose: Optional[bool] = False) -> str:
        """Create interfaces vra config with Jinja2."""

        intf_data = {
            "intf_gateway_ip_and_netmask": self.intf_gateway_ip_and_netmask,
            "vlan_id": self.vlan_id,
            "vrf_name": self.vrf_name,
        }

        generated_intf_config: str = self._jinja2_generate_template("l3_intf_template.jinja2", intf_data)

        if generated_intf_config:
            if verbose:
                self.logger.log("all").info(
                    f"The interface {self.intf_gateway_ip_and_netmask} configuration was completed successfully."
                )
            return generated_intf_config
        else:
            raise ExceptionGenerateConfig(
                f"Error generating interface {self.intf_gateway_ip_and_netmask} configuration."
            )

    def _create_ip_prefix_list_config(self, verbose: Optional[bool] = False) -> str:
        """Create ip prefix-list config for vra networks with Jinja2."""

        ip_prefix_list_data = {
            "environment": self.environment,
            "subnet_with_prefix_len": self.subnet_with_prefix_len,
        }

        generated_ip_prefix_list_config: str = self._jinja2_generate_template(
            "ip_prefix_list_template.jinja2", ip_prefix_list_data
        )

        if generated_ip_prefix_list_config:
            if verbose:
                self.logger.log("all").info(
                    f"The ip prefix list {self.subnet_with_prefix_len} configuration was completed successfully."
                )
            return generated_ip_prefix_list_config
        else:
            raise ExceptionGenerateConfig(
                f"Error generating ip prefix list {self.subnet_with_prefix_len} configuration."
            )

    def _create_ip_routing_config(self, verbose: Optional[bool] = False) -> str:
        """Create ip ip routing config for vra networks with Jinja2."""

        ip_routing_config_data = {
            "environment": self.environment,
            "fw_vrf_testprev_intf_address": self.fw_vrf_testprev_intf_address,
            "fw_vrf_transit_intf_address": self.fw_vrf_transit_intf_address,
            "network_ip_and_netmask": self.network_ip_and_netmask,
            "vrf_name": self.vrf_name,
        }

        generated_ip_routing_config: str = self._jinja2_generate_template(
            "ip_routing_template.jinja2", ip_routing_config_data
        )

        if generated_ip_routing_config:
            if verbose:
                self.logger.log("all").info(
                    f"The ip routing configuration for network {self.network_ip_and_netmask} was completed successfully."
                )
            return generated_ip_routing_config
        else:
            raise ExceptionGenerateConfig(
                f"Error generating ip routing configuration for network {self.network_ip_and_netmask}."
            )

    def _create_l2_intf_config(self, netdev_hostname: str, verbose: Optional[bool] = False) -> str:
        """Create l2 interfaces config for vra networks with Jinja2."""
        intf_d = self.intf_in_scope_d.get(netdev_hostname)

        for intf_params_d in intf_d.values():
            intf_params_d.update(dict(vra_vlan_id=self.vlan_id))

        jinja2_env = Environment(
            loader=FileSystemLoader("net_templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        try:
            jinja2_template = jinja2_env.get_template("l2_intf_template.jinja2")
            generated_config: str = jinja2_template.render(dict=intf_d)

            return generated_config

        except TemplateSyntaxError as jinja2_error:
            self.logger.log("all").error(
                f"Jinja2 template syntax error during render: {jinja2_error.filename}:{jinja2_error.lineno} error: {jinja2_error.message}."
            )

    def generate_config(self, netdev_hostname: str, verbose: Optional[bool] = False):
        """The method generates a configuration for the VRA network
        infrastructure."""

        if any(map(netdev_hostname.startswith, self.DC_CORE)):
            vlan_config: str = self._create_vlan_config(verbose)
            vrf_config: str = self._create_vrf_config(verbose)
            intf_l3_config: str = self._create_l3_intf_config(verbose)
            ip_prefix_list_config: str = self._create_ip_prefix_list_config(verbose)
            ip_routing_config: str = self._create_ip_routing_config(verbose)
            intf_l2_config: str = self._create_l2_intf_config(netdev_hostname, verbose)
            generated_config = (
                vlan_config + vrf_config + intf_l3_config + ip_prefix_list_config + ip_routing_config + intf_l2_config
            )

            return dict([(netdev_hostname, generated_config)])

        elif any(map(netdev_hostname.startswith, self.DC_ACCESS)):
            vlan_config: str = self._create_vlan_config(verbose)
            intf_l2_config: str = self._create_l2_intf_config(netdev_hostname, verbose)
            generated_config = vlan_config + intf_l2_config

            return dict([(netdev_hostname, generated_config)])

        else:
            raise ExceptionGenerateConfig("The configuration can only be configured for MS/MX/SW/NX devices.")


class VraTest(Vra):
    """Inherited class for creating VRA Test network configurations."""

    __slots__ = ()

    rt_export: Final = ["3001:12"]
    rt_import: Final = ["3001:11"]
    fw_vrf_testprev_intf_address: Final = "172.16.100.6"
    fw_vrf_transit_intf_address: Final = "172.16.100.62"
    environment: Final = "TEST"

    def __init__(
        self,
        vlan_id: int,
        subnet_with_prefix_len: str,
        rd_extended_part: int,
        intf_in_scope: list[str],
    ) -> None:
        """Class VraTest __init__."""

        super().__init__(vlan_id, subnet_with_prefix_len, rd_extended_part, intf_in_scope)
        self.vlan_name = "TEST-VRA" + str(self.vlan_id)
        self.vrf_name = "TEST-VRA" + str(self.vlan_id)

    def __repr__(self):
        return f"{self.__class__}: {self.vrf_name}"

    def __str__(self):
        return f"class {self.__class__.__name__}: {self.vrf_name}"


class VraPreview(Vra):
    """Inherited class for creating VRA Preview network configurations."""

    __slots__ = ()

    rt_export: Final = ["3002:12"]
    rt_import: Final = ["3002:11"]
    fw_vrf_testprev_intf_address: Final = "172.16.100.30"
    fw_vrf_transit_intf_address: Final = "172.16.100.70"
    environment: Final = "PREVIEW"

    def __init__(
        self,
        vlan_id: int,
        subnet_with_prefix_len: str,
        rd_extended_part: int,
        intf_in_scope: list[str],
    ) -> None:
        """Class VraPreview __init__."""
        super().__init__(vlan_id, subnet_with_prefix_len, rd_extended_part, intf_in_scope)
        self.vlan_name = "PREVIEW-VRA" + str(self.vlan_id)
        self.vrf_name = "PREVIEW-VRA" + str(self.vlan_id)

    def __repr__(self):
        return f"{self.__class__}: {self.vrf_name}"

    def __str__(self):
        return f"class {self.__class__.__name__}: {self.vrf_name}"

"""Useful classes for network infrastructure."""

__author__ = "ZHEZLYAEV Aleksandr"
__version__ = "1.0"

# -*- coding: utf-8 -*-


import re
from string import ascii_letters, digits
from typing import Optional

from CiscoInterfaceNameConverter.converter import convert_interface

from Utils.zlogger import zLogger


class UnsupportedOsType(Exception):
    """Exception class is generated when the operating system is not supported
    by the parser."""

    def __init__(self, *args):
        self.message = args[0] if args else "Undefined error."

    def __str__(self):
        return f"Error: {self.message}"


class NetworkParsingError(Exception):
    """An exception is generated when data from the device was received, but
    the parser could not process them."""

    def __init__(self, *args):
        self.message = args[0] if args else "Undefined error."

    def __str__(self):
        return f"Error: {self.message}"


class NetHelper:
    """The class with useful methods for getting data from network
    equipment."""

    def __init__(self, ssh_conn, verbose: Optional[bool] = False) -> None:
        self.ssh_conn = ssh_conn
        self.verbose = verbose
        self.logger = zLogger()

    def __repr__(self):
        return f"{self.__class__}"

    def __str__(self):
        return f"{self.__class__.__name__}"

    @staticmethod
    def _verify_vlan_scope_name(vlan_scope_name: str) -> None:
        """The internal method checks the correctness of vlan scope name."""

        if not isinstance(vlan_scope_name, str):
            raise TypeError("The vlan scope name must be a string.")
        if len(vlan_scope_name) < 1:
            raise TypeError("The vlan scope name must have at least one character.")

        letters = ascii_letters + digits + "_"
        if len(vlan_scope_name.strip(letters)) != 0:
            raise TypeError("Only alphabetic characters, numbers and hyphens can be used in a vlan scope name.")

    def get_intf_in_scope_by_description(self, scope_name: str) -> dict[str, dict[str | list[int]]]:
        """The method searches for interfaces in the description of which the
        vlan scope of interest is specified."""

        # Проверяем корректность имени VLAN SCOPE
        self._verify_vlan_scope_name(scope_name)

        cisco_ios_show_interfaces_description_template = "ntc_templates/cisco_ios_show_interfaces_description.textfsm"

        intfs_d: dict[str, dict[str | list[int]]] = {}
        intfs_l: list[str] = []

        log_msg = "{} [{}] - '{}' exists on {} interfaces."

        if self.ssh_conn.device_type == "cisco_ios":
            show_interfaces_description = self.ssh_conn.send_command(
                f"sh int description",
                use_textfsm=True,
                textfsm_template=cisco_ios_show_interfaces_description_template,
            )
            if not isinstance(show_interfaces_description, list):
                raise UnsupportedOsType(f"{self.__class__} {self.ssh_conn.host} OS isn't supported.")

            for output_d in show_interfaces_description:
                if (
                    re.search(rf"\b{scope_name}\b", output_d.get("descrip"))
                    and output_d.get("status") == "up"
                    and output_d.get("protocol") == "up"
                ):
                    intf_of_scope = output_d.get("port")
                    intfs_l.append(intf_of_scope)

            # Проверяем, есть ли в нашем списке PO-интерфейсы
            po_exist_lst = [i for i in intfs_l if "Po" in i]

            if po_exist_lst:
                po_dict: dict[str, list[str]] = self.__get_po_info()
                all_po_members = [item for sublist in list(po_dict.values()) for item in sublist]
                intfs_l = list(set(intfs_l).difference(set(all_po_members)))

            for intf in intfs_l:
                intf_mode, vlan_list = self.__get_intf_switchport_info(intf)
                intfs_d[intf] = dict(intf_mode=intf_mode, allowed_vlans=vlan_list)

            if self.verbose:
                self.logger.log("all").info(
                    log_msg.format(self.ssh_conn.host, self.ssh_conn.device_type, scope_name, ", ".join(intfs_l))
                )
            else:
                self.logger.log("file").info(
                    log_msg.format(self.ssh_conn.host, self.ssh_conn.device_type, scope_name, ", ".join(intfs_l))
                )

            return intfs_d

        else:
            raise UnsupportedOsType(f"{self.__class__} {self.ssh_conn.host} OS isn't supported.")

    def get_intf_in_scope_by_stp_instance(self, vlan_id: int):
        """The method builds a network tree according to the stp protocol
        data."""

        cisco_ios_show_spanning_tree_template = "ntc_templates/cisco_ios_show_spanning-tree.textfsm"
        stp_tree_d = {}
        log_msg = "{} [{}] - interface {} was found based on the search criteria."

        if self.ssh_conn.device_type == "cisco_ios" or self.ssh_conn.device_type == "cisco_nxos":
            # Смотрим в какие порты подан нужный нам vlan
            sh_spanning_tree = self.ssh_conn.send_command(
                f"sh spanning-tree vlan {vlan_id}",
                use_textfsm=True,
                textfsm_template=cisco_ios_show_spanning_tree_template,
            )

            if not isinstance(sh_spanning_tree, list):
                raise NetworkParsingError(
                    f"{self.__class__} {self.ssh_conn.host} could not process the stp network data output."
                )

            for stp_dict in sh_spanning_tree:
                intf_in_stp_topo = stp_dict.get("interface")
                intf_mode, vlan_list = self.__get_intf_switchport_info(intf_in_stp_topo)
                stp_tree_d[intf_in_stp_topo] = dict(intf_mode=intf_mode, allowed_vlans=vlan_list)

                if self.verbose:
                    self.logger.log("all").info(
                        log_msg.format(self.ssh_conn.host, self.ssh_conn.device_type, intf_in_stp_topo)
                    )
                else:
                    self.logger.log("file").self.info(
                        log_msg.format(self.ssh_conn.host, self.ssh_conn.device_type, intf_in_stp_topo)
                    )

            return stp_tree_d

        else:
            raise UnsupportedOsType(f"{self.__class__} {self.ssh_conn.host} OS isn't supported.")

    def __get_po_info(self) -> dict[str, list[str]]:
        """The method finds the port-channel group members and returns them."""

        cisco_ios_show_etherchannel_summary_template = "ntc_templates/cisco_ios_show_etherchannel_summary.textfsm"
        cisco_nxos_show_port_channel_summary_template = "ntc_templates/cisco_nxos_show_port-channel_summary.textfsm"

        po_dict: dict[str, list[str]] = {}

        if self.ssh_conn.device_type == "cisco_ios":
            show_etherchannel_summary = self.ssh_conn.send_command(
                f"sh etherchannel summary",
                use_textfsm=True,
                textfsm_template=cisco_ios_show_etherchannel_summary_template,
            )
            if isinstance(show_etherchannel_summary, list):
                for output_d in show_etherchannel_summary:
                    po_intf_name = output_d.get("po_name")
                    po_intf_members = output_d.get("interfaces")
                    po_dict[po_intf_name] = po_intf_members

                return po_dict
            else:
                raise NetworkParsingError(
                    f"{self.__class__} {self.ssh_conn.host} could not process the network data output."
                )

        elif self.ssh_conn.device_type == "cisco_nxos":
            show_etherchannel_summary = self.ssh_conn.send_command(
                f"sh port-channel summary",
                use_textfsm=True,
                textfsm_template=cisco_nxos_show_port_channel_summary_template,
            )
            if isinstance(show_etherchannel_summary, list):
                for output_d in show_etherchannel_summary:
                    po_intf_name = output_d.get("bundle_iface")
                    po_intf_members = output_d.get("phys_iface")
                    po_dict[po_intf_name] = po_intf_members

                return po_dict

            else:
                raise NetworkParsingError(
                    f"{self.__class__} {self.ssh_conn.host} could not process the network data output."
                )

        else:
            raise UnsupportedOsType(f"{self.__class__} {self.ssh_conn.host} OS isn't supported.")

    def __parse_allowed_vlan_ranges(self, allowed_vlans: list[str]) -> list[int]:
        """The method parses the ranges of allowed vlans from the resulting
        list."""
        final_lst = []
        all_vlan_done = False

        # Случай когда в строке allowed vlans есть "," например ['100-105,250, 200-205']
        if not all_vlan_done:
            if "," in allowed_vlans:
                vlan_ranges: list[str] = allowed_vlans.split(",")
                for vlan_block in vlan_ranges:
                    if "-" in vlan_block:
                        for i in range(
                            int(vlan_block.split("-")[0]),
                            int(vlan_block.split("-")[1]) + 1,
                        ):
                            final_lst.append(i)
                    else:
                        final_lst.append(int(vlan_block))
                all_vlan_done = True

        # Случай когда в строке allowed vlans есть нет "," например ['100-105']
        if not all_vlan_done:
            if "-" in allowed_vlans:
                for i in range(int(allowed_vlans.split("-")[0]), int(allowed_vlans.split("-")[1]) + 1):
                    final_lst.append(i)
                all_vlan_done = True
            else:
                final_lst.append(int(allowed_vlans))
                all_vlan_done = True
        return final_lst

    def __get_intf_switchport_info(self, intf: str) -> tuple[str, list[int]]:
        """The method determines the type of switchport interface and the
        allowed vlans on the interface."""

        cisco_ios_sh_intf_switchport_template = "ntc_templates/cisco_ios_show_interfaces_switchport.textfsm"
        cisco_nxos_show_interfaces_switchport_template = "ntc_templates/cisco_nxos_show_interfaces_switchport.textfsm"

        if self.ssh_conn.device_type == "cisco_ios":
            sh_int_switchport = self.ssh_conn.send_command(
                f"sh int {intf} switchport",
                use_textfsm=True,
                textfsm_template=cisco_ios_sh_intf_switchport_template,
            )

            intf_mode: str = sh_int_switchport[0].get("mode")
            trunking_vlans: list[str] = sh_int_switchport[0].get("trunking_vlans")[0]

        elif self.ssh_conn.device_type == "cisco_nxos":
            sh_int_switchport = self.ssh_conn.send_command(
                f"sh int {intf} switchport",
                use_textfsm=True,
                textfsm_template=cisco_nxos_show_interfaces_switchport_template,
            )
            intf_mode: str = sh_int_switchport[0].get("mode")
            trunking_vlans: list[str] = sh_int_switchport[0].get("trunking_vlans")

        else:
            raise UnsupportedOsType(f"{self.__class__} {self.ssh_conn.host} OS isn't supported.")

        if intf_mode != "down":
            allowed_vlans = self.__parse_allowed_vlan_ranges(trunking_vlans)
            return intf_mode, allowed_vlans

    def get_cdp_neigbors_by_intf(self, intf: str) -> list[str]:
        """The method looks for CDP neighbors behind the interface on the
        switch."""

        cisco_ios_show_cdp_neighbors_detail_template = "ntc_templates/cisco_ios_show_cdp_neighbors_detail.textfsm"
        cisco_nxos_show_cdp_neighbors_detail_template = "ntc_templates/cisco_nxos_show_cdp_neighbors_detail.textfsm"

        intf_todo: list[str] = []
        neighbors_st = set()

        if "Po" in intf:
            po_dict = self.__get_po_info()
            po_members = po_dict[intf]
            intf_todo = intf_todo + po_members
        else:
            intf_todo.append(intf)

        if self.ssh_conn.device_type == "cisco_ios":
            show_cdp_neighbors_detail = self.ssh_conn.send_command(
                f"sh cdp neighbors detail",
                use_textfsm=True,
                textfsm_template=cisco_ios_show_cdp_neighbors_detail_template,
            )

            if not isinstance(show_cdp_neighbors_detail, list):
                raise NetworkParsingError(
                    f"{self.__class__} {self.ssh_conn.host} could not process the cdp network data output."
                )

            for output_d in show_cdp_neighbors_detail:
                for iface in intf_todo:
                    if iface == convert_interface(output_d.get("local_port"), return_short=True):
                        neighbor_host = output_d.get("destination_host").split(".")[0]
                        neighbors_st.add(neighbor_host)

            return list(neighbors_st)

        elif self.ssh_conn.device_type == "cisco_nxos":
            show_cdp_neighbors_detail = self.ssh_conn.send_command(
                f"sh cdp neighbors detail",
                use_textfsm=True,
                textfsm_template=cisco_nxos_show_cdp_neighbors_detail_template,
            )

            if not isinstance(show_cdp_neighbors_detail, list):
                raise NetworkParsingError(
                    f"{self.__class__} {self.ssh_conn.host} could not process the cdp network data output."
                )

            for output_d in show_cdp_neighbors_detail:
                for iface in intf_todo:
                    if iface == convert_interface(output_d.get("local_port"), return_short=True):
                        neighbor_host = output_d.get("dest_host").split(".")[0]
                        neighbors_st.add(neighbor_host)

            return list(neighbors_st)

        else:
            raise UnsupportedOsType(f"{self.__class__} {self.ssh_conn.host} OS isn't supported.")

    def get_ip_interfaces_status(self, intf_name: str):
        """The method returns the state of the IP interfaces."""

        if self.ssh_conn.device_type == "cisco_ios":
            show_ip_int_brief_output = self.ssh_conn.send_command(
                f"show ip int brief | inc {intf_name}",
                textfsm_template="ntc_templates/cisco_ios_show_ip_interface_brief.textfsm",
                use_textfsm=True,
            )
            return show_ip_int_brief_output

        else:
            raise UnsupportedOsType(f"{self.ssh_conn.host} the OS isn't supported by the class parser.")

    def get_stp_status(self, vlan_id: str) -> list:
        """The method checks the state of the stp on interfaces on network
        devices."""

        if self.ssh_conn.device_type == "cisco_ios" or self.ssh_conn.device_type == "cisco_nxos":
            sh_vl_id_output = self.ssh_conn.send_command(
                f"show spanning-tree vlan {vlan_id}",
                textfsm_template="ntc_templates/cisco_ios_show_spanning-tree.textfsm",
                use_textfsm=True,
            )
            return sh_vl_id_output

        else:
            raise UnsupportedOsType(f"{self.ssh_connection.host} the OS isn't supported by the class parser.")

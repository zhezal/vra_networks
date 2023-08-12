"""Utill for generating VRA test/preview network infrastructure
configuration."""

__author__ = "ZHEZLYAEV Aleksandr"
__version__ = "1.0"

# -*- coding: utf-8 -*-

import ipaddress
import json
import os
import pathlib
import random
import shutil
import time
from datetime import datetime
from enum import Enum
from typing import Final, TextIO

import typer
from rich import box, print
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Confirm
from rich.table import Column, Table
from rich.tree import Tree

from Utils.NetErrorDetect import NetErrorDetect
from Utils.NetHelper import NetHelper
from Utils.SSHConnect import SSHConnect
from Utils.zlogger import zLogger
from VRA import VraPreview, VraTest


def check_ipv4_format(networks: TextIO) -> TextIO:
    ip_for_check_list = networks.read().split("\n")
    for subnet_for_check in ip_for_check_list:
        if subnet_for_check.strip():
            try:
                subnet = ipaddress.ip_network(subnet_for_check)
            except ValueError:
                raise typer.BadParameter(f"{subnet_for_check} does not appear to be an IPv4 network.")
            if not subnet.is_private:
                raise typer.BadParameter(f"{subnet_for_check} isn't in the RFС1918 address space.")

    networks.seek(0)
    return networks


# Typer app
app = typer.Typer()

# Rich console
console = Console()

VLAN_SCOPE: Final = "SCOPE_VRA"
TEST_DC_GATEWAY: Final = "MS-TEST-0001"
CONFIG_DIR: Final = "generated_vra_configs"


class DatabaseKeys(str, Enum):
    test = "TEST"
    preview = "PREVIEW"


@app.command()
def create(
    environment: DatabaseKeys = typer.Option(
        ...,
        "-e",
        "--environment",
        case_sensitive=False,
        prompt="choice environment",
        show_choices=True,
    ),
    networks: typer.FileText = typer.Option(
        ...,
        "-n",
        "--network",
        callback=check_ipv4_format,
        prompt="Specify a txt file with a list of networks",
        help="TXT with IPv4 subnets",
    ),
    start_vlan_id: int = typer.Option(
        ...,
        "-v",
        "--vlan",
        min=1,
        max=4096,
        prompt="Enter the start VLAN ID value",
        help="VLAN ID start value",
    ),
    start_rd: int = typer.Option(
        ...,
        "-r",
        "--rd",
        prompt="Enter the extended part of the RD value",
        help="Route Distinguisher start extended part value",
    ),
    username: str = typer.Option(
        ...,
        "-u",
        "--username",
        prompt="Enter username",
        help="Username for authentication",
    ),
    password: str = typer.Option(
        ...,
        "-p",
        "--password",
        prompt="Enter password",
        hide_input=True,
        help="Password for authentication",
    ),
):
    """Create the VRA network configuration."""

    logger = zLogger(username)

    # Удаляем старые конфигурационные файлы перед созданием новых, если они есть.
    if pathlib.Path(CONFIG_DIR).is_dir() and os.listdir(CONFIG_DIR):
        console.rule("Old configuration files found.", style="dark_orange")
        for filename in os.listdir(CONFIG_DIR):
            file_path = os.path.join(CONFIG_DIR, filename)
            df_creation_time = time.ctime(os.path.getmtime(file_path))
            console.print(f"Find old config in '{file_path}' created {df_creation_time}")
        if Confirm.ask(
            "The program found the old configuration files. Delete or move old configuration files to avoid errors. Delete old configuration files?",
            default=False,
        ):
            console.rule("Deleting old configurations", style="dark_orange")
            for filename in os.listdir(CONFIG_DIR):
                file_path = os.path.join(CONFIG_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)

                    logger.log("all").info(f"{filename} - The old configuration was deleted successfully.")
                except Exception as e:
                    logger.log("all").error("Failed to delete %s. Reason: %s" % (file_path, e))

        else:
            logger.log("all").warning(f"The old configuration files are not deleted. The script has finished working.")
            exit()

    start_time = datetime.now()

    # Список будущих VRA сетей
    vra_subnets: list[str] = []

    # Список с экземплярами классов VraTest | VraPreview
    vra_subnets_cls: list[VraTest | VraPreview] = []

    # Берем рандомный vlan из скоупа и ищем путь по нему. Скоупы VLAN описаны в VLANSCOPE.json
    try:
        with open("VLANSCOPE.json") as f:
            vlanscope_d: dict[str, list[int]] = json.load(f)
            # Список vlan в интересуюшем нам VLAN SCOPE
            scope_vlan_id_l: list[int] = vlanscope_d.get(VLAN_SCOPE)
    except FileNotFoundError:
        logger.log("all").error("The 'VLANSCOPE.json' file was not found.")
        exit()

    # Случайно выбранный один vlan id из VLAN SCOPE
    random_vlan_id: int = random.choice(scope_vlan_id_l)

    # Финальный словарь с параметрами интерфейсов в {VLAN SCOPE}
    inf_params_d = {}

    # Список сетевых устройств в котором ищем порты в {VLAN SCOPE}
    net_todo_lst = []
    net_todo_lst.append(TEST_DC_GATEWAY)

    # Список сетевых устройств,которые мы уже проверили на порты в {VLAN SCOPE}
    net_done_lst = []

    # Обходим сетевые устройства и создаем словарь с параметрами портов в {VLAN SCOPE}
    while net_todo_lst:
        net_todo_lst = list(set(net_todo_lst))
        current_netdev = net_todo_lst[0]
        console.rule(f"{current_netdev} - Сollecting data to generate configurations for {VLAN_SCOPE}")

        # С помощью класса NetHelper ищем порты в нужном для нас vlan scope
        with SSHConnect(current_netdev, username, password, log_to="all") as ssh_conn:
            netdev_cls_instance = NetHelper(ssh_conn, verbose=True)
            net_intf_in_scope_d = netdev_cls_instance.get_intf_in_scope_by_stp_instance(random_vlan_id)
            inf_params_d[current_netdev] = net_intf_in_scope_d

            for intf in net_intf_in_scope_d.keys():
                neighbors_lst = netdev_cls_instance.get_cdp_neigbors_by_intf(intf)
                for neighbor in neighbors_lst:
                    if neighbor not in net_done_lst:
                        net_todo_lst.append(neighbor)
        net_done_lst.append(current_netdev)
        net_todo_lst.pop(0)

    # Строим Rich-Tree
    console.rule(f"{VLAN_SCOPE} network structure")
    net_topology_tree = Tree(VLAN_SCOPE, style="red")
    for netdev_host, intf_dict in inf_params_d.items():
        netdev_host_branch = net_topology_tree.add(f"[green]{netdev_host}")
        for intf, intf_params_dict in intf_dict.items():
            intf_mode = intf_params_dict.get("intf_mode")
            inf_branch = netdev_host_branch.add(f"{intf} ({intf_mode})", style="gold1")

    print(net_topology_tree)

    # Считываем сети из текстового файла и добавляем их в список
    for subnet in networks:
        if not subnet.isspace():
            vra_subnets.append(subnet.strip())

    # Создаем экземпляры классы VraTest или VraPreview и добавляем их в список
    for num, subnet in enumerate(vra_subnets):
        vlan_id: int = start_vlan_id + num
        rd_extended_part: int = start_rd + num
        if environment.name == "test":
            vra_subnets_cls.append(VraTest(vlan_id, subnet, rd_extended_part, inf_params_d))
        elif environment.name == "preview":
            vra_subnets_cls.append(VraPreview(vlan_id, subnet, rd_extended_part, inf_params_d))

    # Проходим в цикле по экземплярам классов и вызываем метод генерации конфига
    for net_dev in inf_params_d.keys():
        console.rule(f"Generating configuration for {net_dev}.")

        # Проходим в цикле по сформированным экземплярам класса и вызываем в каждом экземпляре метод generate_config()
        for vra in vra_subnets_cls:
            vra_generate_config = vra.generate_config(net_dev, verbose=False)

            if vra_generate_config:
                pathlib.Path("generated_vra_configs").mkdir(parents=True, exist_ok=True)
                conf_path = "generated_vra_configs/" + vra.vrf_name + "/"
                pathlib.Path(conf_path).mkdir(parents=True, exist_ok=True)

                for net_dev_host, net_dev_config in vra_generate_config.items():
                    try:
                        with open(f"{conf_path}{net_dev}.config", "w") as config_file_dest:
                            for line in net_dev_config:
                                config_file_dest.write(line)
                    except OSError:
                        logger.log("all").error(f"Failed creating {net_dev} file.")
                    else:
                        logger.log("all").info(
                            f"{vra.vrf_name} [{vra.environment}] - configuration has been successfully written to 'generated_vra_configs/{vra.vrf_name}'."
                        )
    end_time = datetime.now()
    print(f"Script execution time is {end_time - start_time}")


@app.command()
def apply(
    username: str = typer.Option(
        ...,
        "-u",
        "--username",
        prompt="Enter username",
        help="Username for authentication",
    ),
    password: str = typer.Option(
        ...,
        "-p",
        "--password",
        prompt="Enter password",
        hide_input=True,
        help="Password for authentication",
    ),
):
    """Apply the VRA network configuration."""

    start_time = datetime.now()
    logger = zLogger(username)

    progress_columns = (
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        "Elapsed:",
        TimeElapsedColumn(),
        "Remaining:",
        TimeRemainingColumn(),
    )
    # Словарь с установленными SSH-соединениями
    ssh_conn_dct = {}

    for vra_name in os.scandir(CONFIG_DIR):
        if vra_name.is_dir():
            print()
            console.rule(
                f"[magenta][bold]{vra_name.name}[/magenta][/bold] - [yellow]Starting to apply the configuration[/yellow]",
                style="dark_orange",
            )
            for vra_config in os.scandir(vra_name):
                if vra_config.name.endswith(".config"):
                    netdev_hostname = vra_config.name.strip(".config")
                    netdev_config = vra_config.path
                    number_of_commands = len(open(netdev_config).readlines())

                    # Если SSH соединение уже установлено - перепрыгиваем на него.
                    if ssh_conn_dct.get(netdev_hostname):
                        ssh_conn = ssh_conn_dct.get(netdev_hostname)
                        logger.log("all").info(
                            f"SSH connection with {ssh_conn.host} [{ssh_conn.device_type}] intercepted from last SSH session."
                        )
                    # Если SSH соединение НЕ установлено - устанавливаем новое SSH-соединение.
                    else:
                        ssh = SSHConnect(netdev_hostname, username, password, log_to="all")
                        ssh_conn = ssh.connect()
                        ssh_conn_dct[netdev_hostname] = ssh_conn

                    with open(netdev_config, "r", encoding="utf-8") as config_text:
                        with Progress(*progress_columns) as progress_bar:
                            progress_bar_task1 = progress_bar.add_task(
                                f"Applying configuration to [green][bold]{ssh_conn.host}[/green][/bold]",
                                total=number_of_commands,
                            )
                            for command in config_text:
                                output = ssh_conn.send_config_set(
                                    command.strip(),
                                    exit_config_mode=False,
                                    strip_prompt=True,
                                )
                                error_message = None

                                if ssh_conn.device_type.startswith("cisco"):
                                    error_message = NetErrorDetect.check_cisco_errors(command, output)
                                elif ssh_conn.device_type.startswith("huawei"):
                                    error_message = NetErrorDetect.check_huawei_errors(command, output)
                                else:
                                    logger.log("all").warning(
                                        f"{netdev_hostname} - It is not possible to check the device output for errors. The OS is not supported."
                                    )

                                if error_message:
                                    logger.log("all").error(
                                        f"{ssh_conn.host} [{ssh_conn.device_type}] - {error_message}"
                                    )
                                progress_bar.update(progress_bar_task1, advance=1)
                    print()
                else:
                    logger.log("all").error(
                        f"The script found a incorrect file '{netdev_hostname}' in the {CONFIG_DIR}. The script is stopped."
                    )
                    exit()

    # Проверяем состояния IP-интерфейсов на TEST_DC_GATEWAY
    console.rule(f"Cheking IPv4 interfaces on {TEST_DC_GATEWAY}", style="bright_blue")

    rich_ip_intf_status_table_headers = [
        "Interface",
        "IPv4 address",
        "Status",
        "Protocol",
    ]

    # Строим Rich-таблицу
    table = Table(box=box.HEAVY_EDGE, show_header=True, header_style="bold")
    for name in rich_ip_intf_status_table_headers:
        table.add_column(name, justify="left")

    # Если SSH соединение уже установлено - перепригиваем на него.
    if ssh_conn_dct.get(TEST_DC_GATEWAY):
        ssh_conn = ssh_conn_dct.get(TEST_DC_GATEWAY)
        logger.log("all").info(
            f"SSH connection with {ssh_conn.host} [{ssh_conn.device_type}] intercepted from last SSH session."
        )

        # Если мы перехватили SSH-соединение, надо убедится что мы находимся не в режиме конфигурирования для дальнейших проверок.
        if ssh_conn.check_config_mode():
            ssh_conn.exit_config_mode()

    # Если SSH соединение НЕ установлено - устанавливаем новое SSH-соединение.
    else:
        ssh = SSHConnect(TEST_DC_GATEWAY, username, password, log_to="all")
        ssh_conn = ssh.connect()
        ssh_conn_dct[TEST_DC_GATEWAY] = ssh_conn

    net_cls_instance = NetHelper(ssh_conn, verbose=True)
    ip_int_br_log_msg = "{} - Interface {} {} has '{}' status, protocol '{}'."

    for vra_name in os.scandir(CONFIG_DIR):
        vlan_id = vra_name.name.split("VRA")[1]
        ipv4_intf_info = net_cls_instance.get_ip_interfaces_status(vlan_id)

        for ipv4_intf_dict in ipv4_intf_info:
            if ipv4_intf_dict.get("status") != "up" or ipv4_intf_dict.get("proto") != "up":
                table.add_row(
                    ipv4_intf_dict["intf"],
                    ipv4_intf_dict["ipaddr"],
                    ipv4_intf_dict["status"],
                    ipv4_intf_dict["proto"],
                    style="red",
                )
                logger.log("all").warning(
                    ip_int_br_log_msg.format(
                        ssh_conn.host,
                        ipv4_intf_dict["intf"],
                        ipv4_intf_dict["ipaddr"],
                        ipv4_intf_dict["status"],
                        ipv4_intf_dict["proto"],
                    )
                )
            else:
                table.add_row(
                    ipv4_intf_dict["intf"],
                    ipv4_intf_dict["ipaddr"],
                    ipv4_intf_dict["status"],
                    ipv4_intf_dict["proto"],
                )
                logger.log("all").info(
                    ip_int_br_log_msg.format(
                        ssh_conn.host,
                        ipv4_intf_dict["intf"],
                        ipv4_intf_dict["ipaddr"],
                        ipv4_intf_dict["status"],
                        ipv4_intf_dict["proto"],
                    )
                )

    print(table)

    # Проверяем состояние STP внововь раскатанных vlan
    stp_check_netdevs: set[str] = set()
    vlan_set: set[str] = set()
    for vra_name in os.scandir(CONFIG_DIR):
        if vra_name.is_dir():
            for vra_config in os.scandir(vra_name):
                if vra_config.name.endswith(".config") and not TEST_DC_GATEWAY in vra_config.name:
                    access_netdev_hostname = vra_config.name.strip(".config")
                    vlan_id = vra_name.name.split("VRA")[1]
                    stp_check_netdevs.add(access_netdev_hostname)
                    vlan_set.add(vlan_id)

    rich_stp_table_headers = [
        "Interface",
        "Role",
        "Status",
        "Cost",
        "Port Priority",
        "Port ID",
        "Type",
    ]

    for access_netdev_hostname in stp_check_netdevs:
        # Если SSH соединение уже установлено - перепригиваем на него.
        if ssh_conn_dct.get(access_netdev_hostname):
            ssh_conn = ssh_conn_dct.get(access_netdev_hostname)
            logger.log("all").info(
                f"SSH connection with {ssh_conn.host} [{ssh_conn.device_type}] intercepted from last SSH session."
            )
            # Если мы перехватили SSH-соединение, надо убедится что мы находимся не в режиме конфигурирования для дальнейших проверок.
            if ssh_conn.check_config_mode():
                ssh_conn.exit_config_mode()

        # Если SSH соединение НЕ установлено - устанавливаем новое SSH-соединение.
        else:
            ssh = SSHConnect(access_netdev_hostname, username, password, log_to="all")
            ssh_conn = ssh.connect()
            ssh_conn_dct[access_netdev_hostname] = ssh_conn

        stp_intf_status = set()
        stp_intf_status.add("LRN")
        while "LRN" in stp_intf_status:
            console.rule(f"[bold]{access_netdev_hostname} - Cheking STP state.[/bold]", style="bright_blue")
            stp_intf_status.clear()

            net_cls_instance = NetHelper(ssh_conn, verbose=True)
            for vlan_id in vlan_set:
                stp_info = net_cls_instance.get_stp_status(vlan_id)

                # Строим Rich-таблицу
                table = Table(
                    title=f"vlan id {vlan_id} stp info.",
                    box=box.HEAVY_EDGE,
                    show_header=True,
                    header_style="bold",
                )

                for name in rich_stp_table_headers:
                    table.add_column(name, justify="left")

                for stp_intf_dict in stp_info:
                    stp_intf_status.add(stp_intf_dict.get("status"))
                    stp_log_msg = "{} - Interface {} vlan {} in {} state, role {}"

                    stp_table_row = (
                        stp_intf_dict["interface"],
                        stp_intf_dict["role"],
                        stp_intf_dict["status"],
                        stp_intf_dict["cost"],
                        stp_intf_dict["port_priority"],
                        stp_intf_dict["port_id"],
                        stp_intf_dict["type"],
                    )

                    if stp_intf_dict.get("status") == "BLK":
                        table.add_row(*stp_table_row, style="red")

                        logger.log("file").warning(
                            stp_log_msg.format(
                                access_netdev_hostname,
                                stp_intf_dict["interface"],
                                stp_intf_dict["vlan_id"],
                                stp_intf_dict["status"],
                                stp_intf_dict["role"],
                            )
                        )
                    elif stp_intf_dict.get("status") == "LRN":
                        table.add_row(*stp_table_row, style="yellow")
                        logger.log("file").warning(
                            stp_log_msg.format(
                                access_netdev_hostname,
                                stp_intf_dict["interface"],
                                stp_intf_dict["vlan_id"],
                                stp_intf_dict["status"],
                                stp_intf_dict["role"],
                            )
                        )
                    else:
                        table.add_row(*stp_table_row)
                        logger.log("file").info(
                            stp_log_msg.format(
                                access_netdev_hostname,
                                stp_intf_dict["interface"],
                                stp_intf_dict["vlan_id"],
                                stp_intf_dict["status"],
                                stp_intf_dict["role"],
                            )
                        )

                print(table)
            if "LRN" in stp_intf_status:
                with console.status(
                    f"Waiting 15 seconds for the STP to converge and check...",
                    spinner="bouncingBall",
                ):
                    for _ in range(16):
                        time.sleep(1)

    for ssh_conn in ssh_conn_dct.values():
        if ssh_conn.is_alive():
            ssh_conn.disconnect()
            logger.log("all").info(f"SSH connection with {ssh_conn.host} [{ssh_conn.device_type}] closed.")

    end_time = datetime.now()
    print(f"Script execution time is {end_time - start_time}")


if __name__ == "__main__":
    app()

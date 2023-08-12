"""The class checks output errors from network devices."""

__author__ = "ZHEZLYAEV Aleksandr"
__version__ = "1.0"

# -*- coding: utf-8 -*-


class NetErrorDetect:
    """Class get output from network devices and checks it for errors
    (Cisco/Huawei)."""

    @classmethod
    def check_cisco_errors(cls, input, output) -> str:
        """Checks Cisco IOS output for errors during configuration.

        The method checks the output for Invalid input detected,
        Incomplete command, Ambiguous command errors.
        """

        if "% Applying VLAN changes" in output:
            pass

        elif "% Warning: use /31 mask" in output:
            pass

        elif "%" in output:
            error = output.split("%")[1].split("\n")[0]
            error_mesage = f'An error occurred while executing the command "{input.strip()}" -> {error.strip()}'
            return error_mesage

        elif "Command rejected" in output:
            error = output.split("Command rejected:")[1].split("\n")[0]
            error_mesage = f'An error occurred while executing the command "{input.strip()}" -> {error.strip()}'
            return error_mesage

    @classmethod
    def check_huawei_errors(cls, input, output) -> str:
        """Checks Huawei VRP output for errors during configuration."""

        if "Error:" in output:
            error = output.split("Error:")[1].split("\n")[0].strip()
            error_mesage = f'An error occurred while executing the command "{input.strip()}" -> {error.strip()}'
            return error_mesage

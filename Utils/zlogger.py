"""A class for working with logging in python."""

__author__ = "ZHEZLYAEV Aleksandr"
__version__ = "1.0"

# -*- coding: utf-8 -*-

import datetime
import logging
import os
import pathlib
import sys
from typing import Literal, Optional

import coloredlogs
from rich.logging import RichHandler


class zLogger:
    """The class creates and formats logs."""

    def __init__(self, username=None) -> None:
        if username:
            if not isinstance(username, str):
                raise TypeError(f"Username must be a string, not a {type(username)}.")
            self.username = username
        else:
            self.username = os.environ.get("USERNAME")

        # adds an additional field to the logger_formatter
        self.extra_logging_field = {"username": self.username}

    @staticmethod
    def logger_basic_init():
        """Basic parameters for the logger."""

        logger = logging.getLogger(__name__)

        # check if handlers are already present and if so, clear them before adding new handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        # to prevent double printing
        logger.propagate = False

        # logging level
        logger.setLevel(logging.DEBUG)
        return logger

    def __create_console_handler(self):
        """The method creates console handler."""

        # create console formatter
        console_formatter = coloredlogs.ColoredFormatter(
            "[%(asctime)s.%(msecs)03d] [%(username)s] [%(levelname)s] - %(message)s",
            datefmt="%d.%m.%Y %H:%M:%S",
        )

        # create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        return console_handler

    def __create_rich_console_handler(self):
        """The method creates rich console handler."""

        # create rich console formatter
        rich_console_formatter = logging.Formatter("[{username}] - {message}", datefmt="%d.%m.%Y %H:%M:%S", style="{")

        # create rich console handler
        rich_console_handler = RichHandler(level=logging.DEBUG, show_path=False, rich_tracebacks=False)

        rich_console_handler.setFormatter(rich_console_formatter)
        return rich_console_handler

    def __create_file_handler(self):
        """The method creates file handler."""

        # create logfile formatter
        file_formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] [%(username)s] [%(levelname)s] - %(message)s",
            datefmt="%d.%m.%Y %H:%M:%S",
        )

        # create log folder if not exist
        pathlib.Path("log").mkdir(parents=True, exist_ok=True)

        # create file handler
        file_handler = logging.FileHandler(
            f"log/{self.username}_{datetime.datetime.now().strftime('%d_%m_%Y')}.log",
            "a",
            "utf-8",
        )

        file_handler.setFormatter(file_formatter)
        return file_handler

    def log(
        self,
        log_to: Optional[Literal["console", "rich_console", "file", "all", "all_use_rich"]] = "console",
    ) -> logging.LoggerAdapter:
        """The method creates and formats logs."""

        # logging init
        logger = self.logger_basic_init()

        if log_to == "console":
            handlers = [self.__create_console_handler()]

        elif log_to == "rich_console":
            handlers = [self.__create_rich_console_handler()]

        elif log_to == "file":
            handlers = [self.__create_file_handler()]

        elif log_to == "all":
            handlers = [
                self.__create_console_handler(),
                self.__create_file_handler(),
            ]

        elif log_to == "all_use_rich":
            handlers = [
                self.__create_rich_console_handler(),
                self.__create_file_handler(),
            ]

        else:
            raise ValueError("Incorrect log output value.")

        for handler in handlers:
            logger.addHandler(handler)

        # add an additional field to the logger_formatter
        logger = logging.LoggerAdapter(logger, self.extra_logging_field)
        return logger

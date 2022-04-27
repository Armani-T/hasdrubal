from sys import exit as sys_exit
from typing import NoReturn

from args import build_config, ConfigData, parser
from log import logger
from run import run_code
import errors

CURRENT_VERSION = "0.0.1"


def run_file(config: ConfigData) -> int:
    """
    Run the source code found inside a file.

    Parameters
    ----------
    config: ConfigData
        Command line options that can change how the function runs.

    Returns
    -------
    int
        The program exit code.
    """
    report, write = config.writers
    try:
        if config.file is None:
            logger.error("No file was passed in to be run.")
            write(
                "Please provide a file for the program to run."
                f"\n\n{parser.format_usage()}\n"
            )
            return 64
        if config.file.is_dir():
            logger.fatal("A folder was passed into the program instead of a file.")
            write(
                report(
                    errors.CMDError(errors.CMDErrorReasons.PATH_IS_FOLDER),
                    "",
                    str(config.file),
                )
            )
            return 65

        source_bytes = config.file.resolve(strict=True).read_bytes()
        out_text = run_code(source_bytes, config)
        write(out_text)
        return 0
    except PermissionError:
        write(
            report(
                errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION),
                "",
                str(config.file),
            )
        )
        return 66
    except FileNotFoundError:
        write(
            report(
                errors.CMDError(errors.CMDErrorReasons.FILE_NOT_FOUND),
                "",
                str(config.file),
            )
        )
        return 66


def main() -> NoReturn:
    """The primary entry point for the entire program."""
    config = build_config(parser.parse_args())
    _, write = config.writers
    status = 0
    if config.show_help:
        logger.info("Printing the help message.")
        write(parser.format_help())
    elif config.show_version:
        logger.info("Printing the version.")
        write(f"Hanno v{CURRENT_VERSION}\n")
    else:
        status = run_file(config)
    sys_exit(status)
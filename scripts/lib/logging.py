"""统一颜色日志。所有模块 from lib.logging import * 即可。"""
import sys

COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_MAGENTA = "\033[95m"
COLOR_WHITE = "\033[97m"
COLOR_DARKGRAY = "\033[90m"
COLOR_RESET = "\033[0m"


def info(msg: str = "") -> None:
    print(f"{COLOR_GREEN}{msg}{COLOR_RESET}")


def warn(msg: str) -> None:
    print(f"{COLOR_YELLOW}{msg}{COLOR_RESET}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"{COLOR_RED}{msg}{COLOR_RESET}", file=sys.stderr)


def hint(msg: str) -> None:
    print(f"{COLOR_DARKGRAY}{msg}{COLOR_RESET}")


def header(msg: str) -> None:
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print(f"{COLOR_CYAN}  {msg}{COLOR_RESET}")
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print()

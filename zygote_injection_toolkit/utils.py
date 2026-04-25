from rich.console import Console

from rich.theme import Theme

from rich.logging import RichHandler

import logging

import sys

TOOLKIT_THEME = Theme({

    "info":       ,

    "warning":         ,

    "error":           ,

    "success":             ,

    "highlight":               ,

    "dim":         ,

})

console = Console(theme=TOOLKIT_THEME)

def setup_logging(level=logging.INFO):

    logging.basicConfig(

        level=level,

        format="%(message)s",

        datefmt="[%X]",

        handlers=[RichHandler(rich_tracebacks=True, console=console)]

    )

    return logging.getLogger("zygote-punch")

def print_banner():

    banner = """
[bold cyan]███████╗██╗   ██╗ ██████╗  ██████╗ ████████╗███████╗[/]
[bold cyan]╚══███╔╝╚██╗ ██╔╝██╔════╝ ██╔═══██╗╚══██╔══╝██╔════╝[/]
[bold cyan]  ███╔╝  ╚████╔╝ ██║  ███╗██║   ██║   ██║   █████╗  [/]
[bold cyan] ███╔╝    ╚██╔╝  ██║   ██║██║   ██║   ██║   ██╔══╝  [/]
[bold cyan]███████╗   ██║   ╚██████╔╝╚██████╔╝   ██║   ███████╗[/]
[bold cyan]╚══════╝   ╚═╝    ╚═════╝  ╚═════╝    ╚═╝   ╚══════╝[/]
[bold magenta]    Zygote Injection Toolkit - CVE-2024-31317[/]
    """

    console.print(banner)

def error_exit(message: str):

    console.print(f"[error]Error:[/] {message}")

    sys.exit(1)

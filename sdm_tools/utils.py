"""UI Utils"""
import subprocess
from pyfiglet import Figlet
from rich.console import Console


console = Console()


def print_banner():
    """ Prints the ASCII art banner. """
    f = Figlet(font='slant')
    ascii_art = f.renderText('SDM-Tools')
    console.print(f"[bold green]{ascii_art}[/bold green]")
    console.print("[bold blue]Customized insights and actions for SDMs.[/bold blue]")


def clear_screen():
    """ Clears the terminal screen. """
    subprocess.run('clear', shell=True)

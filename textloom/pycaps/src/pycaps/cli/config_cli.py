import typer
from typing import Optional
from pycaps.api import ApiKeyService

config_app = typer.Typer()

@config_app.command("config", help="Pycaps configs")
def config(
    api_key: Optional[str] = typer.Option(None, "--set-api-key", help="Set the Pycaps API key to use"),
    unset_api_key: bool = typer.Option(False, "--unset-api-key", help="Remove stored Pycaps API key")
):
    if api_key:
        ApiKeyService.set(api_key)
        typer.echo("API key saved.")
    elif unset_api_key:
        if ApiKeyService.has():
            ApiKeyService.remove()
            typer.echo("API key removed.")
        else:
            typer.echo("No API key found.")
    else:
        if ApiKeyService.has():
            typer.echo(f"Current API key: {ApiKeyService.get()}")
        else:
            typer.echo("No API key set.")

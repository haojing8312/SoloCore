import os
import shutil
import typer
from typing import Optional
from pycaps.template import TemplateService, TemplateFactory, DEFAULT_TEMPLATE_NAME

template_app = typer.Typer(
    help="Manage templates: create new templates or list available templates",
    invoke_without_command=False,
    add_completion=False,
)

@template_app.command("list", help="List available templates (local and builtin).")
def list_templates():
    template_service = TemplateService()
    typer.echo("Available templates:\n")

    typer.echo("Local templates:")
    for tmpl in template_service.list_local_templates():
        typer.echo(f"  - {tmpl}")

    typer.echo("\nBuiltin templates:")
    for tmpl in template_service.list_builtin_templates():
        typer.echo(f"  - {tmpl}")

@template_app.command("create", help="Create a new template in the current directory.")
def create_template(
    name: str = typer.Option(..., "--name", "-n", help="Name of the new template.", show_default=False),
    from_template: Optional[str] = typer.Option(None, "--from", "-f", help="Template to copy from (defaults to builtin default template).", show_default=False)
):
    target_dir = os.path.join(os.getcwd(), name)
    if os.path.exists(target_dir):
        typer.echo(f"Error: Directory '{name}' already exists.", err=True)
        raise typer.Exit(code=1)

    template_factory = TemplateFactory()
    template = template_factory.create(from_template) if from_template else template_factory.create(DEFAULT_TEMPLATE_NAME)
    shutil.copytree(template.get_folder_path(), target_dir)
    typer.echo(f"Template '{name}' created successfully in '{target_dir}'.")

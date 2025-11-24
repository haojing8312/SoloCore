import typer
from typing import Optional
from pycaps.renderer import CssSubtitlePreviewer
from pycaps.template import TemplateLoader, TemplateFactory

preview_app = typer.Typer()

@preview_app.command("preview-styles", help="Preview a CSS file or the CSS styles of a template")
def preview_styles(
    css: Optional[str] = typer.Option(None, "--css", help="CSS file path"),
    resources: Optional[str] = typer.Option(None, "--resources", help="Resources directory path. It is used only if --css is provided"),
    template_name: Optional[str] = typer.Option(None, "--template", help="Template name"),
):
    if not css and not template_name:
        typer.echo("Either --css or --template must be provided. Use --help for more information", err=True)
        return None
    if css and template_name:
        typer.echo("Only one of --css or --template can be provided. Use --help for more information", err=True)
        return None
    
    if css:
        css_content = open(css, "r", encoding="utf-8").read()
        CssSubtitlePreviewer().run(css_content, resources)
    elif template_name:
        # TODO: This breaks encapsulation to get the CSS content and the resources directory of the template
        template = TemplateFactory().create(template_name)
        builder = TemplateLoader(template).load(False)
        css_content = builder._caps_pipeline._renderer._custom_css
        resources_dir = builder._caps_pipeline._resources_dir
        CssSubtitlePreviewer().run(css_content, resources_dir)

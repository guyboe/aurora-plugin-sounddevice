import enum
import pathlib
import asyncio
from typing import Optional

import typer

from benedict import benedict

import sounddevice as sd

from . import Plugin, Config


cli = typer.Typer()

config = Config("development", pathlib.Path.cwd().name)


class ConfigTypes(str, enum.Enum):
    yaml = "yaml"
    json = "json"
    ini = "ini"


@cli.command("config")
def _config(
    section: Optional[str] = typer.Option(None),
    format_: ConfigTypes = typer.Option(ConfigTypes.yaml, "--format"),
    output: Optional[pathlib.Path] = typer.Option(None),
    quiet: bool = typer.Option(False),
    indent: int = typer.Option(4)
):
    if output:
        output = output.open("w", encoding="utf-8")
    if section:
        d = benedict(config.dict()).get(section)
    else:
        d = benedict(config.dict(), keypath_separator=None)
    match format_:
        case "yaml":
            result = d.to_yaml(allow_unicode="utf-8", default_flow_style=False)
        case "json":
            result = d.to_json(ensure_ascii=False, indent=indent)
        case _:
            result = d.to_ini()
    if not quiet:
        print(result, file=output)


@cli.command("info")
def _info(
    format_: ConfigTypes = typer.Option(ConfigTypes.yaml, "--format"),
    output: Optional[pathlib.Path] = typer.Option(None),
    quiet: bool = typer.Option(False),
    indent: int = typer.Option(4)
):
    d = benedict({
        "input": sd.query_devices(device=config.input.device),
        "output": sd.query_devices(device=config.output.device)
    })
    if format_ == "yaml":
        result = d.to_yaml(allow_unicode="utf-8", default_flow_style=False)
    elif format_ == "json":
        result = d.to_json(ensure_ascii=False, indent=indent)
    else:
        result = d.to_ini()
    if not quiet:
        print(result, file=output)


@cli.command("consume")
def _consume():
    plugin = Plugin(config)
    plugin.consume()


@cli.command("listen")
def _listen():
    plugin = Plugin(config)
    plugin.listen()


@cli.command("play")
def _play(
    filename: pathlib.Path,
    queue: config.Queues.Exchange.Name = typer.Option(None, help="play via queue")
):
    if not filename.exists():
        typer.echo(f"File {filename} not found")
        raise typer.Abort()
    plugin = Plugin(config)
    if queue:
        with open(filename, mode="r+b") as f:
            plugin.publish(f.read(), exchange=queue.value)
        return
    plugin.play(filename)


if __name__ == "__main__":
    cli()

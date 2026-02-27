"""Click CLI for StudioMCPHub Studio."""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

import click

from .client import StudioClient
from .config import StudioConfig, load_config
from .dam import DAM
from .models import StageStatus
from .pipeline import Pipeline
from .preview import generate_preview


def _status_icon(status: StageStatus) -> str:
    return {
        StageStatus.completed: "OK",
        StageStatus.failed: "FAIL",
        StageStatus.skipped: "SKIP",
        StageStatus.running: "...",
        StageStatus.pending: " ",
    }.get(status, "?")


def _on_stage(filename: str, stage: str, result) -> None:
    icon = _status_icon(result.status)
    dur = f" ({result.duration_s:.1f}s)" if result.duration_s else ""
    cost = f" [{result.cost_gcx} GCX]" if result.cost_gcx else ""
    click.echo(f"  [{icon}] {stage}{dur}{cost}")
    if result.error:
        click.secho(f"       {result.error}", fg="red")


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """StudioMCPHub Studio — Image to Retail in 90 seconds."""
    ctx.ensure_object(dict)


@cli.command()
@click.argument("path", default=".", type=click.Path())
def init(path: str) -> None:
    """Initialize a Studio project directory."""
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)

    config_path = root / "studio.json"
    if not config_path.exists():
        cfg = StudioConfig()
        config_path.write_text(cfg.model_dump_json(indent=2))
        click.echo(f"Created {config_path}")
    else:
        click.echo(f"Config already exists: {config_path}")

    click.secho("Studio project initialized.", fg="green")
    click.echo(f"  Edit studio.json to configure your pipeline.")
    click.echo(f"  Run: studio process <IMAGE> -c <COLLECTION>")


@cli.command()
@click.argument("image", type=click.Path(exists=True))
@click.option("-c", "--collection", default="default", help="Collection name")
@click.option("--skip", default="", help="Comma-separated stages to skip")
@click.option("--project-dir", type=click.Path(), default=None)
def process(image: str, collection: str, skip: str, project_dir: str | None) -> None:
    """Process a single image through the pipeline."""
    root = Path(project_dir).resolve() if project_dir else Path.cwd()
    config = load_config(root)
    skip_set = {s.strip() for s in skip.split(",") if s.strip()}

    click.secho(f"Processing: {image}", fg="cyan")
    click.echo(f"Collection: {collection}")
    click.echo(f"Stages: {len(config.stages) - len(skip_set)} active, {len(skip_set)} skipped")
    click.echo()

    with StudioClient(config) as client:
        dam = DAM(config, root)
        pipeline = Pipeline(config, client, dam, on_stage_complete=_on_stage)
        asset = pipeline.process(Path(image).resolve(), collection, skip_set)

    click.echo()
    completed = sum(1 for s in asset.stages.values() if s.status == StageStatus.completed)
    click.secho(
        f"Done: {completed}/{len(asset.stages)} stages completed "
        f"({asset.total_cost_gcx} GCX)",
        fg="green",
    )


@cli.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option("-c", "--collection", default="batch", help="Collection name")
@click.option("--skip", default="", help="Comma-separated stages to skip")
@click.option("--project-dir", type=click.Path(), default=None)
def batch(folder: str, collection: str, skip: str, project_dir: str | None) -> None:
    """Process all images in a folder."""
    root = Path(project_dir).resolve() if project_dir else Path.cwd()
    config = load_config(root)
    skip_set = {s.strip() for s in skip.split(",") if s.strip()}

    with StudioClient(config) as client:
        dam = DAM(config, root)
        pipeline = Pipeline(config, client, dam, on_stage_complete=_on_stage)
        assets = pipeline.process_batch(Path(folder).resolve(), collection, skip_set)

    click.secho(f"Batch complete: {len(assets)} images processed", fg="green")


@cli.command()
@click.argument("collection", default="")
@click.option("--project-dir", type=click.Path(), default=None)
def status(collection: str, project_dir: str | None) -> None:
    """Show collection or project status."""
    root = Path(project_dir).resolve() if project_dir else Path.cwd()
    config = load_config(root)
    dam = DAM(config, root)

    if collection:
        manifest = dam.load_manifest(collection)
        click.secho(f"Collection: {collection}", fg="cyan")
        click.echo(f"Assets: {manifest.asset_count()}")
        click.echo(f"Completed: {manifest.completed_count()}")
        click.echo(f"Total cost: {manifest.total_cost_gcx} GCX")
        for fname, asset in manifest.assets.items():
            stages_ok = sum(1 for s in asset.stages.values() if s.status == StageStatus.completed)
            click.echo(f"  {fname}: {stages_ok}/{len(asset.stages)} stages")
    else:
        collections = dam.list_collections()
        if not collections:
            click.echo("No collections found. Run: studio process <IMAGE> -c <COLLECTION>")
            return
        click.secho("Collections:", fg="cyan")
        for col in collections:
            m = dam.load_manifest(col)
            click.echo(f"  {col}: {m.asset_count()} assets, {m.total_cost_gcx} GCX")


@cli.command()
@click.argument("collection")
@click.option("--open/--no-open", default=True, help="Open in browser")
@click.option("--project-dir", type=click.Path(), default=None)
def preview(collection: str, open: bool, project_dir: str | None) -> None:
    """Generate HTML gallery preview for a collection."""
    root = Path(project_dir).resolve() if project_dir else Path.cwd()
    config = load_config(root)
    dam = DAM(config, root)

    html_path = generate_preview(dam, collection)
    click.secho(f"Preview: {html_path}", fg="green")
    if open:
        webbrowser.open(html_path.as_uri())


@cli.command()
@click.argument("collection")
@click.option("--platform", type=click.Choice(["gooten", "printful", "printify"]), required=True)
@click.option("--project-dir", type=click.Path(), default=None)
def export(collection: str, platform: str, project_dir: str | None) -> None:
    """Export collection for POD platform (Phase 2)."""
    click.secho(
        f"Export to {platform} is coming in Phase 2. "
        f"Collection '{collection}' is ready for manual upload.",
        fg="yellow",
    )


@cli.command()
@click.option("--project-dir", type=click.Path(), default=None)
def balance(project_dir: str | None) -> None:
    """Check GCX wallet balance."""
    root = Path(project_dir).resolve() if project_dir else Path.cwd()
    config = load_config(root)
    if not config.wallet:
        click.secho("No wallet configured. Add 'wallet' to studio.json.", fg="yellow")
        return
    with StudioClient(config) as client:
        resp = client.check_balance()
        if resp.status == "error":
            click.secho(f"Error: {resp.error}", fg="red")
        else:
            click.echo(json.dumps(resp.result, indent=2))

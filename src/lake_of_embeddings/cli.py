from pathlib import Path

import click

from lake_of_embeddings.config import load_config, default_config_path, Config
from lake_of_embeddings.sync.engine import SyncEngine


def _make_publisher(source_config):
    if source_config.type == "markdown":
        from lake_of_embeddings.publishers.markdown import MarkdownPublisher
        return MarkdownPublisher(path=source_config.path)
    elif source_config.type == "plaintext":
        from lake_of_embeddings.publishers.plaintext import PlaintextPublisher
        return PlaintextPublisher(path=source_config.path)
    elif source_config.type == "sqlite":
        from lake_of_embeddings.publishers.sqlite import SqlitePublisher
        return SqlitePublisher(
            path=source_config.path,
            table=source_config.table,
            content_column=source_config.content_column,
            metadata_columns=source_config.metadata_columns,
        )
    else:
        raise click.ClickException(f"Unknown source type: {source_config.type}")


def _make_embedder(config: Config):
    if config.embedding.backend == "local":
        from lake_of_embeddings.embeddings.local import LocalEmbedder
        return LocalEmbedder(model=config.embedding.model)
    elif config.embedding.backend == "openai":
        from lake_of_embeddings.embeddings.api import APIEmbedder
        if not config.embedding.api_key:
            raise click.ClickException("OpenAI backend requires api_key in config.")
        return APIEmbedder(
            model=config.embedding.model, api_key=config.embedding.api_key
        )
    else:
        raise click.ClickException(
            f"Unknown embedding backend: {config.embedding.backend}"
        )


def _chromadb_path() -> str:
    path = Path("~/.local/share/lake-of-embeddings/chromadb").expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@click.group()
def cli():
    """Lake of Embeddings — semantic search over your personal knowledge."""
    pass


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
@click.option("--source", default=None, help="Sync only this source name")
@click.option("--rebuild", is_flag=True, help="Delete and re-embed all vectors")
def sync(config_path, source, rebuild):
    """Sync data sources into the vector database."""
    try:
        cfg_path = Path(config_path) if config_path else default_config_path()
        config = load_config(cfg_path)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {cfg_path}")

    embedder = _make_embedder(config)
    engine = SyncEngine(chromadb_path=_chromadb_path(), embedder=embedder)

    sources = config.sources
    if source:
        sources = [s for s in sources if s.name == source]
        if not sources:
            raise click.ClickException(f"Source '{source}' not found in config.")

    for src_config in sources:
        click.echo(f"Syncing {src_config.name}...")
        publisher = _make_publisher(src_config)
        try:
            report = engine.sync(src_config.name, publisher.crawl(), rebuild=rebuild)
            click.echo(f"  {report}")
        except ValueError as e:
            raise click.ClickException(str(e))

    click.echo("Done.")


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
def serve(config_path):
    """Start the MCP server (stdio mode)."""
    from lake_of_embeddings.mcp.server import create_mcp_server

    try:
        cfg_path = Path(config_path) if config_path else default_config_path()
        config = load_config(cfg_path)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {cfg_path}")

    embedder = _make_embedder(config)
    engine = SyncEngine(chromadb_path=_chromadb_path(), embedder=embedder)
    mcp = create_mcp_server(engine)
    mcp.run()


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
def status(config_path):
    """Show sync status for all sources."""
    try:
        cfg_path = Path(config_path) if config_path else default_config_path()
        config = load_config(cfg_path)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {cfg_path}")

    embedder = _make_embedder(config)
    engine = SyncEngine(chromadb_path=_chromadb_path(), embedder=embedder)

    synced = engine.list_sources()
    if not synced:
        click.echo("No sources synced yet. Run 'lake sync' first.")
        return

    for name in synced:
        stats = engine.get_source_stats(name)
        click.echo(
            f"  {name}: {stats['chunk_count']} chunks "
            f"(model: {stats['embedding_model']})"
        )

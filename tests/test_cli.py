import pytest
from click.testing import CliRunner
from lake_of_embeddings.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def config_file(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "test.md").write_text("# Test Note\nSome content here.")
    config = tmp_path / "config.yaml"
    config.write_text(f"""
sources:
  - type: markdown
    name: test-notes
    path: {notes_dir}

embedding:
  backend: local
  model: all-MiniLM-L6-v2
""")
    return str(config)


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "sync" in result.output


def test_sync_command_exists(runner):
    result = runner.invoke(cli, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output
    assert "--rebuild" in result.output


def test_serve_command_exists(runner):
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0


def test_status_command_exists(runner):
    result = runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0


def test_sync_with_missing_config(runner, tmp_path):
    result = runner.invoke(cli, ["sync", "--config", str(tmp_path / "nope.yaml")])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()

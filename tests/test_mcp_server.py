import pytest
from unittest.mock import MagicMock
from lake_of_vectors.mcp.server import create_mcp_server


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.list_sources.return_value = ["security-notes", "knowledge-db"]
    engine.search.return_value = [
        {
            "chunk_text": "SSRF is a vulnerability where...",
            "metadata": {
                "source_id": "/notes/ssrf.md",
                "title": "SSRF Guide",
                "chunk_index": 0,
                "total_chunks": 3,
            },
            "distance": 0.25,
            "source_name": "security-notes",
        },
    ]
    engine.get_source_stats.return_value = {
        "chunk_count": 42,
        "embedding_model": "local:all-MiniLM-L6-v2",
    }
    return engine


def test_create_mcp_server_returns_fastmcp(mock_engine):
    mcp = create_mcp_server(mock_engine)
    assert mcp is not None
    assert mcp.name == "lake-of-vectors"


def test_server_has_semantic_search_tool(mock_engine):
    mcp = create_mcp_server(mock_engine)
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "semantic_search" in tool_names


def test_server_has_list_sources_tool(mock_engine):
    mcp = create_mcp_server(mock_engine)
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "list_sources" in tool_names

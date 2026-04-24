"""Unit tests for MCPSuggester."""
from core.mcp_suggester import MCPSuggester


def test_api_confusion_returns_context7():
    suggester = MCPSuggester()
    result = suggester.suggest("api_confusion")
    assert "Context7" in result.server


def test_aws_issue_returns_aws_docs():
    suggester = MCPSuggester()
    result = suggester.suggest("aws_issue")
    assert "AWS" in result.server


def test_database_issue_returns_project_docs():
    suggester = MCPSuggester()
    result = suggester.suggest("database_issue")
    assert "Project" in result.server or "Documentation" in result.server


def test_repeated_file_edits_returns_workspace_context():
    suggester = MCPSuggester()
    result = suggester.suggest("repeated_file_edits")
    assert "Workspace" in result.server or "Context" in result.server


def test_unknown_signal_returns_default():
    suggester = MCPSuggester()
    result = suggester.suggest("some_unknown_signal_xyz")
    assert result.server  # non-empty
    assert result.reason  # non-empty


def test_all_suggestions_have_non_empty_reason():
    suggester = MCPSuggester()
    for signal_type in ["api_confusion", "aws_issue", "database_issue", "repeated_file_edits", "package_usage"]:
        result = suggester.suggest(signal_type)
        assert result.reason and len(result.reason) > 0

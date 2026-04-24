"""Maps struggle signal types to contextual MCP server recommendations."""
from core.models import MCPSuggestion

# Mapping from struggle signal type keywords to MCP server suggestions
_STRUGGLE_TO_MCP = {
    "api_confusion": MCPSuggestion(
        server="Context7 MCP",
        reason="API or library confusion detected. Context7 provides up-to-date library documentation.",
    ),
    "library_confusion": MCPSuggestion(
        server="Context7 MCP",
        reason="Library usage confusion detected. Context7 provides current library documentation.",
    ),
    "aws_issue": MCPSuggestion(
        server="AWS Docs MCP",
        reason="AWS deployment issue detected. AWS Docs MCP provides official AWS documentation.",
    ),
    "database_issue": MCPSuggestion(
        server="Project Documentation",
        reason="Database schema issue detected. Add project docs or schema context.",
    ),
    "repeated_file_edits": MCPSuggestion(
        server="Workspace Context",
        reason="Repeated file edits detected. Adding workspace context may help the AI understand the codebase.",
    ),
    "package_usage": MCPSuggestion(
        server="Documentation MCP",
        reason="Package usage issue detected. A documentation MCP server can provide current package docs.",
    ),
    # Default fallback for unrecognized signal types
    "default": MCPSuggestion(
        server="Context7 MCP",
        reason="Repeated AI struggle detected. Consider adding more context via an MCP server.",
    ),
}


class MCPSuggester:
    def suggest(self, signal_type: str) -> MCPSuggestion:
        """Return the MCP server recommendation for the given struggle signal type."""
        # Try exact match first, then keyword match, then default
        if signal_type in _STRUGGLE_TO_MCP:
            return _STRUGGLE_TO_MCP[signal_type]
        # Keyword matching
        signal_lower = signal_type.lower()
        for key, suggestion in _STRUGGLE_TO_MCP.items():
            if key != "default" and key in signal_lower:
                return suggestion
        return _STRUGGLE_TO_MCP["default"]

#!/usr/bin/env python3
"""Backend server for the Carbon Optimizer VS Code Extension.

Reads newline-delimited JSON requests from stdin, dispatches to core tools,
and writes newline-delimited JSON responses to stdout.
"""
import sys
import os
import json

# Add the kiro-carbon-optimizer directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from tools.analyze import analyze_efficiency
from tools.optimize import run_pipeline
from core.config_analyzer import analyze_configs
from core.models import ErrorResponse
from core.struggle_detector import StruggleDetector

_detector = StruggleDetector()

DISPATCH = {
    "analyze_efficiency": lambda p: analyze_efficiency(p["code"]),
    "run_pipeline":       lambda p: run_pipeline(p["code"]),
    "analyze_configs":    lambda p: analyze_configs(p["workspace_root"]),
    "on_edit_generated":  lambda p: _detector.on_edit_generated(
        p["file_path"], tuple(p["line_range"])
    ),
}


def _serialize_result(result) -> object:
    """Convert a result to a JSON-serializable object."""
    if isinstance(result, ErrorResponse):
        return {"error": {"message": result.message, "type": result.error_type}}
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, list):
        return [item.to_dict() if hasattr(item, "to_dict") else item for item in result]
    return result


def handle_request(request: dict) -> dict:
    """Dispatch a request and return a response dict."""
    req_id = request.get("id", "")
    method = request.get("method", "")
    params = request.get("params", {})

    if method not in DISPATCH:
        return {"id": req_id, "error": {"message": f"Unknown method: {method}", "type": "MethodNotFound"}}

    try:
        raw_result = DISPATCH[method](params)
        serialized = _serialize_result(raw_result)
        # If the result itself is an error response dict
        if isinstance(serialized, dict) and serialized.get("error"):
            return {"id": req_id, "error": serialized["error"]}
        return {"id": req_id, "result": serialized}
    except Exception as e:
        return {"id": req_id, "error": {"message": str(e), "type": type(e).__name__}}


def main():
    """Main loop: read requests from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            # Can't recover the ID from malformed JSON — write a generic error
            response = {"id": None, "error": {"message": f"Invalid JSON: {e}", "type": "JSONDecodeError"}}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

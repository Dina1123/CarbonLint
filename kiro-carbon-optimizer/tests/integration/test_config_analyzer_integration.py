"""Integration test: config analyzer on a real temp workspace."""
import os
import tempfile
import pytest
from core.config_analyzer import analyze_configs
from core.models import ConfigIssue


def _write(directory, filename, content, mode="w"):
    path = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8" if mode == "w" else None) as f:
        f.write(content)
    return path


def test_full_workspace_scan_detects_all_planted_issues():
    """Workspace with Dockerfile, GitHub Actions workflow, and vercel.json returns expected issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Dockerfile with multiple issues
        _write(tmpdir, "Dockerfile",
            "FROM node:latest\n"
            "COPY . .\n"
            "RUN npm install\n"
            "CMD [\"node\", \"app.js\"]\n"
        )
        # No .dockerignore (intentional)

        # GitHub Actions with high-frequency cron
        _write(tmpdir, ".github/workflows/ci.yml",
            "on:\n"
            "  schedule:\n"
            "    - cron: '*/5 * * * *'\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - run: echo hello\n"
        )

        # vercel.json without cancelDeployment
        _write(tmpdir, "vercel.json", '{"version": 2}\n')

        issues = analyze_configs(tmpdir)
        issue_ids = {i.issue_id for i in issues}

        assert "unpinned-base-image" in issue_ids
        assert "missing-dockerignore" in issue_ids
        assert "suboptimal-copy-order" in issue_ids
        assert "dev-dependencies-included" in issue_ids
        assert "missing-multistage-build" in issue_ids
        assert "high-frequency-cron" in issue_ids
        assert "always-on-preview" in issue_ids


def test_issues_sorted_high_before_medium_before_low():
    """Issues are returned sorted HIGH > MEDIUM > LOW."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, "Dockerfile",
            "FROM node:latest\n"
            "RUN npm install\n"
            "CMD [\"node\", \"app.js\"]\n"
        )
        _write(tmpdir, "vercel.json", '{"version": 2}\n')

        issues = analyze_configs(tmpdir)
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        scores = [order.get(i.carbon_impact_score, 99) for i in issues]
        assert scores == sorted(scores), f"Issues not sorted: {[(i.issue_id, i.carbon_impact_score) for i in issues]}"


def test_all_issues_have_remediation_and_example_fix():
    """Every issue returned has non-empty remediation and example_fix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, "Dockerfile",
            "FROM node:latest\n"
            "RUN npm install\n"
            "CMD [\"node\", \"app.js\"]\n"
        )
        issues = analyze_configs(tmpdir)
        assert len(issues) > 0
        for issue in issues:
            assert issue.remediation, f"Empty remediation for {issue.issue_id}"
            assert issue.example_fix, f"Empty example_fix for {issue.issue_id}"


def test_empty_workspace_returns_empty_list():
    """Empty workspace returns no issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        issues = analyze_configs(tmpdir)
        assert issues == []


def test_malformed_workflow_does_not_stop_dockerfile_scan():
    """Malformed YAML workflow does not prevent Dockerfile issues from being returned."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, "Dockerfile",
            "FROM node:latest\n"
            "CMD [\"node\", \"app.js\"]\n"
        )
        _write(tmpdir, ".dockerignore", "node_modules\n")
        _write(tmpdir, ".github/workflows/bad.yml", "on: [\nbad: {{\n")

        issues = analyze_configs(tmpdir)
        issue_ids = {i.issue_id for i in issues}
        assert "unpinned-base-image" in issue_ids
